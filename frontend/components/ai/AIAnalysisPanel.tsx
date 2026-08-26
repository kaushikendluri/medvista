"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { LoadingState, EmptyState } from "@/components/common/States";
import { formatDateTime } from "@/lib/utils";
import type { AIAnalysisRecord, AIFindingRecord, AIFindingStatus } from "@/types";

const IN_PROGRESS: AIAnalysisRecord["status"][] = ["queued", "running"];

const STATUS_LABEL: Record<AIAnalysisRecord["status"], string> = {
  queued: "Queued",
  running: "Processing…",
  completed: "Completed",
  failed: "Failed",
  unavailable: "Unavailable",
};

const FINDING_STATUS_LABEL: Record<AIFindingStatus, string> = {
  ai_flagged: "AI Flagged",
  physician_reviewing: "Physician Reviewing",
  confirmed_by_physician: "Confirmed",
  dismissed: "Dismissed",
  uncertain: "Uncertain",
};

export function AIAnalysisPanel({ studyId }: { studyId: string }) {
  const queryClient = useQueryClient();

  const analysesQuery = useQuery({
    queryKey: ["ai-analyses", studyId],
    queryFn: () => api.get<AIAnalysisRecord[]>(`studies/${studyId}/analyses`),
    refetchInterval: (query) => {
      const latest = query.state.data?.[0];
      return latest && IN_PROGRESS.includes(latest.status) ? 2000 : false;
    },
  });

  const findingsQuery = useQuery({
    queryKey: ["ai-findings", studyId],
    queryFn: () => api.get<AIFindingRecord[]>(`studies/${studyId}/findings`),
  });

  const runAnalysis = useMutation({
    mutationFn: () => api.post(`studies/${studyId}/analyze`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-analyses", studyId] });
      queryClient.invalidateQueries({ queryKey: ["ai-findings", studyId] });
    },
  });

  const reviewFinding = useMutation({
    mutationFn: ({ id, status }: { id: string; status: AIFindingStatus }) =>
      api.post(`findings/${id}/review`, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ai-findings", studyId] }),
  });

  const latest = analysesQuery.data?.[0];
  const busy = latest ? IN_PROGRESS.includes(latest.status) : false;

  return (
    <div className="flex flex-col gap-4 p-3">
      <div>
        <div className="mb-2 flex items-center justify-between px-1">
          <p className="text-[11px] uppercase tracking-wide text-slate-500">AI Analysis</p>
          <button
            onClick={() => runAnalysis.mutate()}
            disabled={busy || runAnalysis.isPending}
            className="focus-ring rounded-md border border-accent/40 px-2 py-1 text-[11px] text-accent hover:bg-accent/10 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy ? "Running…" : "Run AI Analysis"}
          </button>
        </div>

        {analysesQuery.isLoading && <LoadingState label="" />}

        {!analysesQuery.isLoading && !latest && (
          <EmptyState
            title="No AI analysis run yet."
            description="Decision-support only — any AI finding requires physician review."
          />
        )}

        {latest && (
          <div className="rounded-md border border-base-700/60 px-2.5 py-2 text-xs">
            <div className="flex items-center justify-between">
              <span
                className={
                  latest.status === "unavailable" || latest.status === "failed"
                    ? "text-status-warning"
                    : latest.status === "completed"
                      ? "text-status-success"
                      : "text-slate-300"
                }
              >
                {STATUS_LABEL[latest.status]}
              </span>
              <span className="text-[10px] text-slate-600">{formatDateTime(latest.created_at)}</span>
            </div>
            {latest.error && (
              <p className="mt-1.5 rounded border border-status-warning/30 bg-status-warning/10 px-2 py-1.5 text-[11px] text-status-warning">
                {latest.error}
              </p>
            )}
            {latest.status === "completed" && latest.processing_time_seconds != null && (
              <p className="mt-1 text-[10px] text-slate-600">
                Completed in {latest.processing_time_seconds.toFixed(2)}s
              </p>
            )}
          </div>
        )}
      </div>

      <div>
        <p className="mb-2 px-1 text-[11px] uppercase tracking-wide text-slate-500">AI Findings</p>
        {findingsQuery.isLoading && <LoadingState label="" />}
        {findingsQuery.data && findingsQuery.data.length === 0 && (
          <EmptyState title="No AI findings." description="Findings requiring review will appear here." />
        )}
        <div className="space-y-1.5">
          {findingsQuery.data?.map((finding) => (
            <div key={finding.id} className="rounded-md border border-base-700/60 px-2.5 py-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-200">{finding.finding_type}</span>
                {finding.confidence != null && (
                  <span className="font-mono text-[10px] text-slate-500">
                    {Math.round(finding.confidence * 100)}%
                  </span>
                )}
              </div>
              <p className="mt-1 text-[11px] text-slate-500">{finding.description}</p>
              {finding.anatomical_region && (
                <p className="mt-0.5 text-[10px] text-slate-600">Region: {finding.anatomical_region}</p>
              )}
              <select
                value={finding.status}
                onChange={(e) =>
                  reviewFinding.mutate({ id: finding.id, status: e.target.value as AIFindingStatus })
                }
                className="focus-ring mt-1.5 w-full rounded border border-base-600 bg-base-850 px-1.5 py-1 text-[11px] text-slate-300"
              >
                {Object.entries(FINDING_STATUS_LABEL).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
