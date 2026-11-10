"""
Pydantic schemas and documented default configuration for the
Financial Stress Simulator. Validation prevents invalid or negative
inputs and clamps custom values to admin-configured simulation ranges.
"""

from typing import Optional
from pydantic import BaseModel, Field

from .calculations import CALC_VERSION

# ---------------------------------------------------------------------------
# Default administrative configuration (documented calculation rules)
# ---------------------------------------------------------------------------

DEFAULT_STRESS_CONFIG = {
    "calc_version": CALC_VERSION,
    "description": (
        "Deterministic financial stress simulation configuration. "
        "Thresholds below mirror config/policy_rules.yaml FOIR bands."
    ),
    # EMI derivation for the proposed loan (documented assumption when the
    # application does not store an explicit proposed EMI).
    "default_interest_rate_pct": 12.0,
    # When monthly expenses are not provided, estimate as a ratio of income.
    "estimated_expense_ratio": 0.40,
    # Predefined scenario variation steps (percent).
    "income_reduction_steps": [5.0, 10.0, 15.0, 20.0],
    "expense_increase_steps": [5.0, 10.0, 15.0, 20.0],
    "combined_stress_presets": [
        {"income_reduction": 10.0, "expense_increase": 15.0},
        {"income_reduction": 15.0, "expense_increase": 15.0},
        {"income_reduction": 20.0, "expense_increase": 20.0},
    ],
    # Scenario D: hypothetical additional obligations, as % of net income.
    "additional_obligation_scenarios": [
        {"label": "Additional Loan EMI", "pct_of_income": 5.0},
        {"label": "Medical Expense", "pct_of_income": 5.0},
        {"label": "Education Expense", "pct_of_income": 7.0},
        {"label": "Household Expense Increase", "pct_of_income": 4.0},
    ],
    # Stress indicator bands (fraction of net monthly income remaining).
    # Documented calculation rules sharing policy FOIR bands: 0.35 ~= safe FOIR.
    "stress_thresholds": {
        "stable_min_ratio": 0.20,
        "reduced_buffer_min_ratio": 0.10,
        "elevated_stress_min_ratio": 0.0,
    },
    # FOIR risk bands (percent) consistent with config/policy_rules.yaml tiers.
    "foir_bands": {"safe": 35.0, "moderate": 45.0, "high": 55.0},
    # Permitted simulation ranges for user-customized scenarios.
    "simulation_limits": {
        "income_reduction_max_pct": 50.0,
        "expense_increase_max_pct": 150.0,
        "additional_obligation_max_inr": 200000.0,
        "proposed_emi_max_multiplier": 10.0,   # cap vs computed proposed EMI
        "income_reduction_min_pct": 0.0,
        "expense_increase_min_pct": 0.0,
    },
    "projection_months_default": 12,
    "projection_months_max": 24,
}


def deep_merge_config(payload: dict) -> dict:
    """Merge stored config payload over the documented defaults (shallow)."""
    merged = dict(DEFAULT_STRESS_CONFIG)
    merged.update(payload or {})
    return merged


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class CustomScenarioRequest(BaseModel):
    """User-customized hypothetical scenario (Scenario F)."""
    income_reduction_pct: float = Field(0.0, ge=0.0, le=100.0)
    expense_increase_pct: float = Field(0.0, ge=0.0, le=300.0)
    additional_obligation: float = Field(0.0, ge=0.0)
    # Optional adjustment of the proposed EMI itself (hypothetical).
    proposed_emi: Optional[float] = Field(None, ge=0.0)


class ProjectionRequest(BaseModel):
    """Assumption-based 12-month projection inputs."""
    monthly_income_change_pct: float = Field(0.0, ge=-100.0, le=200.0)
    expense_growth_pct: float = Field(0.0, ge=-100.0, le=300.0)
    additional_obligation: float = Field(0.0, ge=0.0)
    proposed_emi: Optional[float] = Field(None, ge=0.0)
    months: int = Field(12, ge=1, le=24)


class OfficerAssessmentRequest(BaseModel):
    """Officer-recorded advisory assessment of the stress analysis."""
    assessment_note: str = Field(..., min_length=3)
