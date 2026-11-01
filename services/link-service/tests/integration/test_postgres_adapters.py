"""Runs the Postgres adapters against a real database.

    docker compose up -d postgres
    LINK_TEST_DATABASE_URL=postgresql+asyncpg://shortlink:shortlink@localhost:15432/links \
        uv run pytest services/link-service/tests/integration
"""

import asyncio
import os
from datetime import UTC, datetime

import pytest
from alembic import command
from sqlalchemy import text

from link_service.adapters.postgres.uow import SqlAlchemyUnitOfWork, create_session_factory
from link_service.domain.errors import SlugAlreadyExistsError
from link_service.domain.models import Link
from link_service.migrate import alembic_config
from link_service.service import LinkService

DATABASE_URL = os.environ.get("LINK_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DATABASE_URL, reason="LINK_TEST_DATABASE_URL not set"),
]


@pytest.fixture(scope="module")
def migrated():
    command.upgrade(alembic_config(DATABASE_URL), "head")


@pytest.fixture
async def session_factory(migrated):
    engine, factory = create_session_factory(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE links, outbox"))
    yield factory
    await engine.dispose()


@pytest.fixture
def uow_factory(session_factory):
    return lambda: SqlAlchemyUnitOfWork(session_factory)


async def test_create_writes_link_and_outbox_row(uow_factory):
    service = LinkService(uow_factory)

    link = await service.create("https://example.com", slug="int-1")

    assert await service.get("int-1") == link
    async with uow_factory() as uow:
        [message] = await uow.outbox.fetch_pending(10)
    assert message.event_type == "link.created"
    assert message.payload["payload"]["slug"] == "int-1"


async def test_duplicate_insert_maps_to_domain_error(uow_factory):
    await LinkService(uow_factory).create("https://example.com", slug="int-dup")
    now = datetime.now(UTC)

    async with uow_factory() as uow:
        with pytest.raises(SlugAlreadyExistsError):
            await uow.links.add(Link(slug="int-dup", url="https://x.com", created_at=now))


async def test_list_and_delete(uow_factory):
    service = LinkService(uow_factory)
    await service.create("https://a.com", slug="int-a")
    await service.create("https://b.com", slug="int-b")

    assert [link.slug for link in await service.list()] == ["int-b", "int-a"]
    await service.delete("int-a")
    assert [link.slug for link in await service.list()] == ["int-b"]


async def test_skip_locked_lets_concurrent_relays_split_the_work(uow_factory):
    service = LinkService(uow_factory)
    for i in range(4):
        await service.create("https://a.com", slug=f"int-lock-{i}")

    async with uow_factory() as first:
        claimed_first = await first.outbox.fetch_pending(2)
        # A second relay running at the same time must skip the rows locked above.
        async with uow_factory() as second:
            claimed_second = await asyncio.wait_for(second.outbox.fetch_pending(10), timeout=2)

    first_ids = {m.event_id for m in claimed_first}
    second_ids = {m.event_id for m in claimed_second}
    assert len(first_ids) == 2
    assert len(second_ids) == 2
    assert first_ids.isdisjoint(second_ids)


async def test_mark_published_removes_rows_from_pending(uow_factory):
    await LinkService(uow_factory).create("https://a.com", slug="int-pub")

    async with uow_factory() as uow:
        [message] = await uow.outbox.fetch_pending(10)
        await uow.outbox.mark_published([message.event_id], datetime.now(UTC))
        await uow.commit()

    async with uow_factory() as uow:
        assert await uow.outbox.fetch_pending(10) == []
