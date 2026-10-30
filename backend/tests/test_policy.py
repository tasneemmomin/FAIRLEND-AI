import pytest
from backend.services.policy_engine.rules import (
    calculate_estimated_emi,
    calculate_foir,
    calculate_lti,
    calculate_disposable_income
)
from backend.services.policy_engine.engine import policy_engine

def test_financial_ratios():
    # 200,000 principal, 24 months tenure, 10.5% annual rate
    emi = calculate_estimated_emi(200000, 24, 0.105)
    assert 9000 < emi < 9500

    # 50,000 income, 5,000 existing EMIs, 9,275 proposed EMI
    foir = calculate_foir(50000, 5000, emi)
    assert 0.25 < foir < 0.35

    # LTI: 200,000 / (50,000 * 12) = 0.33
    lti = calculate_lti(200000, 50000)
    assert 0.30 <= lti <= 0.40

def test_policy_engine_prime_approval():
    prime_app = {
        "monthly_income": 90000.0,
        "requested_amount": 200000.0,
        "tenure_months": 24,
        "existing_emis": 0.0,
        "age": 30,
        "employment_duration_months": 36,
        "credit_history_years": 3.0,
        "collateral_value": 0.0,
        "consistency_score": 1.0
    }
    result = policy_engine.evaluate(prime_app)
    assert result["recommendation_code"] == "likely_approved"
    assert result["score"] >= 70
    assert len(result["hard_violations"]) == 0

def test_policy_engine_hard_rejection():
    # High FOIR beyond 60%
    stressed_app = {
        "monthly_income": 30000.0,
        "requested_amount": 500000.0,
        "tenure_months": 12,
        "existing_emis": 15000.0,
        "age": 28,
        "employment_duration_months": 12,
        "credit_history_years": 1.0,
        "collateral_value": 0.0,
        "consistency_score": 1.0
    }
    result = policy_engine.evaluate(stressed_app)
    assert result["recommendation_code"] == "unlikely_approved"
    assert len(result["hard_violations"]) > 0
    assert any("Debt-to-income" in v for v in result["hard_violations"])
