import { cookies } from "next/headers";

export const SESSION_COOKIE = "mv_token";

export function backendUrl(path: string): string {
  const base = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";
  return `${base}${path}`;
}

export async function getSessionToken(): Promise<string | undefined> {
  const store = await cookies();
  return store.get(SESSION_COOKIE)?.value;
}
