import { defineConfig, devices } from "@playwright/test";

const externalBaseUrl = process.env.BIZPILOT_BROWSER_BASE_URL?.trim();
const baseURL = externalBaseUrl || "http://localhost:3000";
const browserChannel = process.env.BIZPILOT_BROWSER_CHANNEL?.trim() || "msedge";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? "line" : "list",
  timeout: 30_000,
  expect: { timeout: 8_000 },
  outputDir: "test-results",
  use: {
    ...devices["Desktop Edge"],
    baseURL,
    channel: browserChannel,
    bypassCSP: false,
    ignoreHTTPSErrors: false,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: externalBaseUrl
    ? undefined
    : {
        command: "npm run start",
        url: "http://localhost:3000/inventory",
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
        stdout: "ignore",
        stderr: "pipe",
      },
});
