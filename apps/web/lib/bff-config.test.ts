import assert from "node:assert/strict";
import test from "node:test";

import {
  hasCompleteConfiguration,
  isTrustedMutationOrigin,
  parseAuth0Config,
  parseBffConfig,
} from "./bff-config-values.ts";

function configuredEnv(): NodeJS.ProcessEnv {
  return {
    NODE_ENV: "production",
    APP_BASE_URL: "https://app.bizpilot.example",
    BIZPILOT_API_BASE_URL: "https://api.bizpilot.example",
    BIZPILOT_WORKSPACE_ID: "10000000-0000-4000-8000-000000000001",
    BIZPILOT_WORKSPACE_NAME: "Dhaka Store",
    AUTH0_DOMAIN: "tenant.auth0.com",
    AUTH0_CLIENT_ID: "client-id",
    AUTH0_CLIENT_SECRET: "client-secret",
    AUTH0_SECRET: "a".repeat(64),
    AUTH0_AUDIENCE: "https://api.bizpilot.example",
    BIZPILOT_SESSION_ENCRYPTION_KEY: "b".repeat(64),
    BIZPILOT_SESSION_REDIS_URL: "rediss://default:password@redis.bizpilot.example:6380",
  };
}

test("BFF configuration accepts exact production origins and a server workspace", () => {
  const env = configuredEnv();
  assert.deepEqual(parseBffConfig(env), {
    appBaseUrl: "https://app.bizpilot.example",
    apiBaseUrl: "https://api.bizpilot.example",
    workspaceId: "10000000-0000-4000-8000-000000000001",
    workspaceName: "Dhaka Store",
  });
  assert.equal(parseAuth0Config(env).domain, "tenant.auth0.com");
  assert.equal(hasCompleteConfiguration(env), true);
});

test("production rejects HTTP, URL paths, invalid workspaces, and incomplete secrets", () => {
  for (const mutation of [
    { APP_BASE_URL: "http://app.bizpilot.example" },
    { BIZPILOT_API_BASE_URL: "https://api.bizpilot.example/v1" },
    { BIZPILOT_WORKSPACE_ID: "browser-selected-tenant" },
    { AUTH0_SECRET: "short" },
    { AUTH0_DOMAIN: "https://tenant.auth0.com" },
    { BIZPILOT_SESSION_ENCRYPTION_KEY: "short" },
    { BIZPILOT_SESSION_REDIS_URL: "redis://default:password@redis.bizpilot.example:6379" },
    { BIZPILOT_SESSION_REDIS_URL: "rediss://redis.bizpilot.example:6380" },
  ]) {
    assert.equal(hasCompleteConfiguration({ ...configuredEnv(), ...mutation }), false);
  }
});

test("Auth configuration accepts Render private-network Redis without exposing it publicly", () => {
  const env = configuredEnv();
  env.BIZPILOT_SESSION_REDIS_URL = "redis://red-example-singapore:6379";
  assert.equal(hasCompleteConfiguration(env), true);
});

test("local HTTP is limited to development localhost", () => {
  const env: NodeJS.ProcessEnv = {
    ...configuredEnv(),
    NODE_ENV: "development",
    APP_BASE_URL: "http://localhost:3000",
    BIZPILOT_API_BASE_URL: "http://127.0.0.1:8000",
  };
  assert.equal(hasCompleteConfiguration(env), true);
  assert.equal(hasCompleteConfiguration({ ...env, APP_BASE_URL: "http://192.168.1.4:3000" }), false);
});

test("mutation origin must exactly match the configured application origin", () => {
  assert.equal(isTrustedMutationOrigin("https://app.bizpilot.example", "https://app.bizpilot.example"), true);
  assert.equal(isTrustedMutationOrigin("https://evil.example", "https://app.bizpilot.example"), false);
  assert.equal(isTrustedMutationOrigin(null, "https://app.bizpilot.example"), false);
});
