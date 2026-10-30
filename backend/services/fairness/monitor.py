from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.db.models import Application, FairnessAudit, OfficerDecision

def compute_fairness_metrics(db: Session) -> Dict[str, Any]:
    """
    Computes Demographic Parity Difference, Equal Opportunity Difference,
    and Disparate Impact Ratio on audit groups with explicit consent.
    Includes minimum sample size warnings.
    """
    records = db.query(FairnessAudit, Application, OfficerDecision).join(
        Application, FairnessAudit.application_id == Application.id
    ).outerjoin(
        OfficerDecision, Application.id == OfficerDecision.application_id
    ).filter(FairnessAudit.consent_given == True).all()

    total_audit_cases = len(records)
    if total_audit_cases < 5:
        warning_msg = "Fewer than 5 consented cases recorded. Fairness statistics require more live data."
        return {
            "total_audit_cases": total_audit_cases,
            "status": "insufficient_data",
            "warning": warning_msg,
            "sample_size_warnings": [warning_msg],
            "groups": {}
        }

    # Group by gender as primary audit demographic
    groups: Dict[str, Dict[str, int]] = {}
    for audit, app, dec in records:
        grp = audit.gender or "undisclosed"
        if grp not in groups:
            groups[grp] = {"total": 0, "approved_ai": 0, "approved_officer": 0, "true_positives": 0, "officer_positives": 0}

        groups[grp]["total"] += 1
        ai_approved = (app.ai_recommendation == "likely_approved")
        if ai_approved:
            groups[grp]["approved_ai"] += 1

        if dec and dec.decision == "approve":
            groups[grp]["approved_officer"] += 1
            groups[grp]["officer_positives"] += 1
            if ai_approved:
                groups[grp]["true_positives"] += 1

    group_stats = {}
    selection_rates = []
    tpr_rates = []
    sample_size_warnings = []

    for grp, counts in groups.items():
        n = counts["total"]
        sel_rate = counts["approved_ai"] / n if n > 0 else 0.0
        selection_rates.append(sel_rate)

        # True Positive Rate (TPR) for Equal Opportunity: P(AI=1 | Officer=1)
        tpr = counts["true_positives"] / counts["officer_positives"] if counts["officer_positives"] > 0 else None
        if tpr is not None:
            tpr_rates.append(tpr)

        if n < 10:
            sample_size_warnings.append(f"Group '{grp}' has only {n} samples (minimum 10 recommended).")

        group_stats[grp] = {
            "count": n,
            "ai_approval_count": counts["approved_ai"],
            "ai_selection_rate": round(sel_rate, 3),
            "officer_approval_count": counts["approved_officer"],
            "true_positive_rate": round(tpr, 3) if tpr is not None else "N/A (no officer approvals)"
        }

    # Demographic Parity Difference
    if selection_rates:
        dpd = round(max(selection_rates) - min(selection_rates), 3)
        max_rate = max(selection_rates)
        min_rate = min(selection_rates)
        disparate_impact_ratio = round(min_rate / max_rate, 3) if max_rate > 0 else 1.0
    else:
        dpd = 0.0
        disparate_impact_ratio = 1.0

    # Equal Opportunity Difference
    if len(tpr_rates) >= 2:
        eod = round(max(tpr_rates) - min(tpr_rates), 3)
    else:
        eod = None

    # 4/5ths Rule check (Disparate Impact < 0.80)
    adverse_impact_flag = (disparate_impact_ratio < 0.80)

    return {
        "total_audit_cases": total_audit_cases,
        "status": "active",
        "demographic_parity_difference": dpd,
        "disparate_impact_ratio": disparate_impact_ratio,
        "equal_opportunity_difference": eod,
        "adverse_impact_flag": adverse_impact_flag,
        "sample_size_warnings": sample_size_warnings,
        "groups": group_stats
    }
