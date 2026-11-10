import io
import uuid
import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from fastapi.testclient import TestClient
from backend.api.app import app
from backend.db.session import init_db
from backend.services.ocr.extractor import (
    classify_document_type,
    parse_document_text,
    mask_identifier,
    extract_from_pdf,
)

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

def get_applicant_token() -> str:
    """Register a fresh applicant and return their JWT (applicants self-register)."""
    email = f"docintake_{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post("/api/auth/register", json={
        "full_name": "Document Intake Tester",
        "email": email,
        "phone": "9876500000",
        "password": "DocIntake123"
    })
    assert reg.status_code in (200, 201), reg.text
    res = client.post("/api/auth/login", json={
        "email": email,
        "password": "DocIntake123",
        "expected_role": "applicant"
    })
    assert res.status_code == 200, res.text
    return res.json()["access_token"]

def make_salary_pdf(name: str, employer: str, basic: float, hra: float, gross: float, net: float) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(100, 750, f"Employer: {employer}")
    c.drawString(100, 730, f"PAY SLIP / SALARY CERTIFICATE FOR MARCH 2026")
    c.drawString(100, 710, f"Employee Name: {name}")
    c.drawString(100, 690, f"Designation: Lead Architect")
    c.drawString(100, 670, f"Basic Pay: Rs. {basic:,.0f}")
    c.drawString(100, 650, f"House Rent Allowance (HRA): Rs. {hra:,.0f}")
    c.drawString(100, 630, f"Gross Salary: Rs. {gross:,.0f}")
    c.drawString(100, 610, f"Provident Fund (PF): Rs. 6,000")
    c.drawString(100, 590, f"Total Deductions: Rs. {gross - net:,.0f}")
    c.drawString(100, 570, f"Net Salary: Rs. {net:,.0f}")
    c.save()
    return buf.getvalue()

def make_bank_pdf(holder: str, bank: str, balance: float) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(100, 750, f"{bank} - ACCOUNT STATEMENT")
    c.drawString(100, 730, f"Account Holder: {holder}")
    c.drawString(100, 710, "Account Number: 123456789012")
    c.drawString(100, 690, "Statement Period: 01/01/2026 to 31/03/2026")
    c.drawString(100, 670, f"Opening Balance: Rs. 15,000")
    c.drawString(100, 650, f"Closing Balance: Rs. {balance:,.0f}")
    c.drawString(100, 630, "Transaction: SALARY CREDIT Rs. 75,000")
    c.drawString(100, 610, "Transaction: LOAN EMI DEBIT Rs. 12,500")
    c.save()
    return buf.getvalue()

def test_document_classification():
    salary_text = "SALARY SLIP FOR MARCH 2026. Basic Pay: Rs 40000. Gross Salary: Rs 85000. Net Salary: Rs 75000."
    bank_text = "HDFC BANK ACCOUNT STATEMENT Account Holder: Pooja Nair Closing Balance: Rs 150000 Total Debits: Rs 40000"
    pan_text = "INCOME TAX DEPARTMENT GOVT OF INDIA PERMANENT ACCOUNT NUMBER CARD ABCDE1234F"
    aadhaar_text = "GOVERNMENT OF INDIA UNIQUE IDENTIFICATION AUTHORITY OF INDIA Aadhaar No: 1234 5678 9012"

    assert classify_document_type(salary_text) == "salary_slip"
    assert classify_document_type(bank_text) == "bank_statement"
    assert classify_document_type(pan_text) == "pan_card"
    assert classify_document_type(aadhaar_text) == "aadhaar_card"

def test_masking_identifiers():
    assert mask_identifier("ABCDE1234F", "pan") == "ABCDE****F"
    assert mask_identifier("123456789012", "aadhaar") == "••••-••••-9012"
    assert mask_identifier("1234 5678 9012", "aadhaar") == "••••-••••-9012"
    masked_acc = mask_identifier("987654321098", 4)
    assert masked_acc.endswith("1098")
    assert "X" in masked_acc

def test_salary_slip_extraction():
    pdf_bytes = make_salary_pdf("Pooja Nair", "Innovatech Solutions Pvt Ltd", 45000, 20000, 85000, 75000)
    data = extract_from_pdf(pdf_bytes)

    assert data["extracted_name"] == "Pooja Nair"
    assert "Innovatech Solutions" in (data["employer_name"] or "")
    assert data["monthly_salary"] == 75000
    salary_det = data.get("salary_details", {})
    assert salary_det.get("basic_pay") == 45000
    assert salary_det.get("hra") == 20000
    assert salary_det.get("gross_salary") == 85000
    assert salary_det.get("net_salary") == 75000

