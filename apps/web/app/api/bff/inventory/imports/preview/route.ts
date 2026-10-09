import { NextRequest } from "next/server";

import { getAuth0Client } from "@/lib/auth0";
import { hasCompleteBffConfiguration, isTrustedMutationOrigin, readBffConfig } from "@/lib/bff-config";
import { forwardInventoryPreview } from "@/lib/bff";

export const runtime = "nodejs";

const MAX_FILE_BYTES = 5 * 1024 * 1024;

export async function POST(request: NextRequest): Promise<Response> {
  if (!hasCompleteBffConfiguration()) {
    return Response.json({ detail: "Merchant session is not configured." }, { status: 503 });
  }
  const config = readBffConfig();
  if (!isTrustedMutationOrigin(request.headers.get("origin"), config.appBaseUrl)) {
    return Response.json({ detail: "Request origin denied." }, { status: 403 });
  }
  const auth0 = getAuth0Client();
  if (!auth0 || !(await auth0.getSession())) {
    return Response.json({ detail: "Authentication required." }, { status: 401 });
  }
  const declaredLength = Number(request.headers.get("content-length") ?? "0");
  if (Number.isFinite(declaredLength) && declaredLength > MAX_FILE_BYTES + 64 * 1024) {
    return Response.json({ detail: "CSV file is too large." }, { status: 413 });
  }
  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return Response.json({ detail: "Upload one valid CSV file." }, { status: 400 });
  }
  const file = form.get("file");
  if (!(file instanceof File) || file.size === 0 || file.size > MAX_FILE_BYTES) {
    return Response.json({ detail: "Upload one CSV file up to 5 MB." }, { status: 422 });
  }
  return forwardInventoryPreview(file);
}
