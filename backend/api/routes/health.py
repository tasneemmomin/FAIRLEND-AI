from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.db.models import Application, OfficerDecision
from backend.core.config import settings

router = APIRouter(tags=["Health"])

@router.get("/health")
def get_system_health(db: Session = Depends(get_db)):
    # Check DB connectivity
    total_apps = db.query(Application).count()
    total_decisions = db.query(OfficerDecision).count()
    approvals = db.query(OfficerDecision).filter(OfficerDecision.decision == "approve").count()
    rejections = db.query(OfficerDecision).filter(OfficerDecision.decision == "reject").count()

    # Determine current system stage
    threshold = settings.STAGE_ACTIVATION_MIN_LABELS
    min_per_class = settings.STAGE_ACTIVATION_MIN_PER_CLASS
    
    if total_decisions == 0:
        stage = "stage1_policy"
        stage_label = "Stage 1: Policy Rule Engine"
    elif total_decisions < threshold or approvals < min_per_class or rejections < min_per_class:
        stage = "stage2_hitl"
        stage_label = "Stage 2: Human-in-the-Loop Labeling"
    else:
        stage = "stage3_online_shadow"
        stage_label = "Stage 3: Online Learning (Shadow Mode)"

    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.VERSION,
        "database_connected": True,
        "total_applications": total_apps,
        "labeled_cases": total_decisions,
        "activation_threshold": threshold,
        "min_per_class_required": min_per_class,
        "approvals_count": approvals,
        "rejections_count": rejections,
        "current_stage": stage,
        "current_stage_label": stage_label,
        "shadow_agreement_rate": None,
        "model_promoted": False
    }
