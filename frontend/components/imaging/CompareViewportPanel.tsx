"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { LoadingState, EmptyState } from "@/components/common/States";
import { DicomViewport } from "@/components/imaging/DicomViewport";
import { formatDate } from "@/lib/utils";
import type { InstanceSummary, StudyDetail as StudyDetailType } from "@/types";

export function CompareViewportPanel({ studyId, label }: { studyId: string; label: string }) {
  const [seriesId, setSeriesId] = useState<string | null>(null);

  const studyQuery = useQuery({
    queryKey: ["study", studyId],
    queryFn: () => api.get<StudyDetailType>(`studies/${studyId}`),
  });

  useEffect(() => {
    const first = studyQuery.data?.series[0];
    if (first && !seriesId) setSeriesId(first.id);
  }, [studyQuery.data, seriesId]);

  const instancesQuery = useQuery({
    queryKey: ["instances", studyId, seriesId],
    queryFn: () => api.get<InstanceSummary[]>(`studies/${studyId}/series/${seriesId}/instances`),
    enabled: !!seriesId,
  });

  const imageIds = useMemo(
    () =>
      (instancesQuery.data ?? []).map(
        (instance) => `wadouri:/api/proxy/studies/${studyId}/instances/${instance.id}/file`,
      ),
    [instancesQuery.data, studyId],
  );

  return (
    <div className="flex flex-1 flex-col overflow-hidden rounded-md border border-base-700/60">
      <div className="flex items-center justify-between border-b border-base-700/60 bg-base-900/40 px-3 py-2 text-xs">
        <span className="text-slate-300">{label}</span>
        {studyQuery.data && (
          <span className="text-slate-500">
            {studyQuery.data.study_date ? formatDate(studyQuery.data.study_date) : "Date unknown"} ·{" "}
            {studyQuery.data.modality}
          </span>
        )}
        {studyQuery.data && studyQuery.data.series.length > 1 && (
          <select
            value={seriesId ?? ""}
            onChange={(e) => setSeriesId(e.target.value)}
            className="focus-ring rounded border border-base-600 bg-base-850 px-1.5 py-0.5 text-[11px] text-slate-300"
          >
            {studyQuery.data.series.map((s) => (
              <option key={s.id} value={s.id}>
                {s.description || `Series ${s.series_number ?? ""}`}
              </option>
            ))}
          </select>
        )}
      </div>
      <div className="relative flex-1 bg-black/40">
        {(studyQuery.isLoading || instancesQuery.isLoading) && (
          <div className="flex h-full items-center justify-center">
            <LoadingState label="Loading…" />
          </div>
        )}
        {imageIds.length === 0 && !instancesQuery.isLoading && !studyQuery.isLoading && (
          <div className="flex h-full items-center justify-center">
            <EmptyState title="No images in this series." />
          </div>
        )}
        {imageIds.length > 0 && <DicomViewport key={seriesId} imageIds={imageIds} />}
      </div>
    </div>
  );
}
