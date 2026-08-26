"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api-client";
import type { Patient, Sex } from "@/types";

export function CreatePatientDialog({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    external_patient_id: "",
    first_name: "",
    last_name: "",
    date_of_birth: "",
    sex: "unknown" as Sex,
  });
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => api.post<Patient>("patients", form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["patients"] });
      onClose();
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        const detail = err.detail as { detail?: unknown };
        setError(
          Array.isArray(detail?.detail)
            ? (detail.detail as { msg?: string }[]).map((d) => d.msg).join(", ")
            : (detail?.detail as string) ?? "Unable to create patient.",
        );
      } else {
        setError("Unable to create patient.");
      }
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="glass-panel w-full max-w-md p-6">
        <h2 className="mb-4 text-sm font-semibold text-slate-100">Create Patient</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setError(null);
            mutation.mutate();
          }}
          className="space-y-3"
        >
          <Field label="Patient ID (MRN)">
            <input
              required
              value={form.external_patient_id}
              onChange={(e) => setForm({ ...form, external_patient_id: e.target.value })}
              className="field"
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="First name">
              <input
                required
                value={form.first_name}
                onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                className="field"
              />
            </Field>
            <Field label="Last name">
              <input
                required
                value={form.last_name}
                onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                className="field"
              />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Date of birth">
              <input
                required
                type="date"
                value={form.date_of_birth}
                onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })}
                className="field"
              />
            </Field>
            <Field label="Sex">
              <select
                value={form.sex}
                onChange={(e) => setForm({ ...form, sex: e.target.value as Sex })}
                className="field"
              >
                <option value="unknown">Unknown</option>
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="other">Other</option>
              </select>
            </Field>
          </div>

          {error && (
            <p className="rounded-md border border-status-critical/30 bg-status-critical/10 px-3 py-2 text-xs text-status-critical">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="focus-ring rounded-md px-3 py-1.5 text-xs text-slate-400 hover:bg-base-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="focus-ring rounded-md bg-accent/90 px-3 py-1.5 text-xs font-medium text-base-950 hover:bg-accent disabled:opacity-50"
            >
              {mutation.isPending ? "Creating…" : "Create Patient"}
            </button>
          </div>
        </form>
      </div>
      <style jsx global>{`
        .field {
          width: 100%;
          border-radius: 6px;
          border: 1px solid rgb(51 64 79 / 1);
          background: rgb(20 24 32 / 1);
          padding: 0.4rem 0.6rem;
          font-size: 0.8rem;
          color: rgb(226 232 240 / 1);
        }
      `}</style>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11px] font-medium text-slate-500">{label}</span>
      {children}
    </label>
  );
}
