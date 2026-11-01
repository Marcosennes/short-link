"""Applies database migrations: `python -m link_service.migrate` (one-shot container)."""

from alembic import command
from alembic.config import Config

from link_service.config import Settings


def alembic_config(database_url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", "link_service:migrations")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


if __name__ == "__main__":  # pragma: no cover
    command.upgrade(alembic_config(Settings().database_url), "head")
