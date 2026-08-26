from datetime import date

from tests.conftest import auth_headers


def test_empty_database_returns_empty_list(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    response = client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_create_and_fetch_patient(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    create_response = client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "external_patient_id": "P-100",
            "first_name": "Test",
            "last_name": "Patient",
            "date_of_birth": "1990-01-15",
            "sex": "female",
        },
    )
    assert create_response.status_code == 201, create_response.text
    created = create_response.json()
    assert created["first_name"] == "Test"
    expected_age = date.today().year - 1990 - (
        1 if (date.today().month, date.today().day) < (1, 15) else 0
    )
    assert created["age"] == expected_age

    get_response = client.get(f"/api/v1/patients/{created['id']}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["external_patient_id"] == "P-100"


def test_create_patient_rejects_future_dob(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    response = client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "external_patient_id": "P-101",
            "first_name": "Future",
            "last_name": "Patient",
            "date_of_birth": "2999-01-01",
            "sex": "unknown",
        },
    )
    assert response.status_code == 422


def test_patient_search(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "external_patient_id": "P-200",
            "first_name": "Zoe",
            "last_name": "Nakamura",
            "date_of_birth": "1985-06-01",
            "sex": "female",
        },
    )
    response = client.get("/api/v1/patients", headers=headers, params={"search": "Nakamura"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["last_name"] == "Nakamura"

    response_miss = client.get("/api/v1/patients", headers=headers, params={"search": "NoMatch"})
    assert response_miss.json()["total"] == 0


def test_researcher_cannot_view_identified_patients(client, researcher_user):
    headers = auth_headers(client, "researcher@clinicaltest.io")
    response = client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 403


def test_cross_organization_isolation(client, doctor_user, other_org_doctor):
    doctor_headers = auth_headers(client, "doctor@clinicaltest.io")
    create_response = client.post(
        "/api/v1/patients",
        headers=doctor_headers,
        json={
            "external_patient_id": "P-300",
            "first_name": "Isolated",
            "last_name": "Patient",
            "date_of_birth": "1980-01-01",
            "sex": "male",
        },
    )
    patient_id = create_response.json()["id"]

    other_headers = auth_headers(client, "doctor2@clinicaltest.io")
    response = client.get(f"/api/v1/patients/{patient_id}", headers=other_headers)
    assert response.status_code == 404

    list_response = client.get("/api/v1/patients", headers=other_headers)
    assert list_response.json()["total"] == 0


def test_timeline_empty_for_new_patient(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    create_response = client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "external_patient_id": "P-400",
            "first_name": "Timeline",
            "last_name": "Test",
            "date_of_birth": "1990-01-01",
            "sex": "male",
        },
    )
    patient_id = create_response.json()["id"]
    response = client.get(f"/api/v1/patients/{patient_id}/timeline", headers=headers)
    assert response.status_code == 200
    assert response.json() == []
