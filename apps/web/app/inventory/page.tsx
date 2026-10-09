import { InventoryWorkspace } from "@/components/InventoryWorkspace";

export default function InventoryPage() {
  return (
    <InventoryWorkspace
      workspaceName="Merchant workspace"
      roleLabel="Session not connected"
      permissions={[]}
      items={[]}
      connectionReady={false}
    />
  );
}
