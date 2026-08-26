import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.ai_analysis import AIAnalysis
from app.models.ai_finding import AIFinding
from app.models.enums import AIAnalysisStatus, UserRole
from app.models.user import User
from app.schemas.ai import AIAnalysisRead, AIFindingRead, FindingReviewRequest
from app.services.audit import record_audit_event
from app.services.queue import enqueue_analysis_job
from app.services.study_service import get_study

router = APIRouter(tags=["ai"])

REVIEW_ROLES = (UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.DOCTOR, UserRole.RADIOLOGIST)
VIEW_ROLES = REVIEW_ROLES + (UserRole.TECHNICIAN,)


def _require_study(db: Session, study_id: uuid.UUID, org_id: uuid.UUID):
    study = get_study(db, study_id=study_id, organization_id=org_id)
    if study is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Study not found")
    return study


@router.post(
    "/studies/{study_id}/analyze", response_model=AIAnalysisRead, status_code=status.HTTP_201_CREATED
)
def start_analysis(
    study_id: uuid.UUID,
    current_user: User = Depends(require_roles(*REVIEW_ROLES)),
    db: Session = Depends(get_db),
) -> AIAnalysisRead:
    _require_study(db, study_id, current_user.organization_id)

    analysis = AIAnalysis(study_id=study_id, status=AIAnalysisStatus.QUEUED)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    enqueue_analysis_job(str(analysis.id))

    record_audit_event(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="ai_analysis.started",
        resource_type="ai_analysis",
        resource_id=str(analysis.id),
        meta={"study_id": str(study_id)},
    )
    return AIAnalysisRead.model_validate(analysis)


@router.get("/studies/{study_id}/analyses", response_model=list[AIAnalysisRead])
def list_analyses(
    study_id: uuid.UUID,
    current_user: User = Depends(require_roles(*VIEW_ROLES)),
    db: Session = Depends(get_db),
) -> list[AIAnalysisRead]:
    _require_study(db, study_id, current_user.organization_id)
    rows = db.execute(
        select(AIAnalysis).where(AIAnalysis.study_id == study_id).order_by(AIAnalysis.created_at.desc())
    ).scalars().all()
    return [AIAnalysisRead.model_validate(a) for a in rows]


@router.get("/analyses/{analysis_id}", response_model=AIAnalysisRead)
def get_analysis(
    analysis_id: uuid.UUID,
    current_user: User = Depends(require_roles(*VIEW_ROLES)),
    db: Session = Depends(get_db),
) -> AIAnalysisRead:
    analysis = db.get(AIAnalysis, analysis_id)
    if analysis is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    _require_study(db, analysis.study_id, current_user.organization_id)
    return AIAnalysisRead.model_validate(analysis)


@router.get("/studies/{study_id}/findings", response_model=list[AIFindingRead])
def list_findings(
    study_id: uuid.UUID,
    current_user: User = Depends(require_roles(*VIEW_ROLES)),
    db: Session = Depends(get_db),
) -> list[AIFindingRead]:
    _require_study(db, study_id, current_user.organization_id)
    rows = db.execute(
        select(AIFinding)
        .join(AIAnalysis, AIAnalysis.id == AIFinding.analysis_id)
        .where(AIAnalysis.study_id == study_id)
        .order_by(AIFinding.created_at.desc())
    ).scalars().all()
    return [AIFindingRead.model_validate(f) for f in rows]


@router.post("/findings/{finding_id}/review", response_model=AIFindingRead)
def review_finding(
    finding_id: uuid.UUID,
    payload: FindingReviewRequest,
    current_user: User = Depends(require_roles(*REVIEW_ROLES)),
    db: Session = Depends(get_db),
) -> AIFindingRead:
    finding = db.get(AIFinding, finding_id)
    if finding is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Finding not found")
    analysis = db.get(AIAnalysis, finding.analysis_id)
    _require_study(db, analysis.study_id, current_user.organization_id)

    finding.status = payload.status
    db.commit()
    db.refresh(finding)

    record_audit_event(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="ai_finding.reviewed",
        resource_type="ai_finding",
        resource_id=str(finding.id),
        meta={"new_status": payload.status.value},
    )
    return AIFindingRead.model_validate(finding)
