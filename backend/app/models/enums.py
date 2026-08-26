import enum


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    HOSPITAL_ADMIN = "hospital_admin"
    DOCTOR = "doctor"
    RADIOLOGIST = "radiologist"
    TECHNICIAN = "technician"
    RESEARCHER = "researcher"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INVITED = "invited"
    DISABLED = "disabled"


class OrganizationType(str, enum.Enum):
    HOSPITAL = "hospital"
    CLINIC = "clinic"
    RESEARCH_INSTITUTION = "research_institution"


class Sex(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class ClinicalHistoryStatus(str, enum.Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    CHRONIC = "chronic"


class StudyStatus(str, enum.Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class AIAnalysisStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


class AIFindingStatus(str, enum.Enum):
    AI_FLAGGED = "ai_flagged"
    PHYSICIAN_REVIEWING = "physician_reviewing"
    CONFIRMED = "confirmed_by_physician"
    DISMISSED = "dismissed"
    UNCERTAIN = "uncertain"


class ReportStatus(str, enum.Enum):
    AI_DRAFT = "ai_draft"
    PHYSICIAN_DRAFT = "physician_draft"
    FINALIZED = "finalized"
    SIGNED = "signed"


class ModelStatus(str, enum.Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEPRECATED = "deprecated"
