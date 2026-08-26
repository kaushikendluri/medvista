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
