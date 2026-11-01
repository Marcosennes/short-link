from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="redirect-service")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "redirect-service"}

    return app


app = create_app()
