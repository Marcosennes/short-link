"""In-memory fakes of the ports. The fake unit of work mimics a transaction: changes are
staged on a copy and only reach the shared FakeDatabase on commit()."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import UUID

import pytest

from link_service.domain.errors import SlugAlreadyExistsError
from link_service.domain.models import Link, OutboxMessage


@dataclass
class OutboxEntry:
    message: OutboxMessage
    published_at: datetime | None = None


@dataclass
class FakeDatabase:
    links: dict[str, Link] = field(default_factory=dict)
    outbox: list[OutboxEntry] = field(default_factory=list)
    commits: int = 0

    def pending(self) -> list[OutboxMessage]:
        return [e.message for e in self.outbox if e.published_at is None]


class FakeLinkRepository:
    def __init__(self, links: dict[str, Link]) -> None:
        self._links = links

    async def add(self, link: Link) -> None:
        if link.slug in self._links:
            raise SlugAlreadyExistsError(link.slug)
        self._links[link.slug] = link

    async def get(self, slug: str) -> Link | None:
        return self._links.get(slug)

    async def list(self, *, limit: int, offset: int) -> list[Link]:
        ordered = sorted(self._links.values(), key=lambda link: link.created_at, reverse=True)
        return ordered[offset : offset + limit]

    async def delete(self, slug: str) -> bool:
        return self._links.pop(slug, None) is not None


class FakeOutboxRepository:
    def __init__(self, entries: list[OutboxEntry]) -> None:
        self._entries = entries

    async def add(self, message: OutboxMessage) -> None:
        self._entries.append(OutboxEntry(message))

    async def fetch_pending(self, limit: int) -> list[OutboxMessage]:
        return [e.message for e in self._entries if e.published_at is None][:limit]

    async def mark_published(self, event_ids: Sequence[UUID], published_at: datetime) -> None:
        for entry in self._entries:
            if entry.message.event_id in event_ids:
                entry.published_at = published_at


class FakeUnitOfWork:
    def __init__(self, db: FakeDatabase) -> None:
        self._db = db

    async def __aenter__(self) -> Self:
        self._links = dict(self._db.links)
        self._outbox = [replace(entry) for entry in self._db.outbox]
        self.links = FakeLinkRepository(self._links)
        self.outbox = FakeOutboxRepository(self._outbox)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        pass  # uncommitted staged changes are simply dropped

    async def commit(self) -> None:
        self._db.links = dict(self._links)
        self._db.outbox = [replace(entry) for entry in self._outbox]
        self._db.commits += 1


class FakePublisher:
    def __init__(self, fail_after: int | None = None) -> None:
        self.sent: list[tuple[str, bytes, bytes]] = []
        self._fail_after = fail_after

    async def publish(self, topic: str, key: bytes, value: bytes) -> None:
        if self._fail_after is not None and len(self.sent) >= self._fail_after:
            raise ConnectionError("broker unavailable")
        self.sent.append((topic, key, value))


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def db() -> FakeDatabase:
    return FakeDatabase()


@pytest.fixture
def uow_factory(db: FakeDatabase) -> Callable[[], FakeUnitOfWork]:
    return lambda: FakeUnitOfWork(db)


@pytest.fixture
def fake_publisher() -> type[FakePublisher]:
    return FakePublisher
