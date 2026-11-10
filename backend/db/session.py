from backend.db.database import engine, Base
import backend.db.models  # Ensure all models are registered

from sqlalchemy import inspect, text
from backend.db.database import engine, Base, SessionLocal
import backend.db.models
from backend.db.models import User
from backend.core.auth import hash_password

DEMO_OFFICER_EMAIL = "officer@fairlendai.com"
DEMO_OFFICER_PASSWORD = "Officer@123"
DEMO_OFFICER_NAME = "P. S. Sharma (Senior Credit Underwriter)"
DEMO_OFFICER_PHONE = "+91 98765 00001"

def _run_sqlite_migrations():
    """Add new columns to existing SQLite tables if not already present."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    if "applications" in existing_tables:
        columns = [col["name"] for col in inspector.get_columns("applications")]
        if "applicant_user_id" not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE applications ADD COLUMN applicant_user_id VARCHAR(36) REFERENCES users(id)"))
                conn.commit()
        # Financial Stress Simulator: optional verified monthly expenses
        if "monthly_expenses" not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE applications ADD COLUMN monthly_expenses FLOAT"))
                conn.commit()

def seed_demo_accounts(db=None):
    """Seed or update demo officer and applicant accounts with secure bcrypt hashes."""
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        # 1. Seed Demo Officer: officer@fairlendai.com / Officer@123
        officer = db.query(User).filter(User.email == DEMO_OFFICER_EMAIL.lower()).first()
        if not officer:
            officer = User(
                email=DEMO_OFFICER_EMAIL.lower(),
                password_hash=hash_password(DEMO_OFFICER_PASSWORD),
                full_name=DEMO_OFFICER_NAME,
                phone=DEMO_OFFICER_PHONE,
                role="officer",
                is_active=True
            )
            db.add(officer)
        else:
            # Keep demo password up to date
            officer.password_hash = hash_password(DEMO_OFFICER_PASSWORD)
            officer.role = "officer"
            officer.full_name = DEMO_OFFICER_NAME

        # Also support legacy demo alias if accessed: officer@fairlend.ai
        legacy_officer = db.query(User).filter(User.email == "officer@fairlend.ai").first()
        if not legacy_officer:
            legacy_officer = User(
                email="officer@fairlend.ai",
                password_hash=hash_password("demo_officer_2026"),
                full_name=DEMO_OFFICER_NAME,
                phone=DEMO_OFFICER_PHONE,
                role="officer",
                is_active=True
            )
            db.add(legacy_officer)

        # Applicants are never seeded: every applicant signs up through
        # /api/auth/register and owns their own credentials (DPDP Act 2023).

        db.commit()
    finally:
        if should_close:
            db.close()

def init_db():
    """Initializes the database schema, runs lightweight migrations, and seeds defaults."""
    Base.metadata.create_all(bind=engine)
    _run_sqlite_migrations()
    seed_demo_accounts()

def reset_db():
    """Drops and recreates all database tables (useful with --reset-db flag)."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_demo_accounts()
