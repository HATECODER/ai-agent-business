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
const context = await browser.newContext();
const page = await context.newPage();
console.log("Complete Auth0 sign-in in the opened browser. Credentials are not read by this script.");
await page.goto(new URL("/auth/login", baseURL).toString());
await page.waitForURL(`${baseURL}/inventory`, { timeout: 5 * 60_000 });
await page.getByRole("link", { name: "Sign out" }).waitFor({ timeout: 30_000 });
await context.storageState({ path: authFile });
console.log("Encrypted session state captured locally. The ignored file must never be committed or shared.");
await browser.close();
