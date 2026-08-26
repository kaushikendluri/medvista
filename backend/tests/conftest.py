import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://medvista:medvista@localhost:5433/medvista"
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.enums import OrganizationType, UserRole, UserStatus
from app.models.organization import Organization
from app.models.user import User

settings = get_settings()
engine = create_engine(settings.DATABASE_URL, future=True)
TestSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _clean_tables():
    """App code commits real transactions, so isolate tests by truncating
    every table before each test rather than relying on rollback."""
    table_names = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
    with engine.begin() as conn:
        conn.exec_driver_sql(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE;")
    yield


@pytest.fixture()
def db_session():
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def organization(db_session):
    org = Organization(name="Test Hospital", type=OrganizationType.HOSPITAL)
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture()
def other_organization(db_session):
    org = Organization(name="Other Hospital", type=OrganizationType.HOSPITAL)
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


def make_user(db_session, org, role, email):
    user = User(
        organization_id=org.id,
        role=role,
        name=f"Test {role.value}",
        email=email,
        hashed_password=hash_password("TestPassword123!"),
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def doctor_user(db_session, organization):
    return make_user(db_session, organization, UserRole.DOCTOR, "doctor@clinicaltest.io")


@pytest.fixture()
def other_org_doctor(db_session, other_organization):
    return make_user(db_session, other_organization, UserRole.DOCTOR, "doctor2@clinicaltest.io")


@pytest.fixture()
def researcher_user(db_session, organization):
    return make_user(db_session, organization, UserRole.RESEARCHER, "researcher@clinicaltest.io")


def auth_headers(client, email: str) -> dict:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "TestPassword123!"})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
