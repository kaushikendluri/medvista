from tests.conftest import auth_headers
from tests.dicom_fixtures import make_synthetic_dicom


def _create_patient(client, headers, external_id="P-STUDY-1"):
    response = client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "external_patient_id": external_id,
            "first_name": "Study",
            "last_name": "Subject",
            "date_of_birth": "1980-01-01",
            "sex": "male",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_upload_valid_dicom_creates_study_series_instance(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    patient_id = _create_patient(client, headers, "P-STUDY-100")

    dicom_bytes = make_synthetic_dicom(modality="CT")
    response = client.post(
        f"/api/v1/patients/{patient_id}/studies/upload",
        headers=headers,
        files={"files": ("slice1.dcm", dicom_bytes, "application/dicom")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["instances_created"] == 1
    assert body["instances_already_present"] == 0
    assert body["failures"] == []
    assert body["status"] == "ready"

    studies = client.get(f"/api/v1/patients/{patient_id}/studies", headers=headers)
    assert studies.status_code == 200
    assert len(studies.json()) == 1
    study = studies.json()[0]
    assert study["modality"] == "CT"
    assert study["status"] == "ready"

    detail = client.get(f"/api/v1/studies/{study['id']}", headers=headers)
    assert detail.status_code == 200
    detail_body = detail.json()
    assert len(detail_body["series"]) == 1
    assert detail_body["series"][0]["instance_count"] == 1


def test_upload_multiple_instances_same_series(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    patient_id = _create_patient(client, headers, "P-STUDY-101")

    study_uid = "1.2.826.0.1.3680043.9.9101.1"
    series_uid = "1.2.826.0.1.3680043.9.9101.2"
    file1 = make_synthetic_dicom(study_uid=study_uid, series_uid=series_uid, instance_number=1)
    file2 = make_synthetic_dicom(study_uid=study_uid, series_uid=series_uid, instance_number=2)

    response = client.post(
        f"/api/v1/patients/{patient_id}/studies/upload",
        headers=headers,
        files=[
            ("files", ("slice1.dcm", file1, "application/dicom")),
            ("files", ("slice2.dcm", file2, "application/dicom")),
        ],
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["instances_created"] == 2

    study_id = body["study_id"]
    detail = client.get(f"/api/v1/studies/{study_id}", headers=headers).json()
    assert len(detail["series"]) == 1
    assert detail["series"][0]["instance_count"] == 2


def test_reupload_same_instance_is_idempotent(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    patient_id = _create_patient(client, headers, "P-STUDY-102")
    dicom_bytes = make_synthetic_dicom()

    first = client.post(
        f"/api/v1/patients/{patient_id}/studies/upload",
        headers=headers,
        files={"files": ("slice1.dcm", dicom_bytes, "application/dicom")},
    )
    assert first.json()["instances_created"] == 1

    second = client.post(
        f"/api/v1/patients/{patient_id}/studies/upload",
        headers=headers,
        files={"files": ("slice1.dcm", dicom_bytes, "application/dicom")},
    )
    assert second.status_code == 201
    body = second.json()
    assert body["instances_created"] == 0
    assert body["instances_already_present"] == 1


def test_upload_rejects_invalid_file(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    patient_id = _create_patient(client, headers, "P-STUDY-103")

    response = client.post(
        f"/api/v1/patients/{patient_id}/studies/upload",
        headers=headers,
        files={"files": ("not-dicom.txt", b"this is not a dicom file", "text/plain")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["instances_created"] == 0
    assert len(body["failures"]) == 1
    assert body["study_id"] is None


def test_upload_rejects_cross_patient_study_uid(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    patient_a = _create_patient(client, headers, "P-STUDY-104A")
    patient_b = _create_patient(client, headers, "P-STUDY-104B")

    shared_study_uid = "1.2.826.0.1.3680043.9.9104.1"
    file_a = make_synthetic_dicom(study_uid=shared_study_uid)
    file_b = make_synthetic_dicom(study_uid=shared_study_uid)

    r1 = client.post(
        f"/api/v1/patients/{patient_a}/studies/upload",
        headers=headers,
        files={"files": ("a.dcm", file_a, "application/dicom")},
    )
    assert r1.json()["instances_created"] == 1

    r2 = client.post(
        f"/api/v1/patients/{patient_b}/studies/upload",
        headers=headers,
        files={"files": ("b.dcm", file_b, "application/dicom")},
    )
    body = r2.json()
    assert body["instances_created"] == 0
    assert len(body["failures"]) == 1
    assert "different patient" in body["failures"][0]["reason"]


def test_instance_preview_returns_image(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    patient_id = _create_patient(client, headers, "P-STUDY-105")
    dicom_bytes = make_synthetic_dicom()

    upload = client.post(
        f"/api/v1/patients/{patient_id}/studies/upload",
        headers=headers,
        files={"files": ("slice1.dcm", dicom_bytes, "application/dicom")},
    )
    study_id = upload.json()["study_id"]
    detail = client.get(f"/api/v1/studies/{study_id}", headers=headers).json()
    series_id = detail["series"][0]["id"]

    instances = client.get(
        f"/api/v1/studies/{study_id}/series/{series_id}/instances", headers=headers
    )
    assert instances.status_code == 200
    instance_list = instances.json()
    assert len(instance_list) == 1
    instance_id = instance_list[0]["id"]

    preview = client.get(
        f"/api/v1/studies/{study_id}/instances/{instance_id}/preview", headers=headers
    )
    assert preview.status_code == 200
    assert preview.headers["content-type"].startswith("image/")
    assert len(preview.content) > 0


def test_researcher_cannot_upload(client, researcher_user):
    headers = auth_headers(client, "researcher@clinicaltest.io")
    dicom_bytes = make_synthetic_dicom()
    response = client.post(
        "/api/v1/patients/00000000-0000-0000-0000-000000000000/studies/upload",
        headers=headers,
        files={"files": ("slice1.dcm", dicom_bytes, "application/dicom")},
    )
    assert response.status_code == 403


def test_cross_organization_study_isolation(client, doctor_user, other_org_doctor):
    doctor_headers = auth_headers(client, "doctor@clinicaltest.io")
    patient_id = _create_patient(client, doctor_headers, "P-STUDY-106")
    dicom_bytes = make_synthetic_dicom()

    upload = client.post(
        f"/api/v1/patients/{patient_id}/studies/upload",
        headers=doctor_headers,
        files={"files": ("slice1.dcm", dicom_bytes, "application/dicom")},
    )
    study_id = upload.json()["study_id"]

    other_headers = auth_headers(client, "doctor2@clinicaltest.io")
    response = client.get(f"/api/v1/studies/{study_id}", headers=other_headers)
    assert response.status_code == 404
