import re
from typing import Dict, Any, List
import yaml
from backend.core.config import settings

FORBIDDEN_JARGON = [
    "shap", "logit", "coefficient", "feature", "vector", "hyperplane",
    "stochastic", "gradient", "log-odds", "loss function", "adwin", "river"
]

def count_syllables(word: str) -> int:
    """Estimates syllable count of an English word."""
    w = word.lower().strip()
    if len(w) <= 3:
        return 1
    # Remove silent e at the end
    w = re.sub(r'(?:[^laeiouy]|ed|es|e)$', '', w)
    w = re.sub(r'^y', '', w)
    syllables = len(re.findall(r'[aeiouy]{1,2}', w))
    return max(1, syllables)

def calculate_flesch_kincaid_grade(text: str) -> float:
    """Computes Flesch-Kincaid Grade Level."""
    sentences = [s.strip() for s in re.split(r'[\.\?\!]+', text) if len(s.strip()) > 0]
    words = [w for w in re.findall(r'\b[A-Za-z]+\b', text)]
    if not sentences or not words:
        return 5.0

    total_sentences = len(sentences)
    total_words = len(words)
    total_syllables = sum(count_syllables(w) for w in words)

    grade = 0.39 * (total_words / total_sentences) + 11.8 * (total_syllables / total_words) - 15.59
    return round(max(1.0, grade), 1)

class PlainEnglishTranslator:
    def __init__(self):
        with open(settings.PHRASE_DICTIONARY_FILE, "r", encoding="utf-8") as f:
            self.dict = yaml.safe_load(f)

    def translate_factors(self, app_data: Dict[str, Any], ratios: Dict[str, Any]) -> List[str]:
        """Translates top numerical factors into Grade 6-8 plain-English sentences."""
        reasons_cfg = self.dict.get("reasons", {})
        sentences = []

        foir_pct = round(ratios.get("foir", 0.0) * 100, 1)
        if foir_pct <= 35:
            sentences.append(reasons_cfg["foir_low"].format(foir=foir_pct))
        elif foir_pct <= 48:
            sentences.append(reasons_cfg["foir_moderate"].format(foir=foir_pct))
        else:
            sentences.append(reasons_cfg["foir_high"].format(foir=foir_pct))

        lti = round(ratios.get("lti", 0.0), 1)
        if lti <= 2.5:
            sentences.append(reasons_cfg["lti_healthy"].format(lti=lti))
        else:
            sentences.append(reasons_cfg["lti_high"].format(lti=lti))

        emp_months = int(app_data.get("employment_duration_months", 12))
        if emp_months >= 18:
            sentences.append(reasons_cfg["employment_strong"].format(months=emp_months))
        else:
            sentences.append(reasons_cfg["employment_short"].format(months=emp_months))

        consistency = float(ratios.get("consistency_score", 1.0))
        if consistency >= 0.85:
            sentences.append(reasons_cfg["doc_match"])
        else:
            sentences.append(reasons_cfg["doc_mismatch"])

        # Validate no forbidden jargon
        cleaned = []
        for s in sentences:
            s_clean = s
            for word in FORBIDDEN_JARGON:
                s_clean = re.sub(rf"\b{word}\b", "factor", s_clean, flags=re.IGNORECASE)
            cleaned.append(s_clean)

        return cleaned

    def format_counterfactual(self, cf_type: str, current_val: Any, suggested_val: Any) -> str:
        cf_cfg = self.dict.get("counterfactuals", {})
        if cf_type == "amount_reduction":
            return cf_cfg["amount_reduction"].format(current_val=current_val, suggested_val=suggested_val)
        elif cf_type == "tenure_extension":
            return cf_cfg["tenure_extension"].format(current_val=current_val, suggested_val=suggested_val)
        elif cf_type == "emi_reduction":
            reduction = current_val - suggested_val
            return cf_cfg["emi_reduction"].format(reduction=reduction)
        elif cf_type == "income_coapplicant":
            return cf_cfg["income_coapplicant"].format(suggested_val=suggested_val)
        return f"If {cf_type} were adjusted to {suggested_val}, your loan would likely be approved."

plain_english_translator = PlainEnglishTranslator()
