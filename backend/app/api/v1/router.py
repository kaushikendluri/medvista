from fastapi import APIRouter

from app.api.v1 import (
    ai_analysis,
    ai_models,
    annotations,
    audit_log,
    auth,
    dashboard,
    patients,
    reports,
    studies,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(patients.router)
api_router.include_router(studies.router)
api_router.include_router(annotations.router)
api_router.include_router(ai_models.router)
api_router.include_router(ai_analysis.router)
api_router.include_router(reports.router)
api_router.include_router(dashboard.router)
api_router.include_router(audit_log.router)
