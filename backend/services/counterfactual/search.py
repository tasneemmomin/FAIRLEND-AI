from typing import Dict, Any, List
from backend.services.policy_engine.engine import policy_engine
from backend.services.plain_english.translator import plain_english_translator

def find_counterfactuals(app_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Constrained search for actionable counterfactual and sensitivity explanations.
    For adverse/review outcomes: finds smallest actionable changes to achieve Approval.
    For approved outcomes: finds maximum borrowing capacity, tenure optimization, and debt tolerance.
    Strictly tests FAITHFULNESS by re-scoring each candidate through the policy engine.
    """
    current_eval = policy_engine.evaluate(app_data)
    is_approved = current_eval["recommendation_code"] == "likely_approved"

    candidates = []
    base_data = dict(app_data)

    current_amount = float(app_data.get("requested_amount", 0.0))
    current_tenure = int(app_data.get("tenure_months", 12))
    current_emis = float(app_data.get("existing_emis", 0.0))
    current_income = float(app_data.get("monthly_income", 0.0))

    if is_approved:
        # COUNTERFACTUALS FOR APPROVED APPLICANTS (Sensitivity & Headroom)

        # 1. Borrowing Headroom: Find highest approved loan amount
        max_approved_amount = current_amount
        for multiplier in [1.2, 1.4, 1.6, 1.8, 2.0, 2.5]:
            test_amount = round((current_amount * multiplier) / 25000) * 25000
            test_data = dict(base_data)
            test_data["requested_amount"] = test_amount
            test_eval = policy_engine.evaluate(test_data)
            if test_eval["recommendation_code"] == "likely_approved":
                max_approved_amount = test_amount

        if max_approved_amount > current_amount:
            diff = max_approved_amount - current_amount
            candidates.append({
                "feature_name": "requested_amount",
                "current_value": current_amount,
                "suggested_value": max_approved_amount,
                "change_description": f"Your strong financial profile allows you to qualify for up to ₹{int(max_approved_amount):,} (+₹{int(diff):,} additional headroom) under standard policy limits.",
                "actionability": "Positive Headroom: eligible for higher loan amount",
                "is_faithful": True,
                "direction": "increase",
                "cost": 0.1
            })

        # 2. Tenure Optimization: Shorten tenure to save interest
        if current_tenure >= 24:
            for target_tenure in [current_tenure - 12, current_tenure - 24]:
                if target_tenure >= 12:
                    test_data = dict(base_data)
                    test_data["tenure_months"] = target_tenure
                    test_eval = policy_engine.evaluate(test_data)
                    if test_eval["recommendation_code"] == "likely_approved":
                        candidates.append({
                            "feature_name": "tenure_months",
                            "current_value": current_tenure,
                            "suggested_value": target_tenure,
                            "change_description": f"You can reduce tenure from {current_tenure} months to {target_tenure} months and maintain approval, saving substantial interest payments.",
                            "actionability": "Optimization: shorten repayment to reduce total interest",
                            "is_faithful": True,
                            "direction": "decrease",
                            "cost": 0.2
                        })
                        break

        # 3. Debt Tolerance Buffer: How much extra debt buffer exists
        for extra_emi in [5000, 10000, 15000]:
            test_data = dict(base_data)
            test_data["existing_emis"] = current_emis + extra_emi
            test_eval = policy_engine.evaluate(test_data)
            if test_eval["recommendation_code"] == "likely_approved":
                candidates.append({
                    "feature_name": "existing_emis",
                    "current_value": current_emis,
                    "suggested_value": current_emis + extra_emi,
                    "change_description": f"Your risk buffer is strong: your application remains approved even if monthly obligations rise by ₹{extra_emi:,}.",
                    "actionability": "Safety Margin: robust debt absorption capacity",
                    "is_faithful": True,
                    "direction": "increase",
                    "cost": 0.3
                })
                break

        return candidates

    # COUNTERFACTUALS FOR REJECTED / NEEDS REVIEW APPLICANTS (Recourse Flip)

    # 1. Actionable Search: Reduce requested loan amount
    if current_amount > 20000:
        for ratio in [0.90, 0.80, 0.70, 0.60, 0.50, 0.40]:
            candidate_amount = round((current_amount * ratio) / 5000) * 5000
            test_data = dict(base_data)
            test_data["requested_amount"] = candidate_amount
            test_eval = policy_engine.evaluate(test_data)

            # Faithfulness check: must actually flip outcome to likely_approved
            if test_eval["recommendation_code"] == "likely_approved":
                desc = plain_english_translator.format_counterfactual(
                    "amount_reduction", current_amount, candidate_amount
                )
                candidates.append({
                    "feature_name": "requested_amount",
                    "current_value": current_amount,
                    "suggested_value": candidate_amount,
                    "change_description": desc,
                    "actionability": "High: reduce loan request amount",
                    "is_faithful": True,
                    "direction": "decrease",
                    "cost": 1.0 - ratio
                })
                break

    # 2. Actionable Search: Extend loan tenure
    if current_tenure < 60:
        for add_months in [12, 24, 36, 48]:
            candidate_tenure = current_tenure + add_months
            if candidate_tenure > 84:
                break
            test_data = dict(base_data)
            test_data["tenure_months"] = candidate_tenure
            test_eval = policy_engine.evaluate(test_data)

            if test_eval["recommendation_code"] == "likely_approved":
                desc = plain_english_translator.format_counterfactual(
                    "tenure_extension", current_tenure, candidate_tenure
                )
                candidates.append({
                    "feature_name": "tenure_months",
                    "current_value": current_tenure,
                    "suggested_value": candidate_tenure,
                    "change_description": desc,
                    "actionability": "Medium: extend repayment duration",
                    "is_faithful": True,
                    "direction": "increase",
                    "cost": add_months / 48.0
                })
                break

    # 3. Actionable Search: Pay down existing EMIs
    if current_emis > 0:
        for reduction_ratio in [0.3, 0.5, 0.7, 1.0]:
            candidate_emis = round(current_emis * (1.0 - reduction_ratio))
            test_data = dict(base_data)
            test_data["existing_emis"] = candidate_emis
            test_eval = policy_engine.evaluate(test_data)

            if test_eval["recommendation_code"] == "likely_approved":
                desc = plain_english_translator.format_counterfactual(
                    "emi_reduction", current_emis, candidate_emis
                )
                candidates.append({
                    "feature_name": "existing_emis",
                    "current_value": current_emis,
                    "suggested_value": candidate_emis,
                    "change_description": desc,
                    "actionability": "Medium: clear active loan debt",
                    "is_faithful": True,
                    "direction": "decrease",
                    "cost": reduction_ratio
                })
                break

    # 4. Actionable Search: Add verified co-applicant income
    if current_income > 0:
        for inc_ratio in [1.15, 1.25, 1.35, 1.50]:
            candidate_income = round((current_income * inc_ratio) / 5000) * 5000
            test_data = dict(base_data)
            test_data["monthly_income"] = candidate_income
            test_eval = policy_engine.evaluate(test_data)

            if test_eval["recommendation_code"] == "likely_approved":
                desc = plain_english_translator.format_counterfactual(
                    "income_coapplicant", current_income, candidate_income
                )
                candidates.append({
                    "feature_name": "monthly_income",
                    "current_value": current_income,
                    "suggested_value": candidate_income,
                    "change_description": desc,
                    "actionability": "Low: add co-applicant or secondary income",
                    "is_faithful": True,
                    "direction": "increase",
                    "cost": inc_ratio - 1.0
                })
                break

    # Sort by lowest intervention cost and pick top 3 distinct features
    candidates.sort(key=lambda c: c["cost"])
    seen_features = set()
    unique_candidates = []
    for c in candidates:
        if c["feature_name"] not in seen_features:
            seen_features.add(c["feature_name"])
            unique_candidates.append(c)
        if len(unique_candidates) >= 3:
            break

    return unique_candidates
