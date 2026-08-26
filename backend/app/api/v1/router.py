from fastapi import APIRouter

from app.api.v1 import audit_log, auth, dashboard, patients, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(patients.router)
api_router.include_router(dashboard.router)
api_router.include_router(audit_log.router)
