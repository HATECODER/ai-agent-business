import { readFile } from "node:fs/promises";

const required = [
  "APP_BASE_URL",
  "BIZPILOT_API_BASE_URL",
  "BIZPILOT_WORKSPACE_ID",
  "BIZPILOT_WORKSPACE_NAME",
  "AUTH0_DOMAIN",
  "AUTH0_CLIENT_ID",
  "AUTH0_CLIENT_SECRET",
  "AUTH0_SECRET",
  "AUTH0_AUDIENCE",
  "BIZPILOT_SESSION_REDIS_URL",
  "BIZPILOT_SESSION_ENCRYPTION_KEY",
  "BIZPILOT_OIDC_ISSUER",
  "BIZPILOT_OIDC_AUDIENCE",
  "BIZPILOT_OIDC_JWKS_URL",
  "BIZPILOT_DATABASE_URL",
  "BIZPILOT_AUTH_DATABASE_URL",
];

function parseEnv(contents) {
  const values = {};
  for (const line of contents.split(/\r?\n/u)) {
    const match = line.match(/^([A-Z0-9_]+)=(.*)$/u);
    if (!match) continue;
    let value = match[2].trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    values[match[1]] = value;
  }
  return values;
}

function exactHttpsOrigin(name, value, failures) {
  try {
    const parsed = new URL(value);
    if (parsed.protocol !== "https:" || parsed.pathname !== "/" || parsed.search || parsed.hash || parsed.username || parsed.password) {
      failures.push(`${name} must be an exact HTTPS origin.`);
    }
  } catch {
    failures.push(`${name} must be an absolute HTTPS origin.`);
  }
}

let contents = "";
try {
  contents = await readFile(new URL("../../../.env", import.meta.url), "utf8");
} catch {
  console.error("[FAIL] Repository .env was not found.");
  process.exitCode = 1;
}

if (contents) {
  const env = { ...parseEnv(contents), ...process.env };
  const failures = [];
  for (const name of required) {
    if (!env[name]?.trim()) failures.push(`${name} is missing.`);
  }

  if (env.APP_BASE_URL) exactHttpsOrigin("APP_BASE_URL", env.APP_BASE_URL, failures);
  if (env.BIZPILOT_API_BASE_URL) exactHttpsOrigin("BIZPILOT_API_BASE_URL", env.BIZPILOT_API_BASE_URL, failures);
  if (env.BIZPILOT_WORKSPACE_ID && !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/iu.test(env.BIZPILOT_WORKSPACE_ID)) {
    failures.push("BIZPILOT_WORKSPACE_ID must be a UUID.");
  }
  if (env.AUTH0_SECRET && !/^[0-9a-f]{64}$/iu.test(env.AUTH0_SECRET)) {
    failures.push("AUTH0_SECRET must contain exactly 64 hexadecimal characters.");
  }
  if (env.BIZPILOT_SESSION_ENCRYPTION_KEY && !/^[0-9a-f]{64}$/iu.test(env.BIZPILOT_SESSION_ENCRYPTION_KEY)) {
    failures.push("BIZPILOT_SESSION_ENCRYPTION_KEY must contain exactly 64 hexadecimal characters.");
  }
  if (env.BIZPILOT_SESSION_REDIS_URL) {
    try {
      const redis = new URL(env.BIZPILOT_SESSION_REDIS_URL);
      const authenticatedTls = redis.protocol === "rediss:" && Boolean(redis.password);
      const renderPrivateNetwork =
        redis.protocol === "redis:" &&
        /^red-[a-z0-9-]+$/iu.test(redis.hostname) &&
        !redis.username &&
        !redis.password;
      if ((!authenticatedTls && !renderPrivateNetwork) || !redis.hostname || redis.search || redis.hash || !["", "/"].includes(redis.pathname)) {
        failures.push("BIZPILOT_SESSION_REDIS_URL must use authenticated TLS or a Render private-network Redis host.");
      }
    } catch {
      failures.push("BIZPILOT_SESSION_REDIS_URL is invalid.");
    }
  }
  if (env.AUTH0_DOMAIN && !/^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$/iu.test(env.AUTH0_DOMAIN)) {
    failures.push("AUTH0_DOMAIN must be a hostname without a scheme or path.");
  }
  if (env.AUTH0_AUDIENCE && env.BIZPILOT_OIDC_AUDIENCE && env.AUTH0_AUDIENCE !== env.BIZPILOT_OIDC_AUDIENCE) {
    failures.push("AUTH0_AUDIENCE and BIZPILOT_OIDC_AUDIENCE must match exactly.");
  }
  if (env.AUTH0_DOMAIN && env.BIZPILOT_OIDC_ISSUER) {
    const expectedIssuer = `https://${env.AUTH0_DOMAIN}/`;
    if (env.BIZPILOT_OIDC_ISSUER !== expectedIssuer) failures.push("BIZPILOT_OIDC_ISSUER does not match AUTH0_DOMAIN.");
  }
  if (env.AUTH0_DOMAIN && env.BIZPILOT_OIDC_JWKS_URL) {
    const expectedJwks = `https://${env.AUTH0_DOMAIN}/.well-known/jwks.json`;
    if (env.BIZPILOT_OIDC_JWKS_URL !== expectedJwks) failures.push("BIZPILOT_OIDC_JWKS_URL does not match AUTH0_DOMAIN.");
  }
  for (const name of ["BIZPILOT_DATABASE_URL", "BIZPILOT_AUTH_DATABASE_URL"]) {
    if (env[name] && !env[name].startsWith("postgresql")) failures.push(`${name} must use PostgreSQL.`);
  }

  if (failures.length) {
    console.error(`[FAIL] Staging configuration has ${failures.length} issue(s):`);
    for (const failure of failures) console.error(`- ${failure}`);
    process.exitCode = 1;
  } else {
    console.log(`[PASS] All ${required.length} required staging settings are present and structurally valid.`);
    console.log("No secret values were printed.");
  }
}
