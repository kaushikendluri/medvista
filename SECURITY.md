# Security

This is a prototype/research system handling synthetic data by default, but is built to the access-control and auditing standards a clinical system requires.

## Authentication

- Passwords hashed with `bcrypt` (cost factor library default), never stored or logged in plaintext.
- Sessions are JWTs (`HS256`), signed with `AUTH_SECRET` (env-only, never committed — see `.env.example`). Default expiry 12 hours.
- The frontend never holds the JWT in client-side JavaScript: `app/api/auth/login` sets it as an `httpOnly`, `sameSite=lax`, `secure` (in production) cookie; all subsequent API calls go through `app/api/proxy/[...path]`, which reads the cookie server-side and attaches `Authorization: Bearer`.

## Authorization (RBAC)

- Enforced with the `require_roles(...)` FastAPI dependency on every route that needs it — **server-side only**. The frontend hiding a button is a UX nicety, never the security boundary.
- Roles: `super_admin`, `hospital_admin`, `doctor`, `radiologist`, `technician`, `researcher`. See [API.md](API.md) for the exact role list per endpoint.
- `hospital_admin` cannot create a `super_admin` account (checked explicitly, not just by role hierarchy assumption).
- `researcher` is excluded from every identified-patient endpoint; it's scoped to de-identified research data only (Phase 7).

## Multi-tenancy / organization isolation

- Every patient-scoped query filters on `organization_id == current_user.organization_id` at the service layer (not just the router), so a missed check in one endpoint can't leak data through another code path that reuses the same service function.
- Cross-organization access to a specific record returns `404`, not `403` — this avoids confirming a record exists in another organization.
- Covered by `tests/test_patients.py::test_cross_organization_isolation`.

## Audit logging

- Every login, patient create/view/update, and clinical-history write inserts an `audit_logs` row: actor, organization, action, resource type/id, timestamp.
- Audit log is readable only by `super_admin`/`hospital_admin`, and itself scoped to the caller's organization unless `super_admin`.
- Request logging (`core/logging.py`) is structured JSON and **never logs request/response bodies** — those can contain patient information.

## Input validation

- Every request body is a Pydantic model with explicit types; extra/unexpected fields are rejected by default.
- `PatientCreate` rejects a `date_of_birth` in the future at the schema level (tested).
- SQL is only ever produced through SQLAlchemy's query builder — no string-interpolated SQL anywhere in the codebase.

## Secrets

- All secrets (`AUTH_SECRET`, `DATABASE_URL` credentials, future `LLM_API_KEY`/`OBJECT_STORAGE_*`) are read from environment variables only (`app/core/config.py`). `.env` is gitignored; `.env.example` documents every variable with no real values.
- Docker Compose passes secrets via `env_file: .env`, never bakes them into images.

## Known gaps (tracked, not hidden)

- No rate limiting on `/auth/login` yet (brute-force mitigation) — planned before any non-local deployment.
- No refresh-token rotation; sessions simply expire after `ACCESS_TOKEN_EXPIRE_MINUTES`.
- File upload validation (type/size limits, DICOM sanity checks) arrives with Phase 2, since there's no upload endpoint yet.
