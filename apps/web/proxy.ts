import { NextRequest, NextResponse } from "next/server";

import { getAuth0Client } from "@/lib/auth0";
import { hasCompleteBffConfiguration, readAuth0Config } from "@/lib/bff-config";

function contentSecurityPolicy(nonce: string): string {
  const development = process.env.NODE_ENV !== "production";
  const authDomain = hasCompleteBffConfiguration() ? `https://${readAuth0Config().domain}` : "";
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${development ? " 'unsafe-eval'" : ""}`,
    `style-src 'self' 'nonce-${nonce}'`,
    "img-src 'self' data:",
    "font-src 'self'",
    `connect-src 'self'${development ? " ws: http:" : ""}`,
    "object-src 'none'",
    "base-uri 'self'",
    `form-action 'self' ${authDomain}`.trim(),
    "frame-ancestors 'none'",
    "upgrade-insecure-requests",
  ].join("; ");
}

export async function proxy(request: NextRequest): Promise<NextResponse> {
  if (request.nextUrl.pathname.startsWith("/auth/") && hasCompleteBffConfiguration()) {
    return (await getAuth0Client()!.middleware(request)) as NextResponse;
  }

  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");
  const policy = contentSecurityPolicy(nonce);
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", policy);
  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", policy);
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)"],
};
