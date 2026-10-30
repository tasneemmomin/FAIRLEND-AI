"""
FairLendAI — NLP-Based Intelligent Document Extraction Pipeline
===============================================================
Comprehensive architecture:
1. Document Upload & Preprocessing (Text normalization, layout extraction)
2. Section Segmentation (Header, Employee Details, Earnings, Deductions, Summary, Signatory block)
3. Named Entity Recognition (NER) & Linguistic Analysis:
   - Distinguishes Applicant/Employee vs Employer vs Officer/Approving Authority vs Signatory vs Account Holder
   - Disambiguates multiple PERSON entities using proximity labels, syntactic role, and document layout
4. Context-Aware Financial Entity Extraction (Preserves column/section relationships)
5. Mathematical Consistency Validation (Gross - Deductions == Net check)
6. Evidence & Confidence Audit Trail for every extracted field:
   - value, raw_value, entity_type, source_document, page_number, supporting_text, extraction_method, confidence, status
"""

import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict

# Optional spaCy loader with graceful fallback
try:
    import spacy
    try:
        nlp_spacy = spacy.load("en_core_web_sm")
    except Exception:
        try:
            nlp_spacy = spacy.blank("en")
        except Exception:
            nlp_spacy = None
except ImportError:
    nlp_spacy = None

# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------
@dataclass
class ExtractedFieldEvidence:
    field_key: str
    value: Any
    raw_value: str
    entity_type: str  # PERSON, ORG, MONEY, IDENTIFIER, DATE, DESIGNATION
    source_document: Optional[str] = None
    page_number: int = 1
    supporting_text: str = ""
    extraction_method: str = "nlp_ner_labeled"  # nlp_ner_labeled, layout_table, regex_context, ocr_tesseract
    confidence: float = 0.85
    status: str = "Verified"  # Verified, Needs Confirmation, Not Found

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PersonCandidate:
    name: str
    role: str  # applicant, signatory, approving_officer, unknown
    confidence: float
    supporting_label: str
    line_number: int
    context_snippet: str


# -----------------------------------------------------------------------------
# Known Patterns & Taxonomies
# -----------------------------------------------------------------------------
INDIAN_BANKS = [
    "State Bank of India", "SBI", "HDFC Bank", "HDFC", "ICICI Bank", "ICICI",
    "Axis Bank", "Punjab National Bank", "PNB", "Bank of Baroda", "BOB",
    "Kotak Mahindra Bank", "Kotak", "Canara Bank", "Union Bank of India",
    "IndusInd Bank", "Bank of India", "IDFC FIRST Bank", "Yes Bank", "Federal Bank",
    "Central Bank of India", "Indian Bank", "Bank of Maharashtra"
]

HONORIFICS = r"(?:Shri|Smt\.?|Dr\.?|Mr\.?|Mrs\.?|Ms\.?|Prof\.?)"

# Signatory & Authority keywords that explicitly indicate the person is NOT the applicant
SIGNATORY_KEYWORDS = [
    "authorized signatory", "authorised signatory", "signatory", "signature",
    "signed by", "sd/-", "drawing & disbursing officer", "ddo", "drawing officer",
    "sanctioning authority", "branch manager", "manager", "director", "managing director",
    "general manager", "hr manager", "head - hr", "countersigned", "verified by",
    "approved by", "certifying officer", "accounts officer", "disbursing officer",
    "headmaster", "principal", "secretary", "president", "chairman", "trustee"
]

# Applicant / Employee direct keywords
APPLICANT_KEYWORDS = [
    "employee name", "name of employee", "name of staff", "staff name",
    "applicant name", "name of applicant", "borrower name", "account holder",
    "name of account holder", "customer name", "beneficiary name", "salaried person",
    "cardholder name", "name as on card", "this is to certify that"
]

EMPLOYER_KEYWORDS = [
    "pvt ltd", "private limited", "limited", "ltd", "corporation", "corp",
    "inc", "technologies", "technology", "solutions", "services", "enterprises",
    "ministry of", "department of", "govt of india", "government of", "railways",
    "infotech", "software", "consultancy", "systems", "shikshan", "prasarak",
    "mandal", "sanstha", "vidyalaya", "school", "college", "trust", "foundation",
    "society", "institute", "university", "academy", "parishad"
]


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def parse_words_to_num(words_str: str) -> Optional[float]:
    """Parses Indian currency words (e.g. 'Forty-five Thousand Three Hundred Eighty-Two') into numeric float."""
    num_map = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
        'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15, 'sixteen': 16,
        'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50,
        'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90
    }
    tokens = re.findall(r'[A-Za-z]+', words_str.lower())
    total = 0
    current = 0
    for t in tokens:
        if t in num_map:
            current += num_map[t]
        elif t == 'hundred':
            current = max(1, current) * 100
        elif t == 'thousand':
            total += max(1, current) * 1000
            current = 0
        elif t in ('lakh', 'lac', 'lakhs', 'lacs'):
            total += max(1, current) * 100000
            current = 0
        elif t in ('crore', 'crores'):
            total += max(1, current) * 10000000
            current = 0
    total += current
    return float(total) if total > 0 else None

