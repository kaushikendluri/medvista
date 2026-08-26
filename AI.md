# AI Architecture

**Status: imaging AI pipeline (Phase 4) implemented — orchestration, registry, async job queue, worker, findings/review are all real. Zero models are installed**, so every analysis job legitimately resolves to `unavailable` with a specific reason. The clinical copilot LLM (Phase 6) is still design-only.

## Non-negotiable rule

If a model or provider isn't configured, the corresponding feature reports itself as **unavailable** — a real status value (`AIAnalysisStatus.UNAVAILABLE` in the schema), not a frontend message painted over missing data. No endpoint may ever return a synthesized finding, confidence score, or LLM response.

## Imaging model abstraction (implemented — `backend/app/ai/base.py`)

```python
class MedicalImagingModel(Protocol):
    name: str
    version: str
    modality: str
    task: str

    def validate_input(self, study: Study, instances: list[ImagingInstance]) -> bool: ...
    def preprocess(self, study: Study, instances: list[ImagingInstance]) -> PreprocessedInput: ...
    def predict(self, data: PreprocessedInput) -> object: ...
    def postprocess(self, raw_output: object) -> list[FindingDraft]: ...
```

Two separate registries, deliberately not conflated:

- **`ai_models` (database table):** the catalog an admin curates — name, version, modality, task, provider, intended status. `POST /ai/models` (super_admin only).
- **`AVAILABLE_MODEL_IMPLEMENTATIONS` (`backend/app/ai/registry.py`, in-code, empty today):** what the worker can *actually run*, keyed by `(modality, task)`.

A catalog row's `status` in every API response is **computed**, never trusted from the stored column: `GET /ai/models` reports `available` only if a matching code implementation exists in the registry above. An admin cataloging a model they intend to add later can never make the UI claim it's usable before it truly is.

## Job pipeline (implemented — `backend/app/services/ai_service.py`, `backend/app/worker.py`)

```
POST /studies/:id/analyze
      │  creates an ai_analyses row (status=queued), enqueues the
      │  analysis id on Redis (RPUSH), returns immediately
      ▼
Redis queue (medvista:ai_analysis_queue)
      │  BLPOP — a separate ai-worker process/container, same
      │  codebase, own DB session
      ▼
process_analysis_job()
      │  status → running, started_at set
      │  find_implementation(study.modality) against the registry
      │
      ├─ no match  → status = unavailable, error = a specific,
      │              real message naming the modality — never silent,
      │              never a fabricated finding
      │
      └─ match found → validate_input → preprocess → predict →
                        postprocess → one ai_findings row per
                        FindingDraft, status = completed
      │
      ▼  always: completed_at, processing_time_seconds set,
         any exception caught and stored as `error` (status=failed)
         rather than crashing the worker
```

The frontend polls `GET /studies/:id/analyses` (2s interval) while the latest job is `queued`/`running`; findings are listed from `GET /studies/:id/findings` and reviewed via `POST /findings/:id/review`.

## Clinical LLM provider abstraction (Phase 6 — design only)

```python
class ClinicalAIProvider(Protocol):
    def generate(self, prompt: str, context: RetrievedContext) -> str: ...
    def stream(self, prompt: str, context: RetrievedContext) -> Iterator[str]: ...
    def retrieve_context(self, patient_id: UUID, query: str) -> RetrievedContext: ...
    def validate_output(self, output: str, context: RetrievedContext) -> bool: ...
```

`retrieve_context` is the guardrail against hallucination: the copilot never sends "the whole patient record" to an LLM and never answers from the model's general knowledge. It pulls the specific rows (studies, findings, labs, history) relevant to the question, and every clinical statement in the response is expected to trace back to one of them. If nothing relevant was retrieved, the correct answer is *"I don't have sufficient information in the available patient record,"* not a best-effort guess.

Configured via `LLM_PROVIDER` / `LLM_API_KEY` (env only — see `.env.example`). Unset today, by design, until a real provider is wired in.

## Safety boundaries (apply to both)

- AI output is always labeled *AI finding* / *flagged region* / *requires physician review* — never *diagnosis*.
- The AI may draft a report; it may not finalize or sign one.
- The AI may propose a finding; it may not silently alter a physician-confirmed finding.
- Every finding carries provenance: model name, version, source study/series/instance, and generation timestamp — so a number like "8.4 mm" in the UI is always traceable to AI measurement, physician measurement, or an imported report, never ambiguous.

## Adding a real model

1. Implement `MedicalImagingModel` for it.
2. Register it in `AVAILABLE_MODEL_IMPLEMENTATIONS` keyed by `(modality, task)`.
3. Add (or update) its catalog row via `POST /ai/models` — its computed `status` will now correctly read `available`.

No changes needed to the job queue, worker loop, API routes, or frontend polling/review UI — that's the point of the abstraction.
