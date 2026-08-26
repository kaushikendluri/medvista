"""AI analysis job orchestration — the pipeline documented in AI.md.

Runs identically whether invoked by the worker loop (app/worker.py) or
directly (used by tests to exercise the pipeline synchronously). Never
fabricates a finding: with an empty model registry, every job legitimately
resolves to "unavailable" with a real, specific reason.
"""
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.registry import find_implementation
from app.models.ai_analysis import AIAnalysis
from app.models.ai_finding import AIFinding
from app.models.enums import AIAnalysisStatus, AIFindingStatus
from app.models.imaging_instance import ImagingInstance
from app.models.series import Series
from app.models.study import Study


def _load_instances(db: Session, study_id: uuid.UUID) -> list[ImagingInstance]:
    return list(
        db.execute(
            select(ImagingInstance)
            .join(Series, Series.id == ImagingInstance.series_id)
            .where(Series.study_id == study_id)
        )
        .scalars()
        .all()
    )


def process_analysis_job(db: Session, analysis_id: uuid.UUID) -> None:
    analysis = db.get(AIAnalysis, analysis_id)
    if analysis is None:
        return

    analysis.status = AIAnalysisStatus.RUNNING
    analysis.started_at = datetime.now(timezone.utc)
    db.commit()

    study = db.get(Study, analysis.study_id)
    start = time.perf_counter()

    try:
        implementation = find_implementation(study.modality) if study else None

        if implementation is None:
            analysis.status = AIAnalysisStatus.UNAVAILABLE
            analysis.error = (
                f"No AI model is currently available for modality "
                f"'{study.modality if study else 'unknown'}'. "
                "Configure a model implementation to enable analysis."
            )
        else:
            instances = _load_instances(db, analysis.study_id)
            if not implementation.validate_input(study, instances):
                analysis.status = AIAnalysisStatus.FAILED
                analysis.error = "Study does not meet this model's input requirements."
            else:
                preprocessed = implementation.preprocess(study, instances)
                raw_output = implementation.predict(preprocessed)
                drafts = implementation.postprocess(raw_output)
                for draft in drafts:
                    db.add(
                        AIFinding(
                            analysis_id=analysis.id,
                            finding_type=draft.finding_type,
                            description=draft.description,
                            anatomical_region=draft.anatomical_region,
                            confidence=draft.confidence,
                            severity=draft.severity,
                            status=AIFindingStatus.AI_FLAGGED,
                            coordinates=draft.coordinates,
                            measurement=draft.measurement,
                        )
                    )
                analysis.status = AIAnalysisStatus.COMPLETED
    except Exception as exc:  # a real model failing must not crash the worker
        analysis.status = AIAnalysisStatus.FAILED
        analysis.error = str(exc)
    finally:
        analysis.completed_at = datetime.now(timezone.utc)
        analysis.processing_time_seconds = time.perf_counter() - start
        db.commit()