def clean_currency_str(raw: str) -> Optional[float]:
    """Cleans currency strings handling Indian commas, Rs, ₹, decimals."""
    if not raw:
        return None
    cleaned = re.sub(r"[^\d\.]", "", raw.replace(",", "").strip())
    if not cleaned:
        return None
    try:
        val = float(cleaned)
        return val if val >= 0 else None
    except ValueError:
        return None


def mask_identifier(number_str: str, mode_or_suffix_len: Any = 4) -> str:
    """UIDAI & PAN compliant identifier masking."""
    cleaned = re.sub(r"[\s\-]", "", str(number_str))
    if isinstance(mode_or_suffix_len, str):
        mode = mode_or_suffix_len.lower()
        if mode in ("pan", "pan_card") and len(cleaned) == 10:
            return f"{cleaned[:5]}****{cleaned[-1]}"
        elif mode in ("aadhaar", "aadhaar_card") and len(cleaned) == 12:
            return f"••••-••••-{cleaned[-4:]}"
        else:
            visible_suffix_len = 4
    else:
        visible_suffix_len = int(mode_or_suffix_len)

    if len(cleaned) <= visible_suffix_len:
        return "****" + cleaned
    masked = "X" * (len(cleaned) - visible_suffix_len) + cleaned[-visible_suffix_len:]
    if len(cleaned) == 12:
        return f"{masked[:4]}-{masked[4:8]}-{masked[8:]}"
    elif len(cleaned) == 16:
        return f"{masked[:4]}-{masked[4:8]}-{masked[8:12]}-{masked[12:]}"
    return masked


# -----------------------------------------------------------------------------
# Section Segmentation Engine
# -----------------------------------------------------------------------------
class DocumentSectionSegmenter:
    """
    Splits financial document text into semantic sections:
    - HEADER (Employer, institution, document title)
    - EMPLOYEE_INFO (Name, ID, designation, department, bank a/c, PAN)
    - EARNINGS_TABLE (Basic, DA, HRA, allowances, gross earnings)
    - DEDUCTIONS_TABLE (PF, NPS, tax, insurance, total deductions)
    - NET_SUMMARY (Net salary, bank payment, amount in words)
    - SIGNATORY_BLOCK (Authority signatures, DDO, HR director)
    """

    @classmethod
    def segment(cls, text: str) -> Dict[str, List[Tuple[int, str]]]:
        lines = text.split("\n")
        total_lines = len(lines)
        sections: Dict[str, List[Tuple[int, str]]] = {
            "header": [],
            "employee_info": [],
            "earnings": [],
            "deductions": [],
            "net_summary": [],
            "signatory": [],
            "general": []
        }

        current_section = "header"
        for i, line in enumerate(lines):
            line_str = line.strip()
            if not line_str:
                continue

            lower_line = line_str.lower()
            relative_pos = i / max(1, total_lines)

            # Detect Signatory block (usually in bottom 30% of document)
            if relative_pos >= 0.65 and any(kw in lower_line for kw in [
                "signature", "signatory", "sd/-", "drawing & disbursing", "ddo",
                "verified by", "approved by", "branch manager", "manager", "director"
            ]):
                current_section = "signatory"

            # Detect Earnings header
            elif any(kw in lower_line for kw in ["earnings", "emoluments", "allowances", "gross salary"]):
                current_section = "earnings"

            # Detect Deductions header
            elif any(kw in lower_line for kw in ["deductions", "recoveries", "total deductions"]):
                current_section = "deductions"

            # Detect Net Pay summary
            elif any(kw in lower_line for kw in ["net salary", "net pay", "take home", "amount in words"]):
                current_section = "net_summary"

            # Detect Employee Info block
            elif any(kw in lower_line for kw in [
                "employee", "emp id", "designation", "department", "account no",
                "pan no", "uan no", "doj", "date of birth", "dob"
            ]) and relative_pos < 0.60:
                current_section = "employee_info"

            # Fallback for initial lines
            elif i < 5 and current_section == "header":
                current_section = "header"

            sections[current_section].append((i + 1, line_str))

        return sections


