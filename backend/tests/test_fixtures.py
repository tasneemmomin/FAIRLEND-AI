"""
TEST-ONLY FIXTURES FOR LOANLENS UNIT AND INTEGRATION TESTS.
STRICT COMPLIANCE NOTE:
These hand-crafted profiles (exactly 6 test cases) are explicitly isolated for test assertion verification.
THEY ARE STRICTLY EXCLUDED FROM MODEL TRAINING AND WILL NEVER BE USED TO INITIALIZE THE STREAMING MODEL.
"""

TEST_FIXTURES = [
    {
        "id": "test_prime_salaried_01",
        "name": "Fixture Prime Salaried",
        "monthly_income": 95000.0,
        "requested_amount": 250000.0,
        "tenure_months": 24,
        "existing_emis": 0.0,
        "age": 32,
        "employment_type": "salaried",
        "employment_duration_months": 36,
        "credit_history_years": 4.0,
        "collateral_value": 0.0,
        "consistency_score": 1.0,
        "expected_code": "likely_approved"
    },
    {
        "id": "test_high_dti_02",
        "name": "Fixture High DTI Stressed",
        "monthly_income": 35000.0,
        "requested_amount": 500000.0,
        "tenure_months": 12,
        "existing_emis": 16000.0,
        "age": 28,
        "employment_type": "salaried",
        "employment_duration_months": 12,
        "credit_history_years": 1.0,
        "collateral_value": 0.0,
        "consistency_score": 0.95,
        "expected_code": "unlikely_approved"
    },
    {
        "id": "test_boundary_review_03",
        "name": "Fixture Boundary Review",
        "monthly_income": 50000.0,
        "requested_amount": 350000.0,
        "tenure_months": 24,
        "existing_emis": 8000.0,
        "age": 30,
        "employment_type": "salaried",
        "employment_duration_months": 24,
        "credit_history_years": 2.0,
        "collateral_value": 0.0,
        "consistency_score": 0.90,
        "expected_code": "needs_review"
    },
    {
        "id": "test_self_employed_merchant_04",
        "name": "Fixture Self-Employed Merchant",
        "monthly_income": 120000.0,
        "requested_amount": 400000.0,
        "tenure_months": 36,
        "existing_emis": 12000.0,
        "age": 38,
        "employment_type": "business",
        "employment_duration_months": 48,
        "credit_history_years": 5.0,
        "collateral_value": 200000.0,
        "consistency_score": 1.0,
        "expected_code": "likely_approved"
    },
    {
        "id": "test_underage_hard_reject_05",
        "name": "Fixture Underage Hard Reject",
        "monthly_income": 40000.0,
        "requested_amount": 100000.0,
        "tenure_months": 12,
        "existing_emis": 0.0,
        "age": 17,  # Under minimum age 18
        "employment_type": "salaried",
        "employment_duration_months": 6,
        "credit_history_years": 0.0,
        "collateral_value": 0.0,
        "consistency_score": 1.0,
        "expected_code": "unlikely_approved"
    },
    {
        "id": "test_doc_mismatch_flag_06",
        "name": "Fixture Document Mismatch",
        "monthly_income": 150000.0,
        "requested_amount": 300000.0,
        "tenure_months": 24,
        "existing_emis": 0.0,
        "age": 35,
        "employment_type": "salaried",
        "employment_duration_months": 24,
        "credit_history_years": 2.0,
        "collateral_value": 0.0,
        "consistency_score": 0.50, # Below 0.60 hard consistency floor
        "expected_code": "unlikely_approved"
    }
]

def test_isolated_fixtures_evaluation():
    from backend.services.policy_engine.engine import policy_engine

    assert len(TEST_FIXTURES) <= 10, "Non-negotiable constraint: Maximum 10 test fixtures allowed."

    for fixture in TEST_FIXTURES:
        res = policy_engine.evaluate(fixture)
        assert res["recommendation_code"] == fixture["expected_code"], (
            f"Fixture '{fixture['name']}' produced {res['recommendation_code']}, expected {fixture['expected_code']}"
        )
