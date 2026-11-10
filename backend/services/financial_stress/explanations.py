"""
Deterministic string template explanations for financial stress scenarios.
NO LLM calls. All explanations are computed from numeric values using templates.
"""

from .stress_indicators import StressLevel


def _fmt_inr(amount: float) -> str:
    """Format a number as Indian Rupees with comma grouping."""
    try:
        val = int(round(abs(amount)))
        # Indian number format: last 3 digits, then groups of 2
        s = str(val)
        if len(s) <= 3:
            formatted = s
        else:
            formatted = s[-3:]
            s = s[:-3]
            while s:
                formatted = s[-2:] + "," + formatted
                s = s[:-2]
        sign = "-" if amount < 0 else ""
        return f"Rs.{sign}{formatted}"
    except Exception:
        return f"Rs.{amount:.0f}"


def _pct(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}%"


def generate_baseline_explanation(baseline: dict) -> str:
    """
    Generate a plain-English explanation for the baseline financial scenario.
    
    baseline dict keys: net_income, existing_emis, monthly_expenses,
    proposed_emi, remaining_balance, foir, stress_indicator
    """
    ni = baseline.get("net_income", 0)
    exp = baseline.get("monthly_expenses", 0)
    existing = baseline.get("existing_emis", 0)
    prop = baseline.get("proposed_emi", 0)
    remaining = baseline.get("remaining_balance", 0)
    foir = baseline.get("foir", 0)
    level = baseline.get("stress_indicator", StressLevel.INSUFFICIENT_DATA)

    if ni <= 0:
        return ("Baseline scenario cannot be calculated: monthly income data is missing or zero. "
                "Please verify the application's income information.")

    # Build explanation parts
    parts = []

    # Opening based on stress level
    if level == StressLevel.STABLE or level == "STABLE":
        parts.append(
            f"With a net monthly income of {_fmt_inr(ni)}, your current financial position appears stable."
        )
    elif level == StressLevel.REDUCED_BUFFER or level == "REDUCED_BUFFER":
        parts.append(
            f"With a net monthly income of {_fmt_inr(ni)}, your financial position shows a reduced buffer under the proposed loan."
        )
    elif level == StressLevel.ELEVATED_STRESS or level == "ELEVATED_STRESS":
        parts.append(
            f"With a net monthly income of {_fmt_inr(ni)}, the proposed loan creates elevated financial stress."
        )
    elif level == StressLevel.NEGATIVE_BALANCE or level == "NEGATIVE_BALANCE":
        parts.append(
            f"With a net monthly income of {_fmt_inr(ni)}, the proposed loan results in a monthly deficit — obligations exceed income."
        )
    else:
        parts.append(f"Net monthly income: {_fmt_inr(ni)}.")

    # Obligations breakdown
    if existing > 0:
        parts.append(
            f"Existing EMI obligations of {_fmt_inr(existing)} plus the proposed EMI of {_fmt_inr(prop)} "
            f"bring total monthly loan payments to {_fmt_inr(existing + prop)}."
        )
    else:
        parts.append(
            f"With no existing EMIs, the proposed loan EMI of {_fmt_inr(prop)} is your only loan obligation."
        )

    # Expenses
    if exp > 0:
        parts.append(
            f"Estimated monthly living expenses of {_fmt_inr(exp)} are also factored in."
        )

    # Remaining balance
    if remaining >= 0:
        parts.append(
            f"After all obligations, an estimated monthly surplus of {_fmt_inr(remaining)} remains."
        )
    else:
        parts.append(
            f"After all obligations, there is a monthly shortfall of {_fmt_inr(abs(remaining))} — "
            f"meaning the total outflow exceeds income."
        )

    # FOIR commentary
    if foir <= 35:
        parts.append(
            f"Your debt-to-income ratio (FOIR) of {_pct(foir)} is within the safe zone (below 35%)."
        )
    elif foir <= 45:
        parts.append(
            f"Your FOIR of {_pct(foir)} is in the moderate risk band (35–45%). Lenders generally accept up to 45%."
        )
    elif foir <= 55:
        parts.append(
            f"Your FOIR of {_pct(foir)} is elevated (above 45%). This may concern lenders."
        )
    else:
        parts.append(
            f"Your FOIR of {_pct(foir)} is critically high (above 55%). Loan approval becomes very difficult at this level."
        )

    return " ".join(parts)


