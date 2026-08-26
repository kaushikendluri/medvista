import { NextRequest, NextResponse } from "next/server";
import { backendUrl, getSessionToken } from "@/lib/auth";

/**
 * Backend-for-frontend proxy: forwards authenticated requests to the FastAPI
 * backend using the JWT held in the httpOnly session cookie, so the token
 * never reaches client-side JavaScript.
 */
async function handle(request: NextRequest, params: { path: string[] }) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const path = params.path.join("/");
  const search = request.nextUrl.search;
  const url = backendUrl(`/api/v1/${path}${search}`);

  const init: RequestInit = {
    method: request.method,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    cache: "no-store",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    const text = await request.text();
    if (text) init.body = text;
  }

  const backendResponse = await fetch(url, init);
  const contentType = backendResponse.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return new NextResponse(await backendResponse.text(), { status: backendResponse.status });
  }
  const data = await backendResponse.json();
  return NextResponse.json(data, { status: backendResponse.status });
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
