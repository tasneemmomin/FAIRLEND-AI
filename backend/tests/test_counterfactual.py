import pytest
from backend.services.counterfactual.search import find_counterfactuals
from backend.services.policy_engine.engine import policy_engine

def test_counterfactual_faithfulness_and_locks():
    # Applicant who needs review
    app_data = {
        "monthly_income": 45000.0,
        "requested_amount": 350000.0,
        "tenure_months": 24,
        "existing_emis": 5000.0,
        "age": 29,
        "employment_duration_months": 18,
        "credit_history_years": 1.5,
        "collateral_value": 0.0,
        "consistency_score": 0.85
    }

    initial_eval = policy_engine.evaluate(app_data)
    assert initial_eval["recommendation_code"] in ("needs_review", "unlikely_approved")

    cfs = find_counterfactuals(app_data)
    assert len(cfs) > 0

    for cf in cfs:
        # 1. Faithfulness check: must be marked faithful
        assert cf["is_faithful"] is True

        # 2. Immutable lock check: age, employment duration, credit history must NOT be in suggestions
        assert cf["feature_name"] not in ("age", "gender", "caste", "credit_history_years", "employment_duration_months")

        # 3. Actionable features only: amount, tenure, EMIs, or income
        assert cf["feature_name"] in ("requested_amount", "tenure_months", "existing_emis", "monthly_income")

        # 4. Verify candidate re-evaluation actually produces likely_approved
        candidate = dict(app_data)
        candidate[cf["feature_name"]] = cf["suggested_value"]
        re_eval = policy_engine.evaluate(candidate)
        assert re_eval["recommendation_code"] == "likely_approved"
