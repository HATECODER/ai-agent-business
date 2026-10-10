import { existsSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test } from "@playwright/test";

const authState = resolve("playwright/.auth/merchant.json");
const expectedState = process.env.BIZPILOT_EXPECTED_AUTHORITY_STATE;

test.skip(!existsSync(authState), "Capture a staging merchant session first.");
test.skip(!["revoked", "viewer", "owner"].includes(expectedState ?? ""), "Set an expected authority state.");
test.use({ storageState: authState });

test("deployed UI applies the current database authority", async ({ page }) => {
  await page.goto("/inventory");

  if (expectedState === "revoked") {
    await expect(page.getByText("Your account does not have an active membership for this workspace.")).toBeVisible();
    await expect(page.getByRole("link", { name: "Sign out" })).toHaveCount(0);
    await expect(page.locator("body")).not.toContainText(/inventory_id|product_id|variant_id|location_id/iu);
    return;
  }

  await expect(page.getByRole("link", { name: "Sign out" })).toBeVisible();
  await expect(page.getByText("Secure merchant session required")).toHaveCount(0);
  const workspaceCard = page.locator(".workspace-card");
  await expect(workspaceCard).toContainText(expectedState === "viewer" ? "viewer" : "owner");
  if (expectedState === "viewer") {
    await expect(page.getByRole("button", { name: "Preview not allowed for your role" })).toBeDisabled();
  }
});
