"""Minimal commercial API shell; business endpoints are added behind authz."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(
        title="BizPilot API",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.get("/health/live", include_in_schema=False)
    def liveness() -> dict[str, str]:
        return {"service": "bizpilot-api", "status": "ok"}

    return app


app = create_app()
