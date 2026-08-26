"""Optional development seed data — SYNTHETIC DEMO DATA ONLY.

Never contains real patient information. Safe to run repeatedly (idempotent
on organization name). The application works correctly with an empty
database; this script exists purely to make local development easier.

Usage:
    python -m scripts.seed
"""
from datetime import date

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.clinical_history import ClinicalHistory
from app.models.enums import ClinicalHistoryStatus, OrganizationType, Sex, UserRole, UserStatus
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.user import User
from app.core.security import hash_password

SYNTHETIC_PATIENTS = [
    dict(
        external_patient_id="SYN-0001",
        first_name="Asha",
        last_name="Verma",
        date_of_birth=date(1988, 4, 12),
        sex=Sex.FEMALE,
    ),
    dict(
        external_patient_id="SYN-0002",
        first_name="Daniel",
        last_name="Okafor",
        date_of_birth=date(1972, 11, 3),
        sex=Sex.MALE,
    ),
    dict(
        external_patient_id="SYN-0003",
        first_name="Mei",
        last_name="Lin",
        date_of_birth=date(1995, 7, 21),
        sex=Sex.FEMALE,
    ),
]


def run() -> None:
    db = SessionLocal()
    try:
        org = db.scalar(select(Organization).where(Organization.name == "MedVista Demo Hospital"))
        if org is None:
            org = Organization(name="MedVista Demo Hospital", type=OrganizationType.HOSPITAL)
            db.add(org)
            db.commit()
            db.refresh(org)
            print(f"Created organization: {org.name} ({org.id})")
        else:
            print(f"Organization already exists: {org.name} ({org.id})")

        demo_users = [
            ("Dr. Sarah Chen", "admin@medvista.demo", UserRole.HOSPITAL_ADMIN),
            ("Dr. James Whitfield", "doctor@medvista.demo", UserRole.DOCTOR),
            ("Dr. Priya Nair", "radiologist@medvista.demo", UserRole.RADIOLOGIST),
            ("Alex Rivera", "tech@medvista.demo", UserRole.TECHNICIAN),
        ]
        for name, email, role in demo_users:
            existing = db.scalar(select(User).where(User.email == email))
            if existing is not None:
                print(f"User already exists: {email}")
                continue
            user = User(
                organization_id=org.id,
                role=role,
                name=name,
                email=email,
                hashed_password=hash_password("MedVista!Demo123"),
                status=UserStatus.ACTIVE,
            )
            db.add(user)
            print(f"Created user: {email} / MedVista!Demo123 (role={role.value})")
        db.commit()

        for patient_data in SYNTHETIC_PATIENTS:
            existing = db.scalar(
                select(Patient).where(
                    Patient.organization_id == org.id,
                    Patient.external_patient_id == patient_data["external_patient_id"],
                )
            )
            if existing is not None:
                print(f"Patient already exists: {patient_data['external_patient_id']}")
                continue
            patient = Patient(organization_id=org.id, **patient_data)
            db.add(patient)
            db.commit()
            db.refresh(patient)
            db.add(
                ClinicalHistory(
                    patient_id=patient.id,
                    condition="Synthetic demo condition — no clinical meaning",
                    description="Seeded for local development only.",
                    status=ClinicalHistoryStatus.ACTIVE,
                    source="SYNTHETIC DEMO DATA",
                )
            )
            db.commit()
            print(f"Created patient: {patient.first_name} {patient.last_name} ({patient.external_patient_id})")

        print("\nSeed complete. All data above is SYNTHETIC DEMO DATA.")
        print("Log in with e.g. admin@medvista.demo / MedVista!Demo123")
    finally:
        db.close()


if __name__ == "__main__":
    run()
