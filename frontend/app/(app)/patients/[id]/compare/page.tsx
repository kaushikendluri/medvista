"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { LoadingState, ErrorState, EmptyState } from "@/components/common/States";
import { CompareViewportPanel } from "@/components/imaging/CompareViewportPanel";
import { formatDate } from "@/lib/utils";
import type { ComparisonResult, StudySummary } from "@/types";

const RELATIONSHIP_LABEL: Record<string, string> = {
  present_in_both: "Present in both",
  new_in_b: "New in later study",
  not_re_flagged_in_b: "Not re-flagged in later study",
};

export default function ComparePage({ params }: { params: Promise<{ id: string }> }) {
  const { id: patientId } = use(params);
  const [studyAId, setStudyAId] = useState("");
  const [studyBId, setStudyBId] = useState("");

  const studiesQuery = useQuery({
    queryKey: ["studies", patientId],
    queryFn: () => api.get<StudySummary[]>(`patients/${patientId}/studies`),
  });

  const comparisonQuery = useQuery({
    queryKey: ["compare", studyAId, studyBId],
    queryFn: () => api.get<ComparisonResult>(`studies/${studyAId}/compare/${studyBId}`),
    enabled: !!studyAId && !!studyBId && studyAId !== studyBId,
  });

  const studies = studiesQuery.data ?? [];

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <Link href={`/patients/${patientId}`} className="focus-ring text-xs text-slate-500 hover:text-accent">
        ← Back to patient
      </Link>
      <h1 className="mt-2 mb-1 text-lg font-semibold text-slate-100">Compare Studies</h1>
      <p className="mb-6 text-xs text-slate-500">
        Select two studies to compare. Studies of different modalities are not directly comparable.
      </p>

      {studiesQuery.isLoading && <LoadingState label="Loading studies…" />}
      {studies.length < 2 && !studiesQuery.isLoading && (
        <EmptyState
          title="At least two studies are needed to compare."
          description="Upload another imaging study for this patient to use comparison."
        />
      )}

      {studies.length >= 2 && (
        <>
          <div className="mb-6 flex flex-wrap items-center gap-3">
            <StudyPicker label="Study A" value={studyAId} onChange={setStudyAId} studies={studies} />
            <span className="text-slate-600">vs.</span>
            <StudyPicker label="Study B" value={studyBId} onChange={setStudyBId} studies={studies} />
          </div>

          {comparisonQuery.isLoading && <LoadingState label="Comparing…" />}
          {comparisonQuery.isError && <ErrorState message="Unable to compare these studies." />}

          {comparisonQuery.data && !comparisonQuery.data.comparable && (
            <EmptyState title="Unable to establish a reliable comparison." description={comparisonQuery.data.reason ?? undefined} />
          )}

          {comparisonQuery.data && comparisonQuery.data.comparable && (
            <>
              <div className="mb-6 flex h-[420px] gap-3">
                <CompareViewportPanel studyId={comparisonQuery.data.study_a.id} label="Earlier study" />
                <CompareViewportPanel studyId={comparisonQuery.data.study_b.id} label="Later study" />
              </div>

              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                <section>
                  <h2 className="mb-3 text-sm font-medium text-slate-300">Measurement Changes</h2>
                  {comparisonQuery.data.measurement_comparisons.length === 0 ? (
                    <EmptyState title="No measurements recorded on either study." />
                  ) : (
                    <div className="glass-panel divide-y divide-base-700/50">
                      {comparisonQuery.data.measurement_comparisons.map((m, i) => (
                        <div key={i} className="px-4 py-3 text-sm">
                          <div className="flex items-center justify-between">
                            <span className="text-slate-200 capitalize">{m.type}</span>
                            {m.delta != null && (
                              <span className={m.delta > 0 ? "text-status-warning" : "text-status-success"}>
                                {m.delta > 0 ? "+" : ""}
                                {m.delta} {m.unit}
                                {m.percent_change != null && ` (${m.percent_change > 0 ? "+" : ""}${m.percent_change}%)`}
                              </span>
                            )}
                          </div>
                          {m.value_a != null && m.value_b != null && (
                            <p className="mt-1 text-xs text-slate-500">
                              {m.value_a} {m.unit} → {m.value_b} {m.unit}
                            </p>
                          )}
                          <p className="mt-1 text-[11px] text-slate-600">{m.note}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </section>

                <section>
                  <h2 className="mb-3 text-sm font-medium text-slate-300">Finding Changes</h2>
                  {comparisonQuery.data.finding_comparisons.length === 0 ? (
                    <EmptyState title="No AI findings recorded on either study." />
                  ) : (
                    <div className="glass-panel divide-y divide-base-700/50">
                      {comparisonQuery.data.finding_comparisons.map((f, i) => (
                        <div key={i} className="px-4 py-3 text-sm">
                          <div className="flex items-center justify-between">
                            <span className="text-slate-200">{f.finding_type}</span>
                            <span className="rounded-full border border-base-600 px-2 py-0.5 text-[10px] uppercase text-slate-500">
                              {RELATIONSHIP_LABEL[f.relationship] ?? f.relationship}
                            </span>
                          </div>
                          {f.anatomical_region && (
                            <p className="mt-1 text-xs text-slate-500">{f.anatomical_region}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </section>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}

function StudyPicker({
  label,
  value,
  onChange,
  studies,
}: {
  label: string;
  value: string;
  onChange: (id: string) => void;
  studies: StudySummary[];
}) {
  return (
    <label className="text-xs text-slate-500">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="focus-ring ml-2 rounded-md border border-base-600 bg-base-850 px-2 py-1.5 text-xs text-slate-300"
      >
        <option value="">Select a study…</option>
        {studies.map((s) => (
          <option key={s.id} value={s.id}>
            {s.study_description || s.modality} — {s.study_date ? formatDate(s.study_date) : "date unknown"}
          </option>
        ))}
      </select>
    </label>
  );
}
