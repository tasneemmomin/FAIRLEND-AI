from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.services.fairness.monitor import compute_fairness_metrics

router = APIRouter(prefix="/fairness", tags=["Fairness & Compliance Monitoring"])

@router.get("/metrics")
def get_fairness_audit_metrics(db: Session = Depends(get_db)):
    """Computes real-time fairness statistics over consented applicant demographic records."""
    metrics = compute_fairness_metrics(db)
    return metrics
