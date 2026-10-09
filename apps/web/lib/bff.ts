import "server-only";

import { merchantInventoryItem, type InventoryItem } from "./inventory";
import { getAuth0Client } from "./auth0";
import { hasCompleteBffConfiguration, readBffConfig } from "./bff-config";

export interface WorkspaceSession {
  workspace_id: string;
  role: string;
  permission_version: number;
  permissions: string[];
}

interface ApiInventoryItem extends InventoryItem {
  inventory_id: string;
  product_id: string;
  variant_id: string;
  location_id: string;
  is_low_stock: boolean;
  base_price_minor: number | null;
  currency: string | null;
  record_version: number;
  source_kind: string;
  source_version: string | null;
}

interface ApiInventoryPage {
  items: ApiInventoryItem[];
  next_cursor: string | null;
  limit: number;
}

interface InventoryPage {
  items: InventoryItem[];
  next_cursor: string | null;
  limit: number;
}

export type WorkspaceLoad =
  | { state: "configuration"; workspaceName: string }
  | { state: "signed_out"; workspaceName: string }
  | { state: "denied"; workspaceName: string }
  | { state: "unavailable"; workspaceName: string }
  | {
      state: "ready";
      workspaceName: string;
      workspace: WorkspaceSession;
      inventory: InventoryPage;
    };

const REQUEST_TIMEOUT_MS = 8000;

export function apiHeaders(token: string, workspaceId: string): HeadersInit {
  return {
    Accept: "application/json",
    Authorization: `Bearer ${token}`,
    "X-BizPilot-Tenant": workspaceId,
  };
}

async function apiFetch(path: string, token: string, workspaceId: string, init?: RequestInit): Promise<Response> {
  const config = readBffConfig();
  return fetch(new URL(path, config.apiBaseUrl), {
    ...init,
    cache: "no-store",
    headers: {
      ...apiHeaders(token, workspaceId),
      ...init?.headers,
    },
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });
}

export async function loadInventoryWorkspace(): Promise<WorkspaceLoad> {
  if (!hasCompleteBffConfiguration()) {
    return { state: "configuration", workspaceName: "Merchant workspace" };
  }
  const config = readBffConfig();
  const auth0 = getAuth0Client();
  if (!auth0) return { state: "configuration", workspaceName: config.workspaceName };

  try {
    const session = await auth0.getSession();
    if (!session) return { state: "signed_out", workspaceName: config.workspaceName };
    const { token } = await auth0.getAccessToken();
    const [workspaceResponse, inventoryResponse] = await Promise.all([
      apiFetch("/api/v1/workspace", token, config.workspaceId),
      apiFetch("/api/v1/inventory?limit=100", token, config.workspaceId),
    ]);
    if ([401, 403].includes(workspaceResponse.status) || [401, 403].includes(inventoryResponse.status)) {
      return { state: "denied", workspaceName: config.workspaceName };
    }
    if (!workspaceResponse.ok || !inventoryResponse.ok) {
      return { state: "unavailable", workspaceName: config.workspaceName };
    }
    const workspace = (await workspaceResponse.json()) as WorkspaceSession;
    const apiInventory = (await inventoryResponse.json()) as ApiInventoryPage;
    const inventory: InventoryPage = {
      limit: apiInventory.limit,
      next_cursor: apiInventory.next_cursor,
      items: apiInventory.items.map(merchantInventoryItem),
    };
    return { state: "ready", workspaceName: config.workspaceName, workspace, inventory };
  } catch {
    return { state: "unavailable", workspaceName: config.workspaceName };
  }
}

export async function forwardInventoryPreview(file: File): Promise<Response> {
  const config = readBffConfig();
  const auth0 = getAuth0Client();
  if (!auth0 || !(await auth0.getSession())) {
    return Response.json({ detail: "Authentication required." }, { status: 401 });
  }
  try {
    const { token } = await auth0.getAccessToken();
    const body = new FormData();
    body.set("file", file, file.name);
    const upstream = await apiFetch(
      "/api/v1/inventory/imports/preview",
      token,
      config.workspaceId,
      { method: "POST", body },
    );
    const contentType = upstream.headers.get("content-type") ?? "application/json";
    const payload = await upstream.arrayBuffer();
    return new Response(payload, {
      status: upstream.status,
      headers: { "Content-Type": contentType, "Cache-Control": "no-store" },
    });
  } catch {
    return Response.json({ detail: "Import preview unavailable." }, { status: 503 });
  }
}