def test_bank_statement_extraction():
    pdf_bytes = make_bank_pdf("Pooja Nair", "HDFC Bank", 145000)
    data = extract_from_pdf(pdf_bytes)

    assert data["document_type"] == "bank_statement"
    bank_det = data.get("bank_details", {})
    assert bank_det.get("account_holder_name") == "Pooja Nair"
    assert "HDFC Bank" in (bank_det.get("bank_name") or "")
    assert bank_det.get("closing_balance") == 145000
    assert bank_det.get("detected_monthly_emis") == 12500

def test_intake_upload_endpoint():
    token = get_applicant_token()
    pdf_bytes = make_salary_pdf("Ramesh Gupta", "Tata Motors Ltd", 50000, 25000, 95000, 85000)

    files = {"file": ("salary_slip.pdf", pdf_bytes, "application/pdf")}
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/documents/intake-upload", files=files, headers=headers)
    assert res.status_code == 200
    resp_data = res.json()
    assert resp_data["detected_category"] == "salary_slip"
    assert resp_data["confidence_score"] >= 0.70
    assert resp_data["extracted_data"]["monthly_salary"] == 85000
    assert resp_data["extracted_data"]["extracted_name"] == "Ramesh Gupta"

def test_analyze_intake_endpoint_missing_fields():
    token = get_applicant_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Pass a salary document: should extract name & monthly_income
    docs = [
        {
            "doc_id": "doc-01",
            "filename": "salary_slip.pdf",
            "detected_category": "salary_slip",
            "confidence_score": 0.95,
            "extracted_data": {
                "extracted_name": "Ramesh Gupta",
                "monthly_salary": 85000,
                "document_type": "salary_slip",
                "salary_details": {
                    "employee_name": "Ramesh Gupta",
                    "gross_salary": 95000,
                    "net_salary": 85000,
                }
            }
        }
    ]

    res = client.post("/api/documents/analyze-intake", json={"documents": docs}, headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["merged_fields"]["applicant_name"] == "Ramesh Gupta"
    assert data["merged_fields"]["monthly_income"] == 85000
    assert data["consistency_score"] == 1.0

    # Ensure missing_fields contains fields like age, requested_amount, tenure_months
    # but NOT monthly_income or applicant_name
    missing_keys = [f["field_key"] for f in data["missing_fields"]]
    assert "applicant_name" not in missing_keys
    assert "monthly_income" not in missing_keys
    assert "age" in missing_keys
    assert "requested_amount" in missing_keys
    assert "tenure_months" in missing_keys

def test_analyze_intake_conflict_detection():
    token = get_applicant_token()
    headers = {"Authorization": f"Bearer {token}"}

    docs = [
        {
            "doc_id": "doc-01",
            "filename": "salary_slip.pdf",
            "detected_category": "salary_slip",
            "confidence_score": 0.90,
            "extracted_data": {
                "extracted_name": "Ramesh Gupta",
                "monthly_salary": 85000,
                "document_type": "salary_slip"
            }
        },
        {
            "doc_id": "doc-02",
            "filename": "bank_statement.pdf",
            "detected_category": "bank_statement",
            "confidence_score": 0.85,
            "extracted_data": {
                "extracted_name": "Ramesh K Gupta",
                "monthly_salary": 65000,
                "document_type": "bank_statement"
            }
        }
    ]

    res = client.post("/api/documents/analyze-intake", json={"documents": docs}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["conflicts"]) > 0
    conflict_fields = [c["field"] for c in data["conflicts"]]
    assert "monthly_income" in conflict_fields
    assert data["consistency_score"] < 1.0

def test_document_intake_submission_pipeline():
    token = get_applicant_token()
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "applicant_name": "Sunita Verma",
        "contact_phone": "+91 91234 56789",
        "contact_email": "sunita.verma@example.com",
        "age": 32,
        "employment_type": "salaried",
        "employment_duration_months": 36,
        "monthly_income": 92000,
        "existing_emis": 5000,
        "requested_amount": 350000,
        "tenure_months": 36,
        "loan_purpose": "home_improvement",
        "dependents": 1,
        "residence_type": "owned",
        "credit_history_years": 4.5,
        "collateral_value": 0,
        "intake_mode": "document",
        "intake_transcript": "Document Intake — 2 document(s): salary_slip.pdf, bank_statement.pdf",
        "audit_consent": True,
        "audit_gender": "female",
        "audit_geography_tier": "tier1"
    }

    res = client.post("/api/intake/submit", json=payload, headers=headers)
    assert res.status_code == 200, f"Submission failed: {res.text}"
    data = res.json()
    assert data["applicant_name"] == "Sunita Verma"
    assert "application_id" in data
    assert data["recommendation"] in ["Likely to be approved", "Needs more review", "Unlikely to be approved right now"]

    # Verify that in officer portal, intake_mode is preserved
    app_id = data["application_id"]
    from backend.db.database import SessionLocal
    from backend.db.models import Application
    db = SessionLocal()
    saved = db.query(Application).filter(Application.id == app_id).first()
    db.close()
    assert saved is not None
    assert saved.intake_mode == "document"