# -----------------------------------------------------------------------------
# Intelligent NLP Name Disambiguation Engine
# -----------------------------------------------------------------------------
class IntelligentNameExtractor:
    """
    Distinguishes:
    1. Applicant / Employee Name
    2. Employer / Organization Name
    3. Officer / Approving Authority Name (e.g. DDO, Sanctioning Authority)
    4. Signatory Name (e.g. Director, HR Manager, Authorized Signatory)
    5. Bank Account Holder Name
    6. Other individuals mentioned
    
    Adheres strictly to:
    - Never selects the first detected PERSON entity blindly.
    - If multiple candidates exist without high certainty, flags 'Needs Confirmation'.
    """

    @classmethod
    def extract_names(
        cls,
        text: str,
        sections: Dict[str, List[Tuple[int, str]]],
        doc_type: str = "salary_slip"
    ) -> Dict[str, Any]:
        candidates: List[PersonCandidate] = []
        lines = text.split("\n")
        total_lines = len(lines)

        # 1. Pattern-directed applicant detection
        applicant_label_regexes = [
            (r"This\s+is\s+to\s+certify\s+that\s+(?:Shri|Smt\.?|Dr\.?|Mr\.?|Ms\.?)?\s*([A-Za-z\s\.]+?)(?:\s*\(|\s+is\s+|\s+permanently|\s+working|\s*\,|\s*\n)", "Salary Certificate Subject Label", 0.98),
            (r"(?:Employee\s+Name|Name\s+of\s+(?:the\s+)?Employee)\s*[:\-]\s*(?:Shri|Smt\.?|Dr\.?|Mr\.?|Ms\.?)?\s*([A-Za-z\s\.\,\(\)]+)", "Employee Name Label", 0.95),
            (r"(?:Applicant\s+Name|Name\s+of\s+Applicant|Borrower\s+Name)\s*[:\-]\s*(?:Shri|Smt\.?|Dr\.?|Mr\.?|Ms\.?)?\s*([A-Za-z\s\.\,\(\)]+)", "Applicant Name Label", 0.95),
            (r"(?:Account\s+Holder(?:\s+Name)?|Name\s+of\s+Account\s+Holder|A/c\s+Name)\s*[:\-]\s*(?:Shri|Smt\.?|Dr\.?|Mr\.?|Ms\.?)?\s*([A-Za-z\s\.\,\(\)]+)", "Account Holder Label", 0.95),
            (r"(?:Name\s*[:\-])\s*(?:Shri|Smt\.?|Dr\.?|Mr\.?|Ms\.?)?\s*([A-Za-z\s\.\,\(\)]+)", "Generic Name Label", 0.75),
            (r"(?:Shri|Smt\.|Dr\.|Mr\.|Ms\.)\s+([A-Za-z\s\.]+)", "Honorific Salutation", 0.65),
        ]

        # 2. Pattern-directed Signatory / Approving Officer detection
        signatory_label_regexes = [
            (r"(?:Signature\s+of\s+(?:Drawing\s+&?\s+Disbursing\s+Officer|D\.?D\.?O\.?))\s*[:\-]?\s*(?:Shri|Smt\.?|Dr\.?|Mr\.?|Ms\.?)?\s*([A-Za-z\s\.]+)", "approving_officer", "Drawing & Disbursing Officer", 0.95),
            (r"(?:Sanctioning\s+Authority|Branch\s+Manager|Manager|Accounts\s+Officer)\s*[:\-]?\s*(?:Shri|Smt\.?|Dr\.?|Mr\.?|Ms\.?)?\s*([A-Za-z\s\.]+)", "approving_officer", "Sanctioning Authority", 0.90),
            (r"(?:Headmaster|Principal|Secretary|President|Chairman|Trustee)\s*[:\-]?\s*(?:Shri|Smt\.?|Dr\.?|Mr\.?|Ms\.?)?\s*([A-Za-z\s\.]*)", "signatory", "Headmaster / Authority", 0.92),
            (r"(?:Authorized\s+Signatory|Authorised\s+Signatory|Signed\s+by|Director|Managing\s+Director|HR\s+Manager)\s*[:\-]?\s*(?:Shri|Smt\.?|Dr\.?|Mr\.?|Ms\.?)?\s*([A-Za-z\s\.]+)", "signatory", "Authorized Signatory", 0.92),
            (r"Sd\/\-[\s\:]*(?:Shri|Smt\.?|Dr\.?|Mr\.?|Ms\.?)?\s*([A-Za-z\s\.]+)", "signatory", "Signed (Sd/-)", 0.88),
        ]

        # Search line-by-line with context
        for line_idx, line in enumerate(lines):
            line_str = line.strip()
            if not line_str:
                continue

            lower_line = line_str.lower()
            rel_pos = line_idx / max(1, total_lines)

            # Check if line contains a signatory / officer pattern
            for sig_rx, role, label, conf in signatory_label_regexes:
                m = re.search(sig_rx, line_str, re.IGNORECASE)
                if m:
                    raw_name = m.group(1).split("\n")[0].split("/")[0].strip()
                    clean_name = re.sub(r"^(Shri|Smt\.?|Dr\.?|Mr\.?|Ms\.?)\s+", "", raw_name, flags=re.I).strip()
                    if 2 <= len(clean_name) <= 50 and not any(kw in clean_name.lower() for kw in ["salary", "bank", "ltd", "pvt", "limited", "signature", "officer"]):
                        candidates.append(PersonCandidate(
                            name=clean_name,
                            role=role,
                            confidence=conf,
                            supporting_label=label,
                            line_number=line_idx + 1,
                            context_snippet=line_str
                        ))

            # Check if line contains an applicant pattern
            for app_rx, label, conf in applicant_label_regexes:
                m = re.search(app_rx, line_str, re.IGNORECASE)
                if m:
                    raw_name = m.group(1).split("\n")[0].split("/")[0].strip()
                    clean_name = re.sub(r"^(Shri|Smt\.?|Dr\.?|Mr\.?|Ms\.?)\s+", "", raw_name, flags=re.I).strip()
                    
                    # Context validation: If near bottom and signatory keywords exist, reclassify!
                    is_near_bottom = rel_pos >= 0.65
                    has_sig_kw = any(kw in lower_line for kw in SIGNATORY_KEYWORDS)

                    role = "signatory" if (is_near_bottom and has_sig_kw) else "applicant"
                    
                    if 2 <= len(clean_name) <= 50 and not any(kw in clean_name.lower() for kw in [
                        "salary", "bank", "statement", "pvt", "ltd", "limited", "company",
                        "department", "ministry", "allowance", "deduction", "signature",
                        "shikshan", "prasarak", "mandal", "sanstha", "school", "college",
                        "vidyalaya", "trust", "society", "parishad", "institute", "academy"
                    ]):
                        candidates.append(PersonCandidate(
                            name=clean_name,
                            role=role,
                            confidence=conf if role == "applicant" else 0.85,
                            supporting_label=label if role == "applicant" else f"{label} (in signatory section)",
                            line_number=line_idx + 1,
                            context_snippet=line_str
                        ))

        # 3. Use spaCy NER if available for additional person extraction
        if nlp_spacy:
            try:
                doc = nlp_spacy(text[:3000])
                for ent in doc.ents:
                    if ent.label_ == "PERSON":
                        ent_text = ent.text.strip()
                        if 3 <= len(ent_text) <= 40 and not any(c.name.lower() == ent_text.lower() for c in candidates):
                            # Determine role based on position
                            line_num = text[:ent.start_char].count("\n") + 1
                            rel_pos = line_num / max(1, total_lines)
                            role = "signatory" if rel_pos >= 0.70 else "unknown"
                            candidates.append(PersonCandidate(
                                name=ent_text,
                                role=role,
                                confidence=0.60,
                                supporting_label="spaCy NER PERSON",
                                line_number=line_num,
                                context_snippet=ent.sent.text.strip() if ent.sent else ent_text
                            ))
            except Exception:
                pass

        # 4. Resolve Roles & Disambiguate
        applicant_candidates = [c for c in candidates if c.role == "applicant"]
        signatory_candidates = [c for c in candidates if c.role in ("signatory", "approving_officer")]

        # Sort applicant candidates by confidence descending
        applicant_candidates.sort(key=lambda x: x.confidence, reverse=True)

        selected_applicant: Optional[PersonCandidate] = None
        status = "Verified"

        if len(applicant_candidates) == 1:
            selected_applicant = applicant_candidates[0]
            status = "Verified" if selected_applicant.confidence >= 0.80 else "Needs Confirmation"
        elif len(applicant_candidates) > 1:
            top = applicant_candidates[0]
            second = applicant_candidates[1]
            # If top has significantly higher confidence or clear label vs generic
            if top.confidence >= 0.90 and second.confidence < 0.80:
                selected_applicant = top
                status = "Verified"
            elif top.name.lower() == second.name.lower():
                selected_applicant = top
                status = "Verified"
            else:
                # Multiple ambiguous candidates -> Do NOT guess! Ask applicant to confirm.
                selected_applicant = top
                status = "Needs Confirmation"
        elif len(candidates) > 0:
            # Fallback: check candidates with unknown role (if not in bottom section)
            non_signatories = [c for c in candidates if c.role not in ("signatory", "approving_officer") and c.line_number < total_lines * 0.7]
            if non_signatories:
                selected_applicant = non_signatories[0]
                status = "Needs Confirmation"

        return {
            "selected_applicant": selected_applicant,
            "status": status,
            "all_candidates": [asdict(c) for c in candidates],
            "signatories": [asdict(c) for c in signatory_candidates],
            "requires_user_confirmation": status == "Needs Confirmation"
        }


