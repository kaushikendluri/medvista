import uuid

from app.models.ai_analysis import AIAnalysis
from app.models.ai_finding import AIFinding
from app.models.enums import AIAnalysisStatus, AIFindingStatus
from app.models.measurement import Measurement
from tests.conftest import auth_headers
from tests.dicom_fixtures import make_synthetic_dicom


def _upload_study(client, headers, patient_id, study_uid, modality="CT", study_date="2026-01-01"):
    dicom_bytes = make_synthetic_dicom(study_uid=study_uid, modality=modality, study_date=study_date.replace("-", ""))
    response = client.post(
        f"/api/v1/patients/{patient_id}/studies/upload",
        headers=headers,
        files={"files": (f"{study_uid}.dcm", dicom_bytes, "application/dicom")},
    )
    return response.json()["study_id"]


def test_compare_studies_with_single_matching_measurement(client, db_session, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    patient_response = client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "external_patient_id": "P-CMP-1",
            "first_name": "Compare",
            "last_name": "Subject",
            "date_of_birth": "1980-01-01",
            "sex": "male",
        },
    )
    patient_id = patient_response.json()["id"]

    study_a_id = _upload_study(client, headers, patient_id, "1.2.826.0.1.3680043.9.5001.1", study_date="2026-01-01")
    study_b_id = _upload_study(client, headers, patient_id, "1.2.826.0.1.3680043.9.5002.1", study_date="2026-06-01")

    db_session.add(
        Measurement(
            study_id=uuid.UUID(study_a_id), type="length", value=6.2, unit="mm", geometry={}, source="physician"
        )
    )
    db_session.add(
        Measurement(
            study_id=uuid.UUID(study_b_id), type="length", value=8.4, unit="mm", geometry={}, source="physician"
        )
    )
    db_session.commit()

    response = client.get(f"/api/v1/studies/{study_a_id}/compare/{study_b_id}", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["comparable"] is True
    # study_a in the response is the chronologically earlier one regardless
    # of which id was passed first/second in the URL.
    assert body["study_a"]["id"] == study_a_id
    assert body["study_b"]["id"] == study_b_id

    measurements = body["measurement_comparisons"]
    assert len(measurements) == 1
    assert measurements[0]["value_a"] == 6.2
    assert measurements[0]["value_b"] == 8.4
    assert measurements[0]["delta"] == 2.2


def test_compare_reverses_order_when_urls_passed_reverse_chronological(client, db_session, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    patient_response = client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "external_patient_id": "P-CMP-2",
            "first_name": "Compare",
            "last_name": "Order",
            "date_of_birth": "1980-01-01",
            "sex": "male",
        },
    )
    patient_id = patient_response.json()["id"]
    study_a_id = _upload_study(client, headers, patient_id, "1.2.826.0.1.3680043.9.5003.1", study_date="2026-01-01")
    study_b_id = _upload_study(client, headers, patient_id, "1.2.826.0.1.3680043.9.5004.1", study_date="2026-06-01")

    # Pass the LATER study first in the URL — the service must still report
    # study_a as the chronologically earlier one.
    response = client.get(f"/api/v1/studies/{study_b_id}/compare/{study_a_id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["study_a"]["id"] == study_a_id
    assert body["study_b"]["id"] == study_b_id


def test_compare_different_modalities_not_comparable(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    patient_response = client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "external_patient_id": "P-CMP-3",
            "first_name": "Compare",
            "last_name": "Modality",
            "date_of_birth": "1980-01-01",
            "sex": "male",
        },
    )
    patient_id = patient_response.json()["id"]
    study_a_id = _upload_study(client, headers, patient_id, "1.2.826.0.1.3680043.9.5005.1", modality="CT")
    study_b_id = _upload_study(client, headers, patient_id, "1.2.826.0.1.3680043.9.5006.1", modality="MR")

    response = client.get(f"/api/v1/studies/{study_a_id}/compare/{study_b_id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["comparable"] is False
    assert "modalit" in body["reason"].lower()
    assert body["measurement_comparisons"] == []


def test_compare_findings_relationships(client, db_session, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    patient_response = client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "external_patient_id": "P-CMP-4",
            "first_name": "Compare",
            "last_name": "Findings",
            "date_of_birth": "1980-01-01",
            "sex": "male",
        },
    )
    patient_id = patient_response.json()["id"]
    study_a_id = _upload_study(client, headers, patient_id, "1.2.826.0.1.3680043.9.5007.1", study_date="2026-01-01")
    study_b_id = _upload_study(client, headers, patient_id, "1.2.826.0.1.3680043.9.5008.1", study_date="2026-06-01")

    analysis_a = AIAnalysis(study_id=uuid.UUID(study_a_id), status=AIAnalysisStatus.COMPLETED)
    analysis_b = AIAnalysis(study_id=uuid.UUID(study_b_id), status=AIAnalysisStatus.COMPLETED)
    db_session.add_all([analysis_a, analysis_b])
    db_session.commit()
    db_session.refresh(analysis_a)
    db_session.refresh(analysis_b)

    # Present in both (same type + region).
    db_session.add(
        AIFinding(
            analysis_id=analysis_a.id,
            finding_type="nodule",
            description="a",
            anatomical_region="right upper lobe",
            status=AIFindingStatus.AI_FLAGGED,
        )
    )
    db_session.add(
        AIFinding(
            analysis_id=analysis_b.id,
            finding_type="nodule",
            description="b",
            anatomical_region="right upper lobe",
            status=AIFindingStatus.AI_FLAGGED,
        )
    )
    # New in the later study only.
    db_session.add(
        AIFinding(
            analysis_id=analysis_b.id,
            finding_type="opacity",
            description="c",
            anatomical_region="left lower lobe",
            status=AIFindingStatus.AI_FLAGGED,
        )
    )
    db_session.commit()

    response = client.get(f"/api/v1/studies/{study_a_id}/compare/{study_b_id}", headers=headers)
    assert response.status_code == 200
    comparisons = {c["finding_type"]: c["relationship"] for c in response.json()["finding_comparisons"]}
    assert comparisons["nodule"] == "present_in_both"
    assert comparisons["opacity"] == "new_in_b"
