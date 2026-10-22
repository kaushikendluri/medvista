from app.schemas.ai import AIFindingRead
from app.schemas.study import StudyRead
from pydantic import BaseModel


class MeasurementComparison(BaseModel):
    type: str
    unit: str
    value_a: float | None
    value_b: float | None
    delta: float | None
    percent_change: float | None
    note: str


class FindingComparison(BaseModel):
    finding_type: str
    anatomical_region: str | None
    relationship: str  # "present_in_both" | "new_in_b" | "not_re_flagged_in_b"
    finding_a: AIFindingRead | None
    finding_b: AIFindingRead | None


class ComparisonResult(BaseModel):
    comparable: bool
    reason: str | None
    study_a: StudyRead
    study_b: StudyRead
    measurement_comparisons: list[MeasurementComparison]
    finding_comparisons: list[FindingComparison]
