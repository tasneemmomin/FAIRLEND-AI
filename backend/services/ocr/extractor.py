import re
import io
from datetime import date
from typing import Dict, Any, Optional, List, Tuple
import pdfplumber
from PIL import Image

# Known major Indian banks
INDIAN_BANKS = [
    "State Bank of India", "SBI", "HDFC Bank", "HDFC", "ICICI Bank", "ICICI",
    "Axis Bank", "Punjab National Bank", "PNB", "Bank of Baroda", "BOB",
    "Kotak Mahindra Bank", "Kotak", "Canara Bank", "Union Bank of India",
    "IndusInd Bank", "Bank of India", "IDFC FIRST Bank", "Yes Bank", "Federal Bank"
]

def _clean_currency(raw: str) -> Optional[float]:
    """Clean Indian currency string (handles commas, Rs, INR, decimals)."""
    cleaned = re.sub(r"[^\d\.]", "", raw.replace(",", "").strip())
    try:
        val = float(cleaned)
        return val if val >= 0 else None
    except ValueError:
        return None


def _clean_currency_signed(raw: str) -> Optional[float]:
    """Like _clean_currency, but a trailing 'Dr'/debit marker makes the value negative.
    Real Indian statements annotate balances as '45,000.00 Cr' / '1,500.00 Dr'.
    """
    suffix = raw.strip().lower()
    val = _clean_currency(raw)
    if val is None:
        return None
    # Only treat the trailing token after the digits as the sign marker.
    tail = re.search(r"(Cr|Dr)\s*$", raw.strip(), re.IGNORECASE)
    if tail and tail.group(1).lower() == "dr":
        return -val
    return val

def _extract_number(pattern: str, text: str) -> Optional[float]:
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return _clean_currency(match.group(1))
    return None

def _extract_string(pattern: str, text: str) -> Optional[str]:
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

def mask_identifier(number_str: str, mode_or_suffix_len: any = 4) -> str:
    """Mask account or identity numbers (e.g. XXXX-XXXX-1234 or ABCDE****F).
    Supports either integer suffix length or doc_type string ('pan', 'aadhaar', 'account').
    """
    cleaned = re.sub(r"[\s\-]", "", number_str)
    
    if isinstance(mode_or_suffix_len, str):
        mode = mode_or_suffix_len.lower()
        if mode in ("pan", "pan_card") and len(cleaned) == 10:
            # Mask middle 4 digits of PAN: ABCDE****F
            return f"{cleaned[:5]}****{cleaned[-1]}"
        elif mode in ("aadhaar", "aadhaar_card") and len(cleaned) == 12:
            # UIDAI standard: first 8 digits masked, last 4 visible
            return f"••••-••••-{cleaned[-4:]}"
        elif mode in ("account", "bank_account", "account_number"):
            visible_suffix_len = 4
        else:
            visible_suffix_len = 4
    else:
        visible_suffix_len = int(mode_or_suffix_len)

    if len(cleaned) <= visible_suffix_len:
        return "****" + cleaned
    masked = "X" * (len(cleaned) - visible_suffix_len) + cleaned[-visible_suffix_len:]
    # Format in groups of 4 if 12 or 16 digits
    if len(cleaned) == 12:
        return f"{masked[:4]}-{masked[4:8]}-{masked[8:]}"
    elif len(cleaned) == 16:
        return f"{masked[:4]}-{masked[4:8]}-{masked[8:12]}-{masked[12:]}"
    return masked

def classify_document_type(text: str) -> str:
    """Intelligently detects document category from textual signatures."""
    t = text.lower()
    
    # 1. PAN Card
    if re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", text) or ("income tax department" in t and "permanent account number" in t):
        return "pan_card"
    
    # 2. Aadhaar Card
    if "unique identification authority" in t or "uidai" in t or "aadhaar" in t or re.search(r"\b\d{4}\s\d{4}\s\d{4}\b", text):
        return "aadhaar_card"
    
    # 3. Bank Statement
    bank_kw = ["bank statement", "account statement", "opening balance", "closing balance", "withdrawal", "deposit", "ifsc", "cheque no", "cr/dr", "running balance"]
    if sum(1 for kw in bank_kw if kw in t) >= 2 or any(b.lower() in t for b in ["hdfc bank", "icici bank", "state bank of india", "axis bank"]):
        return "bank_statement"
    
    # 4. Salary Slip / Certificate
    sal_kw = ["salary slip", "pay slip", "payslip", "salary certificate", "basic pay", "dearness allowance", "gross salary", "net salary", "net pay", "deductions", "provident fund", "pf no", "employee no"]
    if sum(1 for kw in sal_kw if kw in t) >= 2 or "salary" in t:
        return "salary_slip"
    
    return "other_financial"

