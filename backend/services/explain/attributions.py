from typing import Dict, Any, List

def compute_feature_attributions(app_data: Dict[str, Any], ratios: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Computes signed feature contributions for the officer view.
    Positive values push toward approval; negative values pull toward rejection.
    """
    attributions = []

    # 1. FOIR (Benchmark: 45%)
    foir = float(ratios.get("foir", 0.0))
    # Centered at 0.45; difference scaled by weight 30
    foir_contrib = round((0.45 - foir) * 60.0, 2)
    attributions.append({
        "feature": "foir",
        "display_label": "Debt-to-Income (FOIR)",
        "value": f"{foir * 100:.1f}%",
        "attribution": foir_contrib,
        "impact": "positive" if foir_contrib >= 0 else "negative"
    })

    # 2. Loan to Income (Benchmark: 3.0x)
    lti = float(ratios.get("lti", 0.0))
    lti_contrib = round((3.0 - lti) * 6.0, 2)
    attributions.append({
        "feature": "lti",
        "display_label": "Loan-to-Income Ratio",
        "value": f"{lti:.2f}x",
        "attribution": lti_contrib,
        "impact": "positive" if lti_contrib >= 0 else "negative"
    })

    # 3. Employment stability (Benchmark: 18 months)
    emp_months = int(app_data.get("employment_duration_months", 12))
    emp_contrib = round(min(15.0, (emp_months - 18) * 0.5), 2)
    attributions.append({
        "feature": "employment_duration_months",
        "display_label": "Employment Duration",
        "value": f"{emp_months} months",
        "attribution": emp_contrib,
        "impact": "positive" if emp_contrib >= 0 else "negative"
    })

    # 4. Document consistency (Benchmark: 85%)
    consistency = float(ratios.get("consistency_score", 1.0))
    doc_contrib = round((consistency - 0.85) * 40.0, 2)
    attributions.append({
        "feature": "consistency_score",
        "display_label": "Document Consistency",
        "value": f"{consistency * 100:.0f}%",
        "attribution": doc_contrib,
        "impact": "positive" if doc_contrib >= 0 else "negative"
    })

    # 5. Credit history length (Benchmark: 2 years)
    ch_years = float(app_data.get("credit_history_years", 0.0))
    ch_contrib = round((ch_years - 2.0) * 3.0, 2)
    attributions.append({
        "feature": "credit_history_years",
        "display_label": "Credit History Length",
        "value": f"{ch_years:.1f} yrs",
        "attribution": ch_contrib,
        "impact": "positive" if ch_contrib >= 0 else "negative"
    })

    # 6. Collateral / LTV
    col_val = float(app_data.get("collateral_value", 0.0))
    req_amt = float(app_data.get("requested_amount", 1.0))
    ltv = col_val / req_amt if req_amt > 0 else 0.0
    col_contrib = round(min(10.0, ltv * 10.0), 2)
    attributions.append({
        "feature": "collateral_value",
        "display_label": "Collateral / Security",
        "value": f"₹{col_val:,.0f}",
        "attribution": col_contrib,
        "impact": "positive" if col_contrib > 0 else "neutral"
    })

    # Sort by absolute attribution impact
    attributions.sort(key=lambda x: abs(x["attribution"]), reverse=True)
    return attributions
