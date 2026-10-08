"""Commercial API shell with managed identity and tenant authorization."""

from uuid import uuid4

from fastapi import Depends, FastAPI, Request, Response
from pydantic import BaseModel

from backend.app.api_auth import AuthServices, require_tenant_authority
from backend.app.authorization import Permission, TenantAuthority, require_permission


class WorkspaceSession(BaseModel):
    workspace_id: str
    role: str
    permission_version: int


def create_app(auth_services: AuthServices | None = None) -> FastAPI:
    app = FastAPI(
        title="BizPilot API",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.auth_services = auth_services

    @app.middleware("http")
    async def correlation_id(request: Request, call_next):
        request.state.correlation_id = uuid4().hex
        response: Response = await call_next(request)
        response.headers["X-Correlation-ID"] = request.state.correlation_id
        return response

    @app.get("/health/live", include_in_schema=False)
    def liveness() -> dict[str, str]:
        return {"service": "bizpilot-api", "status": "ok"}

    @app.get("/api/v1/workspace", response_model=WorkspaceSession)
    def current_workspace(
        authority: TenantAuthority = Depends(require_tenant_authority),
    ) -> WorkspaceSession:
        require_permission(authority, Permission.WORKSPACE_READ)
        return WorkspaceSession(
            workspace_id=authority.tenant_id,
            role=authority.role.value,
            permission_version=authority.permission_version,
        )

    return app


app = create_app()
