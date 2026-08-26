import { NextRequest, NextResponse } from "next/server";
import { backendUrl, getSessionToken } from "@/lib/auth";

/**
 * Backend-for-frontend proxy: forwards authenticated requests to the FastAPI
 * backend using the JWT held in the httpOnly session cookie, so the token
 * never reaches client-side JavaScript.
 *
 * Bodies are forwarded as raw ArrayBuffers in both directions so binary
 * payloads (multipart DICOM uploads, PNG previews) pass through untouched —
 * this must never assume JSON or text.
 */
async function handle(request: NextRequest, params: { path: string[] }) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const path = params.path.join("/");
  const search = request.nextUrl.search;
  const url = backendUrl(`/api/v1/${path}${search}`);

  const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
  const incomingContentType = request.headers.get("content-type");
  if (incomingContentType) headers["Content-Type"] = incomingContentType;

  const init: RequestInit = { method: request.method, headers, cache: "no-store" };

  if (request.method !== "GET" && request.method !== "HEAD") {
    const buffer = await request.arrayBuffer();
    if (buffer.byteLength > 0) init.body = buffer;
  }

  const backendResponse = await fetch(url, init);
  const responseBuffer = await backendResponse.arrayBuffer();
  const responseContentType = backendResponse.headers.get("content-type") ?? "application/octet-stream";

  return new NextResponse(responseBuffer, {
    status: backendResponse.status,
    headers: { "Content-Type": responseContentType },
  });
}

export async function GET(request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return handle(request, await ctx.params);
}
export async function POST(request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return handle(request, await ctx.params);
}
export async function PATCH(request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return handle(request, await ctx.params);
}
export async function DELETE(request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return handle(request, await ctx.params);
}
