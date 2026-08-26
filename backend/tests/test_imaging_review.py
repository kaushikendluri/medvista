from tests.conftest import auth_headers
from tests.dicom_fixtures import make_synthetic_dicom


def _create_patient_and_study(client, headers, external_id):
    patient_response = client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "external_patient_id": external_id,
            "first_name": "Review",
            "last_name": "Subject",
            "date_of_birth": "1980-01-01",
            "sex": "male",
        },
    )
    patient_id = patient_response.json()["id"]
    dicom_bytes = make_synthetic_dicom()
    upload = client.post(
        f"/api/v1/patients/{patient_id}/studies/upload",
        headers=headers,
        files={"files": ("slice1.dcm", dicom_bytes, "application/dicom")},
    )
    return patient_id, upload.json()["study_id"]


def test_instance_file_returns_raw_dicom(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    _, study_id = _create_patient_and_study(client, headers, "P-REVIEW-1")
    detail = client.get(f"/api/v1/studies/{study_id}", headers=headers).json()
    series_id = detail["series"][0]["id"]
    instances = client.get(
        f"/api/v1/studies/{study_id}/series/{series_id}/instances", headers=headers
    ).json()
    instance_id = instances[0]["id"]

    response = client.get(f"/api/v1/studies/{study_id}/instances/{instance_id}/file", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/dicom"
    assert response.content[128:132] == b"DICM"


def test_create_and_list_measurement(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    _, study_id = _create_patient_and_study(client, headers, "P-REVIEW-2")

    response = client.post(
        f"/api/v1/studies/{study_id}/measurements",
        headers=headers,
        json={
            "type": "length",
            "value": 8.4,
            "unit": "mm",
            "geometry": {"start": [10, 10], "end": [20, 20]},
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["value"] == 8.4
    assert body["source"] == "physician"
    assert body["author_name"] == "Test doctor"

    listing = client.get(f"/api/v1/studies/{study_id}/measurements", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_delete_measurement_only_by_owner_or_admin(client, doctor_user, db_session, organization):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    _, study_id = _create_patient_and_study(client, headers, "P-REVIEW-3")
    create = client.post(
        f"/api/v1/studies/{study_id}/measurements",
        headers=headers,
        json={"type": "length", "value": 5.0, "unit": "mm", "geometry": {}},
    )
    measurement_id = create.json()["id"]

    from app.core.security import hash_password
    from app.models.enums import UserRole, UserStatus
    from app.models.user import User

    other_doctor = User(
        organization_id=organization.id,
        role=UserRole.DOCTOR,
        name="Other Doctor",
        email="otherdoc@clinicaltest.io",
        hashed_password=hash_password("TestPassword123!"),
        status=UserStatus.ACTIVE,
    )
    db_session.add(other_doctor)
    db_session.commit()
    other_headers = auth_headers(client, "otherdoc@clinicaltest.io")

    forbidden = client.delete(f"/api/v1/measurements/{measurement_id}", headers=other_headers)
    assert forbidden.status_code == 403

    allowed = client.delete(f"/api/v1/measurements/{measurement_id}", headers=headers)
    assert allowed.status_code == 204


def test_create_and_list_annotation(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    _, study_id = _create_patient_and_study(client, headers, "P-REVIEW-4")

    response = client.post(
        f"/api/v1/studies/{study_id}/annotations",
        headers=headers,
        json={"type": "label", "geometry": {"x": 5, "y": 5}, "label": "Possible nodule"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["label"] == "Possible nodule"

    listing = client.get(f"/api/v1/studies/{study_id}/annotations", headers=headers)
    assert len(listing.json()) == 1


def test_technician_cannot_create_measurement(client, db_session, organization):
    from app.core.security import hash_password
    from app.models.enums import UserRole, UserStatus
    from app.models.user import User

    tech = User(
        organization_id=organization.id,
        role=UserRole.TECHNICIAN,
        name="Test Tech",
        email="reviewtech@clinicaltest.io",
        hashed_password=hash_password("TestPassword123!"),
        status=UserStatus.ACTIVE,
    )
    db_session.add(tech)
    db_session.commit()
    tech_headers = auth_headers(client, "reviewtech@clinicaltest.io")

    # The role check fires before the study lookup, so a nil study id is fine here.
    response = client.post(
        "/api/v1/studies/00000000-0000-0000-0000-000000000000/measurements",
        headers=tech_headers,
        json={"type": "length", "value": 1.0, "unit": "mm", "geometry": {}},
    )
    assert response.status_code == 403
