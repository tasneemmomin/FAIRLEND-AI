from typing import Dict, Any

def extract_feature_vector(app_data: Dict[str, Any], ratios: Dict[str, float]) -> Dict[str, Any]:
    """
    Constructs a normalized, reproducible feature dictionary for the streaming ML model.
    CRITICAL: Protected attributes (gender, caste, religion, etc.) are strictly excluded.
    """
    return {
        "monthly_income": float(app_data.get("monthly_income", 0.0)),
        "requested_amount": float(app_data.get("requested_amount", 0.0)),
        "tenure_months": int(app_data.get("tenure_months", 12)),
        "existing_emis": float(app_data.get("existing_emis", 0.0)),
        "age": int(app_data.get("age", 25)),
        "employment_duration_months": int(app_data.get("employment_duration_months", 12)),
        "credit_history_years": float(app_data.get("credit_history_years", 0.0)),
        "collateral_value": float(app_data.get("collateral_value", 0.0)),
        "dependents": int(app_data.get("dependents", 0)),
        "employment_type": str(app_data.get("employment_type", "salaried")),
        "residence_type": str(app_data.get("residence_type", "rented")),
        "loan_purpose": str(app_data.get("loan_purpose", "personal")),
        # Derived Financial Engineering Ratios
        "foir": float(ratios.get("foir", 0.0)),
        "lti": float(ratios.get("lti", 0.0)),
        "disposable_income": float(ratios.get("disposable_income", 0.0)),
        "consistency_score": float(ratios.get("consistency_score", 1.0)),
    }