# -----------------------------------------------------------------------------
# Context-Aware Financial Entity Extraction Engine
# -----------------------------------------------------------------------------
class FinancialEntityExtractor:
    """
    Extracts all structured financial entities with section and table awareness:
    - Basic Pay, Grade Pay, DA, HRA, Other Allowances
    - Gross Salary
    - Provident Fund, NPS, Professional Tax, Income Tax, Total Deductions
    - Net Salary
    - Bank Statement metrics (Balances, Debits/Credits, Salary Credits, EMIs)
    - Identification details (PAN, Aadhaar)
    """

    @classmethod
    def extract_salary_entities(
        cls,
        text: str,
        sections: Dict[str, List[Tuple[int, str]]],
        doc_filename: str = "document.pdf"
    ) -> Tuple[Dict[str, Any], List[ExtractedFieldEvidence]]:
        evidence_list: List[ExtractedFieldEvidence] = []
        result: Dict[str, Any] = {
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
            "net_salary": None,
            "employer_name": None,
            "designation": None,
            "employee_id": None,
            "salary_month": None
        }

        # 1. Employer Name Extraction
        employer_patterns = [
            (r"(?:Employer|Company(?:\s+Name)?|Organization|Ministry|Department)\s*[:\-]\s*([A-Za-z0-9\s\,\.\-\&]+)", 0.95),
            (r"(?:Account\s+at)\s*[:\-]\s*([A-Za-z0-9\s\,\.\-]+)", 0.85)
        ]
        for p, conf in employer_patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                clean_emp = m.group(1).split("\n")[0].strip()
                if 3 <= len(clean_emp) <= 80:
                    result["employer_name"] = clean_emp
                    evidence_list.append(ExtractedFieldEvidence(
                        field_key="employer_name",
                        value=clean_emp,
                        raw_value=m.group(0),
                        entity_type="ORG",
                        source_document=doc_filename,
                        supporting_text=m.group(0),
                        extraction_method="nlp_ner_labeled",
                        confidence=conf,
                        status="Verified"
                    ))
                    break

        # Fallback to header inspection if not found
        if not result["employer_name"]:
            for line_no, line_str in sections.get("header", [])[:4]:
                if any(kw in line_str.lower() for kw in EMPLOYER_KEYWORDS):
                    clean_emp = line_str[:70].strip()
                    result["employer_name"] = clean_emp
                    evidence_list.append(ExtractedFieldEvidence(
                        field_key="employer_name",
                        value=clean_emp,
                        raw_value=line_str,
                        entity_type="ORG",
                        source_document=doc_filename,
                        page_number=1,
                        supporting_text=line_str,
                        extraction_method="layout_header_heuristic",
                        confidence=0.80,
                        status="Verified"
                    ))
                    break

        # 2. Designation, Employee ID & Salary Month
        desig_m = re.search(r"(?:Designation|Post|Cadre|Role)\s*[:\-]\s*([A-Za-z0-9\s\,\.\-]+)|(?:permanently\s+employed|employed|working)\s+as\s+(?:an?\s+)?([A-Za-z\s\/\-]+?)(?:\s+at|\s+in|\s*\,|\s*\.|\s*\n)", text, re.I)
        if desig_m:
            clean_d = (desig_m.group(1) or desig_m.group(2) or "").split("\n")[0].strip()
            if 2 <= len(clean_d) <= 60:
                result["designation"] = clean_d
                evidence_list.append(ExtractedFieldEvidence(
                    field_key="designation",
                    value=clean_d,
                    raw_value=desig_m.group(0),
                    entity_type="DESIGNATION",
                    source_document=doc_filename,
                    supporting_text=desig_m.group(0),
                    confidence=0.90,
                    status="Verified"
                ))

        sal_m = re.search(r"(?:Salary\s+for\s+(?:the\s+month\s+of\s+)?|for\s+the\s+month\s+of\s+|Month\s*(?:&|and)?\s*Year\s*[:\-]?\s*|Pay\s+Period\s*[:\-]?\s*)([A-Za-z]+[\s\-]+20\d\d|\d{1,2}[\/\-]\d{4}|[A-Za-z]{3,9}\s*\-?\s*\d{2,4})", text, re.I)
        if sal_m:
            result["salary_month"] = sal_m.group(1).strip()
            evidence_list.append(ExtractedFieldEvidence(
                field_key="salary_month",
                value=sal_m.group(1).strip(),
                raw_value=sal_m.group(0),
                entity_type="DATE",
                source_document=doc_filename,
                supporting_text=sal_m.group(0),
                confidence=0.95,
                status="Verified"
            ))

        empid_m = re.search(r"(?:Employee\s+ID|Emp(?:\.|\s+)?(?:Code|ID|No)|Staff\s+No|Personnel\s+No)\s*[:\-]\s*([A-Za-z0-9\-\_]+)", text, re.I)
        if empid_m:
            eid = empid_m.group(1).strip()
            result["employee_id"] = eid
            evidence_list.append(ExtractedFieldEvidence(
                field_key="employee_id",
                value=eid,
                raw_value=empid_m.group(0),
                entity_type="IDENTIFIER",
                source_document=doc_filename,
                supporting_text=empid_m.group(0),
                confidence=0.95,
                status="Verified"
            ))

        # 3. Numeric Earnings and Deductions Patterns
        field_patterns = [
            ("basic_pay", r"(?:Basic\s+(?:Pay|Salary)(?:\s*\([A-Za-z]+\))?)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", "MONEY"),
            ("grade_pay", r"(?:Grade\s+Pay(?:\s*\([A-Za-z]+\))?)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", "MONEY"),
            ("dearness_allowance", r"(?:Dearness\s+Allowance(?:\s*\([A-Za-z]+\))?|D\.?A\.?)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", "MONEY"),
            ("hra", r"(?:House\s+Rent\s+Allowance(?:\s*\([A-Za-z]+\))?|H\.?R\.?A\.?)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", "MONEY"),
            ("other_allowances", r"(?:Transport|Conveyance|Medical|Special|Other)\s+Allowance(?:\s*\([A-Za-z]+\))?\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", "MONEY"),
            ("gross_salary", r"(?:Total\s+(?:Gross\s+)?Salary|Gross\s+(?:Salary|Pay|Earnings|Emoluments)|Total\s+Earnings)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", "MONEY"),
            ("provident_fund", r"(?:Provident\s+Fund|EPF|GPF|P\.?F\.?)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", "MONEY"),
            ("nps", r"(?:NPS(?:\s+Contribution)?|Tier\s*I\s*NPS)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", "MONEY"),
            ("professional_tax", r"(?:Professional\s+Tax|Prof\.?\s+Tax|P\.?Tax)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", "MONEY"),
            ("income_tax", r"(?:Income\s+Tax|TDS|I\.?T\.?)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", "MONEY"),
            ("insurance", r"(?:Group\s+Insurance|GIS|Insurance|LIC)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", "MONEY"),
            ("total_deductions", r"(?:Total\s+Deductions|Total\s+Recoveries)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", "MONEY"),
            ("net_salary", r"(?:Net\s+(?:Salary|Pay|Payable|Amount)|Take\s+Home\s+Pay)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", "MONEY"),
        ]

        for field_k, pat, ent_type in field_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                val = clean_currency_str(m.group(1))
                if val is not None:
                    result[field_k] = val
                    evidence_list.append(ExtractedFieldEvidence(
                        field_key=field_k,
                        value=val,
                        raw_value=m.group(0),
                        entity_type=ent_type,
                        source_document=doc_filename,
                        supporting_text=m.group(0).strip(),
                        extraction_method="regex_context",
                        confidence=0.90,
                        status="Verified"
                    ))

        # 4. Check 'Amount in words' for high-confidence Net Salary
        words_m = re.search(r"Amount\s+in\s+words\s*[:\-]?\s*(?:Rupees|Rs\.?)?\s*([A-Za-z\s\-]+?)(?:\s+Only|\.|\n|$)", text, re.I)
        if words_m:
            words_val = parse_words_to_num(words_m.group(1))
            if words_val:
                result["net_salary"] = words_val
                evidence_list.append(ExtractedFieldEvidence(
                    field_key="net_salary",
                    value=words_val,
                    raw_value=words_m.group(0),
                    entity_type="MONEY",
                    source_document=doc_filename,
                    supporting_text=words_m.group(0).strip(),
                    extraction_method="nlp_amount_in_words",
                    confidence=0.98,
                    status="Verified"
                ))

        # 5. Check sequential column-aligned table structures (when labels & numbers are in separate blocks)
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        if not result.get("basic_pay"):
            for i, ln in enumerate(lines):
                if re.match(r"^Basic\s+Pay", ln, re.I):
                    for j in range(i + 1, min(len(lines), i + 20)):
                        val = clean_currency_str(lines[j])
                        if val and val >= 1000:
                            result["basic_pay"] = val
                            break
                    break

        if not result.get("total_deductions"):
            for i, ln in enumerate(lines):
                if re.search(r"TOTAL\s+DEDUCTIONS", ln, re.I):
                    for j in range(i + 1, min(len(lines), i + 15)):
                        val = clean_currency_str(lines[j])
                        if val and val >= 1000:
                            result["total_deductions"] = val
                    break

        # If gross is not explicitly labeled but net and deductions are present, calculate gross
        if not result.get("gross_salary") and result.get("net_salary") and result.get("total_deductions"):
            result["gross_salary"] = result["net_salary"] + result["total_deductions"]

        return result, evidence_list


