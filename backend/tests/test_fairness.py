import pytest
from backend.services.fairness.monitor import compute_fairness_metrics
from backend.db.database import SessionLocal
from backend.db.models import Application, FairnessAudit, OfficerDecision

def test_fairness_metrics_calculation():
    db = SessionLocal()
    metrics = compute_fairness_metrics(db)
    assert "status" in metrics
    assert "total_audit_cases" in metrics
    assert "sample_size_warnings" in metrics
    db.close()
