import uuid

from app.models.ai_analysis import AIAnalysis
from app.models.ai_finding import AIFinding
from app.models.enums import AIAnalysisStatus, AIFindingStatus
from app.services.ai_service import process_analysis_job
from app.services.queue import ANALYSIS_QUEUE_KEY, get_redis_client
from tests.conftest import auth_headers
from tests.dicom_fixtures import make_synthetic_dicom


def _create_patient_and_study(client, headers, external_id):
    patient_response = client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "external_patient_id": external_id,
            "first_name": "AI",
            "last_name": "Subject",
            "date_of_birth": "1980-01-01",
            "sex": "male",
        },
    )
    patient_id = patient_response.json()["id"]
    dicom_bytes = make_synthetic_dicom(modality="CT")
    upload = client.post(
        f"/api/v1/patients/{patient_id}/studies/upload",
        headers=headers,
        files={"files": ("slice1.dcm", dicom_bytes, "application/dicom")},
    )
    return patient_id, upload.json()["study_id"]


# --- Model registry ---------------------------------------------------------


def test_super_admin_can_register_model(client, db_session, organization):
    from app.core.security import hash_password
    from app.models.enums import UserRole, UserStatus
    from app.models.user import User

    admin = User(
        organization_id=organization.id,
        role=UserRole.SUPER_ADMIN,
        name="Super Admin",
        email="superadmin@clinicaltest.io",
        hashed_password=hash_password("TestPassword123!"),
        status=UserStatus.ACTIVE,
    )
    db_session.add(admin)
    db_session.commit()
    headers = auth_headers(client, "superadmin@clinicaltest.io")

    response = client.post(
        "/api/v1/ai/models",
        headers=headers,
        json={
            "name": "Chest CT Abnormality Detector",
            "version": "1.0.0",
            "modality": "CT",
            "task": "abnormality_detection",
            "provider": "internal",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    # Status is always computed from the worker's actual code registry,
    # never trusted from input — the registry is empty, so this is
    # correctly reported unavailable even though it was just registered.
    assert body["status"] == "unavailable"


def test_doctor_cannot_register_model(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    response = client.post(
        "/api/v1/ai/models",
        headers=headers,
        json={
            "name": "Test Model",
            "version": "1.0.0",
            "modality": "CT",
            "task": "test",
            "provider": "internal",
        },
    )
    assert response.status_code == 403


def test_list_models_empty_by_default(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    response = client.get("/api/v1/ai/models", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


# --- Analysis job lifecycle ---------------------------------------------------


def test_start_analysis_enqueues_job(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    _, study_id = _create_patient_and_study(client, headers, "P-AI-1")

    assert get_redis_client().llen(ANALYSIS_QUEUE_KEY) == 0

    response = client.post(f"/api/v1/studies/{study_id}/analyze", headers=headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "queued"
    assert body["study_id"] == study_id

    assert get_redis_client().llen(ANALYSIS_QUEUE_KEY) == 1
    queued_id = get_redis_client().lindex(ANALYSIS_QUEUE_KEY, 0)
    assert queued_id == body["id"]


def test_technician_cannot_start_analysis(client, db_session, organization):
    from app.core.security import hash_password
    from app.models.enums import UserRole, UserStatus
    from app.models.user import User

    tech = User(
        organization_id=organization.id,
        role=UserRole.TECHNICIAN,
        name="Test Tech",
        email="aitech@clinicaltest.io",
        hashed_password=hash_password("TestPassword123!"),
        status=UserStatus.ACTIVE,
    )
    db_session.add(tech)
    db_session.commit()
    headers = auth_headers(client, "aitech@clinicaltest.io")

    response = client.post(
        "/api/v1/studies/00000000-0000-0000-0000-000000000000/analyze", headers=headers
    )
    assert response.status_code == 403


def test_process_analysis_job_reports_unavailable_honestly(client, db_session, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    _, study_id = _create_patient_and_study(client, headers, "P-AI-2")

    analysis = AIAnalysis(study_id=uuid.UUID(study_id), status=AIAnalysisStatus.QUEUED)
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    process_analysis_job(db_session, analysis.id)
    db_session.refresh(analysis)

    assert analysis.status == AIAnalysisStatus.UNAVAILABLE
    assert "No AI model is currently available" in analysis.error
    assert analysis.started_at is not None
    assert analysis.completed_at is not None
    assert analysis.processing_time_seconds is not None

    # No fabricated findings under any circumstance.
    findings = (
        db_session.query(AIFinding).filter(AIFinding.analysis_id == analysis.id).all()
    )
    assert findings == []


def test_list_analyses_and_findings(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    _, study_id = _create_patient_and_study(client, headers, "P-AI-3")

    client.post(f"/api/v1/studies/{study_id}/analyze", headers=headers)

    analyses = client.get(f"/api/v1/studies/{study_id}/analyses", headers=headers)
    assert analyses.status_code == 200
    assert len(analyses.json()) == 1

    findings = client.get(f"/api/v1/studies/{study_id}/findings", headers=headers)
    assert findings.status_code == 200
    assert findings.json() == []


# --- Finding review ----------------------------------------------------------


def test_review_finding_updates_status(client, db_session, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    _, study_id = _create_patient_and_study(client, headers, "P-AI-4")

    analysis = AIAnalysis(study_id=uuid.UUID(study_id), status=AIAnalysisStatus.COMPLETED)
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    # Simulates output a real future model would produce — inserted directly
    # since no implementation is registered to produce one for real yet.
    finding = AIFinding(
        analysis_id=analysis.id,
        finding_type="pulmonary_nodule",
        description="Possible nodule flagged for review",
        anatomical_region="right upper lobe",
        confidence=0.87,
        severity="moderate",
        status=AIFindingStatus.AI_FLAGGED,
    )
    db_session.add(finding)
    db_session.commit()
    db_session.refresh(finding)

    response = client.post(
        f"/api/v1/findings/{finding.id}/review",
        headers=headers,
        json={"status": "confirmed_by_physician"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "confirmed_by_physician"

    listing = client.get(f"/api/v1/studies/{study_id}/findings", headers=headers)
    assert listing.json()[0]["status"] == "confirmed_by_physician"


def test_patient_ai_findings_aggregates_across_studies(client, db_session, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    patient_id, study_id = _create_patient_and_study(client, headers, "P-AI-6")

    empty = client.get(f"/api/v1/patients/{patient_id}/ai-findings", headers=headers)
    assert empty.status_code == 200
    assert empty.json() == []

    analysis = AIAnalysis(study_id=uuid.UUID(study_id), status=AIAnalysisStatus.COMPLETED)
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)
    finding = AIFinding(
        analysis_id=analysis.id,
        finding_type="pulmonary_nodule",
        description="Test finding",
        status=AIFindingStatus.AI_FLAGGED,
    )
    db_session.add(finding)
    db_session.commit()

    response = client.get(f"/api/v1/patients/{patient_id}/ai-findings", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["study_id"] == study_id


def test_cross_organization_analysis_isolation(client, doctor_user, other_org_doctor):
    doctor_headers = auth_headers(client, "doctor@clinicaltest.io")
    _, study_id = _create_patient_and_study(client, doctor_headers, "P-AI-5")

    other_headers = auth_headers(client, "doctor2@clinicaltest.io")
    response = client.post(f"/api/v1/studies/{study_id}/analyze", headers=other_headers)
    assert response.status_code == 404
