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

`POST /studies/upload`, `GET /studies/:id/series`, `POST /studies/:id/analyze`, `GET /studies/:id/findings`, `POST /findings/:id/review`, `POST /studies/:id/compare`, `POST /annotations`, `GET/POST /reports`, `POST /reports/:id/finalize`, `POST /copilot/query` — arrive with their respective phases in the [roadmap](README.md#roadmap).
