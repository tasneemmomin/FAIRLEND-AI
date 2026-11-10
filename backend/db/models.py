import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from backend.db.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    role = Column(String(30), nullable=False, default="applicant")  # applicant, officer
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    last_login = Column(DateTime, nullable=True)

    applications = relationship("Application", back_populates="applicant_user")

class Application(Base):
    __tablename__ = "applications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Encrypted PII
    applicant_name_enc = Column(Text, nullable=True)
    contact_phone_enc = Column(Text, nullable=True)
    contact_email_enc = Column(Text, nullable=True)

    # Core Financial & Application Attributes
    age = Column(Integer, nullable=False)
    employment_type = Column(String(50), nullable=False)  # salaried, self_employed, business, gig_contract
    employment_duration_months = Column(Integer, nullable=False, default=12)
    monthly_income = Column(Float, nullable=False)
    existing_emis = Column(Float, nullable=False, default=0.0)
    # Optional verified monthly household expenses (None = estimate assumption used by stress simulator)
    monthly_expenses = Column(Float, nullable=True, default=None)
    requested_amount = Column(Float, nullable=False)
    tenure_months = Column(Integer, nullable=False)
    loan_purpose = Column(String(50), nullable=False)  # home, personal, education, vehicle, business, medical
    dependents = Column(Integer, nullable=False, default=0)
    residence_type = Column(String(50), nullable=False, default="rented")  # owned, rented, ancestral
    credit_history_years = Column(Float, nullable=False, default=0.0)
    collateral_value = Column(Float, nullable=False, default=0.0)

    # Intake metadata
    intake_mode = Column(String(20), nullable=False, default="typed")  # typed, voice
    intake_transcript = Column(Text, nullable=True)

    # Document Extraction & Consistency
    consistency_score = Column(Float, nullable=True, default=1.0)
    document_flags = Column(JSON, nullable=True, default=list)

    # Workflow & Recommendation
    status = Column(String(30), nullable=False, default="submitted")  # submitted, under_review, approved, rejected, more_info
    ai_recommendation = Column(String(30), nullable=False, default="needs_review")  # likely_approved, needs_review, unlikely_approved
    ai_confidence = Column(String(20), nullable=False, default="medium")  # low, medium, high
    ai_stage = Column(String(40), nullable=False, default="stage1_policy")  # stage1_policy, stage2_hitl, stage3_online_shadow, stage3_online_active
    ai_rule_hits = Column(JSON, nullable=True, default=list)
    ai_recommendation_reasons = Column(JSON, nullable=True, default=list)
    ai_counterfactuals = Column(JSON, nullable=True, default=list)
    plain_english_summary = Column(Text, nullable=True)

    # Link to authenticated applicant user account
    applicant_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Relationships
    applicant_user = relationship("User", back_populates="applications")
    feature_snapshots = relationship("FeatureSnapshot", back_populates="application", cascade="all, delete-orphan")
    decision = relationship("OfficerDecision", back_populates="application", uselist=False, cascade="all, delete-orphan")
    fairness_record = relationship("FairnessAudit", back_populates="application", uselist=False, cascade="all, delete-orphan")

class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshots"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    application_id = Column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    feature_version = Column(String(20), nullable=False, default="v1.0")
    
    # Key derived ratios
    foir = Column(Float, nullable=False)  # Fixed Obligation to Income Ratio
    lti = Column(Float, nullable=False)   # Loan to Income Ratio
    disposable_income = Column(Float, nullable=False)
    consistency_score = Column(Float, nullable=False, default=1.0)
    
    # Exact normalized feature vector for model and reproducibility
    feature_vector = Column(JSON, nullable=False)

    application = relationship("Application", back_populates="feature_snapshots")

class OfficerDecision(Base):
    __tablename__ = "officer_decisions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    application_id = Column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    officer_id = Column(String(100), nullable=False, default="officer_demo")
    decision = Column(String(30), nullable=False)  # approve, reject, needs_more_info
    reason_code = Column(String(100), nullable=False)
    officer_notes = Column(Text, nullable=True)
    ai_recommendation_snapshot = Column(String(30), nullable=False)
    ai_agreed = Column(Boolean, nullable=False, default=False)
    decision_timestamp = Column(DateTime, default=utc_now, nullable=False)

    # Delayed outcome (reject-inference / repayment tracking)
    repayment_outcome = Column(String(30), nullable=True, default="unobserved")  # current, defaulted, prepaid, unobserved
    repayment_updated_at = Column(DateTime, nullable=True)

    application = relationship("Application", back_populates="decision")

class FairnessAudit(Base):
    __tablename__ = "fairness_audit"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    application_id = Column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, unique=True)
    consent_given = Column(Boolean, nullable=False, default=False)
    gender = Column(String(30), nullable=True)  # female, male, non_binary, prefer_not_say
    social_group = Column(String(50), nullable=True)
    geography_tier = Column(String(30), nullable=True)  # metro, tier1, tier2, rural
    created_at = Column(DateTime, default=utc_now, nullable=False)

    application = relationship("Application", back_populates="fairness_record")

class SystemDriftEvent(Base):
    __tablename__ = "system_drift_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)
    detector_name = Column(String(50), nullable=False, default="ADWIN")
    metric_value = Column(Float, nullable=True)
    message = Column(Text, nullable=False)
    total_cases_at_drift = Column(Integer, nullable=False)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)
    user_role = Column(String(30), nullable=False)  # applicant, officer, admin, system
    user_id = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    resource_id = Column(String(100), nullable=True)
    details = Column(JSON, nullable=True)


class StressScenarioConfig(Base):
    """Versioned administrative configuration for the Financial Stress Simulator.

    Rows are append-only: every authorized update stores a new version so
    historical calculation configurations can be reconstructed. The newest row
    is treated as the active configuration.
    """
    __tablename__ = "stress_scenario_configs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    config_version = Column(Integer, nullable=False, default=1, index=True)
    payload = Column(JSON, nullable=False)
    updated_by = Column(String(100), nullable=False, default="system")
    updated_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    note = Column(Text, nullable=True)
