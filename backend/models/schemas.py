from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ApplicantIntakeRequest(BaseModel):
    applicant_name: str = Field(..., min_length=1, description="Applicant full name")
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    age: int = Field(..., ge=18, le=100)
    employment_type: str = Field("salaried", description="salaried, self_employed, business, gig_contract")
    employment_duration_months: int = Field(12, ge=0)
    monthly_income: float = Field(..., gt=0)
    existing_emis: float = Field(0.0, ge=0)
    requested_amount: float = Field(..., gt=0)
    tenure_months: int = Field(..., ge=6, le=360)
    loan_purpose: str = Field("personal", description="home, personal, education, vehicle, business, medical")
    dependents: int = Field(0, ge=0)
    residence_type: str = Field("rented", description="owned, rented, ancestral")
    credit_history_years: float = Field(0.0, ge=0)
    collateral_value: float = Field(0.0, ge=0)
    intake_mode: str = Field("typed", description="typed or voice")
    intake_transcript: Optional[str] = None

    # Separate optional demographic consent for fairness audit only
    audit_consent: bool = False
    audit_gender: Optional[str] = None
    audit_social_group: Optional[str] = None
    audit_geography_tier: Optional[str] = None

class CounterfactualItem(BaseModel):
    feature_name: str
    current_value: Any
    suggested_value: Any
    change_description: str
    actionability: str
    is_faithful: bool

class ApplicantResponse(BaseModel):
    application_id: str
    created_at: str
    applicant_name: str
    status: str
    recommendation: str  # Plain-English headline
    recommendation_code: str
    confidence: str  # Low, Medium, High
    stage: str  # stage1_policy, stage2_hitl, stage3_online_shadow, stage3_online_active
    plain_english_summary: str
    reasons: List[str]
    counterfactuals: List[CounterfactualItem]
    foir_percentage: float
    loan_to_income_ratio: float
    consistency_score: float

class OfficerDecisionRequest(BaseModel):
    decision: str = Field(..., description="approve, reject, needs_more_info")
    reason_code: str = Field(..., min_length=2, description="Standard credit policy reason code")
    officer_notes: Optional[str] = None
    officer_id: str = "officer_demo"

class OfficerRepaymentUpdateRequest(BaseModel):
    repayment_outcome: str = Field(..., description="current, defaulted, prepaid, unobserved")

class SystemHealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    stage: str
    labeled_cases: int
    activation_threshold: int
    approvals_count: int
    rejections_count: int
    shadow_agreement_rate: Optional[float]
    model_promoted: bool
    whisper_available: bool
    database_connected: bool
