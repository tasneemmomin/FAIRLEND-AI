from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.db.models import Application
from backend.core.security import decrypt_field
from backend.services.plain_english.translator import plain_english_translator, calculate_flesch_kincaid_grade
from backend.services.counterfactual.search import find_counterfactuals
from backend.services.explain.attributions import compute_feature_attributions

router = APIRouter(prefix="/explain", tags=["Explainability Engine"])

@router.get("/{application_id}")
def get_application_explanation(application_id: str, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    snapshot = app.feature_snapshots[0] if app.feature_snapshots else None
    feat_vec = snapshot.feature_vector if snapshot else {}

    ratios = {
        "foir": snapshot.foir if snapshot else 0.0,
        "lti": snapshot.lti if snapshot else 0.0,
        "disposable_income": snapshot.disposable_income if snapshot else 0.0,
        "consistency_score": app.consistency_score or 1.0
    }

    # 1. Plain-English Reasons (Applicant View, Grade 6-8)
    plain_reasons = plain_english_translator.translate_factors(feat_vec, ratios)

    # 2. Actionable, Faithful Counterfactuals ("What could change this result")
    counterfactuals = find_counterfactuals(feat_vec)

    # 3. Technical Feature Attributions (Officer View)
    attributions = compute_feature_attributions(feat_vec, ratios)

    # 4. Readability score verification
    full_text_explanation = " ".join(plain_reasons)
    reading_grade = calculate_flesch_kincaid_grade(full_text_explanation)

    label_map = {
        "likely_approved": "Likely to be approved",
        "needs_review": "Needs more review",
        "unlikely_approved": "Unlikely to be approved right now"
    }

    return {
        "application_id": app.id,
        "applicant_name": decrypt_field(app.applicant_name_enc) or "Applicant",
        "recommendation_code": app.ai_recommendation,
        "recommendation_label": label_map.get(app.ai_recommendation, "Needs more review"),
        "confidence": app.ai_confidence,
        "reading_grade_level": reading_grade,
        "is_applicant_readable": (reading_grade <= 8.5),
        "applicant_view": {
            "headline": label_map.get(app.ai_recommendation, "Needs more review"),
            "confidence_wording": f"{app.ai_confidence} Confidence",
            "why_we_think_this": plain_reasons,
            "what_could_change_this_result": counterfactuals
        },
        "officer_view": {
            "attributions": attributions,
            "rule_hits": app.ai_rule_hits or [],
            "consistency_score": app.consistency_score,
            "counterfactual_matrix": counterfactuals
        }
    }
