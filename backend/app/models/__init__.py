"""Import every model so `Base.metadata` is complete for Alembic autogenerate
and for `create_all` in tests."""
from app.models.ai_analysis import AIAnalysis  # noqa: F401
from app.models.ai_finding import AIFinding  # noqa: F401
from app.models.ai_model import AIModel  # noqa: F401
from app.models.annotation import Annotation  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.clinical_history import ClinicalHistory  # noqa: F401
from app.models.imaging_instance import ImagingInstance  # noqa: F401
from app.models.laboratory_result import LaboratoryResult  # noqa: F401
from app.models.measurement import Measurement  # noqa: F401
from app.models.medication import Medication  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.organization import Organization  # noqa: F401
from app.models.patient import Patient  # noqa: F401
from app.models.patient_event import PatientEvent  # noqa: F401
from app.models.report import Report  # noqa: F401
from app.models.report_version import ReportVersion  # noqa: F401
from app.models.series import Series  # noqa: F401
from app.models.study import Study  # noqa: F401
from app.models.user import User  # noqa: F401
