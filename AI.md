# AI Architecture

**Status: not yet implemented.** This document describes the design Phase 4 (imaging AI) and Phase 6 (clinical copilot) build against, so the abstractions land right the first time. Nothing described here fabricates output today — that's the entire point of writing it down before building it.

## Non-negotiable rule

If a model or provider isn't configured, the corresponding feature reports itself as **unavailable** — a real status value (`AIAnalysisStatus.UNAVAILABLE` in the schema), not a frontend message painted over missing data. No endpoint may ever return a synthesized finding, confidence score, or LLM response.

## Imaging model abstraction (Phase 4)

```python
class MedicalImagingModel(Protocol):
    def load(self) -> None: ...
    def validate_input(self, study: Study) -> bool: ...
    def preprocess(self, instances: list[ImagingInstance]) -> Any: ...
    def predict(self, data: Any) -> Any: ...
    def postprocess(self, raw_output: Any) -> list[AIFindingDraft]: ...
    def generate_visualization(self, finding: AIFindingDraft) -> Overlay: ...
```

Every concrete model (a MONAI bundle, a Hugging Face checkpoint, a future proprietary model) implements this interface and registers itself in the `ai_models` table (name, version, modality, task, provider, status). The frontend discovers available models by querying that table — model names are never hardcoded in a component.

Job flow: `POST /studies/:id/analyze` creates an `ai_analyses` row (`status=queued`), enqueues work on Redis, a worker processes it and writes `ai_findings` rows plus updates `status`/`processing_time_seconds`/`error`. The frontend polls or subscribes (SSE/WebSocket) rather than blocking the request.

## Clinical LLM provider abstraction (Phase 6)

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
