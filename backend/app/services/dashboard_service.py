import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_analysis import AIAnalysis
from app.models.ai_finding import AIFinding
from app.models.audit_log import AuditLog
from app.models.enums import AIAnalysisStatus, AIFindingStatus, ReportStatus
from app.models.patient import Patient
from app.models.report import Report
from app.models.study import Study
from app.models.user import User
from app.schemas.dashboard import ActivityItem, DashboardResponse, DashboardStats


def get_dashboard(db: Session, *, organization_id: uuid.UUID) -> DashboardResponse:
    total_patients = db.scalar(
        select(func.count()).select_from(Patient).where(Patient.organization_id == organization_id)
    ) or 0

    studies_today = db.scalar(
        select(func.count())
        .select_from(Study)
        .join(Patient, Patient.id == Study.patient_id)
        .where(Patient.organization_id == organization_id, Study.study_date == date.today())
    ) or 0

    pending_ai_reviews = db.scalar(
        select(func.count())
        .select_from(AIFinding)
        .join(AIAnalysis, AIAnalysis.id == AIFinding.analysis_id)
        .join(Study, Study.id == AIAnalysis.study_id)
        .join(Patient, Patient.id == Study.patient_id)
        .where(
            Patient.organization_id == organization_id,
            AIFinding.status == AIFindingStatus.AI_FLAGGED,
        )
    ) or 0

    reports_pending = db.scalar(
        select(func.count())
        .select_from(Report)
        .join(Patient, Patient.id == Report.patient_id)
        .where(
            Patient.organization_id == organization_id,
            Report.status.in_([ReportStatus.AI_DRAFT, ReportStatus.PHYSICIAN_DRAFT]),
        )
    ) or 0

    ai_analyses_running = db.scalar(
        select(func.count())
        .select_from(AIAnalysis)
        .join(Study, Study.id == AIAnalysis.study_id)
        .join(Patient, Patient.id == Study.patient_id)
        .where(
            Patient.organization_id == organization_id,
            AIAnalysis.status.in_([AIAnalysisStatus.QUEUED, AIAnalysisStatus.RUNNING]),
        )
    ) or 0

    activity_rows = db.execute(
        select(AuditLog, User.name)
        .outerjoin(User, User.id == AuditLog.user_id)
        .where(AuditLog.organization_id == organization_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(20)
    ).all()

    recent_activity = [
        ActivityItem(
            id=log.id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            actor_name=actor_name,
            timestamp=log.timestamp,
        )
        for log, actor_name in activity_rows
    ]

    return DashboardResponse(
        stats=DashboardStats(
            total_patients=total_patients,
            studies_today=studies_today,
            pending_ai_reviews=pending_ai_reviews,
            reports_pending=reports_pending,
            ai_analyses_running=ai_analyses_running,
        ),
        recent_activity=recent_activity,
    )
