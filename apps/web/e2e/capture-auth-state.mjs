import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

import { chromium } from "@playwright/test";

const baseURL = process.env.BIZPILOT_BROWSER_BASE_URL?.trim();
if (!baseURL?.startsWith("https://")) {
  throw new Error("Set BIZPILOT_BROWSER_BASE_URL to the exact HTTPS staging origin.");
}

const authDirectory = resolve("playwright/.auth");
const authFile = resolve(authDirectory, "merchant.json");
await mkdir(authDirectory, { recursive: true });

const browser = await chromium.launch({ headless: false, channel: process.env.BIZPILOT_BROWSER_CHANNEL || "msedge" });
// Use the real browser window size so the staging page fits the operator's
// display instead of being boxed into Playwright's default 1280x720 viewport.
const context = await browser.newContext({ viewport: null });
const page = await context.newPage();
console.log("Complete Auth0 sign-in in the opened browser. Credentials are not read by this script.");
await page.goto(new URL("/auth/login", baseURL).toString());
await page.waitForURL(`${baseURL}/inventory`, { timeout: 5 * 60_000 });
const deadline = Date.now() + 3 * 60_000;
while (!page.isClosed() && !(await page.getByRole("link", { name: "Sign out" }).isVisible())) {
  if (Date.now() >= deadline) throw new Error("Authenticated inventory did not become ready within three minutes.");
  await page.waitForTimeout(10_000).catch((error) => {
    if (!String(error).includes("Target page") && !String(error).includes("browser has been closed")) throw error;
  });
  if (!page.isClosed() && new URL(page.url()).pathname === "/inventory") {
    await page.reload({ waitUntil: "domcontentloaded" }).catch((error) => {
      if (!String(error).includes("ERR_ABORTED") && !String(error).includes("Target page")) throw error;
    });
  }
}
if (page.isClosed()) {
  throw new Error("The authentication browser was closed before the secure merchant session became ready. Keep it open until capture completes automatically.");
}
await context.storageState({ path: authFile });
console.log("Encrypted session state captured locally. The ignored file must never be committed or shared.");
await browser.close();
