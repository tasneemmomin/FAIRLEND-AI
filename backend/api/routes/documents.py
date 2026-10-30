import io
import uuid
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Response, Depends
from pydantic import BaseModel

from backend.core.config import settings
from backend.core.security import get_fernet
from backend.core.auth import get_current_user
from backend.db.models import User
from backend.services.ocr.extractor import extract_from_pdf, extract_from_image, classify_document_type
from backend.services.ocr.consistency import calculate_consistency

router = APIRouter(prefix="/documents", tags=["Document Intelligence"])

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

MANDATORY_LOAN_FIELDS = [
    {
        "field_key": "applicant_name",
        "label": "Full Legal Name",
        "field_type": "text",
        "required": True,
        "placeholder": "e.g. Rahul Sharma",
        "description": "Full name as per official records."
    },
    {
        "field_key": "contact_phone",
        "label": "Mobile Phone Number",
        "field_type": "tel",
        "required": True,
        "placeholder": "+91 98765 43210",
        "description": "Primary mobile number for application updates."
    },
    {
        "field_key": "contact_email",
        "label": "Email Address",
        "field_type": "email",
        "required": True,
        "placeholder": "rahul.sharma@example.com",
        "description": "Official contact email address."
    },
    {
        "field_key": "age",
        "label": "Age (Years)",
        "field_type": "number",
        "required": True,
        "placeholder": "28",
        "default_value": 28,
        "description": "Applicant age (must be 18 to 100)."
    },
    {
        "field_key": "employment_type",
        "label": "Employment Type",
        "field_type": "select",
        "required": True,
        "default_value": "salaried",
        "description": "Current primary employment categorization.",
        "options": [
            {"value": "salaried", "label": "Salaried Employee"},
            {"value": "self_employed", "label": "Self-Employed Professional"},
            {"value": "business", "label": "Business Owner / Merchant"},
            {"value": "gig_contract", "label": "Gig / Contract Worker"}
        ]
    },
    {
        "field_key": "employment_duration_months",
        "label": "Duration in Current Role (Months)",
        "field_type": "number",
        "required": True,
        "placeholder": "24",
        "default_value": 24,
        "description": "Total months worked in current role/organization."
    },
    {
        "field_key": "monthly_income",
        "label": "Monthly Take-Home Income (₹)",
        "field_type": "number",
        "required": True,
        "placeholder": "50000",
        "description": "Net monthly earnings or salary credit."
    },
    {
        "field_key": "existing_emis",
        "label": "Existing Monthly Loan EMIs (₹)",
        "field_type": "number",
        "required": True,
        "placeholder": "0",
        "default_value": 0,
        "description": "Total existing monthly debt repayment obligations."
    },
    {
        "field_key": "requested_amount",
        "label": "Requested Loan Amount (₹)",
        "field_type": "number",
        "required": True,
        "placeholder": "200000",
        "default_value": 200000,
        "description": "Total loan principal required."
    },
    {
        "field_key": "tenure_months",
        "label": "Repayment Tenure (Months)",
        "field_type": "number",
        "required": True,
        "placeholder": "24",
        "default_value": 24,
        "description": "Requested loan repayment duration (6 to 360 months)."
    },
    {
        "field_key": "loan_purpose",
        "label": "Loan Purpose",
        "field_type": "select",
        "required": True,
        "default_value": "personal",
        "description": "Primary intended purpose for loan funds.",
        "options": [
            {"value": "personal", "label": "Personal / Family"},
            {"value": "home", "label": "Home Purchase / Renovation"},
            {"value": "education", "label": "Higher Education"},
            {"value": "vehicle", "label": "Vehicle Purchase"},
            {"value": "business", "label": "Business Expansion"},
            {"value": "medical", "label": "Medical Treatment"}
        ]
    },
    {
        "field_key": "residence_type",
        "label": "Residence Type",
        "field_type": "select",
        "required": True,
        "default_value": "rented",
        "description": "Residential ownership status.",
        "options": [
            {"value": "rented", "label": "Rented Accommodation"},
            {"value": "owned", "label": "Owned Home"},
            {"value": "ancestral", "label": "Family / Ancestral Residence"}
        ]
    }
]

