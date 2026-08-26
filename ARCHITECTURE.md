# Architecture

## System overview

```
Frontend (Next.js, App Router)
   │
   │  BFF pattern: /app/api/auth/* and /app/api/proxy/[...path]
   │  hold the JWT in an httpOnly cookie and attach it as a
   │  Bearer header when calling the backend. The token never
   │  reaches client-side JavaScript.
   ▼
FastAPI backend (app/)
   │
   ├─ core/     settings (env-only), JWT + bcrypt, RBAC dependency
   ├─ db/       SQLAlchemy engine/session
   ├─ models/   one class per table, full schema from day one
   ├─ schemas/  Pydantic contracts — separate from ORM models
   ├─ api/v1/   route handlers, thin — delegate to services/
   └─ services/ query/business logic (patient_service, dashboard_service, ...)
   │
   ▼
PostgreSQL — single source of truth for every entity
   │
   ├─ Redis            — cache / async job queue (from Phase 4)
   ├─ Orthanc/DICOMweb  — imaging storage (from Phase 2)
   └─ AI orchestration  — imaging models + clinical LLM, both behind a
                          swappable provider interface (from Phase 4/6)
```

## Why a full schema exists before the features that use it

Every table in [DATABASE.md](DATABASE.md) is created by the Phase 1 migration, including ones no endpoint touches yet (`studies`, `ai_findings`, `reports`, ...). This is deliberate: the dashboard, timeline, and organ-status logic are written as real `COUNT`/`JOIN` queries against these tables from the start. When Phase 2+ starts writing rows into them, no query needs to change — it just stops returning empty results. This is the mechanism that keeps the "nothing is hardcoded" rule true even for phases that aren't built yet: an empty table produces an honest empty state, not a fake number.

## Request flow: patient list example

1. Browser calls `GET /api/proxy/patients?search=...` (relative, same origin).
2. The proxy route reads the `mv_token` httpOnly cookie, forwards the request to `BACKEND_INTERNAL_URL/api/v1/patients` with `Authorization: Bearer <token>`.
3. FastAPI's `require_roles(...)` dependency decodes the JWT, loads the `User`, and rejects the request (403) if the role isn't clinical.
4. `patient_service.list_patients` builds a query scoped to `Patient.organization_id == current_user.organization_id` — this is the organization-isolation boundary, enforced in every query, not just at the router layer.
5. Result is serialized through a Pydantic schema (`PatientSummary`), which computes `age` from `date_of_birth` at request time — age is never stored.
6. Every view of a specific patient additionally writes an `AuditLog` row.

## Backend module boundaries

- **Routers (`api/v1/*.py`)** only: parse/validate input (via Pydantic + FastAPI `Depends`), call one service function, shape the response. No SQL, no business rules.
- **Services (`services/*.py`)** hold the actual query/business logic and are what tests exercise directly where useful.
- **Models (`models/*.py`)** are SQLAlchemy ORM classes only — no serialization logic. Pydantic schemas in `schemas/` are the only thing that ever reaches the wire.

This separation is what lets later phases (DICOM ingestion, AI job orchestration, report generation) add new services and routers without touching the auth/RBAC/audit plumbing built in Phase 1.

## Frontend structure

- `app/(app)/` — the authenticated shell (sidebar + topbar), wraps `/dashboard` and `/patients/*`.
- `app/login/` — public.
- `app/api/` — the BFF layer described above; the only place a JWT exists in the frontend process.
- `middleware.ts` — redirects for UX only (no session cookie → bounce to `/login`). It is **not** the authorization boundary; that's enforced server-side on every backend request regardless of what the frontend does.
- `store/auth-store.ts` — Zustand store holding the current user, populated by `AppShell` calling `/api/auth/me` on mount.
- `lib/api-client.ts` — typed fetch wrapper all data-fetching components use, always going through `/api/proxy/*`.

## AI provider abstraction (Phase 4/6, scaffolded now via config only)

`AI_PROVIDER` / `LLM_PROVIDER` are read from environment only. When unset, imaging analysis and the clinical copilot must report themselves as `unavailable` — this is a status value in the schema (`AIAnalysisStatus.UNAVAILABLE`), not a frontend-only message, so it survives even if the UI is bypassed.
