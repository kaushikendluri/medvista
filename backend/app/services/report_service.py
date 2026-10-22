"""Report draft assembly.

Builds an initial draft from real, structured data already in the
database — patient demographics, clinical history, study technique,
and any existing AI findings. This is templating, not generation: no
language model is involved, and the function never invents an
Impression or Recommendation — those sections are left for the
physician to write. See AI.md for the (currently unconfigured) LLM
provider that would eventually offer real AI-assisted drafting.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_analysis import AIAnalysis
from app.models.ai_finding import AIFinding
from app.models.clinical_history import ClinicalHistory
from app.models.patient import Patient
from app.models.study import Study
from app.services.patient_service import calculate_age


def build_draft_template(db: Session, *, patient: Patient, study: Study | None) -> str:
    lines: list[str] = [
        "DRAFT — assembled from patient/study data. Not AI-generated. Requires physician review before finalizing.",
        "",
        "PATIENT",
        f"{patient.first_name} {patient.last_name} — {calculate_age(patient.date_of_birth)} yrs, {patient.sex.value}",
        f"Patient ID: {patient.external_patient_id}",
        "",
    ]

    history = db.execute(
        select(ClinicalHistory).where(ClinicalHistory.patient_id == patient.id)
    ).scalars().all()
    lines.append("CLINICAL HISTORY")
    if history:
        for entry in history:
            lines.append(f"- {entry.condition} ({entry.status.value})")
    else:
        lines.append("(none recorded)")
    lines.append("")

    lines.append("TECHNIQUE")
    if study:
        technique = f"{study.modality}"
        if study.body_part:
            technique += f", {study.body_part}"
        if study.study_date:
            technique += f", performed {study.study_date.isoformat()}"
        lines.append(technique)
        if study.study_description:
            lines.append(study.study_description)
    else:
        lines.append("(no study linked)")
    lines.append("")

    lines.append("FINDINGS")
    if study:
        findings = db.execute(
            select(AIFinding)
            .join(AIAnalysis, AIAnalysis.id == AIFinding.analysis_id)
            .where(AIAnalysis.study_id == study.id)
        ).scalars().all()
        if findings:
            for finding in findings:
                confidence = f" (AI confidence {round(finding.confidence * 100)}%)" if finding.confidence else ""
                lines.append(f"- [AI FINDING — requires review] {finding.description}{confidence}")
        else:
            lines.append("(none — add findings after physician review of the imaging)")
    else:
        lines.append("(no study linked)")
    lines.append("")

    lines.append("IMPRESSION")
    lines.append("(to be completed by the reviewing physician)")
    lines.append("")

    lines.append("RECOMMENDATIONS")
    lines.append("(to be completed by the reviewing physician)")

    return "\n".join(lines)
