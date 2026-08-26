"use client";

import { use, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { LoadingState, ErrorState, EmptyState } from "@/components/common/States";
import { DicomViewport, type DicomViewportHandle, type PersistedAnnotationPayload } from "@/components/imaging/DicomViewport";
import { ViewerToolbar } from "@/components/imaging/ViewerToolbar";
import { MeasurementsPanel } from "@/components/imaging/MeasurementsPanel";
import { AIAnalysisPanel } from "@/components/ai/AIAnalysisPanel";
import { setActivePrimaryTool, type ToolKey } from "@/lib/cornerstone-viewer";
import { formatDate } from "@/lib/utils";
import type { InstanceSummary, StudyDetail } from "@/types";

export default function StudyViewerPage({
  params,
}: {
  params: Promise<{ id: string; studyId: string }>;
}) {
  const { id: patientId, studyId } = use(params);
  const queryClient = useQueryClient();
  const viewportRef = useRef<DicomViewportHandle>(null);

  const [selectedSeriesId, setSelectedSeriesId] = useState<string | null>(null);
  const [activeTool, setActiveTool] = useState<ToolKey>("WindowLevel");
  const [imageIndex, setImageIndex] = useState(0);
  const [imageCount, setImageCount] = useState(0);
  const [viewerError, setViewerError] = useState<string | null>(null);

  const studyQuery = useQuery({
    queryKey: ["study", studyId],
    queryFn: () => api.get<StudyDetail>(`studies/${studyId}`),
  });

  useEffect(() => {
    const firstSeries = studyQuery.data?.series[0];
    if (firstSeries && !selectedSeriesId) setSelectedSeriesId(firstSeries.id);
  }, [studyQuery.data, selectedSeriesId]);

  const instancesQuery = useQuery({
    queryKey: ["instances", studyId, selectedSeriesId],
    queryFn: () =>
      api.get<InstanceSummary[]>(`studies/${studyId}/series/${selectedSeriesId}/instances`),
    enabled: !!selectedSeriesId,
  });

  const imageIds = useMemo(() => {
    const instances = instancesQuery.data ?? [];
    return instances.map(
      (instance) => `wadouri:/api/proxy/studies/${studyId}/instances/${instance.id}/file`,
    );
  }, [instancesQuery.data, studyId]);

  useEffect(() => {
    setViewerError(null);
  }, [selectedSeriesId]);

  const saveMeasurement = useMutation({
    mutationFn: (payload: PersistedAnnotationPayload) =>
      api.post(`studies/${studyId}/measurements`, {
        series_id: selectedSeriesId,
        type: "length",
        value: payload.value ?? 0,
        unit: payload.unit ?? "mm",
        geometry: payload.geometry,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["measurements", studyId] }),
  });

  const saveAnnotation = useMutation({
    mutationFn: (payload: PersistedAnnotationPayload) =>
      api.post(`studies/${studyId}/annotations`, {
        series_id: selectedSeriesId,
        type: "arrow",
        label: payload.label ?? "",
        geometry: payload.geometry,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["annotations", studyId] }),
  });

  function handleAnnotationCompleted(payload: PersistedAnnotationPayload) {
    if (payload.kind === "measurement") saveMeasurement.mutate(payload);
    else saveAnnotation.mutate(payload);
  }

  function handleToolChange(tool: ToolKey) {
    setActiveTool(tool);
    try {
      setActivePrimaryTool(tool);
    } catch {
      // Tool group not ready yet (viewport still initializing) — the next
      // render of DicomViewport establishes it, so this is a harmless no-op.
    }
  }

  if (studyQuery.isLoading) return <div className="px-6 py-8"><LoadingState label="Loading study…" /></div>;
  if (studyQuery.isError || !studyQuery.data)
    return (
      <div className="px-6 py-8">
        <ErrorState message="Study not found or you do not have access to it." />
      </div>
    );

  const study = studyQuery.data;

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

      <ViewerToolbar
        activeTool={activeTool}
        onToolChange={handleToolChange}
        onPreset={(ww, wc) => viewportRef.current?.applyWindowLevel(ww, wc)}
        onReset={() => viewportRef.current?.reset()}
        onInvert={() => viewportRef.current?.toggleInvert()}
      />

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

        <main className="relative flex flex-1 flex-col bg-black/40">
          {instancesQuery.isLoading && (
            <div className="flex flex-1 items-center justify-center">
              <LoadingState label="Loading images…" />
            </div>
          )}
          {imageIds.length === 0 && !instancesQuery.isLoading && (
            <div className="flex flex-1 items-center justify-center">
              <EmptyState title="No images in this series." />
            </div>
          )}
          {viewerError && (
            <div className="flex flex-1 items-center justify-center">
              <ErrorState message={viewerError} />
            </div>
          )}
          {imageIds.length > 0 && !viewerError && (
            <>
              <div className="flex-1">
                <DicomViewport
                  key={selectedSeriesId}
                  ref={viewportRef}
                  imageIds={imageIds}
                  onIndexChange={(index, total) => {
                    setImageIndex(index);
                    setImageCount(total);
                  }}
                  onAnnotationCompleted={handleAnnotationCompleted}
                  onError={setViewerError}
                />
              </div>
              <div className="flex items-center justify-center gap-4 border-t border-base-700/60 bg-base-900/40 px-4 py-2 text-xs text-slate-400">
                <button
                  disabled={imageIndex === 0}
                  onClick={() => viewportRef.current?.goToIndex(Math.max(0, imageIndex - 1))}
                  className="focus-ring rounded-md border border-base-600 px-2.5 py-1 disabled:opacity-30"
                >
                  ← Previous
                </button>
                <span className="font-mono">
                  Image {imageCount === 0 ? 0 : imageIndex + 1} of {imageCount}
                </span>
                <button
                  disabled={imageIndex >= imageCount - 1}
                  onClick={() => viewportRef.current?.goToIndex(Math.min(imageCount - 1, imageIndex + 1))}
                  className="focus-ring rounded-md border border-base-600 px-2.5 py-1 disabled:opacity-30"
                >
                  Next →
                </button>
                <span className="ml-4 text-[10px] text-slate-600">
                  Scroll wheel scrolls the stack · left-drag: {activeTool} · right-drag: zoom · middle-drag: pan
                </span>
              </div>
            </>
          )}
        </main>

        <aside className="w-72 shrink-0 divide-y divide-base-700/60 overflow-y-auto border-l border-base-700/60 bg-base-900/30">
          <AIAnalysisPanel studyId={studyId} />
          <MeasurementsPanel studyId={studyId} />
        </aside>
      </div>
    </div>
  );
}
