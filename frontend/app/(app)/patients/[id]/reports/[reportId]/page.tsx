"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { LoadingState, ErrorState } from "@/components/common/States";
import { formatDateTime } from "@/lib/utils";
import type { ReportRecord, ReportVersionRecord } from "@/types";

const STATUS_LABEL: Record<ReportRecord["status"], string> = {
  ai_draft: "AI Draft",
  physician_draft: "Draft",
  finalized: "Finalized",
  signed: "Signed",
};

export default function ReportDetailPage({
  params,
}: {
  params: Promise<{ id: string; reportId: string }>;
}) {
  const { id: patientId, reportId } = use(params);
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const [showVersions, setShowVersions] = useState(false);

  const reportQuery = useQuery({
    queryKey: ["report", reportId],
    queryFn: () => api.get<ReportRecord>(`reports/${reportId}`),
  });

  useEffect(() => {
    if (reportQuery.data) setDraft(reportQuery.data.draft_content ?? "");
  }, [reportQuery.data]);

  const versionsQuery = useQuery({
    queryKey: ["report-versions", reportId],
    queryFn: () => api.get<ReportVersionRecord[]>(`reports/${reportId}/versions`),
    enabled: showVersions,
  });

  const save = useMutation({
    mutationFn: () => api.patch<ReportRecord>(`reports/${reportId}`, { draft_content: draft }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["report", reportId] });
      queryClient.invalidateQueries({ queryKey: ["report-versions", reportId] });
    },
  });
  const finalize = useMutation({
    mutationFn: () => api.post<ReportRecord>(`reports/${reportId}/finalize`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["report", reportId] }),
  });
  const sign = useMutation({
    mutationFn: () => api.post<ReportRecord>(`reports/${reportId}/sign`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["report", reportId] }),
  });

  if (reportQuery.isLoading) return <div className="px-6 py-8"><LoadingState label="Loading report…" /></div>;
  if (reportQuery.isError || !reportQuery.data)
    return (
      <div className="px-6 py-8">
        <ErrorState message="Report not found or you do not have access to it." />
      </div>
    );

  const report = reportQuery.data;
  const editable = report.status === "physician_draft";
  const dirty = editable && draft !== (report.draft_content ?? "");

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <Link href={`/patients/${patientId}`} className="focus-ring text-xs text-slate-500 hover:text-accent">
        ← Back to patient
      </Link>

      <div className="mt-2 mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-base font-semibold text-slate-100">Report</h1>
          <p className="text-xs text-slate-500">
            {report.author_name ?? "Unknown author"} · Created {formatDateTime(report.created_at)}
            {report.signed_at && ` · Signed ${formatDateTime(report.signed_at)}`}
          </p>
        </div>
        <span className="rounded-full border border-base-600 px-2.5 py-1 text-xs uppercase text-slate-400">
          {STATUS_LABEL[report.status]}
        </span>
      </div>

      <textarea
        value={editable ? draft : (report.finalized_content ?? report.draft_content ?? "")}
        onChange={(e) => setDraft(e.target.value)}
        readOnly={!editable}
        rows={22}
        className="focus-ring w-full resize-y rounded-md border border-base-600 bg-base-850 p-4 font-mono text-xs leading-relaxed text-slate-200 disabled:opacity-70"
      />

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {editable && (
          <>
            <button
              onClick={() => save.mutate()}
              disabled={!dirty || save.isPending}
              className="focus-ring rounded-md bg-accent/90 px-3 py-1.5 text-xs font-medium text-base-950 hover:bg-accent disabled:cursor-not-allowed disabled:opacity-40"
            >
              {save.isPending ? "Saving…" : "Save Draft"}
            </button>
            <button
              onClick={() => finalize.mutate()}
              disabled={dirty || finalize.isPending}
              className="focus-ring rounded-md border border-base-600 px-3 py-1.5 text-xs text-slate-300 hover:bg-base-800 disabled:cursor-not-allowed disabled:opacity-40"
              title={dirty ? "Save your changes before finalizing" : undefined}
            >
              Finalize
            </button>
          </>
        )}
        {report.status === "finalized" && (
          <button
            onClick={() => sign.mutate()}
            disabled={sign.isPending}
            className="focus-ring rounded-md bg-accent/90 px-3 py-1.5 text-xs font-medium text-base-950 hover:bg-accent"
          >
            Sign Report
          </button>
        )}
        <button
          onClick={() => setShowVersions((v) => !v)}
          className="focus-ring ml-auto rounded-md px-3 py-1.5 text-xs text-slate-400 hover:bg-base-800"
        >
          {showVersions ? "Hide" : "Show"} version history
        </button>
      </div>

      {report.status === "signed" && (
        <p className="mt-3 text-[11px] text-slate-600">
          This report is signed and immutable. Physician-finalized content — not an AI output.
        </p>
      )}

      {showVersions && (
        <div className="mt-4 glass-panel divide-y divide-base-700/50">
          {versionsQuery.data && versionsQuery.data.length === 0 && (
            <p className="px-4 py-3 text-xs text-slate-500">No prior versions.</p>
          )}
          {versionsQuery.data?.map((v) => (
            <div key={v.id} className="px-4 py-3">
              <p className="text-xs text-slate-400">
                Version {v.version_number} · {v.author_name ?? "Unknown"} · {formatDateTime(v.created_at)}
              </p>
              <pre className="mt-1.5 whitespace-pre-wrap font-mono text-[11px] text-slate-500">{v.content}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
