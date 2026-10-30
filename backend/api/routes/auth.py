import re
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.db.database import get_db
from backend.db.models import User, Application, AuditLog
from backend.core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_applicant,
    require_officer
)
from backend.core.security import decrypt_field

router = APIRouter(prefix="/auth", tags=["Authentication & Access Control"])

EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w+$"
PHONE_REGEX = r"^\+?[0-9\s\-\(\)]{10,16}$"

class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., max_length=255)
    phone: str = Field(..., max_length=20)
    password: str = Field(..., min_length=8, max_length=128)

class LoginRequest(BaseModel):
    email: str
    password: str
    expected_role: Optional[str] = None  # "applicant" | "officer"

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: Optional[str] = None
    role: str
    created_at: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class ApplicantAppSummary(BaseModel):
    id: str
    created_at: str
    applicant_name: str
    requested_amount: float
    tenure_months: int
    monthly_income: float
    foir: float
    ai_recommendation: str
    ai_confidence: str
    status: str

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register_applicant(req: RegisterRequest, db: Session = Depends(get_db)):
    """
    Registers a new Applicant account, securely hashes password,
    persists profile to database, and issues an immediate JWT session token.
    """
    # 1. Validation: Name
    clean_name = req.full_name.strip()
    if len(clean_name) < 2:
        raise HTTPException(status_code=400, detail="Please enter a valid full name (minimum 2 characters).")

    # 2. Validation: Email
    clean_email = req.email.strip().lower()
    if not re.match(EMAIL_REGEX, clean_email):
        raise HTTPException(status_code=400, detail="Please provide a valid email address.")

    # 3. Validation: Phone
    clean_phone = req.phone.strip()
    digits_only = re.sub(r"\D", "", clean_phone)
    if len(digits_only) < 10:
        raise HTTPException(status_code=400, detail="Please provide a valid mobile number (minimum 10 digits).")

    # 4. Validation: Password strength
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must contain at least 8 characters.")
    if not any(c.isalpha() for c in req.password) or not any(c.isdigit() for c in req.password):
        raise HTTPException(status_code=400, detail="Password must contain both letters and at least one number.")

    # 5. Check duplicate email
    existing_user = db.query(User).filter(User.email == clean_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please sign in instead."
        )

    # 6. Secure bcrypt password hashing & database insertion
    new_user = User(
        email=clean_email,
        password_hash=hash_password(req.password),
        full_name=clean_name,
        phone=clean_phone,
        role="applicant",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        last_login=datetime.now(timezone.utc)
    )
    db.add(new_user)
    db.flush()

    # Log audit event
    audit = AuditLog(
        user_role="applicant",
        user_id=new_user.id,
        action="applicant_registered",
        resource_id=new_user.id,
        details={"email": clean_email, "name": clean_name}
    )
    db.add(audit)
    db.commit()
    db.refresh(new_user)

    # 7. Generate JWT access token for immediate automatic login
    token_claims = {
        "sub": new_user.id,
        "email": new_user.email,
        "role": new_user.role,
        "name": new_user.full_name
    }
    access_token = create_access_token(token_claims)

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=new_user.id,
            email=new_user.email,
            full_name=new_user.full_name,
            phone=new_user.phone,
            role=new_user.role,
            created_at=new_user.created_at.isoformat()
        )
    )

@router.post("/login", response_model=AuthResponse)
def login_user(req: LoginRequest, db: Session = Depends(get_db)):
    """
    Unified authentication endpoint supporting both Applicant and Officer logins.
    Verifies credentials via backend bcrypt validation and enforces portal role separation.
    """
    clean_email = req.email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()

    # Generic error message to prevent user enumeration
    invalid_creds_msg = "Invalid email address or password. Please verify your credentials."

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=invalid_creds_msg)

    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=invalid_creds_msg)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact FairLendAI support."
        )

    # Role enforcement if caller specifies portal role
    if req.expected_role:
        if req.expected_role == "officer" and user.role != "officer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: This account does not possess Underwriter / Officer privileges."
            )
        if req.expected_role == "applicant" and user.role != "applicant":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Officer credentials detected. Please use the Officer Portal to access the command center."
            )

    # Update last login timestamp
    user.last_login = datetime.now(timezone.utc)
    
    # Audit log entry
    audit = AuditLog(
        user_role=user.role,
        user_id=user.id,
        action="user_logged_in",
        resource_id=user.id,
        details={"portal": req.expected_role or user.role}
    )
    db.add(audit)
    db.commit()

    token_claims = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "name": user.full_name
    }
    access_token = create_access_token(token_claims)

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            role=user.role,
            created_at=user.created_at.isoformat()
        )
    )

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Returns the verified profile of the authenticated user."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        role=current_user.role,
        created_at=current_user.created_at.isoformat()
    )

@router.get("/my-applications", response_model=List[ApplicantAppSummary])
def get_my_applications(
    current_user: User = Depends(require_applicant),
    db: Session = Depends(get_db)
):
    """
    Returns the persistent application history strictly belonging to the authenticated applicant.
    """
    apps = (
        db.query(Application)
        .filter(Application.applicant_user_id == current_user.id)
        .order_by(desc(Application.created_at))
        .all()
    )

    results = []
    for app in apps:
        snapshot = app.feature_snapshots[0] if app.feature_snapshots else None
        results.append(
            ApplicantAppSummary(
                id=app.id,
                created_at=app.created_at.isoformat(),
                applicant_name=decrypt_field(app.applicant_name_enc) or current_user.full_name,
                requested_amount=app.requested_amount,
                tenure_months=app.tenure_months,
                monthly_income=app.monthly_income,
                foir=round(snapshot.foir * 100, 1) if snapshot else 0.0,
                ai_recommendation=app.ai_recommendation,
                ai_confidence=app.ai_confidence,
                status=app.status
            )
        )
    return results

@router.post("/logout")
def logout_user(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Logs the user logout action in the compliance audit trail."""
    audit = AuditLog(
        user_role=current_user.role,
        user_id=current_user.id,
        action="user_logged_out",
        resource_id=current_user.id
    )
    db.add(audit)
    db.commit()
    return {"message": "Successfully logged out."}

