import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test, type BrowserContext } from "@playwright/test";

const authState = resolve("playwright/.auth/merchant.json");
const stagingApiURL = "https://bizpilot-hatecoder-staging-api.onrender.com";
test.skip(!existsSync(authState), "Capture a staging merchant session first with npm run browser:auth:capture.");
test.use({ storageState: authState });

test("authenticated merchant reaches only the server-selected workspace", async ({ page }) => {
  await page.goto("/inventory");
  await expect(page.getByRole("link", { name: "Sign out" })).toBeVisible();
  await expect(page.getByText("Secure merchant session required")).toHaveCount(0);
  await expect(page.locator("body")).not.toContainText(/inventory_id|product_id|variant_id|location_id/iu);
});

test("managed session is HTTP-only and absent from web storage", async ({ page, context, baseURL }) => {
  await page.goto("/inventory");
  const cookies = await context.cookies(baseURL);
  const sessionCookies = cookies.filter((cookie) => cookie.name.startsWith("__session"));
  expect(sessionCookies.length).toBeGreaterThan(0);
  for (const cookie of sessionCookies) {
    expect(cookie.httpOnly).toBe(true);
    expect(cookie.sameSite).toBe("Lax");
    if (baseURL?.startsWith("https://")) expect(cookie.secure).toBe(true);
  }
  const storage = await page.evaluate(() => JSON.stringify({
    local: Object.entries(localStorage),
    session: Object.entries(sessionStorage),
  }));
  expect(storage).not.toMatch(/access[_-]?token|id[_-]?token|bearer/iu);
});

test("two tabs share identity without exposing a token", async ({ context, page }) => {
  await page.goto("/inventory");
  const second = await context.newPage();
  await second.goto("/inventory");
  await expect(second.getByRole("link", { name: "Sign out" })).toBeVisible();
  expect(await second.evaluate(() => document.cookie)).not.toMatch(/session|auth|token/iu);
});

test("logout removes the application session and protected content fails closed", async ({ page }) => {
  await page.goto("/inventory");
  await expect(page.getByRole("link", { name: "Sign out" })).toBeVisible();
  await page.goto("/auth/logout");
  await page.waitForURL(/\/inventory(?:\?.*)?$/u);
  await expect(page.getByRole("link", { name: "Sign in" })).toBeVisible();
  await expect(page.getByText("Secure merchant session required")).toBeVisible();
  await expect(page.locator("body")).not.toContainText(/inventory_id|product_id|variant_id|location_id/iu);
});

test("an expired application session requires reauthentication", async ({ browser }) => {
  const state = JSON.parse(readFileSync(authState, "utf8")) as Awaited<ReturnType<BrowserContext["storageState"]>>;
  const expiredState = {
    ...state,
    cookies: state.cookies.map((cookie) => ({ ...cookie, expires: Math.floor(Date.now() / 1000) - 60 })),
  };
  const context = await browser.newContext({ storageState: expiredState });
  try {
    const page = await context.newPage();
    await page.goto("/inventory");
    await expect(page.getByRole("link", { name: "Sign in" })).toBeVisible();
    await expect(page.getByText("Secure merchant session required")).toBeVisible();
  } finally {
    await context.close();
  }
});

test("an invalid callback state grants no authenticated application access", async ({ browser }) => {
  const context = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  try {
    const page = await context.newPage();
    const response = await page.goto("/auth/callback?code=invalid&state=invalid");
    expect(response?.ok()).toBe(false);
    await page.goto("/inventory");
    await expect(page.getByRole("link", { name: "Sign in" })).toBeVisible();
    await expect(page.getByText("Secure merchant session required")).toBeVisible();
  } finally {
    await context.close();
  }
});

test("direct FastAPI access without a bearer token is sanitized", async ({ request }) => {
  const response = await request.get(`${stagingApiURL}/api/v1/workspace`);
  expect(response.status()).toBe(401);
  expect(await response.json()).toEqual({ detail: "Authentication required." });
  expect(response.headers()["www-authenticate"]).toBe("Bearer");
});

test("authenticated cross-origin preview is rejected", async ({ request }) => {
  const response = await request.post("/api/bff/inventory/imports/preview", {
    headers: { Origin: "https://attacker.invalid", "Content-Type": "multipart/form-data; boundary=empty" },
    data: "--empty--",
  });
  expect(response.status()).toBe(403);
});
