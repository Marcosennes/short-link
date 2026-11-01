from datetime import timedelta

import pytest

from link_service.domain.errors import (
    InvalidExpirationError,
    InvalidSlugError,
    LinkNotFoundError,
    SlugAlreadyExistsError,
)
from link_service.service import MAX_SLUG_ATTEMPTS, LinkService


@pytest.fixture
def service(uow_factory, now):
    return LinkService(uow_factory, clock=lambda: now)


async def test_create_stores_link_and_outbox_event_in_one_commit(service, db, now):
    link = await service.create("https://example.com", slug="exa")

    assert db.links == {"exa": link}
    assert link.created_at == now
    assert db.commits == 1
    [message] = db.pending()
    assert message.event_type == "link.created"
    assert message.key == "exa"
    assert message.payload["payload"]["url"] == "https://example.com/"


async def test_create_generates_slug_when_missing(uow_factory, db):
    service = LinkService(uow_factory, slug_generator=lambda: "gen1234")

    link = await service.create("https://example.com")

    assert link.slug == "gen1234"
    assert "gen1234" in db.links


async def test_create_retries_generated_slug_on_collision(uow_factory, db):
    slugs = iter(["taken", "taken", "free1"])
    service = LinkService(uow_factory, slug_generator=lambda: next(slugs))
    await LinkService(uow_factory).create("https://a.com", slug="taken")

    link = await service.create("https://b.com")

    assert link.slug == "free1"


async def test_create_gives_up_after_max_slug_attempts(uow_factory):
    service = LinkService(uow_factory, slug_generator=lambda: "taken")
    await service.create("https://a.com", slug="taken")

    with pytest.raises(SlugAlreadyExistsError):
        await service.create("https://b.com")
    assert MAX_SLUG_ATTEMPTS > 1


async def test_create_rejects_duplicate_slug_without_writing(service, db):
    await service.create("https://a.com", slug="dup")

    with pytest.raises(SlugAlreadyExistsError):
        await service.create("https://b.com", slug="dup")

    assert db.links["dup"].url == "https://a.com"
    assert len(db.outbox) == 1


async def test_create_rejects_invalid_slug(service, db):
    with pytest.raises(InvalidSlugError):
        await service.create("https://a.com", slug="no spaces")
    assert db.commits == 0


@pytest.mark.parametrize("delta", [timedelta(0), timedelta(seconds=-1)])
async def test_create_rejects_expiration_not_in_future(service, now, delta):
    with pytest.raises(InvalidExpirationError):
        await service.create("https://a.com", expires_at=now + delta)


async def test_create_accepts_future_expiration(service, db, now):
    link = await service.create("https://a.com", slug="tmp", expires_at=now + timedelta(days=1))

    assert link.expires_at == now + timedelta(days=1)
    assert db.pending()[0].payload["payload"]["expires_at"] is not None


async def test_nothing_is_persisted_when_the_outbox_write_fails(uow_factory, db):
    """Atomicity: the link must not exist without its event (and vice versa)."""

    class OutboxFailsUnitOfWork:
        """Real fake transaction, but writing to the outbox blows up."""

        def __init__(self):
            self._inner = uow_factory()

        async def __aenter__(self):
            await self._inner.__aenter__()
            self.links = self._inner.links
            self.outbox = self
            return self

        async def __aexit__(self, *exc_info):
            await self._inner.__aexit__(*exc_info)

        async def add(self, message):
            raise RuntimeError("disk full")

        async def commit(self):
            await self._inner.commit()

    with pytest.raises(RuntimeError):
        await LinkService(OutboxFailsUnitOfWork).create("https://a.com", slug="lost")

    assert db.links == {}
    assert db.outbox == []


async def test_get_returns_link(service):
    created = await service.create("https://a.com", slug="get-me")

    assert await service.get("get-me") == created


async def test_get_missing_link_raises(service):
    with pytest.raises(LinkNotFoundError):
        await service.get("nope")


async def test_list_returns_newest_first_with_pagination(uow_factory, now):
    for i in range(3):
        moment = now + timedelta(minutes=i)
        await LinkService(uow_factory, clock=lambda m=moment: m).create(
            "https://a.com", slug=f"link{i}"
        )
    service = LinkService(uow_factory)

    assert [link.slug for link in await service.list()] == ["link2", "link1", "link0"]
    assert [link.slug for link in await service.list(limit=1, offset=1)] == ["link1"]


async def test_delete_removes_link_and_records_event(service, db):
    await service.create("https://a.com", slug="bye")

    await service.delete("bye")

    assert "bye" not in db.links
    assert [m.event_type for m in db.pending()] == ["link.created", "link.deleted"]


async def test_delete_missing_link_raises_without_event(service, db):
    with pytest.raises(LinkNotFoundError):
        await service.delete("ghost")
    assert db.outbox == []
