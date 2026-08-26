# DICOM Architecture

**Status: ingestion implemented (Phase 2). Full diagnostic viewer (window/level, zoom/pan, measurements, annotations) is Phase 3.**

## Server

[Orthanc](https://www.orthanc-server.com/) (`orthancteam/orthanc:26.8.1`), run via `docker-compose.yml` (REST API on `8042`, DICOM protocol on `4242`). Credentials are read from `DICOM_SERVER_URL` / `DICOM_SERVER_USERNAME` / `DICOM_SERVER_PASSWORD` (env only) — see `app/services/orthanc_client.py`.

## Ingestion flow (implemented)

```
POST /patients/{id}/studies/upload — multipart, .dcm files and/or .zip archives
    │
    ▼  validate DICOM header + 100MB/instance, 500MB/request limits
Extract metadata (pydicom, app/services/dicom_metadata.py) — StudyInstanceUID,
    SeriesInstanceUID, SOPInstanceUID, modality, study date, body part,
    institution, accession number, series/instance number — read from the
    file's own header only, nothing inferred
    │
    ▼
Upload raw DICOM bytes to Orthanc (its classic REST API, POST /instances —
    simpler than hand-rolling DICOMweb STOW-RS multipart framing for a
    server we control; WADO-RS remains the Phase 3 retrieval path)
    │
    ▼  upsert, keyed by UID — re-uploading the same instance is a no-op,
    │  not a duplicate; a study_uid already owned by a different patient
    │  is rejected per-file rather than silently reassigned
studies / series / imaging_instances (see DATABASE.md)
    │
    ▼
Study appears in the patient profile with the real extracted metadata.
Each instance's rendered preview is fetched on demand through
GET /studies/{id}/instances/{instance_id}/preview, which proxies
Orthanc's own preview rendering — the frontend never talks to Orthanc
directly, so RBAC/org-isolation is enforced before every image byte
is served.
```

Per-file failures (invalid DICOM, cross-patient UID conflict, Orthanc unreachable) don't abort the batch — the response lists every failure with its actual reason, and valid files in the same request still get indexed. `Study.status` reflects real pipeline state (`processing` while a batch is mid-flight, `ready` once at least one instance is indexed).

## Basic viewer (implemented) vs. full viewer (Phase 3)

The patient profile's study page (`/patients/[id]/studies/[studyId]`) lets a user pick a series and step through its instances via Orthanc's rendered preview — real pixel data from the uploaded file, not a placeholder image. What's *not* here yet: window/level, zoom/pan, measurements, and annotations, which need Cornerstone3D operating on the actual pixel data (via WADO-RS) rather than a flattened preview PNG. The UI says so explicitly rather than pretending those tools exist.

## Why this wasn't stubbed with fake studies

The `studies`/`series`/`imaging_instances` tables existed since the Phase 1 migration specifically so Phase 2 only had to add the ingestion pipeline — not retrofit the data model. Before any upload, patient profiles correctly showed "No imaging studies available," a real empty-table query result, never a hardcoded string.
