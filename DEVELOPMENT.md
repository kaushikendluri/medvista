# Development

## Prerequisites

- Docker Desktop
- Python 3.12+ (for running the backend outside Docker)
- Node.js 22+ (for running the frontend outside Docker)

## Quickest path: Docker Compose

```bash
cp .env.example .env   # edit AUTH_SECRET at minimum for anything beyond throwaway local use
docker compose up -d --build
```

This starts `postgres`, `redis`, `orthanc`, `backend` (port 8000), and `frontend` (port 3000). The backend container does not run migrations automatically — run them once after the database is up:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python -m scripts.seed   # optional synthetic demo data
```

Then visit `http://localhost:3000`. If you seeded, log in with `admin@medvista.demo` / `MedVista!Demo123` (or `doctor@medvista.demo`, `radiologist@medvista.demo`, `tech@medvista.demo` — same password). Without seeding, you land on an empty "No patients yet" state and can create your first patient directly.

## Running the backend natively

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate       # .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
# point DATABASE_URL at a running Postgres (docker compose up -d postgres works)
alembic upgrade head
python -m scripts.seed       # optional
uvicorn app.main:app --reload
```

Swagger UI: `http://localhost:8000/docs`.

## Running the backend tests

Tests run against a **real Postgres instance** — no mocked database. Point `DATABASE_URL` at any disposable Postgres (a throwaway container is fine; the test suite truncates every table before each test):

```bash
docker run -d --name medvista-pg-test -e POSTGRES_USER=medvista -e POSTGRES_PASSWORD=medvista \
  -e POSTGRES_DB=medvista -p 5433:5432 postgres:16-alpine
cd backend
DATABASE_URL=postgresql+psycopg://medvista:medvista@localhost:5433/medvista pytest -q
```

## Note on the imaging viewer and Docker Desktop on Windows

The study viewer route (`/patients/[id]/studies/[studyId]`) pulls in the full Cornerstone3D stack (`@cornerstonejs/core`, `tools`, `dicom-image-loader` and its WASM codecs) — a large module graph. In Next.js dev mode, the **first** request to that route triggers an on-demand compile that can take 60–90s natively, and can stall for many minutes under Docker Desktop on Windows specifically, because bind-mounted `node_modules` (`./frontend:/app`) pay a severe per-file I/O penalty across the Docker Desktop VM boundary — webpack's dev compiler touches thousands of small files in `@cornerstonejs/*`.

If that route seems to hang in `docker compose logs frontend` right after `○ Compiling /patients/[id]/studies/[studyId] ...` for more than ~2 minutes with no progress:

```bash
docker compose stop frontend
cd frontend && npm install && BACKEND_INTERNAL_URL=http://localhost:8000 NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

Running natively avoids the bind-mount overhead entirely (the same first compile takes ~70s instead of stalling indefinitely) and still talks to the same Dockerized backend/Postgres/Orthanc. This is a Windows/Docker Desktop dev-mode characteristic, not a code issue — `next build` (production) is unaffected either way, since it doesn't re-compile per-route on demand.

## Running the frontend natively

```bash
cd frontend
npm install
npm run dev       # http://localhost:3000
npm run typecheck
npm run build      # production build check
```

The frontend expects `BACKEND_INTERNAL_URL` (server-side fetches from the BFF routes) and `NEXT_PUBLIC_API_BASE_URL` — both default to `http://localhost:8000` for native (non-Docker) dev.

## Adding a migration

```bash
cd backend
# edit/add a model in app/models/, add it to app/models/__init__.py
alembic revision --autogenerate -m "describe the change"
# review the generated file in alembic/versions/ before committing —
# autogenerate does not add explicit DROP TYPE for new Postgres enums in
# downgrade(); add those by hand (see the initial migration for the pattern)
alembic upgrade head
```

## Code layout reference

See [ARCHITECTURE.md](ARCHITECTURE.md) for module boundaries and [DATABASE.md](DATABASE.md) for the schema.
