from typing import Dict, Any, List, Tuple

def calculate_consistency(
    declared_data: Dict[str, Any],
    extracted_data: Dict[str, Any]
) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Computes consistency score (0.0 to 1.0) comparing applicant-declared intake
    values against OCR-extracted document values.
    Returns: (score, list_of_mismatch_flags)
    """
    flags = []
    score = 1.0

    declared_income = float(declared_data.get("monthly_income", 0.0))
    declared_name = str(declared_data.get("applicant_name", "")).strip().lower()

    extracted_salary = extracted_data.get("monthly_salary")
    if extracted_salary is None:
        extracted_salary = extracted_data.get("total_credits")

    # 1. Income cross-check
    if declared_income > 0 and extracted_salary is not None and extracted_salary > 0:
        diff = abs(declared_income - extracted_salary)
        ratio = diff / max(declared_income, extracted_salary)

        if ratio <= 0.10:
            # Under 10% discrepancy: Excellent alignment
            pass
        elif ratio <= 0.25:
            # 10-25% discrepancy: Minor discrepancy
            penalty = (ratio - 0.10) * 1.0
            score -= penalty
            flags.append({
                "type": "INCOME_VARIANCE",
                "severity": "low",
                "message": f"Declared income (₹{declared_income:,.0f}) has a minor variance of {ratio*100:.1f}% compared to verified document salary (₹{extracted_salary:,.0f}).",
                "declared": declared_income,
                "verified": extracted_salary
            })
        else:
            # > 25% discrepancy: Serious mismatch flag
            penalty = min(0.60, ratio * 0.8)
            score -= penalty
            flags.append({
                "type": "INCOME_MISMATCH",
                "severity": "high",
                "message": f"Significant mismatch: Declared income (₹{declared_income:,.0f}) differs by {ratio*100:.1f}% from document verified salary (₹{extracted_salary:,.0f}).",
                "declared": declared_income,
                "verified": extracted_salary
            })

    # 2. Name cross-check
    extracted_name = extracted_data.get("extracted_name")
    if declared_name and extracted_name:
        ext_clean = extracted_name.strip().lower()
        # Check token overlap
        dec_tokens = set(declared_name.split())
        ext_tokens = set(ext_clean.split())
        common = dec_tokens.intersection(ext_tokens)

        if not common and len(dec_tokens) > 0 and len(ext_tokens) > 0:
            score -= 0.15
            flags.append({
                "type": "NAME_MISMATCH",
                "severity": "medium",
                "message": f"Name mismatch: Declared applicant name '{declared_data.get('applicant_name')}' does not match document name '{extracted_name}'.",
                "declared": declared_data.get("applicant_name"),
                "verified": extracted_name
            })

    # Bound score between 0.20 and 1.0
    final_score = max(0.20, min(1.0, round(score, 2)))
    return final_score, flags
