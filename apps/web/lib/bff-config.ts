import "server-only";

import {
  hasCompleteConfiguration,
  isTrustedMutationOrigin,
  parseAuth0Config,
  parseBffConfig,
  type Auth0Config,
  type BffConfig,
} from "./bff-config-values";

export type { Auth0Config, BffConfig };
export { isTrustedMutationOrigin };

export function readBffConfig(env: NodeJS.ProcessEnv = process.env): BffConfig {
  return parseBffConfig(env);
}

export function readAuth0Config(env: NodeJS.ProcessEnv = process.env): Auth0Config {
  return parseAuth0Config(env);
}

export function hasCompleteBffConfiguration(env: NodeJS.ProcessEnv = process.env): boolean {
  return hasCompleteConfiguration(env);
}
