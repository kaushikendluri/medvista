from fastapi import APIRouter

from app.api.v1 import annotations, audit_log, auth, dashboard, patients, studies, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(patients.router)
api_router.include_router(studies.router)
api_router.include_router(annotations.router)
api_router.include_router(dashboard.router)
api_router.include_router(audit_log.router)
