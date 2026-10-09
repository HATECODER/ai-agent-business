import { existsSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test } from "@playwright/test";

const authState = resolve("playwright/.auth/merchant.json");
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

test("authenticated cross-origin preview is rejected", async ({ request }) => {
  const response = await request.post("/api/bff/inventory/imports/preview", {
    headers: { Origin: "https://attacker.invalid", "Content-Type": "multipart/form-data; boundary=empty" },
    data: "--empty--",
  });
  expect(response.status()).toBe(403);
});
