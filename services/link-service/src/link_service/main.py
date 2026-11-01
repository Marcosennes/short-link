from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="link-service")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "link-service"}

    return app


app = create_app()
