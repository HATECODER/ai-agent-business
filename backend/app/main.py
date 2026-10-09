"""Commercial API shell with managed identity and tenant authorization."""

from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, File, Query, Request, Response, UploadFile
from pydantic import BaseModel

from backend.app.api_auth import AuthServices, deny_request, require_tenant_authority
from backend.app.authorization import (
    AuthorizationDenied,
    Permission,
    TenantAuthority,
    granted_permissions,
    require_permission,
)
from backend.app.database import create_database_engine
from backend.app.inventory import (
    InventoryPage,
    InventoryReader,
    InventoryUnavailable,
    database_inventory_reader,
)
from backend.app.inventory_import import (
    MAX_FILE_BYTES,
    ImportErrorReporter,
    ImportPreviewUnavailable,
    ImportRejected,
    InventoryImportPreview,
    InventoryImportPreviewer,
)


class WorkspaceSession(BaseModel):
    workspace_id: str
    role: str
    permission_version: int
    permissions: list[str]


def create_app(
    auth_services: AuthServices | None = None,
    inventory_reader: InventoryReader | None = None,
    import_previewer: InventoryImportPreviewer | None = None,
    import_error_reporter: ImportErrorReporter | None = None,
) -> FastAPI:
    app = FastAPI(
        title="BizPilot API",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.auth_services = auth_services
    app.state.inventory_reader = inventory_reader
    app.state.import_previewer = import_previewer
    app.state.import_error_reporter = import_error_reporter

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
            permissions=[
                permission.value for permission in granted_permissions(authority)
            ],
        )

    @app.get("/api/v1/inventory", response_model=InventoryPage)
    def list_inventory(
        request: Request,
        limit: int = Query(default=50, ge=1, le=100),
        after: UUID | None = Query(default=None),
        low_stock_only: bool = Query(default=False),
        authority: TenantAuthority = Depends(require_tenant_authority),
    ) -> InventoryPage:
        try:
            require_permission(authority, Permission.INVENTORY_READ)
        except AuthorizationDenied:
            deny_request(
                request, "inventory_permission_denied", 403, "Permission denied."
            )

        reader = request.app.state.inventory_reader
        if reader is None:
            try:
                reader = database_inventory_reader(create_database_engine())
            except RuntimeError:
                deny_request(
                    request, "inventory_configuration", 503, "Inventory unavailable."
                )
            request.app.state.inventory_reader = reader
        try:
            return reader(authority, limit, after, low_stock_only)
        except InventoryUnavailable:
            deny_request(
                request, "inventory_unavailable", 503, "Inventory unavailable."
            )

    @app.post(
        "/api/v1/inventory/imports/preview",
        response_model=InventoryImportPreview,
    )
    async def preview_inventory_import(
        request: Request,
        file: UploadFile = File(...),
        authority: TenantAuthority = Depends(require_tenant_authority),
    ) -> InventoryImportPreview:
        try:
            require_permission(authority, Permission.INVENTORY_IMPORT)
        except AuthorizationDenied:
            deny_request(
                request, "inventory_import_permission_denied", 403, "Permission denied."
            )
        previewer = request.app.state.import_previewer
        if previewer is None:
            deny_request(
                request,
                "inventory_import_configuration",
                503,
                "Import preview unavailable.",
            )
        try:
            content = await file.read(MAX_FILE_BYTES + 1)
        finally:
            await file.close()
        try:
            return previewer(
                authority, file.filename or "", file.content_type or "", content
            )
        except ImportRejected as error:
            deny_request(request, error.code, 422, error.message)
        except ImportPreviewUnavailable:
            deny_request(
                request,
                "inventory_import_unavailable",
                503,
                "Import preview unavailable.",
            )

    @app.get("/api/v1/inventory/imports/{preview_id}/errors.csv")
    def inventory_import_error_report(
        request: Request,
        preview_id: UUID,
        authority: TenantAuthority = Depends(require_tenant_authority),
    ) -> Response:
        try:
            require_permission(authority, Permission.INVENTORY_IMPORT)
        except AuthorizationDenied:
            deny_request(
                request, "inventory_import_permission_denied", 403, "Permission denied."
            )
        reporter = request.app.state.import_error_reporter
        if reporter is None:
            deny_request(
                request,
                "inventory_import_configuration",
                503,
                "Import preview unavailable.",
            )
        try:
            body = reporter(authority, preview_id)
        except ImportRejected as error:
            deny_request(request, error.code, 404, error.message)
        except ImportPreviewUnavailable:
            deny_request(
                request,
                "inventory_import_unavailable",
                503,
                "Import preview unavailable.",
            )
        return Response(
            content=body,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": 'attachment; filename="inventory-import-errors.csv"'
            },
        )

    return app


app = create_app()
