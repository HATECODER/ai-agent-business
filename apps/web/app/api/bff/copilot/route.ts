import { NextRequest } from "next/server";

import { forwardCopilotQuery } from "@/lib/bff";
import { hasCompleteBffConfiguration, isTrustedMutationOrigin, readBffConfig } from "@/lib/bff-config";

export const runtime = "nodejs";

export async function POST(request: NextRequest): Promise<Response> {
  if (!hasCompleteBffConfiguration()) return Response.json({ detail: "Merchant session is not configured." }, { status: 503 });
  const config = readBffConfig();
  if (!isTrustedMutationOrigin(request.headers.get("origin"), config.appBaseUrl)) return Response.json({ detail: "Request origin denied." }, { status: 403 });
  let payload: unknown;
  try { payload = await request.json(); } catch { return Response.json({ detail: "Enter a supported question." }, { status: 400 }); }
  const message = typeof payload === "object" && payload !== null && "message" in payload ? (payload as { message?: unknown }).message : null;
  if (typeof message !== "string" || message.trim().length < 2 || message.length > 500) return Response.json({ detail: "Question must be between 2 and 500 characters." }, { status: 422 });
  return forwardCopilotQuery(message.trim());
}
