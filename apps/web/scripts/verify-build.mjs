import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";

const manifest = JSON.parse(
  await readFile(new URL("../.next/server/app-paths-manifest.json", import.meta.url), "utf8"),
);

assert.equal(manifest["/inventory/page"], "app/inventory/page.js");
assert.equal(
  manifest["/api/bff/inventory/imports/preview/route"],
  "app/api/bff/inventory/imports/preview/route.js",
);

async function javascriptFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(entries.map((entry) => {
    const path = new URL(`${entry.name}${entry.isDirectory() ? "/" : ""}`, directory);
    return entry.isDirectory() ? javascriptFiles(path) : entry.name.endsWith(".js") ? [path] : [];
  }));
  return nested.flat();
}

const serverFiles = await javascriptFiles(new URL("../.next/server/", import.meta.url));
const serverBundle = (await Promise.all(serverFiles.map((path) => readFile(path, "utf8")))).join("\n");
assert.match(serverBundle, /\/api\/v1\/inventory\?limit=100/);
assert.match(serverBundle, /\/api\/v1\/inventory\/imports\/preview/);
assert.match(serverBundle, /Request origin denied/);
assert.doesNotMatch(serverBundle, /Classic Oxford Shirt/);
console.log("Verified dynamic inventory and same-origin preview BFF build artifacts.");
