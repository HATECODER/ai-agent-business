"""Strict, preview-only inventory CSV ingestion.

The raw file is scanned and validated in memory, then discarded. Only bounded,
tenant-scoped preview metadata and controlled error messages are persisted.
This module deliberately has no inventory write/apply operation.
"""

import csv
import io
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import PurePath
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from backend.app.authorization import TenantAuthority
from backend.app.database import tenant_transaction


MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_ROWS = 10_000
MAX_ERRORS = 200
PREVIEW_TTL_HOURS = 24
ALLOWED_CONTENT_TYPES = frozenset({"text/csv", "application/csv"})
REQUIRED_HEADERS = (
    "product_name",
    "variant_name",
    "sku",
    "location_code",
    "location_name",
    "quantity",
    "low_stock_threshold",
)
OPTIONAL_HEADERS = ("variant_options", "base_price_bdt", "expected_record_version")
ALLOWED_HEADERS = frozenset((*REQUIRED_HEADERS, *OPTIONAL_HEADERS))


class ImportRejected(ValueError):
    """A controlled validation rejection safe to show to the caller."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class ImportPreviewUnavailable(RuntimeError):
    """Preview infrastructure failed without exposing implementation details."""


class MalwareScanner(Protocol):
    def __call__(self, content: bytes) -> None:
        """Raise ImportRejected or ImportPreviewUnavailable unless content is clean."""


class ImportErrorItem(BaseModel):
    row_number: int = Field(ge=1)
    column: str = Field(max_length=64)
    code: str = Field(max_length=64)
    message: str = Field(max_length=240)


class ImportPreviewCounts(BaseModel):
    total: int = Field(ge=0)
    valid: int = Field(ge=0)
    errors: int = Field(ge=0)
    new: int = Field(ge=0)
    changes: int = Field(ge=0)
    conflicts: int = Field(ge=0)
    unchanged: int = Field(ge=0)


class InventoryImportPreview(BaseModel):
    preview_id: UUID
    status: str
    filename: str
    expires_at: datetime
    counts: ImportPreviewCounts
    errors: list[ImportErrorItem]
    error_report_available: bool
    errors_truncated: bool = False
    apply_enabled: bool = False


@dataclass(frozen=True)
class NormalizedRow:
    row_number: int
    product_name: str
    variant_name: str
    sku: str
    location_code: str
    location_name: str
    quantity: int
    low_stock_threshold: int
    variant_options: dict[str, str]
    base_price_minor: int | None
    expected_record_version: int | None


@dataclass(frozen=True)
class ParsedInventoryCsv:
    total_rows: int
    rows: list[NormalizedRow]
    errors: list[ImportErrorItem]


InventoryImportPreviewer = Callable[
    [TenantAuthority, str, str, bytes], InventoryImportPreview
]
ImportErrorReporter = Callable[[TenantAuthority, UUID], bytes]


def _safe_filename(filename: str) -> str:
    name = PurePath(filename.replace("\\", "/")).name.strip()
    if (
        not name
        or name.lower() == ".csv"
        or len(name) > 200
        or not name.lower().endswith(".csv")
        or name[0] in "=+-@"
        or any(character in name for character in "\x00\r\n\t")
    ):
        raise ImportRejected(
            "invalid_file", "Upload a .csv file with a valid filename."
        )
    return name


def _clean_text(value: str | None, column: str, maximum: int) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValueError(f"{column} is required.")
    if len(cleaned) > maximum:
        raise ValueError(f"{column} is too long.")
    if cleaned[0] in "=+-@" or cleaned[0] in "\t\r":
        raise ValueError(f"{column} cannot contain a spreadsheet formula.")
    return cleaned


def _whole_number(value: str | None, column: str, *, minimum: int = 0) -> int:
    raw = (value or "").strip()
    try:
        parsed = int(raw)
    except ValueError as error:
        raise ValueError(f"{column} must be a whole number.") from error
    if str(parsed) != raw:
        raise ValueError(f"{column} must be a whole number.")
    if parsed < minimum or parsed > 9_000_000_000_000:
        raise ValueError(f"{column} is outside the allowed range.")
    return parsed


def _optional_version(value: str | None) -> int | None:
    if not (value or "").strip():
        return None
    return _whole_number(value, "expected_record_version", minimum=1)


def _price_minor(value: str | None) -> int | None:
    raw = (value or "").strip()
    if not raw:
        return None
    if re.fullmatch(r"\d+(?:\.\d{1,2})?", raw) is None:
        raise ValueError("base_price_bdt must be a valid BDT amount.")
    try:
        amount = Decimal(raw)
    except InvalidOperation as error:
        raise ValueError("base_price_bdt must be a valid BDT amount.") from error
    if not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -2:
        raise ValueError("base_price_bdt must be non-negative with at most 2 decimals.")
    minor = int(amount * 100)
    if minor > 9_000_000_000_000:
        raise ValueError("base_price_bdt is outside the allowed range.")
    return minor


def _options(value: str | None) -> dict[str, str]:
    raw = (value or "").strip()
    if not raw:
        return {}
    if len(raw) > 2_000:
        raise ValueError("variant_options is too long.")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("variant_options must be a JSON object.") from error
    if not isinstance(parsed, dict) or len(parsed) > 20:
        raise ValueError(
            "variant_options must be a JSON object with at most 20 entries."
        )
    result: dict[str, str] = {}
    for key, item in parsed.items():
        if not isinstance(key, str) or not isinstance(item, str):
            raise TypeError("variant_options keys and values must be text.")
        result[_clean_text(key, "variant_options key", 100)] = _clean_text(
            item, "variant_options value", 100
        )
    return result


def validate_inventory_csv(
    filename: str,
    content_type: str,
    content: bytes,
) -> tuple[str, ParsedInventoryCsv]:
    safe_name = _safe_filename(filename)
    normalized_type = content_type.split(";", 1)[0].strip().lower()
    if normalized_type not in ALLOWED_CONTENT_TYPES:
        raise ImportRejected(
            "invalid_content_type", "The file must use the CSV content type."
        )
    if not content or len(content) > MAX_FILE_BYTES:
        raise ImportRejected(
            "invalid_file_size", "CSV files must be between 1 byte and 5 MB."
        )
    if b"\x00" in content:
        raise ImportRejected("invalid_encoding", "The CSV must be plain UTF-8 text.")
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ImportRejected(
            "invalid_encoding", "The CSV must be valid UTF-8 text."
        ) from error

    try:
        reader = csv.DictReader(io.StringIO(decoded, newline=""), strict=True)
        headers = reader.fieldnames
        if headers is None:
            raise ImportRejected("missing_header", "The CSV header is required.")
        if len(headers) != len(set(headers)):
            raise ImportRejected("duplicate_header", "CSV header names must be unique.")
        missing = sorted(set(REQUIRED_HEADERS) - set(headers))
        unknown = sorted(set(headers) - ALLOWED_HEADERS)
        if missing or unknown:
            raise ImportRejected(
                "invalid_header",
                "CSV headers do not match the inventory import template.",
            )

        rows: list[NormalizedRow] = []
        errors: list[ImportErrorItem] = []
        seen: set[tuple[str, str]] = set()
        total = 0
        for row_number, raw in enumerate(reader, start=2):
            if raw.get(None):
                raise ImportRejected(
                    "invalid_columns", "A CSV row has too many columns."
                )
            if not any((value or "").strip() for value in raw.values()):
                continue
            total += 1
            if total > MAX_ROWS:
                raise ImportRejected(
                    "row_limit", "CSV files may contain at most 10,000 data rows."
                )
            try:
                row = NormalizedRow(
                    row_number=row_number,
                    product_name=_clean_text(
                        raw.get("product_name"), "product_name", 200
                    ),
                    variant_name=_clean_text(
                        raw.get("variant_name"), "variant_name", 200
                    ),
                    sku=_clean_text(raw.get("sku"), "sku", 120),
                    location_code=_clean_text(
                        raw.get("location_code"), "location_code", 64
                    ),
                    location_name=_clean_text(
                        raw.get("location_name"), "location_name", 160
                    ),
                    quantity=_whole_number(raw.get("quantity"), "quantity"),
                    low_stock_threshold=_whole_number(
                        raw.get("low_stock_threshold"), "low_stock_threshold"
                    ),
                    variant_options=_options(raw.get("variant_options")),
                    base_price_minor=_price_minor(raw.get("base_price_bdt")),
                    expected_record_version=_optional_version(
                        raw.get("expected_record_version")
                    ),
                )
                key = (row.sku, row.location_code)
                if key in seen:
                    raise ValueError(
                        "sku and location_code must be unique within the file."
                    )
                seen.add(key)
                rows.append(row)
            except (TypeError, ValueError) as error:
                if len(errors) < MAX_ERRORS:
                    errors.append(
                        ImportErrorItem(
                            row_number=row_number,
                            column="row",
                            code="invalid_row",
                            message=str(error),
                        )
                    )
    except csv.Error as error:
        raise ImportRejected("invalid_csv", "The CSV structure is invalid.") from error
    if total == 0:
        raise ImportRejected("empty_csv", "The CSV must contain at least one data row.")
    return safe_name, ParsedInventoryCsv(total, rows, errors)


def _classify(row: NormalizedRow, current: dict | None) -> str:
    if current is None:
        return "new"
    if (
        row.expected_record_version is not None
        and row.expected_record_version != current["record_version"]
    ):
        return "conflict"
    comparable = (
        row.product_name,
        row.variant_name,
        row.location_name,
        row.quantity,
        row.low_stock_threshold,
        row.variant_options,
        row.base_price_minor,
    )
    existing = (
        current["product_name"],
        current["variant_name"],
        current["location_name"],
        current["quantity"],
        current["low_stock_threshold"],
        current["variant_options"],
        current["base_price_minor"],
    )
    return "unchanged" if comparable == existing else "change"


def database_import_previewer(
    engine: Engine, scanner: MalwareScanner
) -> InventoryImportPreviewer:
    def preview(
        authority: TenantAuthority,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> InventoryImportPreview:
        scanner(content)
        safe_name, parsed = validate_inventory_csv(filename, content_type, content)
        preview_id = uuid4()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=PREVIEW_TTL_HOURS)
        requested = json.dumps(
            [
                {"sku": row.sku, "location_code": row.location_code}
                for row in parsed.rows
            ]
        )
        try:
            with tenant_transaction(engine, authority) as connection:
                existing_rows = (
                    connection.execute(
                        text("""
                        WITH requested AS (
                            SELECT * FROM jsonb_to_recordset(CAST(:requested AS jsonb))
                            AS item(sku text, location_code text)
                        )
                        SELECT variant.sku, location.code AS location_code,
                               product.name AS product_name, variant.name AS variant_name,
                               location.name AS location_name, balance.quantity,
                               balance.low_stock_threshold, variant.options AS variant_options,
                               variant.base_price_minor, balance.record_version
                        FROM requested
                        JOIN product_variants AS variant ON variant.sku = requested.sku
                        JOIN products AS product
                          ON product.tenant_id = variant.tenant_id
                         AND product.id = variant.product_id
                        JOIN inventory_balances AS balance
                          ON balance.tenant_id = variant.tenant_id
                         AND balance.variant_id = variant.id
                        JOIN locations AS location
                          ON location.tenant_id = balance.tenant_id
                         AND location.id = balance.location_id
                         AND location.code = requested.location_code
                        WHERE variant.tenant_id = :tenant_id
                    """),
                        {
                            "requested": requested,
                            "tenant_id": UUID(authority.tenant_id),
                        },
                    )
                    .mappings()
                    .all()
                )
                current = {
                    (item["sku"], item["location_code"]): dict(item)
                    for item in existing_rows
                }
                categories = {"new": 0, "change": 0, "conflict": 0, "unchanged": 0}
                for row in parsed.rows:
                    categories[
                        _classify(row, current.get((row.sku, row.location_code)))
                    ] += 1
                error_rows = parsed.total_rows - len(parsed.rows)
                status = (
                    "needs_correction"
                    if error_rows
                    else "requires_review"
                    if categories["conflict"]
                    else "ready"
                )
                connection.execute(
                    text("""
                        INSERT INTO inventory_import_previews
                            (id, tenant_id, membership_id, original_filename,
                             content_sha256, byte_size, status, total_rows, valid_rows,
                             error_rows, new_rows, change_rows, conflict_rows,
                             unchanged_rows, expires_at)
                        VALUES
                            (:id, :tenant_id, :membership_id, :filename, :digest,
                             :byte_size, :status, :total, :valid, :errors, :new,
                             :changes, :conflicts, :unchanged, :expires_at)
                    """),
                    {
                        "id": preview_id,
                        "tenant_id": UUID(authority.tenant_id),
                        "membership_id": UUID(authority.membership_id),
                        "filename": safe_name,
                        "digest": sha256(content).hexdigest(),
                        "byte_size": len(content),
                        "status": status,
                        "total": parsed.total_rows,
                        "valid": len(parsed.rows),
                        "errors": error_rows,
                        "new": categories["new"],
                        "changes": categories["change"],
                        "conflicts": categories["conflict"],
                        "unchanged": categories["unchanged"],
                        "expires_at": expires_at,
                    },
                )
                if parsed.errors:
                    connection.execute(
                        text("""
                            INSERT INTO inventory_import_errors
                                (id, tenant_id, preview_id, row_number, column_name,
                                 error_code, message)
                            VALUES
                                (:id, :tenant_id, :preview_id, :row_number,
                                 :column_name, :error_code, :message)
                        """),
                        [
                            {
                                "id": uuid4(),
                                "tenant_id": UUID(authority.tenant_id),
                                "preview_id": preview_id,
                                "row_number": item.row_number,
                                "column_name": item.column,
                                "error_code": item.code,
                                "message": item.message,
                            }
                            for item in parsed.errors
                        ],
                    )
        except SQLAlchemyError as error:
            raise ImportPreviewUnavailable("Import preview failed.") from error

        counts = ImportPreviewCounts(
            total=parsed.total_rows,
            valid=len(parsed.rows),
            errors=parsed.total_rows - len(parsed.rows),
            new=categories["new"],
            changes=categories["change"],
            conflicts=categories["conflict"],
            unchanged=categories["unchanged"],
        )
        return InventoryImportPreview(
            preview_id=preview_id,
            status=status,
            filename=safe_name,
            expires_at=expires_at,
            counts=counts,
            errors=parsed.errors,
            error_report_available=bool(parsed.errors),
            errors_truncated=(parsed.total_rows - len(parsed.rows))
            > len(parsed.errors),
        )

    return preview


def database_error_reporter(engine: Engine) -> ImportErrorReporter:
    def report(authority: TenantAuthority, preview_id: UUID) -> bytes:
        try:
            with tenant_transaction(engine, authority) as connection:
                exists = connection.execute(
                    text("""
                        SELECT 1 FROM inventory_import_previews
                        WHERE tenant_id = :tenant_id AND id = :preview_id
                          AND expires_at > CURRENT_TIMESTAMP
                    """),
                    {"tenant_id": UUID(authority.tenant_id), "preview_id": preview_id},
                ).first()
                if exists is None:
                    raise ImportRejected(
                        "preview_not_found", "Import preview not found or expired."
                    )
                rows = connection.execute(
                    text("""
                        SELECT row_number, column_name, error_code, message
                        FROM inventory_import_errors
                        WHERE tenant_id = :tenant_id AND preview_id = :preview_id
                        ORDER BY row_number, id
                    """),
                    {"tenant_id": UUID(authority.tenant_id), "preview_id": preview_id},
                ).all()
        except ImportRejected:
            raise
        except SQLAlchemyError as error:
            raise ImportPreviewUnavailable("Import error report failed.") from error
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(("row_number", "column", "error_code", "message"))
        for row in rows:
            writer.writerow(row)
        return output.getvalue().encode("utf-8")

    return report
