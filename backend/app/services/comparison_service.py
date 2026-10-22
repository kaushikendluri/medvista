"""Study-to-study comparison ("Time Machine").

Deliberately conservative: measurements are only paired automatically
when there is exactly one measurement of a given type in each study —
anything more ambiguous is surfaced as separate, unpaired entries rather
than guessed at. Findings are matched by exact (finding_type,
anatomical_region) equality only; no fuzzy/spatial matching is
attempted. A finding missing from the later study is reported as
"not re-flagged", never as "resolved" — that clinical judgment belongs
to the reviewing physician, not this heuristic.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_analysis import AIAnalysis
from app.models.ai_finding import AIFinding
from app.models.measurement import Measurement
from app.models.study import Study
from app.schemas.ai import AIFindingRead
from app.schemas.comparison import ComparisonResult, FindingComparison, MeasurementComparison
from app.schemas.study import StudyRead


def _order_chronologically(study_x: Study, study_y: Study) -> tuple[Study, Study]:
    """Earlier study first. Falls back to created_at when study_date is
    missing on either side — never compares a None study_date directly."""
    if study_x.study_date is not None and study_y.study_date is not None:
        return (study_x, study_y) if study_x.study_date <= study_y.study_date else (study_y, study_x)
    return (study_x, study_y) if study_x.created_at <= study_y.created_at else (study_y, study_x)


def _compare_measurements(db: Session, study_a: Study, study_b: Study) -> list[MeasurementComparison]:
    def by_type(study: Study) -> dict[str, list[Measurement]]:
        rows = db.execute(select(Measurement).where(Measurement.study_id == study.id)).scalars().all()
        grouped: dict[str, list[Measurement]] = {}
        for row in rows:
            grouped.setdefault(row.type, []).append(row)
        return grouped

    grouped_a, grouped_b = by_type(study_a), by_type(study_b)
    results: list[MeasurementComparison] = []

    for m_type in sorted(set(grouped_a) | set(grouped_b)):
        list_a, list_b = grouped_a.get(m_type, []), grouped_b.get(m_type, [])
        if len(list_a) == 1 and len(list_b) == 1:
            a, b = list_a[0], list_b[0]
            delta = b.value - a.value
            percent = (delta / a.value * 100) if a.value else None
            results.append(
                MeasurementComparison(
                    type=m_type,
                    unit=b.unit,
                    value_a=a.value,
                    value_b=b.value,
                    delta=round(delta, 3),
                    percent_change=round(percent, 1) if percent is not None else None,
                    note="Directly comparable — one measurement of this type in each study.",
                )
            )
        else:
            note = (
                f"{len(list_a)} measurement(s) of type '{m_type}' in the earlier study and "
                f"{len(list_b)} in the later study — not automatically paired."
            )
            results.append(
                MeasurementComparison(
                    type=m_type,
                    unit=(list_a[0].unit if list_a else list_b[0].unit) if (list_a or list_b) else "",
                    value_a=None,
                    value_b=None,
                    delta=None,
                    percent_change=None,
                    note=note,
                )
            )
    return results


def _compare_findings(db: Session, study_a: Study, study_b: Study) -> list[FindingComparison]:
    def load(study: Study) -> list[AIFinding]:
        return list(
            db.execute(
                select(AIFinding)
                .join(AIAnalysis, AIAnalysis.id == AIFinding.analysis_id)
                .where(AIAnalysis.study_id == study.id)
            )
            .scalars()
            .all()
        )

    findings_a, findings_b = load(study_a), load(study_b)

    def key(f: AIFinding) -> tuple[str, str | None]:
        return (f.finding_type, f.anatomical_region)

    a_by_key = {key(f): f for f in findings_a}
    b_by_key = {key(f): f for f in findings_b}
    results: list[FindingComparison] = []

    for k in sorted(set(a_by_key) | set(b_by_key), key=lambda t: (t[0], t[1] or "")):
        a, b = a_by_key.get(k), b_by_key.get(k)
        if a and b:
            relationship = "present_in_both"
        elif b and not a:
            relationship = "new_in_b"
        else:
            relationship = "not_re_flagged_in_b"
        results.append(
            FindingComparison(
                finding_type=k[0],
                anatomical_region=k[1],
                relationship=relationship,
                finding_a=AIFindingRead.model_validate(a) if a else None,
                finding_b=AIFindingRead.model_validate(b) if b else None,
            )
        )
    return results


def compare_studies(db: Session, study_x: Study, study_y: Study) -> ComparisonResult:
    study_a, study_b = _order_chronologically(study_x, study_y)

    if study_a.patient_id != study_b.patient_id:
        return ComparisonResult(
            comparable=False,
            reason="These studies belong to different patients.",
            study_a=StudyRead.model_validate(study_a),
            study_b=StudyRead.model_validate(study_b),
            measurement_comparisons=[],
            finding_comparisons=[],
        )

    if study_a.modality != study_b.modality:
        return ComparisonResult(
            comparable=False,
            reason=f"Different modalities ({study_a.modality} vs {study_b.modality}) are not directly comparable.",
            study_a=StudyRead.model_validate(study_a),
            study_b=StudyRead.model_validate(study_b),
            measurement_comparisons=[],
            finding_comparisons=[],
        )

    return ComparisonResult(
        comparable=True,
        reason=None,
        study_a=StudyRead.model_validate(study_a),
        study_b=StudyRead.model_validate(study_b),
        measurement_comparisons=_compare_measurements(db, study_a, study_b),
        finding_comparisons=_compare_findings(db, study_a, study_b),
    )
