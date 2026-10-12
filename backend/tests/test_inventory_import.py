from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

import backend.app.main as main_module
from backend.app.api_auth import AuthServices
from backend.app.authorization import MerchantRole, TenantAuthority
from backend.app.identity import VerifiedIdentity
from backend.app.inventory_import import (
    MAX_FILE_BYTES,
    ImportPreviewCounts,
    ImportRejected,
    InventoryImportPreview,
    database_import_previewer,
    purge_expired_import_metadata,
    validate_inventory_csv,
)
from backend.app.main import create_app

TENANT_ID = "10000000-0000-0000-0000-000000000001"
PREVIEW_ID = UUID("10000000-0000-0000-0000-000000000099")
CSV_HEADER = (
    "product_name,variant_name,sku,location_code,location_name,quantity,"
    "low_stock_threshold,variant_options,base_price_bdt,expected_record_version\n"
)


class Verifier:
    def verify(self, _token):
        now = datetime.now(timezone.utc)
        return VerifiedIdentity("https://identity.example", "subject", now, now)


def authority(role=MerchantRole.OWNER):
    return TenantAuthority(
        identity_id="10000000-0000-0000-0000-000000000002",
        membership_id="10000000-0000-0000-0000-000000000003",
        tenant_id=TENANT_ID,
        role=role,
        permission_version=1,
    )


def api_client(role=MerchantRole.OWNER, previewer=None, reporter=None):
    services = AuthServices(Verifier(), lambda _identity, _tenant: authority(role))
    return TestClient(create_app(services, None, previewer, reporter))


def auth_headers():
    return {"Authorization": "Bearer test-token", "X-BizPilot-Tenant": TENANT_ID}


def test_csv_validation_normalizes_valid_rows_and_rejects_formulas():
    content = (
        CSV_HEADER
        + 'Shirt,Blue M,SKU-1,DHAKA,Main,7,3,"{""color"":""Blue""}",1250.50,2\n'
        + "=CMD,Red L,SKU-2,DHAKA,Main,4,2,,,\n"
    ).encode()
    filename, parsed = validate_inventory_csv(
        "incoming.csv", "text/csv; charset=utf-8", content
    )

    assert filename == "incoming.csv"
    assert parsed.total_rows == 2
    assert len(parsed.rows) == 1
    assert parsed.rows[0].base_price_minor == 125050
    assert parsed.rows[0].variant_options == {"color": "Blue"}
    assert (
        parsed.errors[0].message == "product_name cannot contain a spreadsheet formula."
    )
    assert "=CMD" not in parsed.errors[0].message


@pytest.mark.parametrize(
    ("filename", "content_type", "content", "code"),
    [
        ("inventory.xlsx", "text/csv", b"x", "invalid_file"),
        ("inventory.csv", "application/octet-stream", b"x", "invalid_content_type"),
        ("inventory.csv", "text/csv", b"\xff", "invalid_encoding"),
        ("inventory.csv", "text/csv", b"x" * (MAX_FILE_BYTES + 1), "invalid_file_size"),
        ("inventory.csv", "text/csv", b"product_name\n", "invalid_header"),
    ],
    ids=("extension", "mime", "encoding", "size", "header"),
)
def test_csv_validation_rejects_unsafe_file_boundaries(
    filename, content_type, content, code
):
    with pytest.raises(ImportRejected) as raised:
        validate_inventory_csv(filename, content_type, content)
    assert raised.value.code == code


def test_scanner_rejection_happens_before_parse_or_database_access():
    def reject(_content):
        raise ImportRejected("malware_detected", "The uploaded file was rejected.")

    previewer = database_import_previewer(object(), reject)
    with pytest.raises(ImportRejected) as raised:
        previewer(authority(), "inventory.csv", "text/csv", b"not even csv")
    assert raised.value.code == "malware_detected"


