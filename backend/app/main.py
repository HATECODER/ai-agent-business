"""Commercial API shell with managed identity and tenant authorization."""

from datetime import date
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, File, Query, Request, Response, UploadFile
from pydantic import BaseModel, Field

from backend.app.api_auth import AuthServices, deny_request, require_tenant_authority
from backend.app.authorization import (
    AuthorizationDenied,
    Permission,
    TenantAuthority,
    granted_permissions,
    require_permission,
)
from backend.app.business_facts import (
    BusinessFactsUnavailable,
    database_attention_task_reader,
    database_finance_reader,
    database_inactive_customer_reader,
)
from backend.app.copilot import (
    CopilotAnswer,
    CopilotReader,
    UnsupportedQuestion,
    build_copilot_reader,
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
    database_error_reporter,
    database_import_previewer,
)
from backend.app.malware_scanner import clamd_scanner_from_environment


class WorkspaceSession(BaseModel):
    workspace_id: str
    role: str
    permission_version: int
    permissions: list[str]


class CopilotRequest(BaseModel):
    message: str = Field(min_length=2, max_length=500)


DEMO_REFERENCE_DATE = date(2026, 11, 1)


def _configure_import_services(app: FastAPI) -> bool:
    """Lazily activate preview only when the complete private scanner config exists."""
    scanner = clamd_scanner_from_environment()
    if scanner is None:
        return False
    engine = create_database_engine()
    app.state.import_previewer = database_import_previewer(engine, scanner)
    app.state.import_error_reporter = database_error_reporter(engine)
    return True


def create_app(
    auth_services: AuthServices | None = None,
    inventory_reader: InventoryReader | None = None,
    import_previewer: InventoryImportPreviewer | None = None,
    import_error_reporter: ImportErrorReporter | None = None,
    copilot_reader: CopilotReader | None = None,
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
    app.state.copilot_reader = copilot_reader

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
            try:
                configured = _configure_import_services(request.app)
            except (RuntimeError, ValueError):
                configured = False
            if not configured:
                deny_request(
                    request,
                    "inventory_import_configuration",
                    503,
                    "Import preview unavailable.",
                )
            previewer = request.app.state.import_previewer
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
            try:
                configured = _configure_import_services(request.app)
            except (RuntimeError, ValueError):
                configured = False
            if not configured:
                deny_request(
                    request,
                    "inventory_import_configuration",
                    503,
                    "Import preview unavailable.",
                )
            reporter = request.app.state.import_error_reporter
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

    @app.post("/api/v1/copilot/query", response_model=CopilotAnswer)
    def query_copilot(
        payload: CopilotRequest,
        request: Request,
        authority: TenantAuthority = Depends(require_tenant_authority),
    ) -> CopilotAnswer:
        try:
            require_permission(authority, Permission.COPILOT_USE)
        except AuthorizationDenied:
            deny_request(
                request, "copilot_permission_denied", 403, "Permission denied."
            )
        reader = request.app.state.copilot_reader
        if reader is None:
            try:
                engine = create_database_engine()
                reader = build_copilot_reader(
                    database_inventory_reader(engine),
                    database_finance_reader(engine),
                    database_inactive_customer_reader(engine),
                    database_attention_task_reader(engine),
                )
            except RuntimeError:
                deny_request(
                    request, "copilot_configuration", 503, "Copilot unavailable."
                )
            request.app.state.copilot_reader = reader
        try:
            return reader(authority, payload.message, DEMO_REFERENCE_DATE)
        except AuthorizationDenied:
            deny_request(
                request,
                "copilot_domain_permission_denied",
                403,
                "Permission denied for this question.",
            )
        except UnsupportedQuestion as error:
            deny_request(request, "copilot_question_unsupported", 422, str(error))
        except (BusinessFactsUnavailable, InventoryUnavailable, ValueError):
            deny_request(
                request, "copilot_facts_unavailable", 503, "Source facts unavailable."
            )

    return app


app = create_app()
