import { existsSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

const authState = resolve("playwright/.auth/merchant.json");
test.skip(!existsSync(authState), "Capture a staging merchant session first with npm run browser:auth:capture.");
test.use({ storageState: authState, video: "on" });
test.setTimeout(120_000);

async function ask(page: Page, prompt: string, expectedText: RegExp) {
  await page.getByRole("button", { name: prompt, exact: true }).click();
  await page.getByRole("button", { name: "Ask Copilot", exact: true }).click();
  const answer = page.locator(".copilot-answer");
  await expect(answer).toContainText(expectedText, { timeout: 15_000 });
  await expect(answer).toContainText("Source date: 2026-11-01");
  await expect(answer).toContainText("Mode: deterministic");
}

async function runWalkthrough(page: Page) {
  await page.goto("/inventory");
  await expect(page.getByRole("heading", { name: "Inventory", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Sign out" })).toBeVisible();
  await expect(page.getByText("Secure merchant session required")).toHaveCount(0);

  const summary = page.getByRole("region", { name: "Inventory summary" });
  await expect(summary).toContainText(/Variants\s*12/u);
  await expect(summary).toContainText(/Low stock\s*5/u);
  await expect(summary).toContainText(/Out of stock\s*2/u);

  const search = page.getByPlaceholder("Search inventory");
  await search.fill("BP-KUR-BLU-M");
  await expect(page.getByRole("cell", { name: "BP-KUR-BLU-M", exact: true })).toBeVisible();
  await expect(page.getByRole("row")).toHaveCount(2);
  await search.fill("");
  await page.getByLabel("Needs attention").check();
  const stockRows = page.locator("tbody");
  await expect(stockRows.getByText("Low stock", { exact: true })).toHaveCount(5);
  await expect(stockRows.getByText("Out of stock", { exact: true })).toHaveCount(2);
  await page.getByLabel("Needs attention").uncheck();

  await expect(page.getByText("Live CSV preview is not enabled")).toBeVisible();
  await expect(page.getByRole("button", { name: "Preview unavailable" })).toBeDisabled();
  await expect(page.getByText("No stock is changed in this phase")).toBeVisible();

  await page.getByRole("link", { name: "Copilot", exact: true }).click();
  await expect(page.getByRole("heading", { name: "BizPilot Copilot" })).toBeVisible();
  await expect(page.getByText("Deterministic demo mode")).toBeVisible();

  await ask(page, "Which products need restocking?", /7 product variants need attention/iu);
  await ask(page, "Show today's financial summary.", /BDT 5,000 revenue/iu);
  await expect(page.locator(".copilot-answer")).toContainText(/BDT 3,500/iu);
  await expect(page.locator(".copilot-answer")).toContainText(/BDT 1,500/iu);
  await expect(page.locator(".copilot-answer")).toContainText(/BDT 800/iu);
  await ask(page, "Which customers have been inactive?", /CUST-002/iu);
  await expect(page.locator(".copilot-answer")).toContainText(/CUST-004/iu);
  await expect(page.locator(".copilot-answer")).toContainText(/CUST-005/iu);
  await ask(page, "What tasks need attention?", /4 tasks need attention/iu);
  await expect(page.locator(".copilot-answer")).toContainText(/TASK-001/iu);
  await expect(page.locator(".copilot-answer")).toContainText(/TASK-004/iu);
  await ask(page, "Prepare a restock review proposal.", /39 units/iu);
  await expect(page.getByText("Review only", { exact: true })).toBeVisible();
  await expect(page.getByText("No external action has been taken.")).toBeVisible();
  await expect(page.getByRole("button", { name: /approve|execute|order|purchase/iu })).toHaveCount(0);
}

test("clean-browser walkthrough 1", async ({ page }) => {
  await runWalkthrough(page);
});

test("clean-browser walkthrough 2", async ({ page }) => {
  await runWalkthrough(page);
});

for (const device of [
  { name: "phone", width: 390, height: 844 },
  { name: "tablet", width: 820, height: 1180 },
  { name: "desktop", width: 1440, height: 900 },
]) {
  test(`inventory shell fits ${device.name}`, async ({ page }) => {
    await page.setViewportSize({ width: device.width, height: device.height });
    await page.goto("/inventory");
    await expect(page.getByRole("heading", { name: "Inventory", exact: true })).toBeVisible();
    const sizing = await page.evaluate(() => ({
      body: document.body.scrollWidth,
      viewport: document.documentElement.clientWidth,
    }));
    expect(sizing.body).toBeLessThanOrEqual(sizing.viewport);
    await expect(page.getByRole("navigation").getByRole("link", { name: "Copilot", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Preview unavailable" })).toBeVisible();
  });
}
