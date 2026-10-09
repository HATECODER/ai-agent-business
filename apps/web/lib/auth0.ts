import "server-only";

import { Auth0Client } from "@auth0/nextjs-auth0/server";

import { hasCompleteBffConfiguration, readAuth0Config, readBffConfig } from "./bff-config";

let client: Auth0Client | undefined;

export function getAuth0Client(): Auth0Client | null {
  if (!hasCompleteBffConfiguration()) return null;
  if (client) return client;

  const auth = readAuth0Config();
  const bff = readBffConfig();
  client = new Auth0Client({
    appBaseUrl: bff.appBaseUrl,
    domain: auth.domain,
    clientId: auth.clientId,
    clientSecret: auth.clientSecret,
    secret: auth.secret,
    authorizationParameters: {
      audience: auth.audience,
      scope: "openid profile offline_access",
    },
    enableAccessTokenEndpoint: false,
    enableTelemetry: false,
    signInReturnToPath: "/inventory",
    session: {
      rolling: false,
      absoluteDuration: 8 * 60 * 60,
      cookie: {
        sameSite: "lax",
        secure: new URL(bff.appBaseUrl).protocol === "https:",
        path: "/",
      },
    },
  });
  return client;
}