# -----------------------------------------------------------------------------
# Mathematical Consistency & Cross-Validation Engine
# -----------------------------------------------------------------------------
class MathematicalValidator:
    """
    Validates arithmetic consistency:
    Gross Salary - Total Deductions == Net Salary
    If consistent within rounding tolerance, marks fields as 'Verified' with high confidence.
    If inconsistent, flags math discrepancy and adjusts status to 'Needs Confirmation'.
    """

    @classmethod
    def validate_salary_arithmetic(
        cls,
        salary_details: Dict[str, Any],
        evidence_list: List[ExtractedFieldEvidence]
    ) -> Dict[str, Any]:
        gross = salary_details.get("gross_salary")
        deductions = salary_details.get("total_deductions")
        net = salary_details.get("net_salary")

        math_result = {
            "math_validated": False,
            "discrepancy_flag": False,
            "message": "",
            "expected_net": None
        }

        if gross is not None and deductions is not None and net is not None:
            expected_net = gross - deductions
            math_result["expected_net"] = expected_net
            diff = abs(expected_net - net)

            # Allow up to Rs. 5 variance for tax roundoffs
            if diff <= 5.0:
                math_result["math_validated"] = True
                math_result["message"] = f"Mathematical balance verified: Gross (Rs. {gross:,.0f}) - Deductions (Rs. {deductions:,.0f}) = Net (Rs. {net:,.0f})"
                # Boost confidence of related fields
                for ev in evidence_list:
                    if ev.field_key in ("gross_salary", "total_deductions", "net_salary"):
                        ev.confidence = 0.98
                        ev.status = "Verified"
            else:
                math_result["discrepancy_flag"] = True
                math_result["message"] = f"Mathematical variance: Gross (Rs. {gross:,.0f}) - Deductions (Rs. {deductions:,.0f}) = Rs. {expected_net:,.0f}, but Net is recorded as Rs. {net:,.0f} (Difference: Rs. {diff:,.0f})."
                for ev in evidence_list:
                    if ev.field_key == "net_salary":
                        ev.confidence = 0.65
                        ev.status = "Needs Confirmation"
        elif gross is not None and net is not None and deductions is None:
            # Infer deductions if not explicitly stated
            inferred_deductions = gross - net
            if inferred_deductions >= 0:
                salary_details["total_deductions"] = inferred_deductions
                math_result["math_validated"] = True
                math_result["message"] = f"Inferred total deductions: Rs. {inferred_deductions:,.0f}"

        return math_result


