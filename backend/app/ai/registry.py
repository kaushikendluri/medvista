"""The worker's actual runnable-model registry — deliberately empty.

This is distinct from the `ai_models` database table (the catalog an admin
curates, describing models the organization intends to use). A DB row
alone never grants inference capability: the worker only ever runs a
model that has a real code implementation registered here, keyed by
(modality, task). Until a real model is added, every analysis job
honestly resolves to "unavailable" — never a fabricated result.
"""
from app.ai.base import MedicalImagingModel

AVAILABLE_MODEL_IMPLEMENTATIONS: dict[tuple[str, str], MedicalImagingModel] = {}


def find_implementation(modality: str, task: str | None = None) -> MedicalImagingModel | None:
    if task is not None:
        return AVAILABLE_MODEL_IMPLEMENTATIONS.get((modality, task))
    for (impl_modality, _impl_task), impl in AVAILABLE_MODEL_IMPLEMENTATIONS.items():
        if impl_modality == modality:
            return impl
    return None
