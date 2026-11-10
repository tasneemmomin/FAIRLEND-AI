from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.models.schemas import ApplicantIntakeRequest, ApplicantResponse, CounterfactualItem
from backend.db.models import Application, FeatureSnapshot, FairnessAudit, AuditLog
from backend.core.security import encrypt_field
from backend.services.policy_engine.engine import policy_engine
from backend.services.features.feature_store import extract_feature_vector

def process_application_intake(
    req: ApplicantIntakeRequest,
    db: Session,
    consistency_score: float = 1.0,
    document_flags: list | None = None,
    applicant_user_id: str | None = None
) -> Tuple[Application, ApplicantResponse]:
    """
    Core intake processor: encrypts PII, calculates credit policy scorecard,
    records feature snapshot, creates fairness audit record (if consented), and logs audit.
    Generates counterfactuals at submission time (applicant-only, stored server-side).
    """
    app_data = req.model_dump()
    app_data["consistency_score"] = consistency_score

    # 1. Run Policy Engine (Stage 1)
    eval_result = policy_engine.evaluate(app_data)

    # 2. Extract normalized feature vector
    ratios = {
        "foir": eval_result["foir"],
        "lti": eval_result["lti"],
        "disposable_income": eval_result["disposable_income"],
        "consistency_score": consistency_score
    }
    feat_vec = extract_feature_vector(app_data, ratios)

    # 3. Generate counterfactuals at submission time (applicant-only; stored server-side)
    from backend.services.counterfactual.search import find_counterfactuals
    cf_data = {
        "requested_amount": req.requested_amount,
        "monthly_income": req.monthly_income,
        "tenure_months": req.tenure_months,
        "existing_emis": req.existing_emis,
        "employment_type": req.employment_type,
        "employment_duration_months": req.employment_duration_months,
        "consistency_score": consistency_score,
        "credit_history_years": req.credit_history_years or 0.0,
        "collateral_value": req.collateral_value or 0.0,
    }
    counterfactuals_raw = find_counterfactuals(cf_data)

    # 4. Create Application record
    new_app = Application(
        applicant_name_enc=encrypt_field(req.applicant_name),
        contact_phone_enc=encrypt_field(req.contact_phone),
        contact_email_enc=encrypt_field(req.contact_email),
        age=req.age,
        employment_type=req.employment_type,
        employment_duration_months=req.employment_duration_months,
        monthly_income=req.monthly_income,
        existing_emis=req.existing_emis,
        monthly_expenses=req.monthly_expenses,
        requested_amount=req.requested_amount,
        tenure_months=req.tenure_months,
        loan_purpose=req.loan_purpose,
        dependents=req.dependents,
        residence_type=req.residence_type,
        credit_history_years=req.credit_history_years,
        collateral_value=req.collateral_value,
        intake_mode=req.intake_mode,
        intake_transcript=req.intake_transcript,
        consistency_score=consistency_score,
        document_flags=document_flags or [],
        applicant_user_id=applicant_user_id,
        status="submitted",
        ai_recommendation=eval_result["recommendation_code"],
        ai_confidence=eval_result["confidence"],
        ai_stage="stage1_policy",
        ai_rule_hits=eval_result["rule_hits"],
        ai_recommendation_reasons=eval_result["reasons"],
        ai_counterfactuals=counterfactuals_raw,
        plain_english_summary=f"Based on our policy assessment, your application is currently evaluated as: {eval_result['recommendation_label']}."
    )
    db.add(new_app)
    db.flush()

    # 5. Save Feature Snapshot
    snapshot = FeatureSnapshot(
        application_id=new_app.id,
        feature_version="v1.0",
        foir=eval_result["foir"],
        lti=eval_result["lti"],
        disposable_income=eval_result["disposable_income"],
        consistency_score=consistency_score,
        feature_vector=feat_vec
    )
    db.add(snapshot)

    # 6. Handle separate Demographic Fairness Audit (stored apart from model features)
    if req.audit_consent:
        audit_rec = FairnessAudit(
            application_id=new_app.id,
            consent_given=True,
            gender=req.audit_gender,
            social_group=req.audit_social_group,
            geography_tier=req.audit_geography_tier
        )
        db.add(audit_rec)

    # 7. Immutable Audit Log
    log_entry = AuditLog(
        user_role="applicant",
        user_id=new_app.id,
        action="intake_submitted",
        resource_id=new_app.id,
        details={
            "mode": req.intake_mode,
            "recommendation": eval_result["recommendation_code"],
            "score": eval_result["score"],
            "foir": eval_result["foir"]
        }
    )
    db.add(log_entry)
    db.commit()
    db.refresh(new_app)

    # Build CounterfactualItem list for response
    cf_items = [
        CounterfactualItem(
            feature_name=cf.get("feature_name", ""),
            current_value=cf.get("current_value", 0),
            suggested_value=cf.get("suggested_value", 0),
            change_description=cf.get("change_description", ""),
            actionability=cf.get("actionability", ""),
            is_faithful=cf.get("is_faithful", True)
        )
        for cf in counterfactuals_raw
    ]

    response = ApplicantResponse(
        application_id=new_app.id,
        created_at=new_app.created_at.isoformat(),
        applicant_name=req.applicant_name,
        status=new_app.status,
        recommendation=eval_result["recommendation_label"],
        recommendation_code=eval_result["recommendation_code"],
        confidence=eval_result["confidence"],
        stage=new_app.ai_stage,
        plain_english_summary=new_app.plain_english_summary,
        reasons=eval_result["reasons"],
        counterfactuals=cf_items,
        foir_percentage=round(eval_result["foir"] * 100, 1),
        loan_to_income_ratio=round(eval_result["lti"], 2),
        consistency_score=round(consistency_score, 2),
    )

    return new_app, response
