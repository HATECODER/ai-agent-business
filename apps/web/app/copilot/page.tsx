import { CopilotWorkspace } from "@/components/CopilotWorkspace";
import { loadInventoryWorkspace } from "@/lib/bff";

export const dynamic = "force-dynamic";

export default async function CopilotPage() {
  const result = await loadInventoryWorkspace();
  const ready = result.state === "ready";
  return <CopilotWorkspace workspaceName={result.workspaceName} roleLabel={ready ? result.workspace.role : "Session unavailable"} ready={ready} canUse={ready && result.workspace.permissions.includes("copilot.use")} />;
}
