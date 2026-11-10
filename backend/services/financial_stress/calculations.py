"""
Pure deterministic financial calculations for stress simulation.
No I/O, no database access, no side effects.
All values treated as Indian Rupees (INR).
"""

CALC_VERSION = "1.0.0"
DEFAULT_ANNUAL_RATE_PCT = 12.0  # 12% per annum default interest rate


def calculate_emi(principal: float, annual_rate_pct: float, tenure_months: int) -> float:
    """
    Calculate Equated Monthly Installment (EMI) using standard formula.
    EMI = P * r * (1+r)^n / ((1+r)^n - 1)
    Where r = monthly interest rate (annual_rate / 12 / 100)
    Handles zero interest rate gracefully.
    """
    if principal <= 0 or tenure_months <= 0:
        return 0.0
    if annual_rate_pct <= 0:
        # Zero interest: simple division
        return round(principal / tenure_months, 2)
    r = annual_rate_pct / 12 / 100
    power = (1 + r) ** tenure_months
    emi = principal * r * power / (power - 1)
    return round(emi, 2)


def calculate_disposable_income(
    net_income: float,
    existing_emis: float,
    monthly_expenses: float
) -> float:
    """
    Disposable income = Net Income - Existing EMIs - Monthly Expenses (before new loan).
    """
    return round(net_income - existing_emis - monthly_expenses, 2)


def calculate_remaining_balance(
    net_income: float,
    existing_emis: float,
    monthly_expenses: float,
    proposed_emi: float
) -> float:
    """
    Remaining balance = Net Income - Existing EMIs - Monthly Expenses - Proposed EMI.
    Negative value indicates financial stress / deficit.
    """
    return round(net_income - existing_emis - monthly_expenses - proposed_emi, 2)


def calculate_foir(
    existing_emis: float,
    proposed_emi: float,
    net_income: float
) -> float:
    """
    Fixed Obligation to Income Ratio (FOIR) as a percentage.
    FOIR = (Existing EMIs + Proposed EMI) / Net Income * 100
    Returns 0.0 if net_income is zero or negative (safe division).
    """
    if net_income <= 0:
        return 0.0
    total_obligations = existing_emis + proposed_emi
    return round((total_obligations / net_income) * 100, 2)


def calculate_expense_burden_ratio(
    monthly_expenses: float,
    net_income: float
) -> float:
    """
    Expense Burden Ratio = Monthly Expenses / Net Income * 100.
    Represents what percentage of income goes to living expenses.
    """
    if net_income <= 0:
        return 0.0
    return round((monthly_expenses / net_income) * 100, 2)


def calculate_total_emi_burden(existing_emis: float, proposed_emi: float) -> float:
    """Total monthly EMI obligations including proposed loan."""
    return round(existing_emis + proposed_emi, 2)


def apply_income_reduction(net_income: float, reduction_pct: float) -> float:
    """Apply a percentage reduction to income (e.g., 10.0 = reduce by 10%)."""
    factor = max(0.0, 1.0 - (reduction_pct / 100.0))
    return round(net_income * factor, 2)


def apply_expense_increase(monthly_expenses: float, increase_pct: float) -> float:
    """Apply a percentage increase to expenses (e.g., 15.0 = increase by 15%)."""
    factor = 1.0 + (increase_pct / 100.0)
    return round(monthly_expenses * factor, 2)

