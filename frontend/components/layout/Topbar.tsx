"use client";

import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth-store";
import { roleLabel } from "@/lib/utils";

export function Topbar() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-base-700/60 bg-base-900/40 px-6">
      <div className="text-xs text-slate-500">
        {user ? `${user.name} · ${roleLabel(user.role)}` : ""}
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={handleLogout}
          className="focus-ring rounded-md px-3 py-1.5 text-xs text-slate-400 transition hover:bg-base-800 hover:text-slate-200"
        >
          Sign out
        </button>
      </div>
    </header>
  );
}
