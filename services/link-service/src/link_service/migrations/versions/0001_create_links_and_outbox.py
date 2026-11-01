"""create links and outbox tables

Revision ID: 0001
Revises:
Create Date: 2026-10-30
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "links",
        sa.Column("slug", sa.String(32), primary_key=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "outbox",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("event_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Partial index: the relay only ever scans pending rows, which stay few.
    op.create_index(
        "ix_outbox_pending", "outbox", ["id"], postgresql_where=sa.text("published_at IS NULL")
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_pending", table_name="outbox")
    op.drop_table("outbox")
    op.drop_table("links")
