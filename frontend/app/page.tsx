import { redirect } from "next/navigation";
import { getSessionToken } from "@/lib/auth";

export default async function RootPage() {
  const token = await getSessionToken();
  redirect(token ? "/dashboard" : "/login");
}
