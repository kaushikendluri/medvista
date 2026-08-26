# API

Base path: `/api/v1`. Interactive docs at `/docs` (Swagger) and `/redoc` when the backend is running.

All endpoints except `/auth/login` require `Authorization: Bearer <jwt>`. The frontend never sends this header directly — it goes through the Next.js BFF proxy (see [ARCHITECTURE.md](ARCHITECTURE.md)).

## Auth

| Method | Path | Roles | Notes |
|---|---|---|---|
| POST | `/auth/login` | none | `{email, password}` → `{access_token, user}`. Writes an audit log entry. |
| GET | `/auth/me` | any authenticated | Current user |

## Users

| Method | Path | Roles | Notes |
|---|---|---|---|
| GET | `/users` | super_admin, hospital_admin | Scoped to caller's org unless super_admin |
| POST | `/users` | super_admin, hospital_admin | hospital_admin cannot create a super_admin (403) |

## Patients

| Method | Path | Roles | Notes |
|---|---|---|---|
| GET | `/patients?search=&page=&page_size=` | super_admin, hospital_admin, doctor, radiologist, technician | Paginated, org-scoped, name/ID search |
| POST | `/patients` | hospital_admin, doctor, technician, radiologist | Rejects a future `date_of_birth` |
| GET | `/patients/{id}` | (same as list) | 404 (not 403) across org boundary — avoids confirming existence |
| PATCH | `/patients/{id}` | hospital_admin, doctor, technician, radiologist | Partial update |
| GET | `/patients/{id}/timeline` | (same as list) | Merges clinical_history + patient_events + studies + reports, sorted descending. Empty until those tables have rows — never synthesized. |
| GET | `/patients/{id}/clinical-history` | (same as list) | |
| POST | `/patients/{id}/clinical-history` | hospital_admin, doctor, radiologist | |

Note: `researcher` is intentionally excluded from every identified-patient endpoint above — that role is scoped to de-identified research data (Phase 7), not real patient records.

## Studies (imaging)

| Method | Path | Roles | Notes |
|---|---|---|---|
| POST | `/patients/{id}/studies/upload` | hospital_admin, doctor, radiologist, technician | Multipart upload — individual `.dcm` files and/or `.zip` archives. Validates each file, extracts metadata via pydicom, uploads to Orthanc, upserts `studies`/`series`/`imaging_instances`. Per-file failures don't abort the batch; response lists every failure with its reason. Returns 503 if Orthanc is unreachable. |
| GET | `/patients/{id}/studies` | (same as list) | Real studies only — empty list until something is uploaded |
| GET | `/studies/{id}` | (same as list) | Includes series with live `instance_count` |
| GET | `/studies/{id}/series/{series_id}/instances` | (same as list) | Ordered by `instance_number` |
| GET | `/studies/{id}/instances/{instance_id}/preview` | (same as list) | Proxies Orthanc's rendered preview (PNG) — auth/RBAC/org-isolation checked before the proxy call, so Orthanc itself never needs to be reachable from the frontend directly |
| GET | `/studies/{id}/instances/{instance_id}/file` | (same as list) | Proxies Orthanc's original DICOM Part 10 file — consumed by the frontend's Cornerstone3D `wadouri` image loader, which parses the real dataset client-side |

A re-upload of an already-stored SOP instance is idempotent: `instances_already_present` increments instead of creating a duplicate row. A `study_uid` that already exists under a different patient is rejected per-file rather than silently reassigned.

## Imaging review (measurements & annotations)

| Method | Path | Roles | Notes |
|---|---|---|---|
| GET | `/studies/{id}/measurements` | hospital_admin, doctor, radiologist, technician (view), super_admin | |
| POST | `/studies/{id}/measurements` | hospital_admin, doctor, radiologist, super_admin | `source` is always `"physician"` here — AI-sourced measurements are written by the Phase 4 pipeline, never this endpoint |
| DELETE | `/measurements/{id}` | creator, or hospital_admin/super_admin | 403 for any other user, including other doctors |
| GET | `/studies/{id}/annotations` | (same view roles as measurements) | |
| POST | `/studies/{id}/annotations` | (same create roles as measurements) | |
| DELETE | `/annotations/{id}` | creator, or hospital_admin/super_admin | |

Geometry is stored exactly as Cornerstone3D's own tool state represents it (world-space handle points) rather than reprojected into a custom coordinate scheme. Today the viewer surfaces saved measurements/annotations as a real, accurate list (value, unit, author, timestamp — see the study viewer's right panel); re-rendering them back onto the canvas as overlays on revisit is not yet implemented, since it would need world-to-image coordinate reconstruction not yet validated end-to-end.

## AI

| Method | Path | Roles | Notes |
|---|---|---|---|
| GET | `/ai/models` | any authenticated | The model catalog. `status` is always computed from the worker's actual runnable-model registry, never trusted from the stored column — see [AI.md](AI.md) |
| POST | `/ai/models` | super_admin | Catalogs a model an org intends to use; does not by itself make it runnable |
| POST | `/studies/{id}/analyze` | hospital_admin, doctor, radiologist, super_admin | Creates a queued `ai_analyses` row and enqueues it on Redis; returns immediately |
| GET | `/studies/{id}/analyses` | (view roles) | Job history, newest first |
| GET | `/analyses/{id}` | (view roles) | Single job status |
| GET | `/studies/{id}/findings` | (view roles) | Real findings only — empty until a real model produces one |
| POST | `/findings/{id}/review` | hospital_admin, doctor, radiologist, super_admin | Transitions `ai_flagged` → `physician_reviewing`/`confirmed_by_physician`/`dismissed`/`uncertain` |
| GET | `/patients/{id}/ai-findings` | (patient view roles) | Findings aggregated across every study for this patient, newest first |

With no model implementation registered (the default), every `POST /studies/{id}/analyze` job legitimately resolves to `status=unavailable` with a specific error naming the study's modality — confirmed end-to-end against a real Redis queue and a separate worker process, not simulated.

## Dashboard

| Method | Path | Roles | Notes |
|---|---|---|---|
| GET | `/dashboard` | any authenticated | Stats + recent activity, computed live from the caller's organization. Every count is a real `COUNT(*)`/`JOIN`; tables with no data yet (studies, AI findings, reports) simply contribute 0. |

## Audit log

| Method | Path | Roles | Notes |
|---|---|---|---|
| GET | `/audit-log?page=&page_size=` | super_admin, hospital_admin | Paginated |

## Response shapes

Paginated endpoints return:

```json
{ "items": [...], "total": 0, "page": 1, "page_size": 25 }
```

Validation errors return HTTP 422 with FastAPI/Pydantic's standard `{"detail": [...]}` shape.

## Planned (not yet implemented — do not build a frontend against these)

`POST /studies/:id/compare`, `GET/POST /reports`, `POST /reports/:id/finalize`, `POST /copilot/query` — arrive with their respective phases in the [roadmap](README.md#roadmap).
