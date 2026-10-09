import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  filterInventory,
  hasPermission,
  inventoryStatus,
  inventorySummary,
  merchantInventoryItem,
  type InventoryItem,
} from "./inventory.ts";

const base: InventoryItem = {
  product_name: "Classic Oxford Shirt",
  variant_name: "Blue L",
  sku: "OXFORD-BLUE-L",
  location_code: "DHAKA-01",
  location_name: "Dhaka Warehouse",
  quantity: 11,
  low_stock_threshold: 5,
  observed_at: "2026-10-09T00:00:00+06:00",
};

test("status and summary remain deterministic", () => {
  const items = [
    base,
    { ...base, sku: "LOW", quantity: 3 },
    { ...base, sku: "OUT", quantity: 0 },
  ];
  assert.equal(inventoryStatus(items[0]), "in_stock");
  assert.equal(inventoryStatus(items[1]), "low_stock");
  assert.equal(inventoryStatus(items[2]), "out_of_stock");
  assert.deepEqual(inventorySummary(items), { total: 3, lowStock: 1, outOfStock: 1 });
});

test("merchant search uses business labels and low-stock filter", () => {
  const low = { ...base, sku: "LOW", location_name: "Chattogram Shop", quantity: 2 };
  assert.deepEqual(filterInventory([base, low], "chattogram", false), [low]);
  assert.deepEqual(filterInventory([base, low], "", true), [low]);
});

test("UI capability discovery never grants an absent permission", () => {
  const permissions = ["inventory.read"];
  assert.equal(hasPermission(permissions, "inventory.read"), true);
  assert.equal(hasPermission(permissions, "inventory.import"), false);
});

test("merchant client data excludes backend identifiers and write metadata", () => {
  const backendItem = {
    ...base,
    inventory_id: "internal-inventory",
    product_id: "internal-product",
    record_version: 7,
  };
  assert.deepEqual(merchantInventoryItem(backendItem), base);
  assert.equal("inventory_id" in merchantInventoryItem(backendItem), false);
  assert.equal("record_version" in merchantInventoryItem(backendItem), false);
});

test("merchant download and reviewed source template stay identical", async () => {
  const publicTemplate = await readFile(
    new URL("../public/inventory-import-template.csv", import.meta.url),
    "utf8",
  );
  const reviewedTemplate = await readFile(
    new URL("../../../docs/templates/inventory-import-template.csv", import.meta.url),
    "utf8",
  );
  assert.equal(publicTemplate, reviewedTemplate);
});
