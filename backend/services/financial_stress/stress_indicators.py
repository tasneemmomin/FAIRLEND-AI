"""
Stress indicator classification based on remaining balance.
Provides color-coded stress categories and thresholds.
"""

from enum import Enum


class StressLevel(str, Enum):
    STABLE = "STABLE"
    REDUCED_BUFFER = "REDUCED_BUFFER"
    ELEVATED_STRESS = "ELEVATED_STRESS"
    NEGATIVE_BALANCE = "NEGATIVE_BALANCE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


# Thresholds as fractions of net income
STABLE_THRESHOLD = 0.20          # > 20% of income remaining → Stable
REDUCED_BUFFER_THRESHOLD = 0.10  # 10-20% of income remaining → Reduced Buffer
ELEVATED_STRESS_THRESHOLD = 0.0  # 0-10% of income remaining → Elevated Stress
# Below 0 → Negative Balance

STRESS_COLORS = {
    StressLevel.STABLE: "#16a34a",           # green-600
    StressLevel.REDUCED_BUFFER: "#ca8a04",   # yellow-600
    StressLevel.ELEVATED_STRESS: "#ea580c",  # orange-600
    StressLevel.NEGATIVE_BALANCE: "#dc2626", # red-600
    StressLevel.INSUFFICIENT_DATA: "#64748b" # slate-500
}

STRESS_LABELS = {
    StressLevel.STABLE: "Financially Stable",
    StressLevel.REDUCED_BUFFER: "Reduced Buffer",
    StressLevel.ELEVATED_STRESS: "Elevated Stress",
    StressLevel.NEGATIVE_BALANCE: "Negative Balance",
    StressLevel.INSUFFICIENT_DATA: "Insufficient Data"
}

STRESS_DESCRIPTIONS = {
    StressLevel.STABLE: "Comfortable financial buffer with adequate surplus after all obligations.",
    StressLevel.REDUCED_BUFFER: "Moderate financial strain; limited savings buffer may reduce resilience to unexpected expenses.",
    StressLevel.ELEVATED_STRESS: "Very limited monthly surplus; any additional expense or income disruption could cause difficulty.",
    StressLevel.NEGATIVE_BALANCE: "Monthly obligations exceed income in this scenario. Loan repayment would be at high risk.",
    StressLevel.INSUFFICIENT_DATA: "Insufficient income data to determine financial stress level."
}

FOIR_RISK_THRESHOLDS = {
    "safe": 35.0,
    "moderate": 45.0,
    "high": 55.0,
    "critical": 100.0
}


def classify_stress(
    remaining_balance: float,
    net_income: float,
    thresholds: dict | None = None,
) -> StressLevel:
    """
    Classify financial stress based on remaining balance relative to net income.

    thresholds (optional admin config):
        stable_min_ratio, reduced_buffer_min_ratio, elevated_stress_min_ratio

    Args:
        remaining_balance: Monthly surplus after all obligations
        net_income: Monthly net income

    Returns:
        StressLevel enum value
    """
    if net_income is None or net_income <= 0:
        return StressLevel.INSUFFICIENT_DATA

    t = thresholds or {}
    stable_ratio = t.get("stable_min_ratio", STABLE_THRESHOLD)
    reduced_ratio = t.get("reduced_buffer_min_ratio", REDUCED_BUFFER_THRESHOLD)
    elevated_ratio = t.get("elevated_stress_min_ratio", ELEVATED_STRESS_THRESHOLD)

    if remaining_balance <= 0:
        return StressLevel.NEGATIVE_BALANCE
    elif remaining_balance <= reduced_ratio * net_income:
        return StressLevel.ELEVATED_STRESS
    elif remaining_balance <= stable_ratio * net_income:
        return StressLevel.REDUCED_BUFFER
    else:
        return StressLevel.STABLE


def classify_foir_risk(foir_pct: float, bands: dict | None = None) -> str:
    """Classify FOIR into risk bands (optionally from admin config)."""
    b = bands or FOIR_RISK_THRESHOLDS
    safe = b.get("safe", b.get("safe", 35.0))
    moderate = b.get("moderate", 45.0)
    high = b.get("high", 55.0)
    if foir_pct <= safe:
        return "safe"
    elif foir_pct <= moderate:
        return "moderate"
    elif foir_pct <= high:
        return "high"
    else:
        return "critical"


def get_stress_metadata(level: StressLevel) -> dict:
    """Return display metadata for a stress level."""
    return {
        "level": level.value,
        "label": STRESS_LABELS[level],
        "color": STRESS_COLORS[level],
        "description": STRESS_DESCRIPTIONS[level]
    }

