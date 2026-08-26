"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { LoadingState, ErrorState, EmptyState } from "@/components/common/States";
import { StudiesSection } from "@/components/imaging/StudiesSection";
import { PatientFindingsSection } from "@/components/ai/PatientFindingsSection";
import { formatDate, formatDateTime, initials } from "@/lib/utils";
import type { ClinicalHistoryEntry, Patient, TimelineEvent } from "@/types";

export default function PatientProfilePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);

  const patientQuery = useQuery({
    queryKey: ["patient", id],
    queryFn: () => api.get<Patient>(`patients/${id}`),
  });
  const historyQuery = useQuery({
    queryKey: ["clinical-history", id],
    queryFn: () => api.get<ClinicalHistoryEntry[]>(`patients/${id}/clinical-history`),
    enabled: !!patientQuery.data,
  });
  const timelineQuery = useQuery({
    queryKey: ["timeline", id],
    queryFn: () => api.get<TimelineEvent[]>(`patients/${id}/timeline`),
    enabled: !!patientQuery.data,
  });

  if (patientQuery.isLoading) return <div className="px-6 py-8"><LoadingState label="Loading patient…" /></div>;
  if (patientQuery.isError || !patientQuery.data)
    return (
      <div className="px-6 py-8">
        <ErrorState message="Patient not found or you do not have access to this record." />
      </div>
    );

  const patient = patientQuery.data;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <div className="glass-panel mb-6 flex items-center gap-4 p-5">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent/15 text-sm font-semibold text-accent">
          {initials(patient.first_name, patient.last_name)}
        </div>
        <div className="flex-1">
          <h1 className="text-base font-semibold text-slate-100">
            {patient.first_name} {patient.last_name}
          </h1>
          <p className="text-xs text-slate-500">
            {patient.age} yrs · <span className="capitalize">{patient.sex}</span> · DOB{" "}
            {formatDate(patient.date_of_birth)} · ID {patient.external_patient_id}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section>
          <h2 className="mb-3 text-sm font-medium text-slate-300">Clinical History</h2>
          {historyQuery.isLoading && <LoadingState />}
          {historyQuery.data && historyQuery.data.length === 0 && (
            <EmptyState title="No clinical history recorded." />
          )}
          {historyQuery.data && historyQuery.data.length > 0 && (
            <div className="glass-panel divide-y divide-base-700/50">
              {historyQuery.data.map((entry) => (
                <div key={entry.id} className="px-4 py-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-200">{entry.condition}</span>
                    <span className="rounded-full border border-base-600 px-2 py-0.5 text-[10px] uppercase text-slate-500">
                      {entry.status}
                    </span>
                  </div>
                  {entry.description && (
                    <p className="mt-1 text-xs text-slate-500">{entry.description}</p>
                  )}
                  <p className="mt-1 text-[11px] text-slate-600">Source: {entry.source}</p>
                </div>
              ))}
            </div>
          )}
        </section>

        <section>
          <h2 className="mb-3 text-sm font-medium text-slate-300">Timeline</h2>
          {timelineQuery.isLoading && <LoadingState />}
          {timelineQuery.data && timelineQuery.data.length === 0 && (
            <EmptyState title="No timeline events yet." description="Imaging, labs, and reports will appear here as they are recorded." />
          )}
          {timelineQuery.data && timelineQuery.data.length > 0 && (
            <div className="glass-panel divide-y divide-base-700/50">
              {timelineQuery.data.map((event, i) => (
                <div key={i} className="px-4 py-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-200">{event.title}</span>
                    <span className="font-mono text-[11px] text-slate-600">
                      {formatDateTime(event.timestamp)}
                    </span>
                  </div>
                  {event.description && (
                    <p className="mt-1 text-xs text-slate-500">{event.description}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      <div className="mt-6">
        <StudiesSection patientId={id} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <PatientFindingsSection patientId={id} />
        <NotYetAvailable title="Reports" note="Report drafting arrives in Phase 5." />
      </div>
    </div>
  );
}

function NotYetAvailable({ title, note }: { title: string; note: string }) {
  return (
    <section>
      <h2 className="mb-3 text-sm font-medium text-slate-300">{title}</h2>
      <EmptyState title="Not yet available in this build." description={note} />
    </section>
  );
}
