from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from link_service.adapters.postgres.uow import SqlAlchemyUnitOfWork, create_session_factory
from link_service.api.errors import register_error_handlers
from link_service.api.routes import router
from link_service.config import Settings
from link_service.ports.repositories import UnitOfWork
from link_service.service import LinkService


def create_app(
    settings: Settings | None = None,
    uow_factory: Callable[[], UnitOfWork] | None = None,
) -> FastAPI:
    """Builds the app. Tests pass an in-memory `uow_factory`; otherwise Postgres is used."""
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if uow_factory is not None:
            app.state.link_service = LinkService(uow_factory)
            yield
            return

        engine, session_factory = create_session_factory(settings.database_url)
        app.state.link_service = LinkService(lambda: SqlAlchemyUnitOfWork(session_factory))
        yield
        await engine.dispose()

    app = FastAPI(title="link-service", lifespan=lifespan)
    app.state.settings = settings
    app.include_router(router)
    register_error_handlers(app)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "link-service"}

    return app


app = create_app()
