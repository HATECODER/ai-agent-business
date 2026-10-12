import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

test("React escapes an attacker-controlled preview filename", () => {
  const attackerFilename = '<img src=x onerror="globalThis.__bizpilotXss=1">.csv';
  const markup = renderToStaticMarkup(createElement("span", null, attackerFilename));

  assert.equal(markup.includes("<img"), false);
  assert.equal(markup.includes("onerror="), true);
  assert.equal(markup.includes("&lt;img"), true);
});

test("inventory preview component does not use raw HTML rendering", async () => {
  const component = await readFile(
    new URL("../components/InventoryWorkspace.tsx", import.meta.url),
    "utf8",
  );

  assert.equal(component.includes("dangerouslySetInnerHTML"), false);
  assert.equal(component.includes("eval("), false);
});
