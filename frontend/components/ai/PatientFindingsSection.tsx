"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { LoadingState, ErrorState, EmptyState } from "@/components/common/States";
import { formatDateTime } from "@/lib/utils";
import type { PatientFindingRecord } from "@/types";

const STATUS_LABEL: Record<string, string> = {
  ai_flagged: "AI Flagged",
  physician_reviewing: "Reviewing",
  confirmed_by_physician: "Confirmed",
  dismissed: "Dismissed",
  uncertain: "Uncertain",
};

export function PatientFindingsSection({ patientId }: { patientId: string }) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["patient-ai-findings", patientId],
    queryFn: () => api.get<PatientFindingRecord[]>(`patients/${patientId}/ai-findings`),
  });

  return (
    <section>
      <h2 className="mb-3 text-sm font-medium text-slate-300">AI Findings</h2>
      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Unable to load AI findings." onRetry={() => refetch()} />}
      {data && data.length === 0 && (
        <EmptyState
          title="No AI findings."
          description="AI findings are decision support only and always require physician review. Run an analysis from an imaging study to generate findings."
        />
      )}
      {data && data.length > 0 && (
        <div className="glass-panel divide-y divide-base-700/50">
          {data.map((finding) => (
            <Link
              key={finding.id}
              href={`/patients/${patientId}/studies/${finding.study_id}`}
              className="focus-ring block px-4 py-3 transition hover:bg-base-800/50"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-200">{finding.finding_type}</span>
                <span className="rounded-full border border-base-600 px-2 py-0.5 text-[10px] uppercase text-slate-500">
                  {STATUS_LABEL[finding.status] ?? finding.status}
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-500">{finding.description}</p>
              <p className="mt-1 text-[11px] text-slate-600">
                {finding.anatomical_region && `${finding.anatomical_region} · `}
                {formatDateTime(finding.created_at)}
              </p>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
