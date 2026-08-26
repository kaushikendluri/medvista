"""The model abstraction every imaging AI model implementation must satisfy.

This exists so a real model can be plugged in later (a MONAI bundle, a
Hugging Face checkpoint, a future proprietary model) without touching the
job orchestration, API, or frontend — they all depend on this interface,
never on a specific model. See AI.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.models.imaging_instance import ImagingInstance
from app.models.study import Study


@dataclass
class FindingDraft:
    """What a model implementation returns for one detected finding — not
    yet persisted, not yet labeled with model/version/timestamp provenance
    (the orchestrator attaches that when writing the AIFinding row)."""

    finding_type: str
    description: str
    anatomical_region: str | None
    confidence: float
    severity: str | None
    coordinates: dict | None = None
    measurement: dict | None = None


@dataclass
class PreprocessedInput:
    """Opaque container passed from preprocess() to predict(); shape is
    entirely up to the concrete model implementation."""

    payload: object
    meta: dict = field(default_factory=dict)


class MedicalImagingModel(Protocol):
    """One implementation per (modality, task) a real model supports.
    Registered in app/ai/registry.py — an empty registry means every
    analysis job honestly reports itself unavailable rather than
    fabricating output."""

    name: str
    version: str
    modality: str
    task: str

    def validate_input(self, study: Study, instances: list[ImagingInstance]) -> bool:
        """Whether this model can run against the given study."""
        ...

    def preprocess(self, study: Study, instances: list[ImagingInstance]) -> PreprocessedInput:
        ...

    def predict(self, data: PreprocessedInput) -> object:
        ...

    def postprocess(self, raw_output: object) -> list[FindingDraft]:
        ...
