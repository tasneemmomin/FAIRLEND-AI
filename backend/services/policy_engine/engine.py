from pathlib import Path
from typing import Dict, Any, List, Tuple
import yaml
from backend.core.config import settings
from backend.services.policy_engine.rules import (
    calculate_estimated_emi,
    calculate_foir,
    calculate_lti,
    calculate_disposable_income
)

class PolicyEngine:
    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or settings.POLICY_RULES_FILE
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Policy configuration file not found at {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def reload(self):
        self.config = self._load_config()

    def evaluate(self, app_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates an application against hard rules and scorecard tiers.
        Returns recommendation, score, confidence, rule_hits, and reasons.
        """
        monthly_income = float(app_data.get("monthly_income", 0.0))
        requested_amount = float(app_data.get("requested_amount", 0.0))
        tenure_months = int(app_data.get("tenure_months", 12))
        existing_emis = float(app_data.get("existing_emis", 0.0))
        age = int(app_data.get("age", 25))
        emp_months = int(app_data.get("employment_duration_months", 12))
        credit_years = float(app_data.get("credit_history_years", 0.0))
        collateral_val = float(app_data.get("collateral_value", 0.0))
        consistency_score = float(app_data.get("consistency_score", 1.0))

        proposed_emi = calculate_estimated_emi(requested_amount, tenure_months)
        foir = calculate_foir(monthly_income, existing_emis, proposed_emi)
        lti = calculate_lti(requested_amount, monthly_income)
        disposable_income = calculate_disposable_income(monthly_income, existing_emis, proposed_emi)

        hard_rules = self.config.get("hard_rules", {})
        rule_hits = []
        hard_violations = []

        # Check hard rules
        if age < hard_rules.get("min_age", 18):
            hard_violations.append(f"Applicant age ({age}) is below minimum required age of {hard_rules.get('min_age')}.")
        if age > hard_rules.get("max_age", 70):
            hard_violations.append(f"Applicant age ({age}) exceeds maximum allowable age of {hard_rules.get('max_age')}.")
        if monthly_income < hard_rules.get("min_monthly_income", 10000):
            hard_violations.append(f"Monthly income (₹{monthly_income:,.0f}) is below minimum threshold of ₹{hard_rules.get('min_monthly_income', 10000):,.0f}.")
        if foir > hard_rules.get("max_foir", 0.60):
            hard_violations.append(f"Debt-to-income ratio ({foir*100:.1f}%) exceeds hard ceiling of {hard_rules.get('max_foir', 0.60)*100:.0f}%.")
        if consistency_score < hard_rules.get("min_consistency_score", 0.60):
            hard_violations.append(f"Document-declared income consistency score ({consistency_score*100:.0f}%) is below minimum standard of {hard_rules.get('min_consistency_score', 0.60)*100:.0f}%.")

        # Evaluate Scorecard Components
        components = self.config.get("components", {})
        total_score = 0
        score_reasons = []

        # 1. FOIR scoring
        foir_cfg = components.get("foir", {})
        foir_score = 0
        foir_reason = ""
        for tier in foir_cfg.get("tiers", []):
            if foir <= tier["max_val"]:
                foir_score = tier["score"]
                foir_reason = tier["reason"]
                break
        total_score += foir_score
        rule_hits.append({"component": "FOIR", "score": foir_score, "max_score": foir_cfg.get("weight", 30), "value": foir, "reason": foir_reason})
        score_reasons.append(foir_reason)

        # 2. Loan to Income scoring
        lti_cfg = components.get("loan_to_income", {})
        lti_score = 0
        lti_reason = ""
        for tier in lti_cfg.get("tiers", []):
            if lti <= tier["max_val"]:
                lti_score = tier["score"]
                lti_reason = tier["reason"]
                break
        total_score += lti_score
        rule_hits.append({"component": "LoanToIncome", "score": lti_score, "max_score": lti_cfg.get("weight", 20), "value": lti, "reason": lti_reason})
        score_reasons.append(lti_reason)

        # 3. Employment stability scoring
        emp_cfg = components.get("employment_stability", {})
        emp_score = 0
        emp_reason = ""
        for tier in emp_cfg.get("tiers", []):
            if emp_months >= tier["min_months"]:
                emp_score = tier["score"]
                emp_reason = tier["reason"]
                break
        total_score += emp_score
        rule_hits.append({"component": "EmploymentStability", "score": emp_score, "max_score": emp_cfg.get("weight", 15), "value": emp_months, "reason": emp_reason})
        score_reasons.append(emp_reason)

        # 4. Document consistency scoring
        doc_cfg = components.get("document_consistency", {})
        doc_score = 0
        doc_reason = ""
        for tier in doc_cfg.get("tiers", []):
            if consistency_score >= tier["min_val"]:
                doc_score = tier["score"]
                doc_reason = tier["reason"]
                break
        total_score += doc_score
        rule_hits.append({"component": "DocumentConsistency", "score": doc_score, "max_score": doc_cfg.get("weight", 15), "value": consistency_score, "reason": doc_reason})
        score_reasons.append(doc_reason)

        # 5. Credit history scoring
        ch_cfg = components.get("credit_history", {})
        ch_score = 0
        ch_reason = ""
        for tier in ch_cfg.get("tiers", []):
            if credit_years >= tier["min_years"]:
                ch_score = tier["score"]
                ch_reason = tier["reason"]
                break
        total_score += ch_score
        rule_hits.append({"component": "CreditHistory", "score": ch_score, "max_score": ch_cfg.get("weight", 10), "value": credit_years, "reason": ch_reason})
        score_reasons.append(ch_reason)

        # 6. Collateral scoring
        ltv = collateral_val / requested_amount if requested_amount > 0 else 0.0
        col_cfg = components.get("collateral_or_asset", {})
        col_score = 0
        col_reason = ""
        for tier in col_cfg.get("tiers", []):
            if ltv >= tier["min_ltv"]:
                col_score = tier["score"]
                col_reason = tier["reason"]
                break
        total_score += col_score
        rule_hits.append({"component": "Collateral", "score": col_score, "max_score": col_cfg.get("weight", 10), "value": round(ltv, 2), "reason": col_reason})
        score_reasons.append(col_reason)

        # Determine Recommendation
        thresholds = self.config.get("score_thresholds", {"approve_threshold": 70, "review_threshold": 45})
        
        if len(hard_violations) > 0:
            recommendation_code = "unlikely_approved"
            recommendation_label = "Unlikely to be approved right now"
            confidence = "High"
            final_reasons = hard_violations
        elif total_score >= thresholds["approve_threshold"]:
            recommendation_code = "likely_approved"
            recommendation_label = "Likely to be approved"
            confidence = "High" if total_score >= 85 else "Medium"
            final_reasons = score_reasons[:4]
        elif total_score >= thresholds["review_threshold"]:
            recommendation_code = "needs_review"
            recommendation_label = "Needs more review"
            confidence = "Medium"
            final_reasons = [r for r in score_reasons if "Moderate" in r or "Elevated" in r or "Short" in r or "Discrepancy" in r][:4] or score_reasons[:3]
        else:
            recommendation_code = "unlikely_approved"
            recommendation_label = "Unlikely to be approved right now"
            confidence = "Medium"
            final_reasons = [r for r in score_reasons if "High" in r or "Short" in r or "discrepancy" in r or "burden" in r][:4] or score_reasons[:3]

        return {
            "score": total_score,
            "max_score": 100,
            "foir": foir,
            "lti": lti,
            "proposed_emi": proposed_emi,
            "disposable_income": disposable_income,
            "consistency_score": consistency_score,
            "recommendation_code": recommendation_code,
            "recommendation_label": recommendation_label,
            "confidence": confidence,
            "hard_violations": hard_violations,
            "rule_hits": rule_hits,
            "reasons": final_reasons
        }

policy_engine = PolicyEngine()
