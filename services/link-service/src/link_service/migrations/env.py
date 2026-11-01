import asyncio

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from link_service.adapters.postgres.tables import Base

target_metadata = Base.metadata


def _run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    engine = create_async_engine(context.config.get_main_option("sqlalchemy.url"))
    async with engine.connect() as connection:
        await connection.run_sync(_run)
    await engine.dispose()


asyncio.run(_run_async())
