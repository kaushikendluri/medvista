# Database

PostgreSQL, managed via Alembic (`backend/alembic/versions/`). No manual schema edits — every change is a migration, generated with `alembic revision --autogenerate` against a real database and reviewed before committing.

## Conventions

- Every table has a UUID primary key (`id`, default `uuid4()`).
- Every table except `audit_logs`/`notifications` has `created_at`/`updated_at` (server-side defaults).
- Foreign keys are indexed explicitly (`index=True`) where they're the primary access pattern (e.g. `patient_id` on every patient-owned table).
- Enums are native Postgres `ENUM` types (not free-text columns), so invalid states are rejected at the database level, not just in application code.
- No JSON-blob-as-a-table-substitute: `annotations.geometry`, `measurements.geometry`, `ai_findings.coordinates`/`measurement` use `JSONB` only for genuinely variable-shape geometric/measurement payloads — never for structured fields that have their own columns elsewhere.

## Tables

### Identity & access
| Table | Key columns | Notes |
|---|---|---|
| `organizations` | name, type | Tenant boundary |
| `users` | organization_id, role, email (unique), hashed_password, status | `role` enum: super_admin / hospital_admin / doctor / radiologist / technician / researcher |

### Patient record
| Table | Key columns | Notes |
|---|---|---|
| `patients` | organization_id, external_patient_id, first_name, last_name, date_of_birth, sex | Age is **computed**, never stored |
| `clinical_history` | patient_id, condition, status, source | |
| `laboratory_results` | patient_id, test_name, value, unit, reference_range, collection_date | Populated from Phase 5 |
| `medications` | patient_id, name, dosage, frequency, status | Populated from Phase 5 |
| `patient_events` | patient_id, event_type, title, event_timestamp | Catch-all for timeline entries with no dedicated table (appointments, notes) |

### Imaging (Phase 2 — implemented)
| Table | Key columns | Notes |
|---|---|---|
| `studies` | patient_id, study_uid (unique), modality, status | `status` enum tracks upload/processing pipeline |
| `series` | study_id, series_uid (unique), instance_count | `instance_count` is incremented as real instances are registered, never set directly |
| `imaging_instances` | series_id, sop_instance_uid (unique), storage_reference | `storage_reference` holds the Orthanc instance ID (Orthanc is the storage backend for Phase 2; swapping in dedicated S3-compatible storage later needs no schema change) |

### AI (Phase 4+)
| Table | Key columns | Notes |
|---|---|---|
| `ai_models` | name, version, modality, task, provider, status | The model registry — frontend discovers models from here, never hardcodes names |
| `ai_analyses` | study_id, model_id, status, error | One row per inference job run |
| `ai_findings` | analysis_id, finding_type, confidence, status, coordinates, measurement, evidence_reference | `status` enum: ai_flagged → physician_reviewing → confirmed/dismissed/uncertain |

### Review artifacts (Phase 3/5+)
| Table | Key columns | Notes |
|---|---|---|
| `annotations` | study_id, series_id, user_id, type, geometry | |
| `measurements` | study_id, series_id, user_id, value, unit, source | `source`: physician vs. AI, so the UI can never conflate the two |
| `reports` | patient_id, study_id, author_id, status, draft_content, finalized_content | `status` enum: ai_draft → physician_draft → finalized → signed |
| `report_versions` | report_id, version_number, author_id, content | Immutable snapshot per edit |

### Operational
| Table | Key columns | Notes |
|---|---|---|
| `audit_logs` | user_id, organization_id, action, resource_type, resource_id, timestamp | Written on login, patient view/create/update, clinical history writes, user creation |
| `notifications` | user_id, type, title, read | Populated from Phase 5/6 |

## Migrations

```bash
cd backend
alembic upgrade head                                  # apply
alembic revision --autogenerate -m "add X"             # generate (needs a live DB connection)
alembic downgrade -1                                   # roll back one step
```

Postgres `ENUM` types are separate objects from the columns that use them — dropping a table does not drop its enum type. The initial migration's `downgrade()` explicitly drops every enum type it created; follow that pattern in future migrations that add new enums.
