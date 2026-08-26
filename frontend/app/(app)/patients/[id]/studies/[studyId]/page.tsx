"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { LoadingState, ErrorState, EmptyState } from "@/components/common/States";
import { formatDate } from "@/lib/utils";
import type { InstanceSummary, StudyDetail } from "@/types";

export default function StudyViewerPage({
  params,
}: {
  params: Promise<{ id: string; studyId: string }>;
}) {
  const { id: patientId, studyId } = use(params);
  const [selectedSeriesId, setSelectedSeriesId] = useState<string | null>(null);
  const [instanceIndex, setInstanceIndex] = useState(0);

  const studyQuery = useQuery({
    queryKey: ["study", studyId],
    queryFn: () => api.get<StudyDetail>(`studies/${studyId}`),
  });

  useEffect(() => {
    const firstSeries = studyQuery.data?.series[0];
    if (firstSeries && !selectedSeriesId) {
      setSelectedSeriesId(firstSeries.id);
    }
  }, [studyQuery.data, selectedSeriesId]);

  const instancesQuery = useQuery({
    queryKey: ["instances", studyId, selectedSeriesId],
    queryFn: () =>
      api.get<InstanceSummary[]>(`studies/${studyId}/series/${selectedSeriesId}/instances`),
    enabled: !!selectedSeriesId,
  });

  useEffect(() => {
    setInstanceIndex(0);
  }, [selectedSeriesId]);

  if (studyQuery.isLoading) return <div className="px-6 py-8"><LoadingState label="Loading study…" /></div>;
  if (studyQuery.isError || !studyQuery.data)
    return (
      <div className="px-6 py-8">
        <ErrorState message="Study not found or you do not have access to it." />
      </div>
    );

  const study = studyQuery.data;
  const instances = instancesQuery.data ?? [];
  const currentInstance = instances[instanceIndex];

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-base-700/60 bg-base-900/40 px-6 py-3">
        <div>
          <Link
            href={`/patients/${patientId}`}
            className="focus-ring text-xs text-slate-500 hover:text-accent"
          >
            ← Back to patient
          </Link>
          <h1 className="mt-1 text-sm font-semibold text-slate-100">
            {study.study_description || `${study.modality} study`}
          </h1>
          <p className="text-[11px] text-slate-500">
            {study.study_date ? formatDate(study.study_date) : "Date unknown"}
            {study.body_part && ` · ${study.body_part}`} · {study.modality}
          </p>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        <aside className="w-56 shrink-0 overflow-y-auto border-r border-base-700/60 bg-base-900/30 p-3">
          <p className="mb-2 px-1 text-[11px] uppercase tracking-wide text-slate-500">Series</p>
          <div className="space-y-1">
            {study.series.map((series) => (
              <button
                key={series.id}
                onClick={() => setSelectedSeriesId(series.id)}
                className={`focus-ring w-full rounded-md px-3 py-2 text-left text-xs transition ${
                  series.id === selectedSeriesId
                    ? "bg-accent/10 text-accent"
                    : "text-slate-400 hover:bg-base-800"
                }`}
              >
                <p className="truncate">{series.description || `Series ${series.series_number ?? ""}`}</p>
                <p className="mt-0.5 text-[10px] text-slate-600">
                  {series.instance_count} image{series.instance_count === 1 ? "" : "s"}
                </p>
              </button>
            ))}
          </div>
        </aside>

        <main className="flex flex-1 flex-col items-center justify-center bg-black/40 p-6">
          {instancesQuery.isLoading && <LoadingState label="Loading images…" />}
          {instances.length === 0 && !instancesQuery.isLoading && (
            <EmptyState title="No images in this series." />
          )}
          {currentInstance && (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`/api/proxy/studies/${studyId}/instances/${currentInstance.id}/preview`}
                alt={`Instance ${currentInstance.instance_number ?? instanceIndex + 1}`}
                className="max-h-[70vh] max-w-full rounded-md border border-base-700/60 object-contain"
              />
              <div className="mt-4 flex items-center gap-4 text-xs text-slate-400">
                <button
                  disabled={instanceIndex === 0}
                  onClick={() => setInstanceIndex((i) => Math.max(0, i - 1))}
                  className="focus-ring rounded-md border border-base-600 px-2.5 py-1 disabled:opacity-30"
                >
                  ← Previous
                </button>
                <span className="font-mono">
                  Image {instanceIndex + 1} of {instances.length}
                </span>
                <button
                  disabled={instanceIndex >= instances.length - 1}
                  onClick={() => setInstanceIndex((i) => Math.min(instances.length - 1, i + 1))}
                  className="focus-ring rounded-md border border-base-600 px-2.5 py-1 disabled:opacity-30"
                >
                  Next →
                </button>
              </div>
              <p className="mt-3 max-w-md text-center text-[11px] text-slate-600">
                Basic preview rendering. Window/level, zoom/pan, measurements, and
                annotations arrive with the full imaging viewer in Phase 3.
              </p>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
