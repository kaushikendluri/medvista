"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { LoadingState, ErrorState, EmptyState } from "@/components/common/States";
import { formatDateTime } from "@/lib/utils";
import type { ReportRecord } from "@/types";

const STATUS_LABEL: Record<ReportRecord["status"], string> = {
  ai_draft: "AI Draft",
  physician_draft: "Draft",
  finalized: "Finalized",
  signed: "Signed",
};

export function ReportsSection({ patientId }: { patientId: string }) {
  const queryClient = useQueryClient();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["reports", patientId],
    queryFn: () => api.get<ReportRecord[]>(`patients/${patientId}/reports`),
  });

  const createReport = useMutation({
    mutationFn: () => api.post<ReportRecord>(`patients/${patientId}/reports`, {}),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reports", patientId] }),
  });

  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-medium text-slate-300">Reports</h2>
        <button
          onClick={() => createReport.mutate()}
          disabled={createReport.isPending}
          className="focus-ring rounded-md border border-accent/40 px-2.5 py-1 text-xs text-accent hover:bg-accent/10 disabled:opacity-50"
        >
          {createReport.isPending ? "Creating…" : "+ New Report"}
        </button>
      </div>

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Unable to load reports." onRetry={() => refetch()} />}
      {data && data.length === 0 && (
        <EmptyState
          title="No reports yet."
          description="A new report is assembled from real patient/study data — not AI-generated — for the physician to complete and sign."
        />
      )}
      {data && data.length > 0 && (
        <div className="glass-panel divide-y divide-base-700/50">
          {data.map((report) => (
            <Link
              key={report.id}
              href={`/patients/${patientId}/reports/${report.id}`}
              className="focus-ring flex items-center justify-between px-4 py-3 transition hover:bg-base-800/50"
            >
              <div>
                <p className="text-sm text-slate-200">Report — {formatDateTime(report.created_at)}</p>
                <p className="mt-0.5 text-[11px] text-slate-600">{report.author_name ?? "Unknown author"}</p>
              </div>
              <span className="rounded-full border border-base-600 px-2 py-0.5 text-[10px] uppercase text-slate-500">
                {STATUS_LABEL[report.status]}
              </span>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
