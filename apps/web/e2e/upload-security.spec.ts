import { existsSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test } from "@playwright/test";

const authState = resolve("playwright/.auth/merchant.json");
const csvHeader = "product_name,variant_name,sku,location_code,location_name,quantity,low_stock_threshold,variant_options,base_price_bdt,expected_record_version\n";

test.skip(!existsSync(authState), "Capture a staging merchant session first.");
test.use({ storageState: authState });

test("CSV payload fails closed without executing or injecting uploaded text", async ({ page }) => {
  let dialogOpened = false;
  page.on("dialog", async (dialog) => {
    dialogOpened = true;
    await dialog.dismiss();
  });
  await page.goto("/inventory");
  await expect(page.getByRole("link", { name: "Sign out" })).toBeVisible();

  const payload = `${csvHeader}<script>globalThis.__bizpilotXss=1</script>,<img src=x onerror=alert(1)>,XSS-1,DHAKA,Main,1,1,,,\n`;
  await page.getByLabel("CSV file").setInputFiles({
    name: "<img src=x onerror=alert(1)>.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(payload, "utf8"),
  });
  await page.getByRole("button", { name: "Preview CSV" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Preview failed" })).toContainText("Import preview unavailable.");
  expect(dialogOpened).toBe(false);
  expect(await page.evaluate(() => (globalThis as typeof globalThis & { __bizpilotXss?: number }).__bizpilotXss)).toBeUndefined();
  await expect(page.locator("script", { hasText: "__bizpilotXss" })).toHaveCount(0);
  await expect(page.locator("img[src='x']")).toHaveCount(0);
});

test("oversized multipart upload is rejected before parsing", async ({ request, baseURL }) => {
  const response = await request.post("/api/bff/inventory/imports/preview", {
    headers: { Origin: baseURL! },
    multipart: {
      file: {
        name: "oversized.csv",
        mimeType: "text/csv",
        buffer: Buffer.alloc(5 * 1024 * 1024 + 65 * 1024, 0x61),
      },
    },
  });
  expect(response.status()).toBe(413);
  expect(await response.json()).toEqual({ detail: "CSV file is too large." });
});
