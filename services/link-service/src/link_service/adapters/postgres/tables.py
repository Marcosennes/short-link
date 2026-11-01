from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Identity, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class LinkRow(Base):
    __tablename__ = "links"

    slug: Mapped[str] = mapped_column(String(32), primary_key=True)
    url: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OutboxRow(Base):
    __tablename__ = "outbox"

    # Monotonic id gives a stable publishing order; created_at can tie within a transaction.
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    event_id: Mapped[UUID] = mapped_column(unique=True)
    topic: Mapped[str] = mapped_column(String(255))
    key: Mapped[str] = mapped_column(String(255))
    event_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_outbox_pending", "id", postgresql_where=text("published_at IS NULL")),
    )
