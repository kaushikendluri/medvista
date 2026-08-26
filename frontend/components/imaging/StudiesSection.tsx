"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { LoadingState, ErrorState, EmptyState } from "@/components/common/States";
import { UploadStudyDialog } from "./UploadStudyDialog";
import { formatDate } from "@/lib/utils";
import type { StudySummary } from "@/types";

const STATUS_LABEL: Record<string, string> = {
  pending: "Pending",
  uploading: "Uploading",
  processing: "Processing",
  ready: "Ready",
  failed: "Failed",
};

export function StudiesSection({ patientId }: { patientId: string }) {
  const [showUpload, setShowUpload] = useState(false);
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["studies", patientId],
    queryFn: () => api.get<StudySummary[]>(`patients/${patientId}/studies`),
  });

  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-medium text-slate-300">Imaging Studies</h2>
        <button
          onClick={() => setShowUpload(true)}
          className="focus-ring rounded-md border border-accent/40 px-2.5 py-1 text-xs text-accent hover:bg-accent/10"
        >
          + Upload Study
        </button>
      </div>

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Unable to load imaging studies." onRetry={() => refetch()} />}
      {data && data.length === 0 && !isLoading && (
        <EmptyState
          title="No imaging studies available."
          description="Upload a DICOM file or .zip archive to get started."
        />
      )}
      {data && data.length > 0 && (
        <div className="glass-panel divide-y divide-base-700/50">
          {data.map((study) => (
            <Link
              key={study.id}
              href={`/patients/${patientId}/studies/${study.id}`}
              className="focus-ring flex items-center justify-between px-4 py-3 transition hover:bg-base-800/50"
            >
              <div>
                <p className="text-sm text-slate-200">
                  {study.study_description || `${study.modality} study`}
                  {study.body_part && <span className="text-slate-500"> · {study.body_part}</span>}
                </p>
                <p className="mt-0.5 text-[11px] text-slate-600">
                  {study.study_date ? formatDate(study.study_date) : "Date unknown"}
                  {study.institution && ` · ${study.institution}`}
                </p>
              </div>
              <span className="rounded-full border border-base-600 px-2 py-0.5 text-[10px] uppercase text-slate-500">
                {STATUS_LABEL[study.status] ?? study.status}
              </span>
            </Link>
          ))}
        </div>
      )}

      {showUpload && (
        <UploadStudyDialog patientId={patientId} onClose={() => setShowUpload(false)} />
      )}
    </section>
  );
}
