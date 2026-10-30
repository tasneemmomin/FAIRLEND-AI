import pytest
from backend.services.online_model.streaming_pipeline import OnlineModelManager

def test_online_model_incremental_learning():
    manager = OnlineModelManager()

    # Synthetic stream of 5 samples
    samples = [
        ({"monthly_income": 80000, "requested_amount": 150000, "foir": 0.20, "lti": 1.5}, "approve"),
        ({"monthly_income": 30000, "requested_amount": 600000, "foir": 0.70, "lti": 5.0}, "reject"),
        ({"monthly_income": 95000, "requested_amount": 200000, "foir": 0.18, "lti": 1.2}, "approve"),
        ({"monthly_income": 25000, "requested_amount": 400000, "foir": 0.65, "lti": 4.5}, "reject"),
        ({"monthly_income": 70000, "requested_amount": 180000, "foir": 0.25, "lti": 1.8}, "approve"),
    ]

    for feat_vec, decision in samples:
        # Mock application object with feature_snapshots
        class MockApp:
            def __init__(self, f):
                self.feature_snapshots = [type("Snapshot", (), {"feature_vector": f})()]

        app = MockApp(feat_vec)
        manager.handle_officer_decision(app, decision)

    stats = manager.get_shadow_stats()
    assert stats["rolling_window"] == 5
    assert stats["agreement_rate"] is not None
    assert stats["brier_score"] is not None

def test_online_model_predict_one():
    manager = OnlineModelManager()
    prob, pred = manager.predict_one({"monthly_income": 85000, "foir": 0.22})
    assert 0.0 <= prob <= 1.0
    assert pred in ("likely_approved", "needs_review", "unlikely_approved")
