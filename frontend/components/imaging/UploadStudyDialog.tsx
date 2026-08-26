"use client";

import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { uploadWithProgress, ApiError } from "@/lib/api-client";
import type { UploadResult } from "@/types";

type Phase = "idle" | "uploading" | "processing" | "done" | "error";

export function UploadStudyDialog({
  patientId,
  onClose,
}: {
  patientId: string;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleFiles(files: FileList) {
    setPhase("uploading");
    setProgress(0);
    setError(null);
    try {
      const uploadResult = await uploadWithProgress<UploadResult>(
        `patients/${patientId}/studies/upload`,
        Array.from(files),
        (percent) => {
          setProgress(percent);
          if (percent >= 100) setPhase("processing");
        },
      );
      setResult(uploadResult);
      setPhase("done");
      queryClient.invalidateQueries({ queryKey: ["studies", patientId] });
      queryClient.invalidateQueries({ queryKey: ["timeline", patientId] });
    } catch (err) {
      setPhase("error");
      if (err instanceof ApiError) {
        const detail = err.detail as { detail?: string };
        setError(typeof detail?.detail === "string" ? detail.detail : "Upload failed.");
      } else {
        setError("Upload failed.");
      }
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="glass-panel w-full max-w-lg p-6">
        <h2 className="mb-1 text-sm font-semibold text-slate-100">Upload DICOM Study</h2>
        <p className="mb-4 text-xs text-slate-500">
          Select individual .dcm files or a .zip archive containing a study.
        </p>

        {phase === "idle" && (
          <div
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              if (e.dataTransfer.files.length > 0) handleFiles(e.dataTransfer.files);
            }}
            className="focus-ring cursor-pointer rounded-md border border-dashed border-base-600 px-4 py-10 text-center text-sm text-slate-500 transition hover:border-accent/50 hover:text-slate-300"
          >
            Click or drag files here
            <input
              ref={inputRef}
              type="file"
              multiple
              accept=".dcm,.zip,application/dicom"
              className="hidden"
              onChange={(e) => e.target.files && handleFiles(e.target.files)}
            />
          </div>
        )}

        {(phase === "uploading" || phase === "processing") && (
          <div className="py-6">
            <div className="mb-2 flex justify-between text-xs text-slate-400">
              <span>{phase === "uploading" ? "Uploading" : "Processing DICOM…"}</span>
              {phase === "uploading" && <span className="font-mono">{progress}%</span>}
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-base-800">
              <div
                className="h-full bg-accent transition-all"
                style={{ width: phase === "uploading" ? `${progress}%` : "100%" }}
              />
            </div>
          </div>
        )}

        {phase === "done" && result && (
          <div className="py-4">
            <p className="mb-2 text-sm text-slate-200">
              {result.instances_created} image{result.instances_created === 1 ? "" : "s"} indexed
              {result.instances_already_present > 0 &&
                ` (${result.instances_already_present} already present)`}
              .
            </p>
            {result.failures.length > 0 && (
              <div className="mt-2 space-y-1 rounded-md border border-status-warning/30 bg-status-warning/10 px-3 py-2 text-xs text-status-warning">
                {result.failures.map((f, i) => (
                  <p key={i}>
                    {f.filename}: {f.reason}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}

        {phase === "error" && (
          <p className="my-4 rounded-md border border-status-critical/30 bg-status-critical/10 px-3 py-2 text-xs text-status-critical">
            {error}
          </p>
        )}

        <div className="mt-4 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="focus-ring rounded-md px-3 py-1.5 text-xs text-slate-400 hover:bg-base-800"
          >
            {phase === "done" ? "Close" : "Cancel"}
          </button>
        </div>
      </div>
    </div>
  );
}
