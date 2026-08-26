"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { LoadingState, ErrorState, EmptyState } from "@/components/common/States";
import { CreatePatientDialog } from "@/components/patient/CreatePatientDialog";
import { formatDate } from "@/lib/utils";
import type { Page, PatientSummary } from "@/types";

export default function PatientsPage() {
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const pageSize = 25;

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["patients", search, page],
    queryFn: () =>
      api.get<Page<PatientSummary>>(
        `patients?page=${page}&page_size=${pageSize}${search ? `&search=${encodeURIComponent(search)}` : ""}`,
      ),
    placeholderData: (prev) => prev,
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / pageSize)) : 1;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-slate-100">Patients</h1>
          <p className="text-xs text-slate-500">Search and manage patients in your organization.</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="focus-ring rounded-md bg-accent/90 px-3 py-1.5 text-xs font-medium text-base-950 hover:bg-accent"
        >
          + Create Patient
        </button>
      </div>

      <input
        value={searchInput}
        onChange={(e) => setSearchInput(e.target.value)}
        placeholder="Search by name or patient ID…"
        className="focus-ring mb-4 w-full max-w-sm rounded-md border border-base-600 bg-base-850 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600"
      />

      {isLoading && <LoadingState label="Loading patients…" />}
      {isError && <ErrorState message="Unable to load patients." onRetry={() => refetch()} />}

      {data && data.items.length === 0 && !isLoading && (
        <EmptyState
          title={search ? "No patients match your search." : "No patients yet."}
          description={search ? undefined : "Create your first patient to get started."}
          action={
            !search && (
              <button
                onClick={() => setShowCreate(true)}
                className="focus-ring mt-2 rounded-md border border-accent/40 px-3 py-1.5 text-xs text-accent hover:bg-accent/10"
              >
                Create your first patient
              </button>
            )
          }
        />
      )}

      {data && data.items.length > 0 && (
        <div className="glass-panel overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-base-700/60 text-left text-[11px] uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2.5 font-medium">Patient</th>
                <th className="px-4 py-2.5 font-medium">Patient ID</th>
                <th className="px-4 py-2.5 font-medium">Age</th>
                <th className="px-4 py-2.5 font-medium">Sex</th>
                <th className="px-4 py-2.5 font-medium">Date of Birth</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-base-700/40">
              {data.items.map((patient) => (
                <tr key={patient.id} className="transition hover:bg-base-800/50">
                  <td className="px-4 py-2.5">
                    <Link
                      href={`/patients/${patient.id}`}
                      className="focus-ring rounded text-slate-200 hover:text-accent"
                    >
                      {patient.first_name} {patient.last_name}
                    </Link>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs text-slate-500">
                    {patient.external_patient_id}
                  </td>
                  <td className="px-4 py-2.5 text-slate-400">{patient.age}</td>
                  <td className="px-4 py-2.5 capitalize text-slate-400">{patient.sex}</td>
                  <td className="px-4 py-2.5 text-slate-400">{formatDate(patient.date_of_birth)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data && data.total > pageSize && (
        <div className="mt-4 flex items-center justify-between text-xs text-slate-500">
          <span>
            Page {page} of {totalPages} · {data.total} patients
          </span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="focus-ring rounded-md border border-base-600 px-2.5 py-1 disabled:opacity-40"
            >
              Previous
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="focus-ring rounded-md border border-base-600 px-2.5 py-1 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {showCreate && <CreatePatientDialog onClose={() => setShowCreate(false)} />}
    </div>
  );
}
