"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { LoadingState, EmptyState } from "@/components/common/States";
import { formatDateTime } from "@/lib/utils";
import type { AnnotationRecord, MeasurementRecord } from "@/types";

export function MeasurementsPanel({ studyId }: { studyId: string }) {
  const queryClient = useQueryClient();

  const measurementsQuery = useQuery({
    queryKey: ["measurements", studyId],
    queryFn: () => api.get<MeasurementRecord[]>(`studies/${studyId}/measurements`),
  });
  const annotationsQuery = useQuery({
    queryKey: ["annotations", studyId],
    queryFn: () => api.get<AnnotationRecord[]>(`studies/${studyId}/annotations`),
  });

  async function deleteMeasurement(id: string) {
    await api.del(`measurements/${id}`);
    queryClient.invalidateQueries({ queryKey: ["measurements", studyId] });
  }
  async function deleteAnnotation(id: string) {
    await api.del(`annotations/${id}`);
    queryClient.invalidateQueries({ queryKey: ["annotations", studyId] });
  }

  const loading = measurementsQuery.isLoading || annotationsQuery.isLoading;
  const measurements = measurementsQuery.data ?? [];
  const annotationList = annotationsQuery.data ?? [];

  return (
    <div className="flex flex-col gap-4 p-3">
      <div>
        <p className="mb-2 px-1 text-[11px] uppercase tracking-wide text-slate-500">Measurements</p>
        {loading && <LoadingState label="" />}
        {!loading && measurements.length === 0 && (
          <EmptyState title="No measurements yet." description="Use the Measure tool on the image." />
        )}
        <div className="space-y-1">
          {measurements.map((m) => (
            <div key={m.id} className="rounded-md border border-base-700/60 px-2.5 py-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-mono text-slate-200">
                  {m.value.toFixed(1)} {m.unit}
                </span>
                <button
                  onClick={() => deleteMeasurement(m.id)}
                  className="focus-ring text-[10px] text-slate-600 hover:text-status-critical"
                >
                  Delete
                </button>
              </div>
              <p className="mt-0.5 text-[10px] text-slate-600">
                {m.author_name ?? "Unknown"} · {formatDateTime(m.created_at)}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 px-1 text-[11px] uppercase tracking-wide text-slate-500">Annotations</p>
        {!loading && annotationList.length === 0 && (
          <EmptyState title="No annotations yet." description="Use the Annotate tool on the image." />
        )}
        <div className="space-y-1">
          {annotationList.map((a) => (
            <div key={a.id} className="rounded-md border border-base-700/60 px-2.5 py-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-200">{a.label || "(no label)"}</span>
                <button
                  onClick={() => deleteAnnotation(a.id)}
                  className="focus-ring text-[10px] text-slate-600 hover:text-status-critical"
                >
                  Delete
                </button>
              </div>
              <p className="mt-0.5 text-[10px] text-slate-600">
                {a.author_name ?? "Unknown"} · {formatDateTime(a.created_at)}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
