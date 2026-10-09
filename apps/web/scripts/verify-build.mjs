import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const inventoryHtml = await readFile(
  new URL("../.next/server/app/inventory.html", import.meta.url),
  "utf8",
);

assert.match(inventoryHtml, /Secure merchant session required/);
assert.match(inventoryHtml, /Connect secure session to import/);
assert.doesNotMatch(inventoryHtml, /Classic Oxford Shirt/);
assert.doesNotMatch(inventoryHtml, /inventory_id/);
console.log("Verified fail-closed inventory build output.");
