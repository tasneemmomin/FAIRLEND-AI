import math
from typing import Dict, Any, Tuple, List
import yaml
from backend.core.config import settings

def calculate_estimated_emi(principal: float, tenure_months: int, annual_interest_rate: float = 0.105) -> float:
    """Calculates standard reducing-balance monthly installment (EMI)."""
    if principal <= 0 or tenure_months <= 0:
        return 0.0
    r = annual_interest_rate / 12.0
    # Formula: E = P * r * (1+r)^n / ((1+r)^n - 1)
    emi = principal * r * ((1.0 + r) ** tenure_months) / (((1.0 + r) ** tenure_months) - 1.0)
    return round(emi, 2)

def calculate_foir(monthly_income: float, existing_emis: float, proposed_emi: float) -> float:
    """Fixed Obligation to Income Ratio (total monthly debt payments / monthly income)."""
    if monthly_income <= 0:
        return 1.0
    return round((existing_emis + proposed_emi) / monthly_income, 4)

def calculate_lti(requested_amount: float, monthly_income: float) -> float:
    """Loan to Annual Income ratio."""
    annual_income = monthly_income * 12.0
    if annual_income <= 0:
        return 999.0
    return round(requested_amount / annual_income, 2)

def calculate_disposable_income(monthly_income: float, existing_emis: float, proposed_emi: float) -> float:
    return round(monthly_income - (existing_emis + proposed_emi), 2)
