import uuid
import pytest
from fastapi.testclient import TestClient
from backend.api.app import app
from backend.db.session import init_db
from backend.db.database import SessionLocal
from backend.db.models import User
import bcrypt

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

def test_demo_officer_login_and_seed():
    """Verify demo officer account exists, authenticates via backend, and issues JWT with officer role."""
    # 1. Login with correct demo credentials
    res = client.post("/api/auth/login", json={
        "email": "officer@fairlendai.com",
        "password": "Officer@123",
        "expected_role": "officer"
    })
    assert res.status_code == 200, f"Demo officer login failed: {res.text}"
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "officer"
    assert data["user"]["email"] == "officer@fairlendai.com"

    # 2. Verify invalid password rejected
    res_bad = client.post("/api/auth/login", json={
        "email": "officer@fairlendai.com",
        "password": "WrongPassword!23",
        "expected_role": "officer"
    })
    assert res_bad.status_code == 401

def test_password_never_stored_in_plaintext():
    """Verify passwords in the database are hashed with bcrypt."""
    db = SessionLocal()
    officer = db.query(User).filter(User.email == "officer@fairlendai.com").first()
    db.close()

    assert officer is not None
    assert officer.password_hash != "Officer@123"
    assert officer.password_hash.startswith("$2b$") or officer.password_hash.startswith("$2a$")
    assert bcrypt.checkpw(b"Officer@123", officer.password_hash.encode("utf-8"))

def test_applicant_registration_and_login_flow():
    """Test full registration, validation, duplicate check, and login flow for applicants."""
    unique_suffix = uuid.uuid4().hex[:8]
    test_email = f"applicant_{unique_suffix}@example.com"
    test_password = "SecurePassword@2026"

    # 1. Register new applicant
    reg_res = client.post("/api/auth/register", json={
        "full_name": f"Applicant {unique_suffix}",
        "email": test_email,
        "phone": "+91 98765 11223",
        "password": test_password
    })
    assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == test_email
    assert reg_data["user"]["role"] == "applicant"

    token = reg_data["access_token"]

    # 2. Check duplicate email rejection
    dup_res = client.post("/api/auth/register", json={
        "full_name": "Duplicate User",
        "email": test_email,
        "phone": "+91 98765 11223",
        "password": test_password
    })
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"]

    # 3. Log in with registered applicant credentials
    login_res = client.post("/api/auth/login", json={
        "email": test_email,
        "password": test_password,
        "expected_role": "applicant"
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["user"]["role"] == "applicant"

    # 4. Access /api/auth/me with Bearer token
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == test_email

def test_field_validation_on_registration():
    """Test validation errors for invalid email, short phone, and weak password."""
    # Invalid email
    res1 = client.post("/api/auth/register", json={
        "full_name": "Test User",
        "email": "not-an-email",
        "phone": "9876543210",
        "password": "Password123"
    })
    assert res1.status_code == 400

    # Short phone
    res2 = client.post("/api/auth/register", json={
        "full_name": "Test User",
        "email": "valid@example.com",
        "phone": "12345",
        "password": "Password123"
    })
    assert res2.status_code == 400

    # Weak password (under 8 chars or no numbers)
    res3 = client.post("/api/auth/register", json={
        "full_name": "Test User",
        "email": "valid2@example.com",
        "phone": "9876543210",
        "password": "short"
    })
    assert res3.status_code in (400, 422)

def test_role_based_access_control():
    """Verify applicants cannot access officer routes and officers cannot access applicant routes."""
    # 1. Register + login a real applicant (no seeded demo applicant exists)
    reg_email = f"rbac_{uuid.uuid4().hex[:8]}@example.com"
    reg_res = client.post("/api/auth/register", json={
        "full_name": "RBAC Test Applicant",
        "email": reg_email,
        "phone": "9876500000",
        "password": "RbacPass123"
    })
    assert reg_res.status_code in (200, 201), reg_res.text
    app_res = client.post("/api/auth/login", json={
        "email": reg_email,
        "password": "RbacPass123",
        "expected_role": "applicant"
    })
    assert app_res.status_code == 200, app_res.text
    applicant_token = app_res.json()["access_token"]

    # 2. Login as officer
    off_res = client.post("/api/auth/login", json={
        "email": "officer@fairlendai.com",
        "password": "Officer@123",
        "expected_role": "officer"
    })
    officer_token = off_res.json()["access_token"]

    # 3. Applicant attempts to access officer dashboard applications -> 403 Forbidden
    res_officer_access = client.get("/api/officer/applications", headers={"Authorization": f"Bearer {applicant_token}"})
    assert res_officer_access.status_code == 403, "Applicant should NOT be able to access officer applications endpoint"

    # 4. Unauthenticated access to officer dashboard -> 401 Unauthorized
    res_unauth = client.get("/api/officer/applications")
    assert res_unauth.status_code == 401

    # 5. Officer CAN access officer dashboard
    res_officer_ok = client.get("/api/officer/applications", headers={"Authorization": f"Bearer {officer_token}"})
    assert res_officer_ok.status_code == 200

    # 6. Officer attempts to access applicant portal with expected_role='applicant' -> 403 Forbidden
    res_cross_login = client.post("/api/auth/login", json={
        "email": "officer@fairlendai.com",
        "password": "Officer@123",
        "expected_role": "applicant"
    })
    assert res_cross_login.status_code == 403
