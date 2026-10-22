export type UserRole =
  | "super_admin"
  | "hospital_admin"
  | "doctor"
  | "radiologist"
  | "technician"
  | "researcher";

export interface User {
  id: string;
  organization_id: string;
  role: UserRole;
  name: string;
  email: string;
  status: "active" | "invited" | "disabled";
}

export type Sex = "male" | "female" | "other" | "unknown";

export interface PatientSummary {
  id: string;
  external_patient_id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  sex: Sex;
  age: number;
}

export interface Patient extends PatientSummary {
  organization_id: string;
  phone: string | null;
  email: string | null;
}

export interface ClinicalHistoryEntry {
  id: string;
  patient_id: string;
  condition: string;
  description: string | null;
  onset_date: string | null;
  status: "active" | "resolved" | "chronic";
  source: string;
}

export interface TimelineEvent {
  event_type: string;
  title: string;
  description: string | null;
  timestamp: string;
  reference_id: string | null;
  source: string;
}

export interface DashboardStats {
  total_patients: number;
  studies_today: number;
  pending_ai_reviews: number;
  reports_pending: number;
  ai_analyses_running: number;
}

export interface ActivityItem {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  actor_name: string | null;
  timestamp: string;
}

export interface DashboardResponse {
  stats: DashboardStats;
  recent_activity: ActivityItem[];
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export type StudyStatus = "pending" | "uploading" | "processing" | "ready" | "failed";

export interface StudySummary {
  id: string;
  patient_id: string;
  study_uid: string;
  accession_number: string | null;
  modality: string;
  study_description: string | null;
  study_date: string | null;
  institution: string | null;
  body_part: string | null;
  status: StudyStatus;
}

export interface SeriesSummary {
  id: string;
  series_uid: string;
  modality: string;
  description: string | null;
  series_number: number | null;
  instance_count: number;
}

export interface StudyDetail extends StudySummary {
  series: SeriesSummary[];
}

export interface InstanceSummary {
  id: string;
  sop_instance_uid: string;
  instance_number: number | null;
}

export interface UploadFailure {
  filename: string;
  reason: string;
}

export interface UploadResult {
  study_id: string | null;
  files_received: number;
  instances_created: number;
  instances_already_present: number;
  failures: UploadFailure[];
  status: StudyStatus | null;
}

export interface MeasurementRecord {
  id: string;
  study_id: string;
  series_id: string | null;
  user_id: string | null;
  author_name: string | null;
  type: string;
  value: number;
  unit: string;
  geometry: unknown;
  source: string;
  created_at: string;
}

export interface AnnotationRecord {
  id: string;
  study_id: string;
  series_id: string | null;
  user_id: string;
  author_name: string | null;
  type: string;
  geometry: unknown;
  label: string | null;
  meta: Record<string, unknown> | null;
  created_at: string;
}

export type AIAnalysisStatus = "queued" | "running" | "completed" | "failed" | "unavailable";
export type AIFindingStatus =
  | "ai_flagged"
  | "physician_reviewing"
  | "confirmed_by_physician"
  | "dismissed"
  | "uncertain";
export type ModelStatus = "available" | "unavailable" | "deprecated";

export interface AIModelRecord {
  id: string;
  name: string;
  version: string;
  modality: string;
  anatomy: string | null;
  task: string;
  provider: string;
  model_location: string | null;
  supported_input: string | null;
  output_format: string | null;
  status: ModelStatus;
}

export interface AIAnalysisRecord {
  id: string;
  study_id: string;
  model_id: string | null;
  model_version: string | null;
  status: AIAnalysisStatus;
  started_at: string | null;
  completed_at: string | null;
  processing_time_seconds: number | null;
  error: string | null;
  created_at: string;
}

export interface AIFindingRecord {
  id: string;
  analysis_id: string;
  finding_type: string;
  description: string;
  anatomical_region: string | null;
  confidence: number | null;
  severity: string | null;
  status: AIFindingStatus;
  coordinates: unknown;
  measurement: unknown;
  evidence_reference: string | null;
  created_at: string;
}

export interface PatientFindingRecord extends AIFindingRecord {
  study_id: string;
}

export type ReportStatus = "ai_draft" | "physician_draft" | "finalized" | "signed";

export interface ReportRecord {
  id: string;
  patient_id: string;
  study_id: string | null;
  author_id: string | null;
  author_name: string | null;
  status: ReportStatus;
  draft_content: string | null;
  finalized_content: string | null;
  signed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReportVersionRecord {
  id: string;
  report_id: string;
  version_number: number;
  author_id: string | null;
  author_name: string | null;
  content: string;
  created_at: string;
}

export interface MeasurementComparison {
  type: string;
  unit: string;
  value_a: number | null;
  value_b: number | null;
  delta: number | null;
  percent_change: number | null;
  note: string;
}

export interface FindingComparison {
  finding_type: string;
  anatomical_region: string | null;
  relationship: "present_in_both" | "new_in_b" | "not_re_flagged_in_b";
  finding_a: AIFindingRecord | null;
  finding_b: AIFindingRecord | null;
}

export interface ComparisonResult {
  comparable: boolean;
  reason: string | null;
  study_a: StudySummary;
  study_b: StudySummary;
  measurement_comparisons: MeasurementComparison[];
  finding_comparisons: FindingComparison[];
}

export interface Notification {
  id: string;
  type: string;
  title: string;
  body: string | null;
  read: boolean;
  reference_id: string | null;
  created_at: string;
}

export interface SearchResultItem {
  type: "patient" | "study" | "report";
  id: string;
  title: string;
  subtitle: string | null;
  href: string;
}