class RecordingPreviewer:
    def __init__(self):
        self.calls = []

    def __call__(self, tenant_authority, filename, content_type, content):
        self.calls.append((tenant_authority, filename, content_type, content))
        return InventoryImportPreview(
            preview_id=PREVIEW_ID,
            status="ready",
            filename="inventory.csv",
            expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
            counts=ImportPreviewCounts(
                total=1, valid=1, errors=0, new=1, changes=0, conflicts=0, unchanged=0
            ),
            errors=[],
            error_report_available=False,
        )


def test_preview_endpoint_requires_permission_and_never_enables_apply():
    previewer = RecordingPreviewer()
    files = {"file": ("inventory.csv", CSV_HEADER.encode(), "text/csv")}

    denied = api_client(MerchantRole.VIEWER, previewer).post(
        "/api/v1/inventory/imports/preview", headers=auth_headers(), files=files
    )
    assert denied.status_code == 403
    assert previewer.calls == []

    allowed = api_client(MerchantRole.OPERATIONS, previewer).post(
        "/api/v1/inventory/imports/preview", headers=auth_headers(), files=files
    )
    assert allowed.status_code == 200
    assert allowed.json()["apply_enabled"] is False
    assert len(previewer.calls) == 1


def test_preview_and_error_report_fail_closed_without_configured_services():
    files = {"file": ("inventory.csv", CSV_HEADER.encode(), "text/csv")}
    response = api_client().post(
        "/api/v1/inventory/imports/preview", headers=auth_headers(), files=files
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Import preview unavailable."}

    response = api_client().get(
        f"/api/v1/inventory/imports/{PREVIEW_ID}/errors.csv", headers=auth_headers()
    )
    assert response.status_code == 503


def test_preview_runtime_wiring_requires_explicit_complete_environment(monkeypatch):
    monkeypatch.setenv("BIZPILOT_IMPORT_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("BIZPILOT_CLAMAV_HOST", "clamav.internal")
    previewer = RecordingPreviewer()
    engine = object()
    monkeypatch.setattr(main_module, "create_database_engine", lambda: engine)
    monkeypatch.setattr(
        main_module,
        "database_import_previewer",
        lambda configured_engine, _scanner: (
            previewer if configured_engine is engine else None
        ),
    )
    monkeypatch.setattr(
        main_module,
        "database_error_reporter",
        lambda configured_engine: (
            (lambda *_args: b"row_number,message\n")
            if configured_engine is engine
            else None
        ),
    )
    files = {"file": ("inventory.csv", CSV_HEADER.encode(), "text/csv")}

    response = api_client().post(
        "/api/v1/inventory/imports/preview", headers=auth_headers(), files=files
    )

    assert response.status_code == 200
    assert len(previewer.calls) == 1


def test_error_report_uses_fixed_safe_download_name():
    response = api_client(
        reporter=lambda _authority, _preview: b"row_number,message\n"
    ).get(f"/api/v1/inventory/imports/{PREVIEW_ID}/errors.csv", headers=auth_headers())
    assert response.status_code == 200
    assert response.headers["content-disposition"] == (
        'attachment; filename="inventory-import-errors.csv"'
    )
    assert response.content == b"row_number,message\n"

    denied = api_client(MerchantRole.VIEWER, reporter=lambda *_args: b"private").get(
        f"/api/v1/inventory/imports/{PREVIEW_ID}/errors.csv", headers=auth_headers()
    )
    assert denied.status_code == 403
    assert denied.content != b"private"


def test_expired_preview_cleanup_uses_database_time_and_returns_count():
    class Result:
        rowcount = 3

    class Connection:
        def __init__(self):
            self.statement = ""

        def execute(self, statement):
            self.statement = str(statement)
            return Result()

    class Transaction:
        def __init__(self, connection):
            self.connection = connection

        def __enter__(self):
            return self.connection

        def __exit__(self, *_args):
            return False

    class Engine:
        def __init__(self):
            self.connection = Connection()

        def begin(self):
            return Transaction(self.connection)

    engine = Engine()
    assert purge_expired_import_metadata(engine) == 3
    assert "expires_at <= CURRENT_TIMESTAMP" in engine.connection.statement
