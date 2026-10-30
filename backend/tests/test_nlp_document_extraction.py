import io
import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from backend.services.ocr.extractor import extract_from_pdf, extract_from_image, parse_document_text
from backend.services.ocr.nlp_pipeline import (
    DocumentNLPExtractionPipeline,
    IntelligentNameExtractor,
    MathematicalValidator,
    DocumentSectionSegmenter
)

def make_corp_salary_slip_with_signatory(
    emp_name: str,
    signatory_name: str,
    employer: str,
    basic: float,
    hra: float,
    gross: float,
    deductions: float,
    net: float
) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(100, 750, f"{employer}")
    c.drawString(100, 730, "MONTHLY PAYSLIP - MARCH 2026")
    c.drawString(100, 700, f"Employee Name: {emp_name}")
    c.drawString(100, 680, "Employee ID: EMP-99214")
    c.drawString(100, 660, "Designation: Senior Software Engineer")
    c.drawString(100, 630, f"Basic Pay: Rs. {basic:,.0f}")
    c.drawString(100, 610, f"House Rent Allowance (HRA): Rs. {hra:,.0f}")
    c.drawString(100, 590, f"Gross Salary: Rs. {gross:,.0f}")
    c.drawString(100, 560, f"Total Deductions: Rs. {deductions:,.0f}")
    c.drawString(100, 540, f"Net Salary: Rs. {net:,.0f}")
    c.drawString(100, 480, "For and on behalf of the company:")
    c.drawString(100, 460, f"Authorized Signatory: {signatory_name}")
    c.drawString(100, 440, "HR & Operations Directorate")
    c.save()
    return buf.getvalue()

def make_govt_salary_certificate_with_ddo(
    emp_name: str,
    ddo_name: str,
    dept: str,
    basic: float,
    da: float,
    hra: float,
    gross: float,
    deductions: float,
    net: float
) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(100, 760, f"GOVERNMENT OF INDIA - {dept.upper()}")
    c.drawString(100, 740, "OFFICIAL SALARY CERTIFICATE")
    c.drawString(100, 710, f"Name of Employee: Shri {emp_name}")
    c.drawString(100, 690, "Cadre: Executive Engineer (Civil)")
    c.drawString(100, 670, "Staff ID: GOV-ENG-8812")
    c.drawString(100, 640, f"Basic Pay: Rs. {basic:,.0f}")
    c.drawString(100, 620, f"Dearness Allowance (DA): Rs. {da:,.0f}")
    c.drawString(100, 600, f"House Rent Allowance (HRA): Rs. {hra:,.0f}")
    c.drawString(100, 580, f"Gross Emoluments: Rs. {gross:,.0f}")
    c.drawString(100, 550, f"Total Deductions: Rs. {deductions:,.0f}")
    c.drawString(100, 530, f"Net Payable: Rs. {net:,.0f}")
    c.drawString(100, 460, f"Signature of Drawing & Disbursing Officer: {ddo_name}")
    c.drawString(100, 440, "Office Seal & Sanction Stamp")
    c.save()
    return buf.getvalue()

def make_bank_statement_with_emis(
    holder_name: str,
    bank_name: str,
    balance: float,
    salary_cr: float,
    emi_dr: float
) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(100, 750, f"{bank_name} - ACCOUNT STATEMENT")
    c.drawString(100, 730, f"Account Holder Name: {holder_name}")
    c.drawString(100, 710, "Account Number: 50100234567890")
    c.drawString(100, 690, "Period: 01/02/2026 to 28/02/2026")
    c.drawString(100, 660, f"Closing Balance: Rs. {balance:,.0f}")
    c.drawString(100, 630, f"28/02/2026 SALARY CREDIT FROM TCS LTD: Rs. {salary_cr:,.0f}")
    c.drawString(100, 600, f"05/02/2026 HDFC LOAN EMI DEBIT: Rs. {emi_dr:,.0f}")
    c.save()
    return buf.getvalue()

def test_nlp_applicant_name_vs_corporate_signatory():
    """
    Critical requirement: Distinguish applicant from authorized signatory/HR Director.
    Must extract 'Rahul Sharma', NOT 'Sunita Rao'.
    """
    pdf_bytes = make_corp_salary_slip_with_signatory(
        emp_name="Rahul Sharma",
        signatory_name="Sunita Rao",
        employer="Cognizant Technology Solutions",
        basic=50000,
        hra=25000,
        gross=90000,
        deductions=12000,
        net=78000
    )
    result = extract_from_pdf(pdf_bytes)

    # Evaluation
    actual_applicant = "Rahul Sharma"
    extracted_applicant = result["extracted_name"]
    signatories = result.get("signatories", [])

    print(f"\n[Test 1] Corp Pay Slip:")
    print(f"  Actual Applicant: {actual_applicant}")
    print(f"  Extracted Applicant: {extracted_applicant}")
    print(f"  Detected Signatories: {[s['name'] for s in signatories]}")

    assert extracted_applicant == actual_applicant, f"Expected {actual_applicant}, got {extracted_applicant}"
    assert any("Sunita Rao" in s["name"] for s in signatories), "Signatory Sunita Rao was not recognized as a signatory"

def test_nlp_applicant_name_vs_government_ddo():
    """
    Critical requirement: In government salary certificates, distinguish applicant from Drawing & Disbursing Officer.
    Must extract 'Manoj Kumar', NOT 'Shri R. K. Saxena'.
    """
    pdf_bytes = make_govt_salary_certificate_with_ddo(
        emp_name="Manoj Kumar",
        ddo_name="Shri R. K. Saxena",
        dept="Ministry of Railways",
        basic=56100,
        da=28050,
        hra=15147,
        gross=99297,
        deductions=14297,
        net=85000
    )
    result = extract_from_pdf(pdf_bytes)

    actual_applicant = "Manoj Kumar"
    extracted_applicant = result["extracted_name"]
    signatories = result.get("signatories", [])

    print(f"\n[Test 2] Govt Certificate:")
    print(f"  Actual Applicant: {actual_applicant}")
    print(f"  Extracted Applicant: {extracted_applicant}")
    print(f"  Detected Signatories/DDO: {[s['name'] for s in signatories]}")

    assert extracted_applicant == actual_applicant
    assert any("Saxena" in s["name"] for s in signatories)

