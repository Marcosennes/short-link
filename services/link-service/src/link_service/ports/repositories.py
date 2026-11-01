from collections.abc import Sequence
from datetime import datetime
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from link_service.domain.models import Link, OutboxMessage


class LinkRepository(Protocol):
    async def add(self, link: Link) -> None:
        """Raises SlugAlreadyExistsError if the slug is taken."""
        ...

    async def get(self, slug: str) -> Link | None: ...

    async def list(self, *, limit: int, offset: int) -> list[Link]: ...

    async def delete(self, slug: str) -> bool:
        """Removes the link; returns False when it did not exist."""
        ...


class OutboxRepository(Protocol):
    async def add(self, message: OutboxMessage) -> None: ...

    async def fetch_pending(self, limit: int) -> list[OutboxMessage]:
        """Returns unpublished messages in insertion order, locking them for this
        transaction (rows locked by another relay are skipped)."""
        ...

    async def mark_published(self, event_ids: Sequence[UUID], published_at: datetime) -> None: ...


class UnitOfWork(Protocol):
    """One database transaction. Leaving the context without `commit()` rolls back."""

    links: LinkRepository
    outbox: OutboxRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...
