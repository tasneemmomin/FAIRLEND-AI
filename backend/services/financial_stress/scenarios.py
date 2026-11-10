"""
Scenario generation for financial stress simulation.
Produces predefined and custom scenario sets from baseline financial parameters.
All threshold/step values can be supplied from the admin-configured
StressScenarioConfig; documented module defaults are used otherwise.
"""

from .calculations import (
    apply_income_reduction,
    apply_expense_increase,
    calculate_remaining_balance,
    calculate_foir,
    calculate_total_emi_burden,
    calculate_disposable_income,
    calculate_expense_burden_ratio,
)
from .stress_indicators import (
    classify_stress,
    get_stress_metadata,
    STABLE_THRESHOLD,
    REDUCED_BUFFER_THRESHOLD,
    ELEVATED_STRESS_THRESHOLD,
)
from .explanations import generate_scenario_explanation

# Documented default steps (overridable via admin configuration)
DEFAULT_INCOME_REDUCTION_STEPS = [5.0, 10.0, 15.0, 20.0]
DEFAULT_EXPENSE_INCREASE_STEPS = [5.0, 10.0, 15.0, 20.0]
DEFAULT_COMBINED_PRESETS = [
    {"income_reduction": 10.0, "expense_increase": 10.0},
    {"income_reduction": 15.0, "expense_increase": 15.0},
    {"income_reduction": 20.0, "expense_increase": 20.0},
]
# Scenario D: hypothetical additional obligations as % of net income
DEFAULT_ADDITIONAL_OBLIGATION_SCENARIOS = [
    {"label": "Additional Loan EMI", "pct_of_income": 5.0},
    {"label": "Medical Expense", "pct_of_income": 5.0},
    {"label": "Education Expense", "pct_of_income": 7.0},
    {"label": "Household Expense Increase", "pct_of_income": 4.0},
]


def _stress_thresholds(config: dict | None) -> dict | None:
    if not config:
        return None
    return config.get("stress_thresholds")


def _build_scenario_result(
    scenario_name: str,
    net_income: float,
    existing_emis: float,
    monthly_expenses: float,
    proposed_emi: float,
    baseline: dict,
    config: dict | None = None,
) -> dict:
    """Build a complete scenario result dict from financial parameters."""
    thresholds = _stress_thresholds(config)
    foir_bands = config.get("foir_bands") if config else None

    disposable = calculate_disposable_income(net_income, existing_emis, monthly_expenses)
    remaining = calculate_remaining_balance(net_income, existing_emis, monthly_expenses, proposed_emi)
    foir = calculate_foir(existing_emis, proposed_emi, net_income)
    total_emi = calculate_total_emi_burden(existing_emis, proposed_emi)
    expense_ratio = calculate_expense_burden_ratio(monthly_expenses, net_income)
    stress = classify_stress(remaining, net_income, thresholds)
    stress_meta = get_stress_metadata(stress)
    explanation = generate_scenario_explanation(scenario_name, {
        "remaining_balance": remaining,
        "net_income": net_income,
        "monthly_expenses": monthly_expenses,
        "foir": foir,
        "stress_indicator": stress.value
    }, baseline)

    return {
        "scenario_name": scenario_name,
        "net_income": net_income,
        "existing_emis": existing_emis,
        "monthly_expenses": monthly_expenses,
        "proposed_emi": proposed_emi,
        "disposable_income": disposable,
        "remaining_balance": remaining,
        "total_emi_burden": total_emi,
        "expense_burden_ratio": expense_ratio,
        "foir": foir,
        "stress_indicator": stress.value,
        "stress_label": stress_meta["label"],
        "stress_color": stress_meta["color"],
        "explanation": explanation
    }


def generate_baseline_scenario(
    baseline_income: float,
    existing_emis: float,
    monthly_expenses: float,
    proposed_emi: float,
    baseline: dict,
    config: dict | None = None,
) -> dict:
    """Scenario A: Current Financial Condition (validated application data)."""
    return _build_scenario_result(
        scenario_name="Current Financial Condition",
        net_income=baseline_income,
        existing_emis=existing_emis,
        monthly_expenses=monthly_expenses,
        proposed_emi=proposed_emi,
        baseline=baseline,
        config=config,
    )


def generate_income_reduction_scenarios(
    baseline_income: float,
    existing_emis: float,
    monthly_expenses: float,
    proposed_emi: float,
    baseline: dict,
    steps: list[float] | None = None,
    config: dict | None = None,
) -> list[dict]:
    """Scenario B: income reduction scenarios (default 5/10/15/20%)."""
    results = []
    for pct in (steps or DEFAULT_INCOME_REDUCTION_STEPS):
        reduced_income = apply_income_reduction(baseline_income, pct)
        result = _build_scenario_result(
            scenario_name=f"{pct:g}% Income Reduction",
            net_income=reduced_income,
            existing_emis=existing_emis,
            monthly_expenses=monthly_expenses,
            proposed_emi=proposed_emi,
            baseline=baseline,
            config=config,
        )
        result["variation_pct"] = pct
        results.append(result)
    return results


