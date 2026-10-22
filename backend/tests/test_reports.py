from tests.conftest import auth_headers
from tests.dicom_fixtures import make_synthetic_dicom


def _create_patient_and_study(client, headers, external_id):
    patient_response = client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "external_patient_id": external_id,
            "first_name": "Report",
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


def test_create_report_populates_real_data_template(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    patient_id, study_id = _create_patient_and_study(client, headers, "P-RPT-1")

    response = client.post(
        f"/api/v1/patients/{patient_id}/reports", headers=headers, json={"study_id": study_id}
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "physician_draft"
    assert "Report Subject" in body["draft_content"]
    assert "CT" in body["draft_content"]
    assert "Not AI-generated" in body["draft_content"]


def test_edit_report_creates_version_snapshot(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    patient_id, study_id = _create_patient_and_study(client, headers, "P-RPT-2")
    create = client.post(
        f"/api/v1/patients/{patient_id}/reports", headers=headers, json={"study_id": study_id}
    )
    report_id = create.json()["id"]
    original_content = create.json()["draft_content"]

    edit = client.patch(
        f"/api/v1/reports/{report_id}", headers=headers, json={"draft_content": "Edited impression text."}
    )
    assert edit.status_code == 200
    assert edit.json()["draft_content"] == "Edited impression text."

    versions = client.get(f"/api/v1/reports/{report_id}/versions", headers=headers)
    assert versions.status_code == 200
    assert len(versions.json()) == 1
    assert versions.json()[0]["content"] == original_content


def test_finalize_and_sign_flow(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    patient_id, study_id = _create_patient_and_study(client, headers, "P-RPT-3")
    create = client.post(
        f"/api/v1/patients/{patient_id}/reports", headers=headers, json={"study_id": study_id}
    )
    report_id = create.json()["id"]

    finalize = client.post(f"/api/v1/reports/{report_id}/finalize", headers=headers)
    assert finalize.status_code == 200
    assert finalize.json()["status"] == "finalized"

    # Can't edit a finalized report.
    edit = client.patch(
        f"/api/v1/reports/{report_id}", headers=headers, json={"draft_content": "too late"}
    )
    assert edit.status_code == 409

    sign = client.post(f"/api/v1/reports/{report_id}/sign", headers=headers)
    assert sign.status_code == 200
    assert sign.json()["status"] == "signed"
    assert sign.json()["signed_at"] is not None


def test_only_author_can_sign(client, db_session, organization, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    patient_id, study_id = _create_patient_and_study(client, headers, "P-RPT-4")
    create = client.post(
        f"/api/v1/patients/{patient_id}/reports", headers=headers, json={"study_id": study_id}
    )
    report_id = create.json()["id"]
    client.post(f"/api/v1/reports/{report_id}/finalize", headers=headers)

    from app.core.security import hash_password
    from app.models.enums import UserRole, UserStatus
    from app.models.user import User

    other_doctor = User(
        organization_id=organization.id,
        role=UserRole.DOCTOR,
        name="Other Doctor",
        email="otherrptdoc@clinicaltest.io",
        hashed_password=hash_password("TestPassword123!"),
        status=UserStatus.ACTIVE,
    )
    db_session.add(other_doctor)
    db_session.commit()
    other_headers = auth_headers(client, "otherrptdoc@clinicaltest.io")

    response = client.post(f"/api/v1/reports/{report_id}/sign", headers=other_headers)
    assert response.status_code == 403


def test_cannot_finalize_twice(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    patient_id, study_id = _create_patient_and_study(client, headers, "P-RPT-5")
    create = client.post(
        f"/api/v1/patients/{patient_id}/reports", headers=headers, json={"study_id": study_id}
    )
    report_id = create.json()["id"]
    client.post(f"/api/v1/reports/{report_id}/finalize", headers=headers)

    response = client.post(f"/api/v1/reports/{report_id}/finalize", headers=headers)
    assert response.status_code == 409


def test_cross_organization_report_isolation(client, doctor_user, other_org_doctor):
    doctor_headers = auth_headers(client, "doctor@clinicaltest.io")
    patient_id, study_id = _create_patient_and_study(client, doctor_headers, "P-RPT-6")
    create = client.post(
        f"/api/v1/patients/{patient_id}/reports", headers=doctor_headers, json={"study_id": study_id}
    )
    report_id = create.json()["id"]

    other_headers = auth_headers(client, "doctor2@clinicaltest.io")
    response = client.get(f"/api/v1/reports/{report_id}", headers=other_headers)
    assert response.status_code == 404
