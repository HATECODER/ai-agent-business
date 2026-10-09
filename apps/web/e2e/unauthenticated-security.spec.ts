import { expect, test } from "@playwright/test";

test.use({ storageState: { cookies: [], origins: [] } });

test("inventory fails closed without a managed session", async ({ page }) => {
  const response = await page.goto("/inventory");
  expect(response?.status()).toBe(200);
  await expect(page.getByRole("heading", { level: 1, name: "Inventory", exact: true })).toBeVisible();
  await expect(page.getByText("Secure merchant session required")).toBeVisible();
  await expect(page.getByText("Classic Oxford Shirt")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /preview/i })).toBeDisabled();
});

test("application responses carry the browser security policy", async ({ page }) => {
  const response = await page.goto("/inventory");
  const headers = response?.headers() ?? {};
  expect(headers["content-security-policy"]).toContain("script-src 'self' 'nonce-");
  expect(headers["content-security-policy"]).toContain("frame-ancestors 'none'");
  expect(headers["x-frame-options"]).toBe("DENY");
  expect(headers["x-content-type-options"]).toBe("nosniff");
  expect(headers["permissions-policy"]).toContain("camera=()");
  expect(headers["x-powered-by"]).toBeUndefined();
});

test("browser storage contains no bearer or identity token", async ({ page, context }) => {
  await page.goto("/inventory");
  const storage = await page.evaluate(() => ({
    local: Object.entries(localStorage),
    session: Object.entries(sessionStorage),
    visibleCookie: document.cookie,
  }));
  expect(JSON.stringify(storage)).not.toMatch(/access[_-]?token|id[_-]?token|bearer/iu);
  const cookies = await context.cookies();
  expect(cookies.filter((cookie) => !cookie.httpOnly).map((cookie) => cookie.name).join(" ")).not.toMatch(/session|auth|token/iu);
});

test("client access-token route is unavailable", async ({ request }) => {
  const response = await request.get("/auth/access-token", { maxRedirects: 0 });
  expect(response.status()).not.toBe(200);
  expect(await response.text()).not.toMatch(/"token"\s*:/u);
});

test("cross-origin preview mutation is never accepted", async ({ request }) => {
  const response = await request.post("/api/bff/inventory/imports/preview", {
    headers: { Origin: "https://attacker.invalid", "Content-Type": "multipart/form-data; boundary=empty" },
    data: "--empty--",
  });
  expect([403, 503]).toContain(response.status());
  expect(await response.json()).toEqual(
    response.status() === 403
      ? { detail: "Request origin denied." }
      : { detail: "Merchant session is not configured." },
  );
});