class AnalyzeIntakeRequest(BaseModel):
    documents: List[Dict[str, Any]]
    applicant_profile: Optional[Dict[str, Any]] = None

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form("salary_slip"),
    declared_income: Optional[float] = Form(None),
    declared_name: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """Legacy single document upload with consistency scoring."""
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file format '{ext}'. Allowed: PDF, PNG, JPG.")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowable limit of 10MB.")

    if ext == ".pdf":
        extracted = extract_from_pdf(contents)
    else:
        extracted = extract_from_image(contents)

    declared_dict = {
        "monthly_income": declared_income or 0.0,
        "applicant_name": declared_name or ""
    }
    consistency_score, flags = calculate_consistency(declared_dict, extracted)

    doc_id = str(uuid.uuid4())
    fernet = get_fernet()
    encrypted_bytes = fernet.encrypt(contents)
    
    save_path = settings.UPLOAD_DIR / f"{doc_id}{ext}.enc"
    save_path.write_bytes(encrypted_bytes)

    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "doc_type": doc_type,
        "extension": ext,
        "extracted_data": extracted,
        "consistency_score": consistency_score,
        "mismatch_flags": flags,
        "preview_url": f"/api/documents/{doc_id}/preview?ext={ext}"
    }

@router.post("/intake-upload")
async def intake_upload_document(
    file: UploadFile = File(...),
    doc_type: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    Dedicated Document Intake Upload endpoint:
    Processes salary slips, bank statements, PAN, Aadhaar, and other documents
    with intelligent classification and structured multi-entity extraction.
    """
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file format '{ext}'. Allowed: PDF, PNG, JPG.")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowable limit of 10MB.")

    # 1. Multi-format OCR parsing
    if ext == ".pdf":
        extracted = extract_from_pdf(contents)
    else:
        extracted = extract_from_image(contents)

    detected_category = extracted.get("document_type") or "other_financial"
    final_category = doc_type if (doc_type and doc_type != "auto") else detected_category

    # 2. Encrypted storage at rest under user context
    doc_id = str(uuid.uuid4())
    fernet = get_fernet()
    encrypted_bytes = fernet.encrypt(contents)
    save_path = settings.UPLOAD_DIR / f"{doc_id}{ext}.enc"
    save_path.write_bytes(encrypted_bytes)

    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "doc_type": final_category,
        "detected_category": detected_category,
        "confidence_score": extracted.get("confidence_score", 0.85),
        "extracted_data": extracted,
        "preview_url": f"/api/documents/{doc_id}/preview?ext={ext}",
        "applicant_verified": False,
        "applicant_corrections": {}
    }

@router.post("/analyze-intake")
def analyze_intake_documents(
    req: AnalyzeIntakeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Dynamic Missing Information Analyzer:
    Consolidates extracted fields across all uploaded documents,
    detects conflicts/variances, and generates the dynamic missing fields list.
    """
    docs = req.documents or []
    profile = req.applicant_profile or {}

    merged_fields: Dict[str, Any] = {}
    field_sources: Dict[str, str] = {}
    conflicts: List[Dict[str, Any]] = []

    # Initialize with user profile if available
    if profile.get("full_name") or profile.get("name"):
        merged_fields["applicant_name"] = profile.get("full_name") or profile.get("name")
        field_sources["applicant_name"] = "Applicant Profile"
    if profile.get("phone"):
        merged_fields["contact_phone"] = profile.get("phone")
        field_sources["contact_phone"] = "Applicant Profile"
    if profile.get("email"):
        merged_fields["contact_email"] = profile.get("email")
        field_sources["contact_email"] = "Applicant Profile"

    # Iterate through documents to extract and merge
    names_seen = []
    salaries_seen = []

    for doc in docs:
        filename = doc.get("filename", "Document")
        extracted = doc.get("extracted_data") or {}
        flat_fields = extracted.get("all_extracted_fields") or {}
        sal_details = extracted.get("salary_details") or {}
        bank_details = extracted.get("bank_details") or {}

        # 1. Name
        doc_name = extracted.get("extracted_name") or flat_fields.get("applicant_name")
        if doc_name:
            names_seen.append((doc_name, filename))
            if "applicant_name" not in merged_fields or field_sources.get("applicant_name") == "Applicant Profile":
                merged_fields["applicant_name"] = doc_name
                field_sources["applicant_name"] = filename

        # 2. Monthly Income
        doc_salary = extracted.get("monthly_salary") or flat_fields.get("monthly_income")
        if doc_salary and doc_salary > 0:
            salaries_seen.append((doc_salary, filename))
            if "monthly_income" not in merged_fields:
                merged_fields["monthly_income"] = doc_salary
                field_sources["monthly_income"] = filename

        # 3. Existing EMIs
        doc_emi = bank_details.get("detected_monthly_emis") or flat_fields.get("existing_emis")
        if doc_emi is not None:
            if "existing_emis" not in merged_fields:
                merged_fields["existing_emis"] = doc_emi
                field_sources["existing_emis"] = filename

        # 4. Employer & Employment Type
        emp_name = extracted.get("employer_name") or sal_details.get("employer_name")
        if emp_name and "employer_name" not in merged_fields:
            merged_fields["employer_name"] = emp_name
            field_sources["employer_name"] = filename
            merged_fields["employment_type"] = "salaried"
            field_sources["employment_type"] = filename

        # 5. Age from DOB
        doc_age = flat_fields.get("age")
        if doc_age and "age" not in merged_fields:
            merged_fields["age"] = doc_age
            field_sources["age"] = filename

    # Detect conflicts between documents
    # Name conflicts
    if len(names_seen) > 1:
        base_name = names_seen[0][0].lower().split()
        for other_name, other_file in names_seen[1:]:
            other_tokens = set(other_name.lower().split())
            if not set(base_name).intersection(other_tokens):
                conflicts.append({
                    "field": "applicant_name",
                    "message": f"Name variance detected: '{names_seen[0][0]}' in {names_seen[0][1]} differs from '{other_name}' in {other_file}.",
                    "values": [f"{n} ({f})" for n, f in names_seen]
                })
                break

    # Income discrepancies between salary slip and bank credits
    if len(salaries_seen) > 1:
        s1, f1 = salaries_seen[0]
        s2, f2 = salaries_seen[1]
        diff_ratio = abs(s1 - s2) / max(s1, s2)
        if diff_ratio > 0.15:
            conflicts.append({
                "field": "monthly_income",
                "message": f"Income discrepancy: ₹{s1:,.0f} in {f1} vs ₹{s2:,.0f} in {f2} ({diff_ratio*100:.1f}% variance).",
                "values": [f"₹{s:,.0f} ({f})" for s, f in salaries_seen]
            })

    # Determine missing mandatory fields
    missing_fields = []
    for field_def in MANDATORY_LOAN_FIELDS:
        key = field_def["field_key"]
        val = merged_fields.get(key)
        # Check if missing or empty
        is_missing = val is None or val == ""
        if key == "monthly_income" and (val is None or val <= 0):
            is_missing = True
        if key == "applicant_name" and (not val or len(str(val).strip()) < 2):
            is_missing = True

        if is_missing:
            missing_fields.append(field_def)

    # Consistency score computation
    base_score = 1.0
    if conflicts:
        base_score -= 0.15 * len(conflicts)
    if not merged_fields.get("monthly_income"):
        base_score -= 0.10
    final_consistency = max(0.40, min(1.0, round(base_score, 2)))

    # Aggregate Evidence, Candidates & Math Validation
    all_evidence = []
    candidate_names = []
    signatories = []
    math_validations = []
    requires_name_confirmation = False

    for doc in docs:
        extracted = doc.get("extracted_data") or {}
        if extracted.get("evidence_list"):
            all_evidence.extend(extracted["evidence_list"])
        if extracted.get("candidate_names"):
            candidate_names.extend(extracted["candidate_names"])
        if extracted.get("signatories"):
            signatories.extend(extracted["signatories"])
        if extracted.get("math_validation"):
            math_validations.append(extracted["math_validation"])
        if extracted.get("requires_user_confirmation"):
            requires_name_confirmation = True

    # If multiple candidate names exist across documents without unanimous agreement, request confirmation
    unique_candidates = list({c["name"]: c for c in candidate_names if isinstance(c, dict) and "name" in c}.values())
    if len(unique_candidates) > 1:
        requires_name_confirmation = True

    return {
        "merged_fields": merged_fields,
        "field_sources": field_sources,
        "missing_fields": missing_fields,
        "conflicts": conflicts,
        "consistency_score": final_consistency,
        "total_documents": len(docs),
        "is_ready_for_review": len(missing_fields) == 0,
        "evidence_list": all_evidence,
        "candidate_names": unique_candidates,
        "signatories": signatories,
        "math_validations": math_validations,
        "requires_name_confirmation": requires_name_confirmation
    }

@router.get("/{doc_id}/preview")
def preview_document(doc_id: str, ext: str = ".pdf"):
    save_path = settings.UPLOAD_DIR / f"{doc_id}{ext}.enc"
    if not save_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")

    encrypted_bytes = save_path.read_bytes()
    fernet = get_fernet()
    try:
        decrypted_bytes = fernet.decrypt(encrypted_bytes)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to decrypt document.")

    media_type = "application/pdf" if ext == ".pdf" else f"image/{ext.replace('.', '')}"
    return Response(content=decrypted_bytes, media_type=media_type)
