"use client";

import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { useAuthStore } from "@/store/auth-store";
import type { User } from "@/types";

async function fetchMe(): Promise<User> {
  const response = await fetch("/api/auth/me");
  if (!response.ok) throw new Error("Not authenticated");
  return response.json();
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const setUser = useAuthStore((s) => s.setUser);
  const status = useAuthStore((s) => s.status);

  const { data, isError } = useQuery({ queryKey: ["me"], queryFn: fetchMe, retry: false });

  useEffect(() => {
    if (data) setUser(data);
    else if (isError) setUser(null);
  }, [data, isError, setUser]);

  return (
    <div className="flex h-screen overflow-hidden bg-base-950">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex-1 overflow-y-auto">
          {status === "loading" ? null : children}
        </main>
      </div>
    </div>
  );
}
