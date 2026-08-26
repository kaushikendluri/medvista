import { NextResponse } from "next/server";
import { backendUrl, getSessionToken } from "@/lib/auth";

export async function GET() {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const backendResponse = await fetch(backendUrl("/api/v1/auth/me"), {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  const data = await backendResponse.json();
  return NextResponse.json(data, { status: backendResponse.status });
}
