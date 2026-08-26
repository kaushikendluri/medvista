from tests.conftest import auth_headers


def test_login_success(client, doctor_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "doctor@clinicaltest.io", "password": "TestPassword123!"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "doctor@clinicaltest.io"
    assert "access_token" in body


def test_login_wrong_password(client, doctor_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "doctor@clinicaltest.io", "password": "WrongPassword"},
    )
    assert response.status_code == 401


def test_login_unknown_email(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@clinicaltest.io", "password": "whatever"},
    )
    assert response.status_code == 401


def test_me_requires_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user(client, doctor_user):
    headers = auth_headers(client, "doctor@clinicaltest.io")
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "doctor@clinicaltest.io"
