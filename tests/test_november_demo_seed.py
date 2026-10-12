from uuid import UUID

from scripts.seed_november_demo_inventory import (
    FIXTURE_DIR,
    SOURCE_REFERENCE,
    assert_reviewed_counts,
    load_seed_rows,
)

WORKSPACE_A = UUID("10000000-0000-4000-8000-000000000001")
WORKSPACE_B = UUID("20000000-0000-4000-8000-000000000002")


def test_seed_rows_are_stable_unique_and_tenant_specific():
    manifest, first = load_seed_rows(WORKSPACE_A, FIXTURE_DIR)
    _, repeated = load_seed_rows(WORKSPACE_A, FIXTURE_DIR)
    _, other_tenant = load_seed_rows(WORKSPACE_B, FIXTURE_DIR)

    assert manifest["fixture_version"] == "november-v1"
    assert first == repeated
    assert len(first) == 12
    assert len({row.variant_id for row in first}) == 12
    assert len({row.balance_id for row in first}) == 12
    assert {row.variant_id for row in first}.isdisjoint(
        {row.variant_id for row in other_tenant}
    )


def test_seed_rows_preserve_reviewed_inventory_values():
    _, rows = load_seed_rows(WORKSPACE_A, FIXTURE_DIR)
    by_sku = {row.sku: row for row in rows}

    assert SOURCE_REFERENCE == "bizpilot-november-demo"
    assert {row.location_code for row in rows} == {"DHAKA", "CTG"}
    assert by_sku["BP-TS-BLK-M"].quantity == 3
    assert by_sku["BP-TS-BLK-M"].low_stock_threshold == 5
    assert by_sku["BP-TS-BLK-M"].base_price_minor == 85_000
    assert by_sku["BP-KUR-BLU-M"].options == {"color": "Blue", "size": "M"}


def test_database_verification_requires_reviewed_counts():
    assert_reviewed_counts({"variants": 12, "low_stock": 7, "out_of_stock": 2})
