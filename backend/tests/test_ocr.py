import io
import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from backend.services.ocr.extractor import extract_from_pdf
from backend.services.ocr.consistency import calculate_consistency

def create_sample_salary_pdf(name: str, employer: str, net_salary: float) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(100, 750, f"Employer: {employer}")
    c.drawString(100, 730, f"Employee Name: {name}")
    c.drawString(100, 710, "Designation: Software Engineer")
    c.drawString(100, 690, f"Gross Salary: Rs. {net_salary + 8000:,.0f}")
    c.drawString(100, 670, "Total Deductions: Rs. 8,000")
    c.drawString(100, 650, f"Net Salary: Rs. {net_salary:,.0f}")
    c.save()
    return buf.getvalue()

def test_pdf_extraction():
    pdf_bytes = create_sample_salary_pdf("Pooja Nair", "TCS Global Tech", 72000.0)
    extracted = extract_from_pdf(pdf_bytes)

    assert extracted["extracted_name"] == "Pooja Nair"
    assert "TCS Global Tech" in (extracted["employer_name"] or "")
    assert extracted["monthly_salary"] is not None
    assert extracted["monthly_salary"] >= 72000.0

def test_consistency_scoring():
    extracted = {"monthly_salary": 72000.0, "extracted_name": "Pooja Nair"}
    
    # 1. Matching declared income
    score, flags = calculate_consistency({"monthly_income": 72000.0, "applicant_name": "Pooja Nair"}, extracted)
    assert score == 1.0
    assert len(flags) == 0

    # 2. Minor discrepancy
    score_minor, flags_minor = calculate_consistency({"monthly_income": 80000.0, "applicant_name": "Pooja Nair"}, extracted)
    assert 0.80 <= score_minor <= 1.0

    # 3. Major discrepancy (e.g. declared 150k vs verified 72k)
    score_major, flags_major = calculate_consistency({"monthly_income": 150000.0, "applicant_name": "Pooja Nair"}, extracted)
    assert score_major < 0.70
    assert len(flags_major) > 0
    assert flags_major[0]["type"] == "INCOME_MISMATCH"
