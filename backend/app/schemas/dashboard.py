import uuid
from datetime import datetime

from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_patients: int
    studies_today: int
    pending_ai_reviews: int
    reports_pending: int
    ai_analyses_running: int


class ActivityItem(BaseModel):
    id: uuid.UUID
    action: str
    resource_type: str
    resource_id: str | None
    actor_name: str | None
    timestamp: datetime


class DashboardResponse(BaseModel):
    stats: DashboardStats
    recent_activity: list[ActivityItem]


class TimelineEvent(BaseModel):
    event_type: str
    title: str
    description: str | None
    timestamp: datetime
    reference_id: uuid.UUID | None
    source: str
