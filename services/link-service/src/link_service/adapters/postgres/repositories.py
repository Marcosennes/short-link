from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from link_service.adapters.postgres.tables import LinkRow, OutboxRow
from link_service.domain.errors import SlugAlreadyExistsError
from link_service.domain.models import Link, OutboxMessage


def _to_link(row: LinkRow) -> Link:
    return Link(slug=row.slug, url=row.url, created_at=row.created_at, expires_at=row.expires_at)


class SqlLinkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, link: Link) -> None:
        self._session.add(
            LinkRow(
                slug=link.slug,
                url=link.url,
                created_at=link.created_at,
                expires_at=link.expires_at,
            )
        )
        try:
            await self._session.flush()
        except IntegrityError as error:
            # A concurrent request took the slug between our check and this insert.
            raise SlugAlreadyExistsError(link.slug) from error

    async def get(self, slug: str) -> Link | None:
        row = await self._session.get(LinkRow, slug)
        return _to_link(row) if row else None

    async def list(self, *, limit: int, offset: int) -> list[Link]:
        stmt = (
            select(LinkRow)
            .order_by(LinkRow.created_at.desc(), LinkRow.slug)
            .limit(limit)
            .offset(offset)
        )
        return [_to_link(row) for row in await self._session.scalars(stmt)]

    async def delete(self, slug: str) -> bool:
        result = await self._session.execute(delete(LinkRow).where(LinkRow.slug == slug))
        return result.rowcount > 0


class SqlOutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, message: OutboxMessage) -> None:
        self._session.add(
            OutboxRow(
                event_id=message.event_id,
                topic=message.topic,
                key=message.key,
                event_type=message.event_type,
                payload=message.payload,
                created_at=message.created_at,
            )
        )

    async def fetch_pending(self, limit: int) -> list[OutboxMessage]:
        stmt = (
            select(OutboxRow)
            .where(OutboxRow.published_at.is_(None))
            .order_by(OutboxRow.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return [
            OutboxMessage(
                event_id=row.event_id,
                topic=row.topic,
                key=row.key,
                event_type=row.event_type,
                payload=row.payload,
                created_at=row.created_at,
            )
            for row in await self._session.scalars(stmt)
        ]

    async def mark_published(self, event_ids: Sequence[UUID], published_at: datetime) -> None:
        await self._session.execute(
            update(OutboxRow)
            .where(OutboxRow.event_id.in_(event_ids))
            .values(published_at=published_at)
        )