def extract_from_pdf(pdf_bytes: bytes) -> Dict[str, Any]:
    """Extracts text, tables, and structured financial entities from digital PDF documents."""
    text_content = ""
    tables_content = []
    
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_content += t + "\n"
                tables = page.extract_tables()
                if tables:
                    tables_content.extend(tables)
    except Exception as e:
        # Fallback if pdfplumber encounters an unusual PDF stream
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                text_content += (page.extract_text() or "") + "\n"
        except Exception:
            pass

    return parse_document_text(text_content, tables_content)

def _run_windows_native_ocr(image_bytes: bytes) -> str:
    """Uses Windows 10/11 native WinRT OCR engine via PowerShell when Tesseract is offline/uninstalled."""
    import tempfile
    import subprocess
    import os

    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = os.path.abspath(tmp.name)

        ps_script = f"""
        Add-Type -AssemblyName System.Runtime.WindowsRuntime
        $asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {{ $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }}
        function Await-Async($asyncOp, $type) {{
            $asTask = $asTaskGeneric.MakeGenericMethod($type)
            $netTask = $asTask.Invoke($null, @($asyncOp))
            $netTask.Wait()
            return $netTask.Result
        }}
        [Windows.Globalization.Language,Windows.Foundation.Globalization,ContentType=WindowsRuntime] | Out-Null
        [Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime] | Out-Null
        [Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime] | Out-Null
        [Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime] | Out-Null

        $file = Await-Async ([Windows.Storage.StorageFile]::GetFileFromPathAsync('{tmp_path}')) ([Windows.Storage.StorageFile])
        $stream = Await-Async ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
        $decoder = Await-Async ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap = Await-Async ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

        $lang = [Windows.Globalization.Language]::new('en-US')
        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
        $ocrResult = Await-Async ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])

        foreach ($line in $ocrResult.Lines) {{
            Write-Output $line.Text
        }}
        """
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True, timeout=25)
        return res.stdout.strip()
    except Exception:
        return ""
    finally:
        try:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

def extract_from_image(image_bytes: bytes) -> Dict[str, Any]:
    """Extracts text from images using enhanced image preprocessing (grayscale, contrast, sharpening) + OCR (Tesseract / Windows Media OCR)."""
    text_content = ""
    try:
        import pytesseract
        from PIL import ImageEnhance, ImageFilter
        orig_img = Image.open(io.BytesIO(image_bytes))
        
        # 1. Grayscale & Contrast enhancement
        gray = orig_img.convert("L")
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(1.7)
        sharpened = enhanced.filter(ImageFilter.SHARPEN)
        
        text_content = pytesseract.image_to_string(sharpened)
        
        # Fallback to RGB if grayscale produced very little text
        if len(text_content.strip()) < 30:
            rgb_img = orig_img.convert("RGB")
            alt = pytesseract.image_to_string(rgb_img)
            if len(alt.strip()) > len(text_content.strip()):
                text_content = alt
    except Exception:
        text_content = ""

    # Windows native OCR fallback if Tesseract is uninstalled or produced insufficient text
    if len(text_content.strip()) < 30:
        win_text = _run_windows_native_ocr(image_bytes)
        if len(win_text.strip()) > len(text_content.strip()):
            text_content = win_text

    return parse_document_text(text_content, [])