def generate_expense_increase_scenarios(
    baseline_income: float,
    existing_emis: float,
    baseline_expenses: float,
    proposed_emi: float,
    baseline: dict,
    steps: list[float] | None = None,
    config: dict | None = None,
) -> list[dict]:
    """Scenario C: expense increase scenarios (default 5/10/15/20%)."""
    results = []
    for pct in (steps or DEFAULT_EXPENSE_INCREASE_STEPS):
        increased_expenses = apply_expense_increase(baseline_expenses, pct)
        result = _build_scenario_result(
            scenario_name=f"{pct:g}% Expense Increase",
            net_income=baseline_income,
            existing_emis=existing_emis,
            monthly_expenses=increased_expenses,
            proposed_emi=proposed_emi,
            baseline=baseline,
            config=config,
        )
        result["variation_pct"] = pct
        results.append(result)
    return results


def generate_additional_obligation_scenarios(
    baseline_income: float,
    existing_emis: float,
    monthly_expenses: float,
    proposed_emi: float,
    baseline: dict,
    obligation_defs: list[dict] | None = None,
    config: dict | None = None,
) -> list[dict]:
    """
    Scenario D: hypothetical additional recurring obligations.
    Each definition is contributed as a percentage of net income and is
    explicitly labelled a hypothetical assumption, not a verified fact.
    """
    results = []
    for od in (obligation_defs or DEFAULT_ADDITIONAL_OBLIGATION_SCENARIOS):
        amount = round((baseline_income or 0.0) * (od.get("pct_of_income", 0.0) / 100.0), 2)
        if amount <= 0:
            continue
        result = _build_scenario_result(
            scenario_name=f"{od['label']}: +Rs.{amount:,.0f}/month (hypothetical)",
            net_income=baseline_income,
            existing_emis=existing_emis + amount,
            monthly_expenses=monthly_expenses,
            proposed_emi=proposed_emi,
            baseline=baseline,
            config=config,
        )
        result["hypothetical"] = True
        result["additional_obligation"] = amount
        result["obligation_type"] = od["label"]
        results.append(result)
    return results


def generate_combined_scenarios(
    baseline_income: float,
    existing_emis: float,
    baseline_expenses: float,
    proposed_emi: float,
    baseline: dict,
    presets: list[dict] | None = None,
    config: dict | None = None,
) -> list[dict]:
    """Scenario E: combined income reduction + expense increase scenarios."""
    results = []
    for preset in (presets or DEFAULT_COMBINED_PRESETS):
        ir = preset["income_reduction"]
        ei = preset["expense_increase"]
        adj_income = apply_income_reduction(baseline_income, ir)
        adj_expenses = apply_expense_increase(baseline_expenses, ei)
        result = _build_scenario_result(
            scenario_name=f"Combined: -{ir:g}% Income, +{ei:g}% Expenses",
            net_income=adj_income,
            existing_emis=existing_emis,
            monthly_expenses=adj_expenses,
            proposed_emi=proposed_emi,
            baseline=baseline,
            config=config,
        )
        result["income_reduction_pct"] = ir
        result["expense_increase_pct"] = ei
        results.append(result)
    return results


def generate_custom_scenario(
    income_reduction_pct: float,
    expense_increase_pct: float,
    additional_obligation: float,
    baseline_income: float,
    existing_emis: float,
    baseline_expenses: float,
    proposed_emi: float,
    custom_proposed_emi: float | None,
    baseline: dict,
    config: dict | None = None,
) -> dict:
    """Scenario F: fully user-defined hypothetical scenario."""
    adj_income = apply_income_reduction(baseline_income, income_reduction_pct)
    adj_expenses = apply_expense_increase(baseline_expenses, expense_increase_pct)
    adj_existing = existing_emis + additional_obligation
    emi = custom_proposed_emi if custom_proposed_emi is not None else proposed_emi

    name_parts = []
    if income_reduction_pct > 0:
        name_parts.append(f"-{income_reduction_pct:g}% income")
    if expense_increase_pct > 0:
        name_parts.append(f"+{expense_increase_pct:g}% expenses")
    if additional_obligation > 0:
        name_parts.append(f"+Rs.{additional_obligation:,.0f} obligation")
    if custom_proposed_emi is not None:
        name_parts.append(f"EMI adjusted to Rs.{emi:,.0f}")

    scenario_name = "Custom: " + (", ".join(name_parts) if name_parts else "Baseline Replicated")

    result = _build_scenario_result(
        scenario_name=scenario_name,
        net_income=adj_income,
        existing_emis=adj_existing,
        monthly_expenses=adj_expenses,
        proposed_emi=emi,
        baseline=baseline,
        config=config,
    )
    result["hypothetical"] = True
    result["custom_inputs"] = {
        "income_reduction_pct": income_reduction_pct,
        "expense_increase_pct": expense_increase_pct,
        "additional_obligation": additional_obligation,
        "proposed_emi": emi,
    }
    return result