def generate_scenario_explanation(
    scenario_name: str,
    scenario: dict,
    baseline: dict
) -> str:
    """
    Generate explanation comparing a scenario to baseline.
    
    scenario_name: human-readable name (e.g., "10% Income Reduction")
    scenario: scenario result dict
    baseline: baseline result dict
    """
    remaining = scenario.get("remaining_balance", 0)
    baseline_remaining = baseline.get("remaining_balance", 0)
    foir = scenario.get("foir", 0)
    level = scenario.get("stress_indicator", "")
    ni = scenario.get("net_income", 0)
    exp = scenario.get("monthly_expenses", 0)

    delta = remaining - baseline_remaining
    delta_sign = "decreases" if delta < 0 else "increases"
    delta_abs = abs(delta)

    parts = []

    # Scenario header
    parts.append(f"Under the '{scenario_name}' scenario:")

    # Net income note if changed
    baseline_ni = baseline.get("net_income", 0)
    if abs(ni - baseline_ni) > 1:
        parts.append(
            f"Net income adjusts to {_fmt_inr(ni)} (from {_fmt_inr(baseline_ni)} baseline)."
        )

    # Expense note if changed
    baseline_exp = baseline.get("monthly_expenses", 0)
    if abs(exp - baseline_exp) > 1:
        parts.append(
            f"Monthly expenses adjust to {_fmt_inr(exp)} (from {_fmt_inr(baseline_exp)} baseline)."
        )

    # Remaining balance impact
    parts.append(
        f"Monthly surplus {delta_sign} by {_fmt_inr(delta_abs)}, "
        f"resulting in a {'surplus' if remaining >= 0 else 'deficit'} of {_fmt_inr(abs(remaining))}."
    )

    # Stress level assessment
    if level == StressLevel.STABLE or level == "STABLE":
        parts.append("Financial position remains stable in this scenario.")
    elif level == StressLevel.REDUCED_BUFFER or level == "REDUCED_BUFFER":
        parts.append(
            "Financial buffer reduces significantly. Emergency reserves may be strained."
        )
    elif level == StressLevel.ELEVATED_STRESS or level == "ELEVATED_STRESS":
        parts.append(
            "Elevated financial stress detected. Very limited monthly surplus leaves little room for unexpected costs."
        )
    elif level == StressLevel.NEGATIVE_BALANCE or level == "NEGATIVE_BALANCE":
        parts.append(
            "This scenario creates a monthly deficit — total obligations would exceed income. "
            "Loan repayment sustainability would be at serious risk."
        )

    # FOIR
    if foir > 45:
        parts.append(
            f"FOIR rises to {_pct(foir)}, exceeding the typical 45% lender threshold."
        )
    else:
        parts.append(f"FOIR in this scenario: {_pct(foir)}.")

    return " ".join(parts)


def generate_stress_explanation(stress_level: str, key_factors: list) -> str:
    """
    Generate a summary explanation of the overall stress assessment
    with key contributing factors.
    """
    level_explanations = {
        "STABLE": (
            "Overall financial assessment: STABLE. "
            "The applicant demonstrates strong capacity to manage the proposed loan obligations. "
            "Income comfortably covers all expenses and loan repayments."
        ),
        "REDUCED_BUFFER": (
            "Overall financial assessment: REDUCED BUFFER. "
            "The applicant can service the loan, but with limited monthly surplus. "
            "Financial resilience to unexpected events (medical costs, income disruption) is reduced."
        ),
        "ELEVATED_STRESS": (
            "Overall financial assessment: ELEVATED STRESS. "
            "The applicant faces meaningful financial pressure under the proposed loan. "
            "A small disruption in income or increase in expenses could make repayment difficult."
        ),
        "NEGATIVE_BALANCE": (
            "Overall financial assessment: NEGATIVE BALANCE — CRITICAL. "
            "The proposed loan obligations, combined with current expenses, would exceed monthly income. "
            "Loan approval at the current terms presents significant repayment risk."
        ),
        "INSUFFICIENT_DATA": (
            "Financial stress assessment could not be completed due to missing or zero income data."
        )
    }

    base = level_explanations.get(
        stress_level,
        "Financial stress level has been assessed based on current application data."
    )

    if key_factors:
        factor_text = "; ".join(key_factors)
        return f"{base} Key contributing factors: {factor_text}."
    return base


def generate_projection_explanation(
    months_to_stress: int | None,
    income_change_pct: float,
    expense_growth_pct: float
) -> str:
    """Generate explanation for the 12-month projection."""
    parts = ["12-Month Forward Projection (Assumption-Based, Not a Forecast)."]

    if income_change_pct != 0:
        direction = "decreasing" if income_change_pct < 0 else "growing"
        parts.append(
            f"Income is assumed to be {direction} at {abs(income_change_pct):.1f}% per month."
        )
    else:
        parts.append("Income is assumed to remain constant over the projection period.")

    if expense_growth_pct > 0:
        parts.append(
            f"Monthly expenses are assumed to grow at {expense_growth_pct:.1f}% per month."
        )

    if months_to_stress is not None:
        if months_to_stress == 0:
            parts.append(
                "Financial stress is present from Month 1 under these assumptions."
            )
        else:
            parts.append(
                f"Based on these assumptions, financial stress conditions may emerge around Month {months_to_stress + 1}."
            )
    else:
        parts.append(
            "Financial position remains stable throughout the projected 12-month period under these assumptions."
        )

    parts.append(
        "Note: This projection uses applicant-provided assumptions and is not a guaranteed forecast of future financial conditions."
    )

    return " ".join(parts)

