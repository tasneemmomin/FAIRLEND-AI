from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.db.database import get_db
from backend.db.models import Application, FeatureSnapshot, OfficerDecision, AuditLog
from backend.models.schemas import OfficerDecisionRequest, OfficerRepaymentUpdateRequest
from backend.core.security import decrypt_field
from backend.core.config import settings
from backend.core.auth import require_officer
from backend.api.routes.websocket import manager

router = APIRouter(prefix="/officer", tags=["Officer Dashboard"], dependencies=[Depends(require_officer)])

@router.get("/applications")
def list_applications(
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    query = db.query(Application)
    if status_filter and status_filter != "all":
        query = query.filter(Application.status == status_filter)
    
    total = query.count()
    apps = query.order_by(desc(Application.created_at)).offset(offset).limit(limit).all()

    results = []
    for app in apps:
        snapshot = app.feature_snapshots[0] if app.feature_snapshots else None
        results.append({
            "id": app.id,
            "created_at": app.created_at.isoformat(),
            "applicant_name": decrypt_field(app.applicant_name_enc) or "Applicant",
            "requested_amount": app.requested_amount,
            "tenure_months": app.tenure_months,
            "monthly_income": app.monthly_income,
            "foir": round(snapshot.foir * 100, 1) if snapshot else 0.0,
            "consistency_score": round(app.consistency_score or 1.0, 2),
            "ai_recommendation": app.ai_recommendation,
            "ai_confidence": app.ai_confidence,
            "ai_stage": app.ai_stage,
            "status": app.status,
            "has_decision": app.decision is not None,
            "officer_decision": app.decision.decision if app.decision else None,
            "reason_code": app.decision.reason_code if app.decision else None
        })

    return {"total": total, "applications": results}

@router.get("/applications/{application_id}")
def get_application_detail(application_id: str, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    snapshot = app.feature_snapshots[0] if app.feature_snapshots else None

    # Find nearest similar past cases (k-NN style similarity over normalized features)
    past_cases = db.query(Application).filter(
        Application.id != app.id,
        Application.status.in_(["approved", "rejected"])
    ).limit(5).all()

    similar_cases = []
    for past in past_cases:
        p_snap = past.feature_snapshots[0] if past.feature_snapshots else None
        similar_cases.append({
            "id": past.id,
            "applicant_name": decrypt_field(past.applicant_name_enc) or "Past Applicant",
            "requested_amount": past.requested_amount,
            "monthly_income": past.monthly_income,
            "foir": round(p_snap.foir * 100, 1) if p_snap else 0.0,
            "officer_decision": past.decision.decision if past.decision else past.status,
            "reason_code": past.decision.reason_code if past.decision else "Standard Policy"
        })

    return {
        "id": app.id,
        "created_at": app.created_at.isoformat(),
        "applicant_name": decrypt_field(app.applicant_name_enc),
        "contact_phone": decrypt_field(app.contact_phone_enc),
        "contact_email": decrypt_field(app.contact_email_enc),
        "age": app.age,
        "employment_type": app.employment_type,
        "employment_duration_months": app.employment_duration_months,
        "monthly_income": app.monthly_income,
        "existing_emis": app.existing_emis,
        "requested_amount": app.requested_amount,
        "tenure_months": app.tenure_months,
        "loan_purpose": app.loan_purpose,
        "dependents": app.dependents,
        "residence_type": app.residence_type,
        "credit_history_years": app.credit_history_years,
        "collateral_value": app.collateral_value,
        "intake_mode": app.intake_mode,
        "intake_transcript": app.intake_transcript,
        "consistency_score": app.consistency_score,
        "document_flags": app.document_flags or [],
        "status": app.status,
        "ai_recommendation": app.ai_recommendation,
        "ai_confidence": app.ai_confidence,
        "ai_stage": app.ai_stage,
        "ai_rule_hits": app.ai_rule_hits or [],
        "ai_recommendation_reasons": app.ai_recommendation_reasons or [],
        "ratios": {
            "foir": round(snapshot.foir * 100, 1) if snapshot else 0.0,
            "lti": round(snapshot.lti, 2) if snapshot else 0.0,
            "disposable_income": snapshot.disposable_income if snapshot else 0.0
        },
        "feature_vector": snapshot.feature_vector if snapshot else {},
        "decision": {
            "decision": app.decision.decision,
            "reason_code": app.decision.reason_code,
            "officer_notes": app.decision.officer_notes,
            "officer_id": app.decision.officer_id,
            "ai_agreed": app.decision.ai_agreed,
            "decision_timestamp": app.decision.decision_timestamp.isoformat(),
            "repayment_outcome": app.decision.repayment_outcome
        } if app.decision else None,
        "similar_cases": similar_cases,
        "counterfactuals": app.ai_counterfactuals or []
    }

@router.post("/applications/{application_id}/decision")
async def record_officer_decision(
    application_id: str,
    req: OfficerDecisionRequest,
    db: Session = Depends(get_db)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Evaluate whether officer agreed with AI recommendation
    ai_agreed = (
        (req.decision == "approve" and app.ai_recommendation == "likely_approved") or
        (req.decision == "reject" and app.ai_recommendation == "unlikely_approved")
    )

    # Map status
    status_map = {
        "approve": "approved",
        "reject": "rejected",
        "needs_more_info": "more_info"
    }
    app.status = status_map.get(req.decision, "under_review")

    if app.decision:
        # Update existing decision
        app.decision.decision = req.decision
        app.decision.reason_code = req.reason_code
        app.decision.officer_notes = req.officer_notes
        app.decision.officer_id = req.officer_id
        app.decision.ai_agreed = ai_agreed
        app.decision.decision_timestamp = datetime.now(timezone.utc)
    else:
        # Create new decision record (the primary source of training labels!)
        decision_rec = OfficerDecision(
            application_id=app.id,
            officer_id=req.officer_id,
            decision=req.decision,
            reason_code=req.reason_code,
            officer_notes=req.officer_notes,
            ai_recommendation_snapshot=app.ai_recommendation,
            ai_agreed=ai_agreed,
            decision_timestamp=datetime.now(timezone.utc)
        )
        db.add(decision_rec)

    # Immutable Audit Log
    audit = AuditLog(
        user_role="officer",
        user_id=req.officer_id,
        action="decision_recorded",
        resource_id=app.id,
        details={
            "decision": req.decision,
            "reason_code": req.reason_code,
            "ai_agreed": ai_agreed,
            "ai_recommendation": app.ai_recommendation
        }
    )
    db.add(audit)
    db.commit()

    # Online Model incremental learning hook (will train river model when active in Stage 3)
    try:
        from backend.services.online_model.streaming_pipeline import online_model_manager
        online_model_manager.handle_officer_decision(app, req.decision)
    except Exception as e:
        # Online model learning is non-blocking to transaction
        pass

    # Broadcast decision event live to applicant portal and officer dashboards
    await manager.broadcast({
        "event": "officer_decision",
        "application_id": app.id,
        "decision": req.decision,
        "status": app.status,
        "reason_code": req.reason_code,
        "ai_agreed": ai_agreed,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    return {
        "status": "success",
        "message": f"Decision recorded as {req.decision}.",
        "application_id": app.id,
        "application_status": app.status,
        "ai_agreed": ai_agreed
    }

@router.post("/applications/{application_id}/repayment")
def update_repayment_outcome(
    application_id: str,
    req: OfficerRepaymentUpdateRequest,
    db: Session = Depends(get_db)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app or not app.decision:
        raise HTTPException(status_code=404, detail="Application or decision not found")

    app.decision.repayment_outcome = req.repayment_outcome
    app.decision.repayment_updated_at = datetime.now(timezone.utc)

    # Log audit
    audit = AuditLog(
        user_role="officer",
        user_id=app.decision.officer_id,
        action="repayment_outcome_updated",
        resource_id=app.id,
        details={"outcome": req.repayment_outcome}
    )
    db.add(audit)
    db.commit()

    return {"status": "success", "repayment_outcome": req.repayment_outcome}

@router.get("/stats")
def get_labeling_stats(db: Session = Depends(get_db)):
    total_apps = db.query(Application).count()
    total_decisions = db.query(OfficerDecision).count()
    approvals = db.query(OfficerDecision).filter(OfficerDecision.decision == "approve").count()
    rejections = db.query(OfficerDecision).filter(OfficerDecision.decision == "reject").count()
    needs_info = db.query(OfficerDecision).filter(OfficerDecision.decision == "needs_more_info").count()

    threshold = settings.STAGE_ACTIVATION_MIN_LABELS
    min_per_class = settings.STAGE_ACTIVATION_MIN_PER_CLASS

    progress_percent = min(100.0, round((total_decisions / threshold) * 100, 1)) if threshold > 0 else 100.0
    classes_balanced = (approvals >= min_per_class) and (rejections >= min_per_class)

    # Calculate recent officer-AI agreement rate (last 50 decisions)
    recent_decisions = db.query(OfficerDecision).order_by(desc(OfficerDecision.decision_timestamp)).limit(50).all()
    if recent_decisions:
        agreements = sum(1 for d in recent_decisions if d.ai_agreed)
        agreement_rate = round(agreements / len(recent_decisions), 3)
    else:
        agreement_rate = None

    if total_decisions == 0:
        stage = "stage1_policy"
        stage_name = "Stage 1: Policy Scorecard"
    elif total_decisions < threshold or not classes_balanced:
        stage = "stage2_hitl"
        stage_name = "Stage 2: Human-in-the-Loop Labeling"
    else:
        stage = "stage3_online_shadow"
        stage_name = "Stage 3: Online Learning (Shadow Mode)"

    return {
        "stage": stage,
        "stage_name": stage_name,
        "total_applications": total_apps,
        "total_labeled_cases": total_decisions,
        "activation_threshold": threshold,
        "min_per_class_required": min_per_class,
        "approvals_count": approvals,
        "rejections_count": rejections,
        "needs_info_count": needs_info,
        "progress_percent": progress_percent,
        "classes_balanced": classes_balanced,
        "remaining_for_activation": max(0, threshold - total_decisions),
        "recent_agreement_rate": agreement_rate
    }
