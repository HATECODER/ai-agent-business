export interface BffConfig {
  apiBaseUrl: string;
  appBaseUrl: string;
  workspaceId: string;
  workspaceName: string;
}

export interface Auth0Config {
  audience: string;
  clientId: string;
  clientSecret: string;
  domain: string;
  secret: string;
}

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function bounded(name: string, value: string | undefined, maximum = 2048): string {
  const clean = value?.trim() ?? "";
  if (!clean || clean.length > maximum || /[\r\n\0]/u.test(clean)) throw new Error(`${name} is not safely configured.`);
  return clean;
}

function exactOrigin(name: string, value: string, production: boolean): string {
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    throw new Error(`${name} must be an absolute URL.`);
  }
  const localHttp = !production && parsed.protocol === "http:" && ["localhost", "127.0.0.1"].includes(parsed.hostname);
  if ((parsed.protocol !== "https:" && !localHttp) || parsed.username || parsed.password || parsed.search || parsed.hash || parsed.pathname !== "/") {
    throw new Error(`${name} must be an exact HTTPS origin.`);
  }
  return parsed.origin;
}

export function parseBffConfig(env: NodeJS.ProcessEnv): BffConfig {
  const production = env.NODE_ENV === "production";
  const appBaseUrl = exactOrigin("APP_BASE_URL", bounded("APP_BASE_URL", env.APP_BASE_URL), production);
  const apiBaseUrl = exactOrigin("BIZPILOT_API_BASE_URL", bounded("BIZPILOT_API_BASE_URL", env.BIZPILOT_API_BASE_URL), production);
  const workspaceId = bounded("BIZPILOT_WORKSPACE_ID", env.BIZPILOT_WORKSPACE_ID, 36);
  if (!UUID_PATTERN.test(workspaceId)) throw new Error("BIZPILOT_WORKSPACE_ID is invalid.");
  return { apiBaseUrl, appBaseUrl, workspaceId, workspaceName: bounded("BIZPILOT_WORKSPACE_NAME", env.BIZPILOT_WORKSPACE_NAME, 100) };
}

export function parseAuth0Config(env: NodeJS.ProcessEnv): Auth0Config {
  const domain = bounded("AUTH0_DOMAIN", env.AUTH0_DOMAIN, 253).toLowerCase();
  if (!/^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$/u.test(domain)) throw new Error("AUTH0_DOMAIN is invalid.");
  const secret = bounded("AUTH0_SECRET", env.AUTH0_SECRET, 64);
  if (!/^[0-9a-f]{64}$/iu.test(secret)) throw new Error("AUTH0_SECRET must be 32 bytes encoded as hex.");
  return {
    audience: bounded("AUTH0_AUDIENCE", env.AUTH0_AUDIENCE, 512),
    clientId: bounded("AUTH0_CLIENT_ID", env.AUTH0_CLIENT_ID, 512),
    clientSecret: bounded("AUTH0_CLIENT_SECRET", env.AUTH0_CLIENT_SECRET, 1024),
    domain,
    secret,
  };
}

export function hasCompleteConfiguration(env: NodeJS.ProcessEnv): boolean {
  try {
    parseBffConfig(env);
    parseAuth0Config(env);
    return true;
  } catch {
    return false;
  }
}

export function isTrustedMutationOrigin(origin: string | null, appBaseUrl: string): boolean {
  if (!origin) return false;
  try {
    return new URL(origin).origin === new URL(appBaseUrl).origin;
  } catch {
    return false;
  }
}