# -----------------------------------------------------------------------------
# Master Document Intelligence Pipeline
# -----------------------------------------------------------------------------
class DocumentNLPExtractionPipeline:
    """
    Complete end-to-end extraction pipeline integrating OCR, NLP, Section Analysis,
    NER, Name Disambiguation, and Mathematical Validation.
    """

    @classmethod
    def process_text(
        cls,
        text: str,
        doc_filename: str = "document.pdf",
        doc_type: Optional[str] = None
    ) -> Dict[str, Any]:
        # 1. Classify document type if not specified
        from backend.services.ocr.extractor import classify_document_type
        detected_type = doc_type or classify_document_type(text)

        # 2. Section Segmentation
        sections = DocumentSectionSegmenter.segment(text)

        # 3. Intelligent Name Disambiguation
        name_analysis = IntelligentNameExtractor.extract_names(text, sections, detected_type)
        selected_applicant = name_analysis["selected_applicant"]

        # 4. Extract Financial Details
        salary_details, salary_evidence = FinancialEntityExtractor.extract_salary_entities(text, sections, doc_filename)

        # 5. Attach Applicant Name Evidence
        all_evidence = list(salary_evidence)
        applicant_name_str = None
        if selected_applicant:
            applicant_name_str = selected_applicant.name
            all_evidence.append(ExtractedFieldEvidence(
                field_key="applicant_name",
                value=selected_applicant.name,
                raw_value=selected_applicant.context_snippet,
                entity_type="PERSON",
                source_document=doc_filename,
                page_number=1,
                supporting_text=selected_applicant.context_snippet,
                extraction_method="nlp_ner_labeled" if "Label" in selected_applicant.supporting_label else "nlp_context_rules",
                confidence=selected_applicant.confidence,
                status=name_analysis["status"]
            ))

        # 6. Mathematical Validation for Salary Slips
        math_check = MathematicalValidator.validate_salary_arithmetic(salary_details, all_evidence)

        # 7. Bank Statement Entity Extraction (if bank statement)
        bank_details: Dict[str, Any] = {
            "account_holder_name": applicant_name_str if detected_type == "bank_statement" else None,
            "bank_name": None,
            "account_number_masked": None,
            "opening_balance": None,
            "closing_balance": None,
            "total_credits": None,
            "total_debits": None,
            "detected_salary_credits": None,
            "detected_monthly_emis": None
        }

        if detected_type == "bank_statement":
            # Extract Bank Name
            for b in INDIAN_BANKS:
                if b.lower() in text.lower():
                    bank_details["bank_name"] = b
                    all_evidence.append(ExtractedFieldEvidence(
                        field_key="bank_name",
                        value=b,
                        raw_value=b,
                        entity_type="ORG",
                        source_document=doc_filename,
                        confidence=0.95,
                        status="Verified"
                    ))
                    break

            # Balances
            cb_m = re.search(r"(?:Closing\s+Balance|Balance\s+as\s+on|End\s+Balance)\s*[:\-]?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", text, re.I)
            if cb_m:
                cb = clean_currency_str(cb_m.group(1))
                bank_details["closing_balance"] = cb

            # Salary credit detection
            sal_cr_m = re.search(r"(?:SALARY|SAL|CMS|PAYROLL|NEFT.*SAL)\s+.*?(?:CR|CREDIT)?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", text, re.I)
            if sal_cr_m:
                sc = clean_currency_str(sal_cr_m.group(1))
                bank_details["detected_salary_credits"] = sc

            # Loan EMI detection
            emi_m = re.search(r"(?:LOAN|EMI|ACH|NACH|BAJAJ|HDFC\s*LOAN)\s+.*?(?:DR|DEBIT)?\s*(?:(?:Rs\.?|INR|\u20B9)\s*)?([\d\,]+(?:\.\d{1,2})?)", text, re.I)
            if emi_m:
                emi_val = clean_currency_str(emi_m.group(1))
                bank_details["detected_monthly_emis"] = emi_val

        # 8. Masked Identifiers (PAN, Aadhaar)
        identity_details: Dict[str, Any] = {
            "pan_number_masked": None,
            "aadhaar_number_masked": None,
            "dob": None
        }
        pan_m = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", text)
        if pan_m:
            identity_details["pan_number_masked"] = mask_identifier(pan_m.group(1), "pan")

        aadh_m = re.search(r"\b(\d{4}\s?\d{4}\s?\d{4})\b", text)
        if aadh_m:
            identity_details["aadhaar_number_masked"] = mask_identifier(aadh_m.group(1), "aadhaar")

        dob_m = re.search(r"(?:DOB|Date\s+of\s+Birth|Birth\s+Date)\s*[:\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})", text, re.I)
        if dob_m:
            identity_details["dob"] = dob_m.group(1)

        # 9. Build Comprehensive Response
        overall_confidence = 0.90
        if name_analysis["requires_user_confirmation"]:
            overall_confidence -= 0.15
        if math_check["discrepancy_flag"]:
            overall_confidence -= 0.15

        return {
            "extracted_name": applicant_name_str,
            "employer_name": salary_details.get("employer_name"),
            "monthly_salary": salary_details.get("net_salary") or salary_details.get("gross_salary") or bank_details.get("detected_salary_credits"),
            "document_type": detected_type,
            "confidence_score": max(0.40, min(0.99, round(overall_confidence, 2))),
            "salary_details": salary_details,
            "bank_details": bank_details,
            "identity_details": identity_details,
            "name_analysis": name_analysis,
            "math_validation": math_check,
            "evidence_list": [e.to_dict() for e in all_evidence],
            "all_extracted_fields": {
                "applicant_name": applicant_name_str,
                "monthly_income": salary_details.get("net_salary") or salary_details.get("gross_salary") or bank_details.get("detected_salary_credits"),
                "employer_name": salary_details.get("employer_name"),
                "basic_pay": salary_details.get("basic_pay"),
                "gross_salary": salary_details.get("gross_salary"),
                "net_salary": salary_details.get("net_salary"),
                "total_deductions": salary_details.get("total_deductions"),
                "existing_emis": bank_details.get("detected_monthly_emis") or 0,
                "closing_balance": bank_details.get("closing_balance")
            }
        }