def test_mathematical_consistency_validation_success():
    """
    Verification of arithmetic balance: Gross (90,000) - Deductions (12,000) = Net (78,000).
    Must mark math_validated = True.
    """
    pdf_bytes = make_corp_salary_slip_with_signatory(
        emp_name="Pooja Nair",
        signatory_name="Amit Patel",
        employer="Infosys Limited",
        basic=45000,
        hra=22000,
        gross=85000,
        deductions=10000,
        net=75000
    )
    result = extract_from_pdf(pdf_bytes)
    math_val = result.get("math_validation", {})

    print(f"\n[Test 3] Mathematical Validation (Balanced):")
    print(f"  Validation message: {math_val.get('message')}")
    print(f"  Validated: {math_val.get('math_validated')}")

    assert math_val.get("math_validated") is True
    assert math_val.get("discrepancy_flag") is False

def test_mathematical_consistency_discrepancy_detection():
    """
    If Gross - Deductions != Net, system must flag discrepancy and not mark verified.
    """
    # Gross 100,000, Deductions 10,000, but Net printed as 65,000 (discrepancy of 25,000)
    text = """
    EMPLOYER: ACME TECHNOLOGIES PVT LTD
    Employee Name: Vikram Mehta
    Gross Salary: Rs. 100,000
    Total Deductions: Rs. 10,000
    Net Salary: Rs. 65,000
    """
    result = parse_document_text(text)
    math_val = result.get("math_validation", {})

    print(f"\n[Test 4] Mathematical Discrepancy Detection:")
    print(f"  Validation message: {math_val.get('message')}")
    print(f"  Discrepancy flag: {math_val.get('discrepancy_flag')}")

    assert math_val.get("discrepancy_flag") is True
    assert math_val.get("math_validated") is False

def test_bank_statement_with_salary_and_emi():
    """
    Extracts Account Holder, Closing Balance, Salary credit, and Loan EMI debit.
    """
    pdf_bytes = make_bank_statement_with_emis(
        holder_name="Anita Sen",
        bank_name="HDFC Bank",
        balance=185000,
        salary_cr=85000,
        emi_dr=15000
    )
    result = extract_from_pdf(pdf_bytes)

    assert result["extracted_name"] == "Anita Sen"
    assert result["bank_details"]["bank_name"] == "HDFC Bank"
    assert result["bank_details"]["closing_balance"] == 185000
    assert result["bank_details"]["detected_salary_credits"] == 85000
    assert result["bank_details"]["detected_monthly_emis"] == 15000

def test_nlp_extraction_precision_recall_f1():
    """
    Field-level Precision, Recall, and F1-score evaluation across gold-standard annotations.
    """
    ground_truth_cases = [
        {
            "text": "ABC CORP PVT LTD\nEmployee Name: Aarti Iyer\nGross Salary: Rs. 95000\nTotal Deductions: Rs. 15000\nNet Salary: Rs. 80000\nAuthorized Signatory: Devendra Bose",
            "expected": {
                "applicant_name": "Aarti Iyer",
                "gross_salary": 95000.0,
                "total_deductions": 15000.0,
                "net_salary": 80000.0
            }
        },
        {
            "text": "MINISTRY OF COMMUNICATIONS\nName of Employee: Shri Sandeep Varma\nBasic Pay: Rs. 60000\nGross Salary: Rs. 105000\nTotal Deductions: Rs. 20000\nNet Salary: Rs. 85000\nSignature of Drawing & Disbursing Officer: K. K. Pillai",
            "expected": {
                "applicant_name": "Sandeep Varma",
                "basic_pay": 60000.0,
                "gross_salary": 105000.0,
                "net_salary": 85000.0
            }
        },
        {
            "text": "STATE BANK OF INDIA\nAccount Holder Name: Deepa Menon\nClosing Balance: Rs. 240000\nSALARY CREDIT Rs. 92000\nLOAN EMI DEBIT Rs. 14000",
            "expected": {
                "applicant_name": "Deepa Menon",
                "closing_balance": 240000.0,
                "existing_emis": 14000.0
            }
        }
    ]

    tp = 0
    fp = 0
    fn = 0

    print("\n[Precision / Recall / F1 Benchmark Evaluation]")
    for idx, case in enumerate(ground_truth_cases):
        res = parse_document_text(case["text"])
        flat = res["all_extracted_fields"]

        for field, exp_val in case["expected"].items():
            pred_val = flat.get(field)
            if pred_val == exp_val:
                tp += 1
                status = "CORRECT"
            elif pred_val is None:
                fn += 1
                status = "MISSED (FN)"
            else:
                fp += 1
                status = f"INCORRECT (FP: got {pred_val})"

            print(f"  Case {idx+1} | Field: {field:<16} | Expected: {str(exp_val):<15} | Predicted: {str(pred_val):<15} | {status}")

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    print(f"\nBenchmark Results: Precision = {precision*100:.1f}%, Recall = {recall*100:.1f}%, F1 = {f1*100:.1f}%")
    assert precision >= 0.90, f"Precision below 90%: {precision}"
    assert recall >= 0.90, f"Recall below 90%: {recall}"
    assert f1 >= 0.90, f"F1-score below 90%: {f1}"

