from tests.conftest import auth_headers


def test_technician_cannot_create_users(client, db_session, organization):
    from app.core.security import hash_password
    from app.models.enums import UserRole, UserStatus
    from app.models.user import User

    tech = User(
        organization_id=organization.id,
        role=UserRole.TECHNICIAN,
        name="Test Technician",
        email="tech@clinicaltest.io",
        hashed_password=hash_password("TestPassword123!"),
        status=UserStatus.ACTIVE,
    )
    db_session.add(tech)
    db_session.commit()

    headers = auth_headers(client, "tech@clinicaltest.io")
    response = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "name": "New User",
            "email": "new@clinicaltest.io",
            "password": "Password123!",
            "role": "doctor",
        },
    )
    assert response.status_code == 403


def test_hospital_admin_can_create_doctor(client, db_session, organization):
    from app.core.security import hash_password
    from app.models.enums import UserRole, UserStatus
    from app.models.user import User

    admin = User(
        organization_id=organization.id,
        role=UserRole.HOSPITAL_ADMIN,
        name="Test Admin",
        email="admin@clinicaltest.io",
        hashed_password=hash_password("TestPassword123!"),
        status=UserStatus.ACTIVE,
    )
    db_session.add(admin)
    db_session.commit()

    headers = auth_headers(client, "admin@clinicaltest.io")
    response = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "name": "New Doctor",
            "email": "newdoc@clinicaltest.io",
            "password": "Password123!",
            "role": "doctor",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["role"] == "doctor"


def test_hospital_admin_cannot_create_super_admin(client, db_session, organization):
    from app.core.security import hash_password
    from app.models.enums import UserRole, UserStatus
    from app.models.user import User

    admin = User(
        organization_id=organization.id,
        role=UserRole.HOSPITAL_ADMIN,
        name="Test Admin",
        email="admin2@clinicaltest.io",
        hashed_password=hash_password("TestPassword123!"),
        status=UserStatus.ACTIVE,
    )
    db_session.add(admin)
    db_session.commit()

    headers = auth_headers(client, "admin2@clinicaltest.io")
    response = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "name": "Sneaky Admin",
            "email": "sneaky@clinicaltest.io",
            "password": "Password123!",
            "role": "super_admin",
        },
    )
    assert response.status_code == 403
