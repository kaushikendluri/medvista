"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { StatCard } from "@/components/common/StatCard";
import { LoadingState, ErrorState, EmptyState } from "@/components/common/States";
import { formatDateTime } from "@/lib/utils";
import type { DashboardResponse } from "@/types";

export default function DashboardPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.get<DashboardResponse>("dashboard"),
  });

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <h1 className="mb-1 text-lg font-semibold text-slate-100">Dashboard</h1>
      <p className="mb-6 text-xs text-slate-500">
        Live counts computed from your organization&apos;s data.
      </p>

      {isLoading && <LoadingState label="Loading dashboard…" />}
      {isError && <ErrorState message="Unable to load dashboard data." onRetry={() => refetch()} />}

      {data && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
            <StatCard label="Total Patients" value={data.stats.total_patients} />
            <StatCard label="Studies Today" value={data.stats.studies_today} />
            <StatCard label="Pending AI Reviews" value={data.stats.pending_ai_reviews} />
            <StatCard label="Reports Pending" value={data.stats.reports_pending} />
            <StatCard label="AI Analyses Running" value={data.stats.ai_analyses_running} />
          </div>

          <div className="mt-8">
            <h2 className="mb-3 text-sm font-medium text-slate-300">Recent Activity</h2>
            {data.recent_activity.length === 0 ? (
              <EmptyState
                title="Nothing to review."
                description="Activity will appear here as patients are created and studies are reviewed."
              />
            ) : (
              <div className="glass-panel divide-y divide-base-700/50">
                {data.recent_activity.map((item) => (
                  <div key={item.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
                    <div>
                      <span className="text-slate-300">{item.actor_name ?? "System"}</span>
                      <span className="mx-1.5 text-slate-600">·</span>
                      <span className="text-slate-500">{item.action}</span>
                    </div>
                    <span className="font-mono text-xs text-slate-600">
                      {formatDateTime(item.timestamp)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
