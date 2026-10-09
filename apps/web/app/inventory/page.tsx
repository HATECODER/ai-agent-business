import { InventoryWorkspace } from "@/components/InventoryWorkspace";
import { loadInventoryWorkspace } from "@/lib/bff";

export const dynamic = "force-dynamic";

export default async function InventoryPage() {
  const result = await loadInventoryWorkspace();
  const ready = result.state === "ready";
  return (
    <InventoryWorkspace
      workspaceName={result.workspaceName}
      roleLabel={ready ? result.workspace.role : result.state === "signed_out" ? "Signed out" : "Session unavailable"}
      permissions={ready ? result.workspace.permissions : []}
      items={ready ? result.inventory.items : []}
      connectionState={result.state}
    />
  );
}
