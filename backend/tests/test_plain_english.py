import pytest
from backend.services.plain_english.translator import (
    plain_english_translator,
    calculate_flesch_kincaid_grade,
    FORBIDDEN_JARGON
)

def test_plain_english_readability_and_jargon_absence():
    app_data = {
        "monthly_income": 60000.0,
        "requested_amount": 250000.0,
        "employment_duration_months": 24,
    }
    ratios = {
        "foir": 0.32,
        "lti": 2.1,
        "consistency_score": 0.95
    }

    reasons = plain_english_translator.translate_factors(app_data, ratios)
    assert len(reasons) >= 3

    full_text = " ".join(reasons)

    # 1. Target Reading Level: Flesch-Kincaid Grade 6 to 8
    grade = calculate_flesch_kincaid_grade(full_text)
    assert grade <= 8.5, f"Reading grade level {grade} is too high for non-technical borrower"

    # 2. Strict Jargon Prohibition
    for forbidden in FORBIDDEN_JARGON:
        assert forbidden not in full_text.lower(), f"Forbidden technical jargon '{forbidden}' detected in applicant text"

def test_counterfactual_sentence_formatting():
    desc_amt = plain_english_translator.format_counterfactual("amount_reduction", 300000, 240000)
    assert "₹240,000" in desc_amt
    assert "₹300,000" in desc_amt
    assert "likely be approved" in desc_amt

    grade = calculate_flesch_kincaid_grade(desc_amt)
    assert grade <= 8.5
