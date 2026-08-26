# DICOM Architecture

**Status: not yet implemented (Phase 2).** This document describes the intended design so imaging ingestion lands against the schema already in place.

## Server

[Orthanc](https://www.orthanc-server.com/) with DICOMweb enabled, run via `docker-compose.yml` (REST API on `8042`, DICOM protocol on `4242`). Credentials are read from `DICOM_SERVER_URL` / `DICOM_SERVER_USERNAME` / `DICOM_SERVER_PASSWORD` (env only).

## Ingestion flow

```
Select files (DICOM / folder / ZIP)
    │
    ▼  validate file type + size limits
Extract metadata (pydicom) — StudyInstanceUID, SeriesInstanceUID,
    SOPInstanceUID, modality, study date, body part, manufacturer, ...
    │
    ▼
Upload to Orthanc via DICOMweb STOW-RS
    │
    ▼  identify or create matching rows
studies / series / imaging_instances (see DATABASE.md)
    │
    ▼
Study becomes visible in the patient profile with real, extracted
metadata — nothing in this table is ever hand-populated.
```

`Study.status` tracks real pipeline state (`pending → uploading → processing → ready`, or `failed` with the underlying error surfaced to the user) — progress shown in the UI must reflect this column, not a simulated timer.

## Viewer

Cornerstone3D (via OHIF building blocks where useful) consuming the study over DICOMweb (WADO-RS) from Orthanc — not a custom-built DICOM renderer. Window/level presets (lung/bone/soft-tissue/brain), measurements, and annotations operate on the real viewport and persist to the `measurements`/`annotations` tables (Phase 3).

## Why this isn't stubbed with fake studies

The `studies`/`series`/`imaging_instances` tables already exist (Phase 1 migration) specifically so Phase 2 only has to add the ingestion pipeline and viewer — not retrofit the data model. Until Phase 2 ships, patient profiles correctly show "No imaging studies available," which is a real empty-table query result, not a hardcoded string keyed off a feature flag.
