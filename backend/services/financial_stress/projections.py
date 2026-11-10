"""
Assumption-based monthly financial projection (up to 24 months).

IMPORTANT: This is a transparent, deterministic assumption-based projection.
It is NOT a statistically trained forecast and must never be labelled as one.
All inputs are hypothetical assumptions (monthly income change, expense growth,
new obligations). The engine compounds assumed changes month by month and
reports the remaining monthly balance and cumulative cash-flow buffer.
"""

from .calculations import calculate_foir
from .stress_indicators import classify_stress, get_stress_metadata
from .explanations import generate_projection_explanation

DEFAULT_PROJECTION_MONTHS = 12
MAX_PROJECTION_MONTHS = 24
EPSILON = 0.005  # tolerance for float rounding on yearly compounding


def generate_monthly_projection(
    baseline_income: float,
    existing_emis: float,
    monthly_expenses: float,
    proposed_emi: float,
    monthly_income_change_pct: float = 0.0,
    expense_growth_pct: float = 0.0,
    additional_obligation: float = 0.0,
    months: int = DEFAULT_PROJECTION_MONTHS,
    baseline: dict | None = None,
) -> dict:
    """
    Produce a month-by-month projection under assumption-based inputs.

    Month m (1-indexed):
      income_m    = baseline_income * (1 + monthly_income_change_pct/100) ** (m-1)
      expenses_m  = (monthly_expenses + additional_obligation) * (1 + expense_growth_pct/100) ** (m-1)
      balance_m   = income_m - existing_emis - expenses_m - proposed_emi

    Existing EMI and proposed EMI remain constant unless the caller adjusts
    proposed_emi itself (custom scenario "Proposed EMI Adjustment").
    """
    months = max(1, min(int(months), MAX_PROJECTION_MONTHS))
    income_factor = 1.0 + (monthly_income_change_pct / 100.0)
    expense_factor = 1.0 + (expense_growth_pct / 100.0)
    insufficient = baseline_income is None or baseline_income <= 0

    income_factor = max(0.0, income_factor)
    expense_factor = max(0.0, expense_factor)

    monthly_rows = []
    cumulative_buffer = 0.0
    months_to_stress: int | None = None

    for m in range(1, months + 1):
        proj_income = round(baseline_income * (income_factor ** (m - 1)), 2)
        proj_expenses = round((monthly_expenses + additional_obligation) * (expense_factor ** (m - 1)), 2)
        balance = round(proj_income - existing_emis - proj_expenses - proposed_emi, 2)
        cumulative_buffer = round(cumulative_buffer + balance, 2)

        stress = classify_stress(balance, proj_income)
        if balance < 0 and months_to_stress is None and not insufficient:
            months_to_stress = m - 1  # 0-based index so display = index + 1

        foir = calculate_foir(existing_emis, proposed_emi, proj_income)
        meta = get_stress_metadata(stress)

        monthly_rows.append({
            "month": m,
            "income": proj_income,
            "expenses": proj_expenses,
            "existing_emis": existing_emis,
            "proposed_emi": proposed_emi,
            "total_outflow": round(proj_expenses + existing_emis + proposed_emi, 2),
            "remaining_balance": balance,
            "cumulative_buffer": cumulative_buffer,
            "stress_indicator": stress.value,
            "stress_label": meta["label"],
            "stress_color": meta["color"],
            "foir": foir,
        })

    total_surplus = monthly_rows[-1]["cumulative_buffer"] if monthly_rows else 0.0

    explanation = generate_projection_explanation(
        months_to_stress if not insufficient else None,
        monthly_income_change_pct,
        expense_growth_pct,
    )
    if insufficient:
        explanation = (
            "Projection could not be evaluated: monthly income data is missing or zero. "
            + explanation
        )

    return {
        "projection_months": months,
        "assumptions": {
            "monthly_income_change_pct": monthly_income_change_pct,
            "expense_growth_pct": expense_growth_pct,
            "additional_obligation": additional_obligation,
        },
        "monthly": monthly_rows,
        "months_to_stress": months_to_stress,
        "final_cumulative_buffer": total_surplus,
        "insufficient_data": insufficient,
        "explanation": explanation,
        "disclaimer": (
            "Assumption-based scenario projection. This is not a statistically "
            "trained forecast of future income or expenses."
        ),
    }
