"""Use cases. Every write stores the link change and its event in one transaction."""

from collections.abc import Callable
from datetime import UTC, datetime

from link_service.domain import events
from link_service.domain.errors import (
    InvalidExpirationError,
    LinkNotFoundError,
    SlugAlreadyExistsError,
)
from link_service.domain.models import Link, generate_slug, validate_slug
from link_service.ports.repositories import UnitOfWork

MAX_SLUG_ATTEMPTS = 5


def utcnow() -> datetime:
    return datetime.now(UTC)


class LinkService:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        *,
        clock: Callable[[], datetime] = utcnow,
        slug_generator: Callable[[], str] = generate_slug,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._slug_generator = slug_generator

    async def create(
        self, url: str, slug: str | None = None, expires_at: datetime | None = None
    ) -> Link:
        now = self._clock()
        if expires_at is not None and expires_at <= now:
            raise InvalidExpirationError("expires_at must be in the future")

        async with self._uow_factory() as uow:
            slug = await self._choose_slug(uow, slug)
            link = Link(slug=slug, url=url, created_at=now, expires_at=expires_at)
            await uow.links.add(link)
            await uow.outbox.add(events.link_created(link, occurred_at=now))
            await uow.commit()
        return link

    async def get(self, slug: str) -> Link:
        async with self._uow_factory() as uow:
            link = await uow.links.get(slug)
        if link is None:
            raise LinkNotFoundError(slug)
        return link

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[Link]:
        async with self._uow_factory() as uow:
            return await uow.links.list(limit=limit, offset=offset)

    async def delete(self, slug: str) -> None:
        async with self._uow_factory() as uow:
            if not await uow.links.delete(slug):
                raise LinkNotFoundError(slug)
            await uow.outbox.add(events.link_deleted(slug, occurred_at=self._clock()))
            await uow.commit()

    async def _choose_slug(self, uow: UnitOfWork, requested: str | None) -> str:
        if requested is not None:
            validate_slug(requested)
            if await uow.links.get(requested) is not None:
                raise SlugAlreadyExistsError(requested)
            return requested

        for _ in range(MAX_SLUG_ATTEMPTS):
            candidate = self._slug_generator()
            if await uow.links.get(candidate) is None:
                return candidate
        raise SlugAlreadyExistsError(candidate)
