from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.db.models import Application, User
from backend.models.schemas import ApplicantIntakeRequest, ApplicantResponse, CounterfactualItem
from backend.services.intake.intake_service import process_application_intake
from backend.core.security import decrypt_field
from backend.core.auth import get_current_user, require_applicant
from backend.api.routes.websocket import manager

router = APIRouter(prefix="/intake", tags=["Applicant Intake"])

@router.post("/submit", response_model=ApplicantResponse)
async def submit_application(
    req: ApplicantIntakeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "applicant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Underwriters and officers cannot submit applicant intake."
        )

    try:
        app_model, response = process_application_intake(
            req, db, applicant_user_id=current_user.id
        )

        # Broadcast live event to Officer Dashboard via WebSocket
        await manager.broadcast({
            "event": "new_application",
            "application_id": app_model.id,
            "applicant_name": req.applicant_name,
            "requested_amount": req.requested_amount,
            "recommendation": response.recommendation,
            "confidence": response.confidence,
            "created_at": response.created_at
        })

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process application: {str(e)}")

@router.get("/{application_id}", response_model=ApplicantResponse)
def get_application_status(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    app_record = db.query(Application).filter(Application.id == application_id).first()
    if not app_record:
        raise HTTPException(status_code=404, detail="Application not found")

    # Authorization check: only owning applicant or authorized officer may view
    if current_user.role == "applicant" and app_record.applicant_user_id and app_record.applicant_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not have permission to view this application."
        )

    plain_name = decrypt_field(app_record.applicant_name_enc) or "Applicant"

    # Map recommendation code to plain-English label
    label_map = {
        "likely_approved": "Likely to be approved",
        "needs_review": "Needs more review",
        "unlikely_approved": "Unlikely to be approved right now"
    }

    # Fetch latest snapshot for ratios
    latest_snapshot = app_record.feature_snapshots[0] if app_record.feature_snapshots else None
    foir = latest_snapshot.foir if latest_snapshot else 0.0
    lti = latest_snapshot.lti if latest_snapshot else 0.0

    # Parse stored counterfactuals back into CounterfactualItem objects
    from backend.models.schemas import CounterfactualItem
    stored_cfs = app_record.ai_counterfactuals or []
    cf_items = [
        CounterfactualItem(
            feature_name=cf.get("feature_name", ""),
            current_value=cf.get("current_value", 0),
            suggested_value=cf.get("suggested_value", 0),
            change_description=cf.get("change_description", ""),
            actionability=cf.get("actionability", ""),
            is_faithful=cf.get("is_faithful", True)
        )
        for cf in stored_cfs
    ]

    return ApplicantResponse(
        application_id=app_record.id,
        created_at=app_record.created_at.isoformat(),
        applicant_name=plain_name,
        status=app_record.status,
        recommendation=label_map.get(app_record.ai_recommendation, "Needs more review"),
        recommendation_code=app_record.ai_recommendation,
        confidence=app_record.ai_confidence,
        stage=app_record.ai_stage,
        plain_english_summary=app_record.plain_english_summary or "",
        reasons=app_record.ai_recommendation_reasons or [],
        counterfactuals=cf_items,
        foir_percentage=round(foir * 100, 1),
        loan_to_income_ratio=round(lti, 2),
        consistency_score=round(app_record.consistency_score or 1.0, 2),
    )
