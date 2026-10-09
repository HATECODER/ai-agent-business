export type InventoryStatus = "in_stock" | "low_stock" | "out_of_stock";

export interface InventoryItem {
  product_name: string;
  variant_name: string;
  sku: string;
  location_code: string;
  location_name: string;
  quantity: number;
  low_stock_threshold: number;
  observed_at: string;
}

export interface InventorySummary {
  total: number;
  lowStock: number;
  outOfStock: number;
}

export function merchantInventoryItem(item: InventoryItem): InventoryItem {
  return {
    product_name: item.product_name,
    variant_name: item.variant_name,
    sku: item.sku,
    location_code: item.location_code,
    location_name: item.location_name,
    quantity: item.quantity,
    low_stock_threshold: item.low_stock_threshold,
    observed_at: item.observed_at,
  };
}

export function inventoryStatus(item: Pick<InventoryItem, "quantity" | "low_stock_threshold">): InventoryStatus {
  if (item.quantity === 0) return "out_of_stock";
  if (item.quantity <= item.low_stock_threshold) return "low_stock";
  return "in_stock";
}

export function inventorySummary(items: InventoryItem[]): InventorySummary {
  return items.reduce(
    (summary, item) => {
      summary.total += 1;
      const status = inventoryStatus(item);
      if (status === "low_stock") summary.lowStock += 1;
      if (status === "out_of_stock") summary.outOfStock += 1;
      return summary;
    },
    { total: 0, lowStock: 0, outOfStock: 0 },
  );
}

export function filterInventory(
  items: InventoryItem[],
  query: string,
  lowStockOnly: boolean,
): InventoryItem[] {
  const normalized = query.trim().toLocaleLowerCase("en");
  return items.filter((item) => {
    if (lowStockOnly && inventoryStatus(item) === "in_stock") return false;
    if (!normalized) return true;
    return [
      item.product_name,
      item.variant_name,
      item.sku,
      item.location_name,
      item.location_code,
    ].some((value) => value.toLocaleLowerCase("en").includes(normalized));
  });
}

export function hasPermission(permissions: string[], permission: string): boolean {
  return permissions.includes(permission);
}

export function formatObservedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return "Unknown";
  return new Intl.DateTimeFormat("en-BD", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Dhaka",
  }).format(date);
}