def parse_document_text(text: str, tables: list = None) -> Dict[str, Any]:
    """
    Intelligent NLP & NER entity extraction engine supporting:
    - Multi-entity context disambiguation (Applicant vs Signatory vs DDO vs Bank Holder)
    - Corporate & Government Salary Certificates (Basic, Grade Pay, DA, HRA, Gross, PF, NPS, PT, Deductions, Net)
    - Mathematical consistency checks (Gross - Deductions == Net)
    - Bank Statements (Account Holder, Bank, Masked Account, Balances, Salary Credits, EMIs)
    - Identity Documents (PAN Card, Aadhaar Card with masked identifiers)
    - Complete evidence audit trail for every extracted field
    """
    tables = tables or []
    doc_type = classify_document_type(text)

    # 1. Run Master NLP Pipeline for Sectioning, NER, Name Disambiguation & Math Check
    from backend.services.ocr.nlp_pipeline import DocumentNLPExtractionPipeline
    nlp_result = DocumentNLPExtractionPipeline.process_text(text, doc_filename="document", doc_type=doc_type)

    # Initialize structured data dictionary
    field_confidence: Dict[str, str] = {}
    
    # -------------------------------------------------------------------------
    # 1. Salary Slip / Salary Certificate Entity Extraction
    # -------------------------------------------------------------------------
    salary_details: Dict[str, Any] = {
        "employee_name": nlp_result.get("extracted_name"),
        "employer_name": nlp_result.get("employer_name"),
        "employee_id": None,
        "designation": None,
        "salary_month": None,
        "basic_pay": None,
        "grade_pay": None,
        "dearness_allowance": None,
        "hra": None,
        "other_allowances": None,
        "gross_salary": None,
        "provident_fund": None,
        "nps": None,
        "professional_tax": None,
        "income_tax": None,
        "insurance": None,
        "other_deductions": None,
        "total_deductions": None,
        "net_salary": None
    }

    # Populate from NLP result if available
    nlp_sal = nlp_result.get("salary_details") or {}
    for k, v in nlp_sal.items():
        if v is not None and k in salary_details:
            salary_details[k] = v
            field_confidence[k] = "high"

    # Employee Name (only if not already resolved by NLP pipeline)
    if not salary_details["employee_name"]:
        name_patterns = [
            r"Employee\s+Name\s*[:\-]\s*([A-Za-z\s\.\,\(\)]+)",
            r"Name\s+of\s+Employee\s*[:\-]\s*([A-Za-z\s\.\,\(\)]+)",
            r"(?:Shri|Smt\.|Dr\.|Mr\.|Ms\.)\s+([A-Za-z\s\.]+)",
            r"Name\s*[:\-]\s*([A-Za-z\s\.]+)",
            r"Account\s+Holder\s*[:\-]\s*([A-Za-z\s\.]+)"
        ]
        for p in name_patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                clean_n = m.group(1).split("\n")[0].split("/")[0].strip()
                # Remove title prefixes if present
                clean_n = re.sub(r"^(Shri|Smt\.|Dr\.|Mr\.|Ms\.)\s+", "", clean_n, flags=re.I).strip()
                if 2 <= len(clean_n) <= 60 and not any(kw in clean_n.lower() for kw in [
                    "salary", "bank", "statement", "month", "account", "pvt", "ltd",
                    "shikshan", "prasarak", "mandal", "sanstha", "school", "college"
                ]):
                    salary_details["employee_name"] = clean_n
                    field_confidence["employee_name"] = "high"
                    break

    # Employer / Organization Name
    emp_patterns = [
        r"(?:Company(?:\s+Name)?|Employer|Organization|Ministry|Department)\s*[:\-]\s*([A-Za-z0-9\s\,\.\-\&]+)",
        r"Account\s+at\s*[:\-]\s*([A-Za-z0-9\s\,\.\-]+)"
    ]
    for p in emp_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            clean_emp = m.group(1).split("\n")[0].strip()
            if 3 <= len(clean_emp) <= 80:
                salary_details["employer_name"] = clean_emp
                field_confidence["employer_name"] = "high"
                break
    
    # If employer not found via pattern, check header lines
    if not salary_details["employer_name"] and doc_type not in ("pan_card", "aadhaar_card"):
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        for ln in lines[:4]:
            if any(kw in ln.lower() for kw in ["ltd", "limited", "technologies", "tech", "ministry", "services", "corporation", "govt", "solutions"]):
                salary_details["employer_name"] = ln[:70]
                field_confidence["employer_name"] = "medium"
                break

    # Clean up accidental employer matches on identity documents
    if doc_type in ("pan_card", "aadhaar_card") and salary_details["employer_name"]:
        if any(kw in salary_details["employer_name"].lower() for kw in ["income tax", "govt", "india", "uidai", "identification"]):
            salary_details["employer_name"] = None

    # Employee ID
    emp_id = _extract_string(r"(?:Employee\s+ID|Emp(?:\.|\s+)?(?:Code|ID|No)|Staff\s+No|Personnel\s+No)\s*[:\-]\s*([A-Za-z0-9\-\_]+)", text)
    if emp_id:
        salary_details["employee_id"] = emp_id
        field_confidence["employee_id"] = "high"

    # Designation
    desig = _extract_string(r"(?:Designation|Post|Role|Cadre)\s*[:\-]\s*([A-Za-z0-9\s\,\.\-]+)", text)
    if desig:
        clean_d = desig.split("\n")[0].strip()
        if len(clean_d) <= 60:
            salary_details["designation"] = clean_d
            field_confidence["designation"] = "high"

    # Salary Month & Year
    sal_month = _extract_string(r"(?:Salary\s+for\s+(?:the\s+month\s+of\s+)?|Month\s*(?:&|and)?\s*Year\s*[:\-]?\s*|Pay\s+Period\s*[:\-]?\s*)([A-Za-z]+[\s\-]+20\d\d|\d{1,2}[\/\-]\d{4}|[A-Za-z]{3,9}\s*\-?\s*\d{2,4})", text)
    if sal_month:
        salary_details["salary_month"] = sal_month.split("\n")[0].strip()
        field_confidence["salary_month"] = "high"

    # Earnings items (preserving values already extracted by NLP pipeline)
    if not salary_details.get("basic_pay"):
        salary_details["basic_pay"] = _extract_number(r"(?:Basic\s+(?:Pay|Salary)(?:\s*\([A-Za-z]+\))?)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", text)
        if salary_details["basic_pay"]:
            field_confidence["basic_pay"] = "high"

    if not salary_details.get("grade_pay"):
        salary_details["grade_pay"] = _extract_number(r"(?:Grade\s+Pay(?:\s*\([A-Za-z]+\))?)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", text)
        if salary_details["grade_pay"]:
            field_confidence["grade_pay"] = "high"

    if not salary_details.get("dearness_allowance"):
        salary_details["dearness_allowance"] = _extract_number(r"(?:Dearness\s+Allowance(?:\s*\([A-Za-z]+\))?|D\.?A\.?)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", text)
        if salary_details["dearness_allowance"]:
            field_confidence["dearness_allowance"] = "high"

    if not salary_details.get("hra"):
        salary_details["hra"] = _extract_number(r"(?:House\s+Rent\s+Allowance(?:\s*\([A-Za-z]+\))?|H\.?R\.?A\.?)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", text)
        if salary_details["hra"]:
            field_confidence["hra"] = "high"

    if not salary_details.get("other_allowances"):
        salary_details["other_allowances"] = _extract_number(r"(?:Transport|Conveyance|Medical|Special|Other)\s+Allowance(?:\s*\([A-Za-z]+\))?\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", text)

    # Gross Salary
    if not salary_details.get("gross_salary"):
        gross_val = _extract_number(r"(?:Total\s+Gross\s+Salary|Gross\s+(?:Salary|Pay|Earnings|Emoluments)|Total\s+Earnings)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", text)
        if gross_val:
            salary_details["gross_salary"] = gross_val
            field_confidence["gross_salary"] = "high"

    # Deductions
    if not salary_details.get("provident_fund"):
        salary_details["provident_fund"] = _extract_number(r"(?:Provident\s+Fund(?:\s*\([A-Za-z]+\))?|G\.?P\.?F\.?|E\.?P\.?F\.?|P\.?F\.?)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", text)
    if not salary_details.get("nps"):
        salary_details["nps"] = _extract_number(r"(?:N\.?P\.?S\.?|National\s+Pension)(?:\s*(?:Contribution|Ded\.?))?(?:\s*\([A-Za-z]+\))?\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", text)
    if not salary_details.get("professional_tax"):
        salary_details["professional_tax"] = _extract_number(r"(?:Professional\s+Tax(?:\s*\([A-Za-z]+\))?|P\.?T\.?)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", text)
    if not salary_details.get("income_tax"):
        salary_details["income_tax"] = _extract_number(r"(?:Income\s+Tax(?:\s*\([A-Za-z]+\))?|T\.?D\.?S\.?|I\.?T\.?)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", text)
    if not salary_details.get("insurance"):
        salary_details["insurance"] = _extract_number(r"(?:Insurance(?:\s*\([A-Za-z]+\))?|LIC|G\.?I\.?S\.?)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", text)
    if not salary_details.get("total_deductions"):
        salary_details["total_deductions"] = _extract_number(r"(?:Total\s+Deductions?)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", text)

    # Net Salary / Take-Home Pay
    if not salary_details.get("net_salary"):
        net_val = _extract_number(r"(?:Net\s+(?:Salary(?:\s+Payable)?|Pay(?:able)?|Amount)|Take\s+Home\s+Pay)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", text)
        if net_val:
            salary_details["net_salary"] = net_val
            field_confidence["net_salary"] = "high"

    # If net salary was not explicitly labeled, check tables
    if not salary_details["net_salary"] and tables:
        for tbl in tables:
            for row in tbl:
                row_str = " ".join([str(c) for c in row if c])
                if any(w in row_str.lower() for w in ["net pay", "net salary", "take home", "amount paid"]):
                    val = _clean_currency(row_str)
                    if val and val > 1000:
                        salary_details["net_salary"] = val
                        field_confidence["net_salary"] = "medium"
                        break
            if salary_details["net_salary"]:
                break

    # If Net is still None but Gross and Total Deductions are present, calculate Net
    if not salary_details["net_salary"] and salary_details["gross_salary"] and salary_details["total_deductions"]:
        calc_net = salary_details["gross_salary"] - salary_details["total_deductions"]
        if calc_net > 0:
            salary_details["net_salary"] = calc_net
            field_confidence["net_salary"] = "calculated"

    # Effective monthly salary for credit scoring (Net preferred over Gross)
    monthly_salary = salary_details["net_salary"] or salary_details["gross_salary"]

    # -------------------------------------------------------------------------
    # 2. Bank Statement Entity Extraction
    # -------------------------------------------------------------------------
    bank_details: Dict[str, Any] = {
        "account_holder_name": salary_details["employee_name"],
        "bank_name": None,
        "account_number_masked": None,
        "statement_period": None,
        "opening_balance": None,
        "closing_balance": None,
        "total_credits": None,
        "total_debits": None,
        "detected_salary_credits": None,
        "detected_monthly_emis": None
    }

    # Bank Name Detection
    for b in INDIAN_BANKS:
        if re.search(r"\b" + re.escape(b) + r"\b", text, re.IGNORECASE):
            bank_details["bank_name"] = b
            field_confidence["bank_name"] = "high"
            break

    # Account Number
    acct_m = re.search(r"(?:Account\s+(?:No|Number)|A\/C(?:\s+No)?)\s*[:\-]?\s*([X\*\d\s\-]{8,22})", text, re.IGNORECASE)
    if acct_m:
        raw_acct = acct_m.group(1).strip()
        bank_details["account_number_masked"] = mask_identifier(raw_acct)
        field_confidence["account_number_masked"] = "high"

    # Balances — handle both "label: value" text layouts and real-world suffixes
    # like "45,000.00 Cr" / "12,000.00 Dr" (negative). If the labels are absent
    # (table-only statement PDFs), fall back to the Balance column row values.
    _NUM_CRDR = r"([\d\,]+(?:\.\d{1,2})?)[\s\.]?\s*(Cr|Dr|CR|DR)?\.?"

    def labeled_value(label_variants: List[str]) -> Optional[float]:
        # Gap is confined to the SAME line and cannot contain digits or dashes,
        # so a table header like "Closing Balance" followed by a newline + a
        # transaction row ("01-04-2026 ...") can never be mistaken for a value.
        for lbl in label_variants:
            pat = (r"(?:" + lbl + r")[^\n\r0-9\-]{0,16}(?:(?:Rs\.?|INR|\u20B9)\s*)?" + _NUM_CRDR)
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                marker = (m.group(2) or "").strip()
                val = _clean_currency_signed(f"{m.group(1)} {marker}".strip())
                if val is not None:
                    return val
        return None

    def line_last_amount(label_re: str) -> Optional[float]:
        """Amount from rows like '01-04-2026  OPN BAL  ... 185,000.00' where the
        balance is the LAST grouped/decimal monetary token on the line."""
        for ln in text.splitlines():
            if re.search(label_re, ln, re.IGNORECASE):
                toks = re.findall(
                    r"(?<![\d.,])(?:\d{1,3}(?:\,\d{2,3})+(?:\.\d{1,2})?|\d+\.\d{2})(?![\d.,])", ln)
                for tok in reversed(toks):
                    v = _clean_currency_signed(tok)
                    if v is not None:
                        return v
        return None

    opening_labeled = labeled_value([r"Opening\s+Balance", r"Opening\s+Bal\.?", r"BAL\.?\s+B\/F", r"BALANCE\s+B\/F"])
    closing_labeled = labeled_value([r"Closing\s+Balance", r"Closing\s+Bal\.?", r"Closing\s+\w{1,6}\s*Balance", r"CLBAL", r"Available\s+Balance", r"Ending\s+Balance", r"CLOSING\s+ABMBAL"])
    bank_details["opening_balance"] = opening_labeled
    bank_details["closing_balance"] = closing_labeled
    bank_details["total_credits"] = labeled_value([r"Total\s+Credits?", r"Total\s+Credit\s*(?:Amount)?"])
    bank_details["total_debits"] = labeled_value([r"Total\s+Debits?", r"Total\s+Debit\s*(?:Amount)?"])

    # Row-style statements (SBI/HDFC passbooks print "OPN BAL" without a
    # label-value layout): the balance sits at the end of the opening row.
    if bank_details["opening_balance"] is None:
        opn_row = line_last_amount(r"\bOPN\.?\s*BAL(?:ANCE)?\b")
        if opn_row is None:
            opn_row = line_last_amount(r"\bB\/F\b")
        if opn_row is not None:
            bank_details["opening_balance"] = opn_row
            field_confidence["opening_balance"] = "medium"

    if (bank_details["opening_balance"] is None or bank_details["closing_balance"] is None) and tables:
        for tbl in tables:
            # Locate a balance column in the header row, e.g. "Closing Balance"
            balance_idx = None
            for row in tbl:
                for ci, cell in enumerate(row):
                    if cell and re.search(r"(closing|opening|balance)\s*bal", str(cell).lower()):
                        balance_idx = ci
                        break
                if balance_idx is not None:
                    break
            if balance_idx is None:
                continue
            data_rows = [r for r in tbl if r[balance_idx] is not None]
            if len(data_rows) < 2:
                continue
            def cell_val(cell) -> Optional[float]:
                return _clean_currency_signed(str(cell).strip())
            vals = [cell_val(r[balance_idx]) for r in data_rows]
            vals = [v for v in vals if v is not None]
            if not vals:
                continue
            if bank_details["opening_balance"] is None:
                bank_details["opening_balance"] = vals[0]
                field_confidence["opening_balance"] = "medium"
            if bank_details["closing_balance"] is None:
                bank_details["closing_balance"] = vals[-1]
                field_confidence["closing_balance"] = "medium"
            break

    # Detected Salary Credits in bank statement: parse per LINE, prefer
    # comma-grouped / decimal tokens (so narration/reference numbers can never
    # be mistaken for money), take the first in-range credit per line, then use
    # the MEDIAN across months as the monthly salary estimate.
    _amount_tokens = re.compile(
        r"(?<![\d.,])(?:\d{1,3}(?:\,\d{2,3})+(?:\.\d{1,2})?|\d+\.\d{2})(?![\d.,])")
    _plain_tokens = re.compile(r"(?<![\d.\-])(\d+)(?![\d.])")

    def line_amounts(ln: str, lo: float, hi: float) -> List[float]:
        toks = _amount_tokens.findall(ln) or _plain_tokens.findall(ln)
        vals = []
        for tok in toks:
            v = _clean_currency(tok)
            if v is not None and lo <= v <= hi:
                vals.append(v)
        return vals

    salary_kw = re.compile(
        r"\b(?:SAL(?:ARY)?\s*CR(?:EDIT)?|SALARY(?:\s*CREDIT)?|PAYROLL|STIPEND|WAGES)\b", re.IGNORECASE)
    sal_credit_vals = []
    for ln in text.splitlines():
        if not salary_kw.search(ln):
            continue
        for v in line_amounts(ln, 5000, 1000000):
            sal_credit_vals.append(v)
            break
    if sal_credit_vals:
        sal_credit_vals.sort()
        n = len(sal_credit_vals)
        median_val = sal_credit_vals[n // 2] if n % 2 else (sal_credit_vals[n // 2 - 1] + sal_credit_vals[n // 2]) / 2
        bank_details["detected_salary_credits"] = median_val
        bank_details["salary_credit_count"] = n
        field_confidence["detected_salary_credits"] = "high" if n >= 2 else "medium"
        if not monthly_salary:
            monthly_salary = median_val

    # Detected Recurring Loan EMIs: NACH/auto-debit lines repeat monthly, so the
    # correct monthly obligation is the MOST COMMON amount (mode), never their
    # sum. Parsed per line with decimal/comma preference, so reference codes
    # like "ACH-8891", account digits, or dates (07-04-2026) are never amounts.
    from collections import Counter
    emi_kw = re.compile(
        r"\b(?:EMI|NACH|ACH|ECS|AUTO\s+DEBIT|AUTO\s+PAY|STANDING\s+INSTRUCTION)\b", re.IGNORECASE)
    emi_vals = []
    for ln in text.splitlines():
        if not emi_kw.search(ln):
            continue
        for v in line_amounts(ln, 500, 200000):
            # Round to the nearest 10 to absorb duplicate decimals
            emi_vals.append(round(v, -1))
    if emi_vals:
        counts = Counter(emi_vals)
        common_val, common_count = counts.most_common(1)[0]
        occurrences = sum(1 for v in emi_vals if abs(v - common_val) < 1)
        bank_details["detected_monthly_emis"] = common_val
        bank_details["emi_debit_count"] = occurrences
        field_confidence["detected_monthly_emis"] = "high" if occurrences >= 2 else "medium"

    # Statement Period — labelled headers and free-form "from … to …" layouts
    period_m = re.search(r"(?:Statement\s+Period|Period)\s*[:\-]?\s*([0-9A-Za-z\s\-\/\,]+(?:to|–|-)[0-9A-Za-z\s\-\/\,]+)", text, re.IGNORECASE)
    if not period_m:
        period_from = re.search(r"(?:Statement|For\s+the\s+period)\s+(?:from\s+)?([0-9]{1,2}[\-\/\.][0-9]{1,2}[\-\/\.][0-9]{2,4})\s*(?:to|-|–)\s*([0-9]{1,2}[\-\/\.][0-9]{1,2}[\-\/\.][0-9]{2,4})", text, re.IGNORECASE)
        if period_from:
            bank_details["statement_period"] = f"{period_from.group(1)} to {period_from.group(2)}"
    else:
        bank_details["statement_period"] = period_m.group(1).strip()[:60]

    # -------------------------------------------------------------------------
    # 3. Identity Documents (PAN & Aadhaar)
    # -------------------------------------------------------------------------
    identity_details: Dict[str, Any] = {
        "pan_number_masked": None,
        "aadhaar_number_masked": None,
        "dob": None,
        "gender": None
    }

    # PAN number extraction & masking
    pan_m = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", text)
    if pan_m:
        raw_pan = pan_m.group(1)
        identity_details["pan_number_masked"] = f"{raw_pan[:5]}****{raw_pan[-1]}"
        field_confidence["pan_number_masked"] = "high"
        if doc_type == "pan_card" and not salary_details["employee_name"]:
            # Extract name on PAN Card (typically line before father's name or after Income Tax Dept)
            pan_name_m = re.search(r"Name\s*[:\-]?\s*([A-Za-z\s]+)", text, re.IGNORECASE)
            if pan_name_m:
                salary_details["employee_name"] = pan_name_m.group(1).strip()

    # Aadhaar number extraction & UIDAI-compliant masking.
    # Handles: full "1234 5678 9012", compact "123456789012", and the masked
    # "XXXXXXXX1234" form that UIDAI actually prints on physical cards / e-Aadhaar.
    aadhaar_m = re.search(r"\b(\d{4}\s\d{4}\s\d{4}|\d{12})\b", text)
    if aadhaar_m:
        raw_aadhaar = aadhaar_m.group(1).replace(" ", "")
        identity_details["aadhaar_number_masked"] = f"XXXX-XXXX-{raw_aadhaar[-4:]}"
        field_confidence["aadhaar_number_masked"] = "high"
    else:
        aadhaar_masked_m = re.search(r"\b([Xx\*]{8}[ \-]?)(\d{4})\b", text)
        if aadhaar_masked_m:
            identity_details["aadhaar_number_masked"] = f"XXXX-XXXX-{aadhaar_masked_m.group(2)}"
            field_confidence["aadhaar_number_masked"] = "high (already masked on document)"

    # Date of Birth
    dob_m = re.search(r"(?:DOB|Date\s+of\s+Birth|Birth\s+Date|Year\s+of\s+Birth)\s*[:\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4})", text, re.IGNORECASE)
    if dob_m:
        identity_details["dob"] = dob_m.group(1).strip()
        field_confidence["dob"] = "high"

    # Gender
    gender_m = re.search(r"\b(Male|Female|Transgender)\b", text, re.IGNORECASE)
    if gender_m:
        identity_details["gender"] = gender_m.group(1).capitalize()
        field_confidence["gender"] = "high"

    # -------------------------------------------------------------------------
    # 4. Consolidated Flat Extracted Fields (For Editable UI Form)
    # -------------------------------------------------------------------------
    # A bank statement's header line is the BANK, not an employer — never
    # report "HDFC BANK LTD" as the applicant's employer. Only a genuinely
    # labelled employer field survives.
    if doc_type == "bank_statement" and salary_details["employer_name"]:
        emp_l = salary_details["employer_name"].lower().strip()
        bank_name_l = (bank_details.get("bank_name") or "").lower().strip()
        if ("bank" in emp_l
                or (bank_name_l and (emp_l == bank_name_l or bank_name_l in emp_l))):
            salary_details["employer_name"] = None
            field_confidence.pop("employer_name", None)

    extracted_name = salary_details["employee_name"] or bank_details["account_holder_name"]

    all_extracted_fields: Dict[str, Any] = {}
    if extracted_name:
        all_extracted_fields["applicant_name"] = extracted_name
    if salary_details["employer_name"]:
        all_extracted_fields["employer_name"] = salary_details["employer_name"]
    if monthly_salary:
        all_extracted_fields["monthly_income"] = monthly_salary
    if salary_details.get("basic_pay"):
        all_extracted_fields["basic_pay"] = salary_details["basic_pay"]
    if salary_details.get("gross_salary"):
        all_extracted_fields["gross_salary"] = salary_details["gross_salary"]
    if salary_details.get("total_deductions"):
        all_extracted_fields["total_deductions"] = salary_details["total_deductions"]
    if salary_details.get("net_salary"):
        all_extracted_fields["net_salary"] = salary_details["net_salary"]
    if bank_details.get("closing_balance"):
        all_extracted_fields["closing_balance"] = bank_details["closing_balance"]
    if bank_details["detected_monthly_emis"]:
        all_extracted_fields["existing_emis"] = bank_details["detected_monthly_emis"]
    if identity_details["dob"]:
        # Compute age estimate if 4-digit year present (uses the current year, not a hardcoded one)
        try:
            year_match = re.search(r"\b(19\d\d|200\d)\b", identity_details["dob"])
            if year_match:
                birth_year = int(year_match.group(1))
                all_extracted_fields["age"] = max(18, min(80, date.today().year - birth_year))
        except Exception:
            pass

    # Overall extraction confidence score (0.0 to 1.0)
    found_fields_count = sum(1 for v in [extracted_name, monthly_salary, salary_details["employer_name"], salary_details["basic_pay"], bank_details["closing_balance"]] if v is not None)
    confidence_score = min(1.0, max(0.40, found_fields_count * 0.20))

    return {
        # Core backwards-compatible top-level keys
        "extracted_name": extracted_name,
        "employer_name": salary_details["employer_name"],
        "monthly_salary": monthly_salary,
        "average_bank_balance": bank_details["closing_balance"] or bank_details["opening_balance"],
        "total_credits": bank_details["total_credits"],
        "total_debits": bank_details["total_debits"],
        "raw_text_snippet": text[:500] if text else "",
        # Rich document intake additions
        "document_type": doc_type,
        "confidence_score": round(confidence_score, 2),
        "salary_details": salary_details,
        "bank_details": bank_details,
        "identity_details": identity_details,
        "field_confidence": field_confidence,
        "all_extracted_fields": all_extracted_fields,
        # NLP & Document AI Intelligence additions
        "name_analysis": nlp_result.get("name_analysis", {}),
        "math_validation": nlp_result.get("math_validation", {}),
        "evidence_list": nlp_result.get("evidence_list", []),
        "requires_user_confirmation": nlp_result.get("name_analysis", {}).get("requires_user_confirmation", False),
        "candidate_names": nlp_result.get("name_analysis", {}).get("all_candidates", []),
        "signatories": nlp_result.get("name_analysis", {}).get("signatories", [])
    }
