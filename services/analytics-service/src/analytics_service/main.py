from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="analytics-service")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "analytics-service"}

    return app


app = create_app()
