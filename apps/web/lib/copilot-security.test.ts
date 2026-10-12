import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const component = readFileSync(new URL("../components/CopilotWorkspace.tsx", import.meta.url), "utf8");
const route = readFileSync(new URL("../app/api/bff/copilot/route.ts", import.meta.url), "utf8");
const bff = readFileSync(new URL("bff.ts", import.meta.url), "utf8");

test("restock proposal remains visibly review-only and safely rendered", () => {
  assert.match(component, /Review only/);
  assert.match(component, /No external action has been taken/);
  assert.doesNotMatch(component, /dangerouslySetInnerHTML/);
  assert.doesNotMatch(component, /Approve|Execute|Purchase now/);
});

test("Copilot BFF keeps authentication, same-origin, and input bounds server-side", () => {
  assert.match(route, /isTrustedMutationOrigin/);
  assert.match(route, /message\.length > 500/);
  assert.match(route, /Request origin denied/);
  assert.match(bff, /auth0\.getSession/);
  assert.match(bff, /\/api\/v1\/copilot\/query/);
  assert.doesNotMatch(component, /Authorization:\s*`Bearer/);
});
