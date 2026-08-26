# DICOM Architecture

**Status: ingestion (Phase 2) and viewer (Phase 3) both implemented.**

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

## Viewer (Phase 3 — implemented)

The study page (`/patients/[id]/studies/[studyId]`) is a real Cornerstone3D `StackViewport`, not a flattened preview image. It loads instances via the `wadouri` scheme — the frontend's `dicom-image-loader` fetches the original file from `GET /studies/{id}/instances/{instance_id}/file` (proxying Orthanc's own `/instances/{id}/file`) and parses the actual dataset client-side (`app/services/orthanc_client.py::fetch_instance_file`, `frontend/lib/cornerstone-viewer.ts`).

Implemented tools: window/level (drag, plus Soft Tissue/Lung/Bone/Brain presets — standard clinical WW/WL constants, not fabricated), zoom, pan, mouse-wheel stack scroll, invert, reset. Length measurements and arrow annotations are real Cornerstone3D tools; on completion the frontend persists them to `POST /studies/{id}/measurements` / `/annotations` using Cornerstone's own world-space handle points as the geometry (`app/api/v1/annotations.py`) — not a custom coordinate scheme. They're surfaced back as an accurate list (value, unit, author, timestamp) in the viewer's right panel.

**Known gap:** compressed transfer syntaxes (JPEG2000, JPEG-LS, etc.) need the loader's WASM codecs; `wasmBasePath` isn't specially configured, so only uncompressed native pixel data (what this project's own upload pipeline and test fixtures produce) is guaranteed to decode today. Re-rendering saved measurements/annotations as overlays on revisit (vs. the current accurate list view) is also not yet implemented — see [API.md](API.md#imaging-review-measurements--annotations).

## Why this wasn't stubbed with fake studies

The `studies`/`series`/`imaging_instances` tables existed since the Phase 1 migration specifically so Phase 2 only had to add the ingestion pipeline — not retrofit the data model. Before any upload, patient profiles correctly showed "No imaging studies available," a real empty-table query result, never a hardcoded string.
