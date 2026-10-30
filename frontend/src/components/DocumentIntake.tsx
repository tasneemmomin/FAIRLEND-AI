import React, { useState, useRef, useCallback } from "react";
import {
  Upload,
  FileText,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Loader2,
  ArrowRight,
  ArrowLeft,
  Eye,
  Edit3,
  X,
  FileBadge,
  Building,
  CreditCard,
  UserCheck,
  Info,
  Send,
  RotateCcw,
  Banknote
} from "lucide-react";
import { ApplicantIntakeForm, ApplicantResponse, ApplicantUser, UploadedDocumentItem } from "../types";
import { uploadIntakeDocument, analyzeIntakeDocuments, submitApplicantIntake } from "../api";
import { RecommendationCard } from "./RecommendationCard";

// ─────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────
type StepId = "upload" | "missing-fields" | "review" | "submitted";

interface MissingField {
  field_key: string;
  label: string;
  field_type: "text" | "number" | "select" | "tel" | "email";
  required: boolean;
  placeholder?: string;
  description?: string;
  options?: { value: string; label: string }[];
  default_value?: any;
}

interface AnalysisResult {
  merged_fields: Record<string, any>;
  missing_fields: MissingField[];
  conflicts: { field: string; values: any[]; sources: string[] }[];
  consistency_score: number;
  document_count: number;
  extracted_field_count: number;
  candidate_names?: { name: string; role: string; confidence: number; supporting_label: string }[];
  signatories?: { name: string; role: string; supporting_label: string }[];
  math_validations?: { math_validated: boolean; discrepancy_flag: boolean; message: string }[];
  requires_name_confirmation?: boolean;
  evidence_list?: any[];
}

interface DocumentIntakeProps {
  applicantUser: ApplicantUser | null;
  onSubmitted: (response: ApplicantResponse) => void;
}

// ─────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────
const DOC_TYPE_META: Record<string, { label: string; icon: React.ReactNode; color: string; bg: string }> = {
  salary_slip: {
    label: "Salary Slip",
    icon: <Banknote size={15} />,
    color: "text-emerald-700",
    bg: "bg-emerald-50 border-emerald-200"
  },
  bank_statement: {
    label: "Bank Statement",
    icon: <Building size={15} />,
    color: "text-blue-700",
    bg: "bg-blue-50 border-blue-200"
  },
  pan_card: {
    label: "PAN Card",
    icon: <CreditCard size={15} />,
    color: "text-violet-700",
    bg: "bg-violet-50 border-violet-200"
  },
  aadhaar_card: {
    label: "Aadhaar Card",
    icon: <UserCheck size={15} />,
    color: "text-amber-700",
    bg: "bg-amber-50 border-amber-200"
  },
  other_financial: {
    label: "Other Document",
    icon: <FileBadge size={15} />,
    color: "text-slate-600",
    bg: "bg-slate-50 border-slate-200"
  }
};

function docMeta(cat: string) {
  return DOC_TYPE_META[cat] || DOC_TYPE_META["other_financial"];
}

function fmt(val: any, prefix = ""): string {
  if (val === null || val === undefined || val === "") return "—";
  if (typeof val === "number") return `${prefix}${val.toLocaleString("en-IN")}`;
  return String(val);
}

const STEPS: { id: StepId; label: string }[] = [
  { id: "upload", label: "Upload Documents" },
  { id: "missing-fields", label: "Complete Details" },
  { id: "review", label: "Review & Confirm" },
  { id: "submitted", label: "Submitted" }
];

// ─────────────────────────────────────────────────────────
// Sub-component: Progress Stepper
// ─────────────────────────────────────────────────────────
function Stepper({ current }: { current: StepId }) {
  const idx = STEPS.findIndex((s) => s.id === current);
  return (
    <div className="flex items-center gap-0 mb-6">
      {STEPS.map((step, i) => {
        const done = i < idx;
        const active = i === idx;
        return (
          <React.Fragment key={step.id}>
            <div className="flex flex-col items-center min-w-0">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all ${
                  done
                    ? "bg-[#28766B] border-[#28766B] text-white"
                    : active
                    ? "bg-white border-[#28766B] text-[#28766B]"
                    : "bg-white border-[#CBD5E0] text-[#A0AEC0]"
                }`}
              >
                {done ? <CheckCircle2 size={14} /> : i + 1}
              </div>
              <span
                className={`text-[10px] mt-1 font-medium hidden sm:block truncate max-w-[80px] text-center ${
                  active ? "text-[#28766B]" : done ? "text-[#28766B]/70" : "text-[#A0AEC0]"
                }`}
              >
                {step.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div
                className={`flex-1 h-0.5 mx-1 mt-[-12px] ${done ? "bg-[#28766B]" : "bg-[#CBD5E0]"}`}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ─────────────────────────────────────────────────────────
// Sub-component: Document Card
// ─────────────────────────────────────────────────────────
function DocumentCard({
  doc,
  onRemove
}: {
  doc: UploadedDocumentItem;
  onRemove: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const meta = docMeta(doc.detected_category);
  const conf = Math.round((doc.confidence_score || 0) * 100);
  const fields = doc.extracted_data?.all_extracted_fields || {};
  const visibleFields = Object.entries(fields).filter(([, v]) => v !== null && v !== undefined && v !== "");

  return (
    <div className="bg-white rounded-xl border border-[#E3E8E5] shadow-sm overflow-hidden">
      <div className="flex items-center gap-3 p-4">
        <div className={`px-2 py-1 rounded-md border flex items-center gap-1.5 text-xs font-semibold ${meta.bg} ${meta.color}`}>
          {meta.icon}
          {meta.label}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-[#172C3D] truncate">{doc.filename}</p>
          <div className="flex items-center gap-2 mt-0.5">
            <div className="flex-1 h-1.5 bg-[#E3E8E5] rounded-full max-w-[80px]">
              <div
                className={`h-1.5 rounded-full ${conf >= 70 ? "bg-[#28766B]" : conf >= 40 ? "bg-amber-400" : "bg-rose-400"}`}
                style={{ width: `${conf}%` }}
              />
            </div>
            <span className={`text-[11px] font-semibold ${conf >= 70 ? "text-[#28766B]" : conf >= 40 ? "text-amber-600" : "text-rose-600"}`}>
              {conf}% confidence
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setExpanded((e) => !e)}
            className="p-1.5 rounded-lg hover:bg-[#F7F8F5] text-[#718096] transition"
            title={expanded ? "Collapse details" : "View extracted data"}
          >
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          <button
            type="button"
            onClick={onRemove}
            className="p-1.5 rounded-lg hover:bg-rose-50 text-[#A0AEC0] hover:text-rose-500 transition"
            title="Remove document"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-[#E3E8E5] bg-[#F8FAFC] px-4 py-3">
          {visibleFields.length === 0 ? (
            <p className="text-xs text-[#718096] italic">No structured data could be extracted from this document.</p>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-2">
              {visibleFields.slice(0, 18).map(([k, v]) => (
                <div key={k}>
                  <p className="text-[10px] text-[#A0AEC0] uppercase tracking-wide">{k.replace(/_/g, " ")}</p>
                  <p className="text-xs font-semibold text-[#2D3748] truncate">
                    {typeof v === "number" ? `₹${v.toLocaleString("en-IN")}` : String(v)}
                  </p>
                </div>
              ))}
              {visibleFields.length > 18 && (
                <p className="text-[11px] text-[#28766B] col-span-full">+{visibleFields.length - 18} more fields extracted</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────
export const DocumentIntake: React.FC<DocumentIntakeProps> = ({ applicantUser, onSubmitted }) => {
  const [step, setStep] = useState<StepId>("upload");
  const [documents, setDocuments] = useState<UploadedDocumentItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [manualInputs, setManualInputs] = useState<Record<string, any>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submittedResponse, setSubmittedResponse] = useState<ApplicantResponse | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Upload handlers ──────────────────────────────────────
  const handleFiles = useCallback(
    async (files: FileList | File[]) => {
      const arr = Array.from(files);
      if (arr.length === 0) return;

      setUploading(true);
      setUploadError(null);

      for (const file of arr) {
        const fd = new FormData();
        fd.append("file", file);
        try {
          const result = await uploadIntakeDocument(fd);
          const item: UploadedDocumentItem = {
            doc_id: result.doc_id || `local-${Date.now()}`,
            filename: file.name,
            detected_category: result.detected_category || "other_financial",
            doc_type: result.detected_category || "other_financial",
            confidence_score: result.confidence_score ?? 0.5,
            extracted_data: result.extracted_data || {},
            mismatch_flags: result.mismatch_flags || []
          };
          setDocuments((prev) => [...prev, item]);
        } catch (err: any) {
          setUploadError(`Failed to upload "${file.name}": ${err.message}`);
        }
      }
      setUploading(false);
    },
    []
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };
  const handleDragLeave = () => setIsDragging(false);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) handleFiles(e.target.files);
    e.target.value = "";
  };

  const removeDocument = (docId: string) => {
    setDocuments((prev) => prev.filter((d) => d.doc_id !== docId));
  };

  // ── Analyze ──────────────────────────────────────────────
  const handleAnalyze = async () => {
    if (documents.length === 0) return;
    setAnalyzing(true);
    setUploadError(null);
    try {
      const profile = applicantUser
        ? { name: applicantUser.name, email: applicantUser.email, phone: applicantUser.phone }
        : undefined;
      const result: AnalysisResult = await analyzeIntakeDocuments(
        documents.map((d) => ({
          doc_id: d.doc_id,
          filename: d.filename,
          detected_category: d.detected_category,
          confidence_score: d.confidence_score,
          extracted_data: d.extracted_data
        })),
        profile
      );
      setAnalysisResult(result);
      // Pre-fill manual inputs with defaults from missing fields
      const defaults: Record<string, any> = {};
      (result.missing_fields || []).forEach((f) => {
        if (f.default_value !== undefined && f.default_value !== null) {
          defaults[f.field_key] = f.default_value;
        }
      });
      // Also pre-fill from applicant profile
      if (applicantUser) {
        if (!result.merged_fields?.applicant_name && applicantUser.name) defaults.applicant_name = applicantUser.name;
        if (!result.merged_fields?.contact_email && applicantUser.email) defaults.contact_email = applicantUser.email;
        if (!result.merged_fields?.contact_phone && applicantUser.phone) defaults.contact_phone = applicantUser.phone;
      }
      setManualInputs(defaults);
      setStep("missing-fields");
    } catch (err: any) {
      setUploadError(`Analysis failed: ${err.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  // ── Missing-fields form helpers ──────────────────────────
  const setManual = (key: string, value: any) => {
    setManualInputs((prev) => ({ ...prev, [key]: value }));
  };

  const allRequiredFilled = () => {
    if (!analysisResult) return false;
    return analysisResult.missing_fields
      .filter((f) => f.required)
      .every((f) => {
        const merged = analysisResult.merged_fields?.[f.field_key];
        const manual = manualInputs[f.field_key];
        return (merged !== undefined && merged !== null && merged !== "") ||
          (manual !== undefined && manual !== null && manual !== "");
      });
  };

  // ── Build final IntakeForm payload ───────────────────────
  const buildIntakePayload = (): ApplicantIntakeForm => {
    const merged = analysisResult?.merged_fields || {};
    const get = (key: string, fallback: any) => {
      if (manualInputs[key] !== undefined && manualInputs[key] !== null && manualInputs[key] !== "") return manualInputs[key];
      if (merged[key] !== undefined && merged[key] !== null && merged[key] !== "") return merged[key];
      return fallback;
    };

    return {
      applicant_name: get("applicant_name", applicantUser?.name || "Unknown"),
      contact_phone: get("contact_phone", applicantUser?.phone || ""),
      contact_email: get("contact_email", applicantUser?.email || ""),
      age: Number(get("age", 28)),
      employment_type: get("employment_type", "salaried"),
      employment_duration_months: Number(get("employment_duration_months", 24)),
      monthly_income: Number(get("monthly_income", 0)),
      existing_emis: Number(get("existing_emis", 0)),
      requested_amount: Number(get("requested_amount", 200000)),
      tenure_months: Number(get("tenure_months", 24)),
      loan_purpose: get("loan_purpose", "personal"),
      dependents: Number(get("dependents", 0)),
      residence_type: get("residence_type", "rented"),
      credit_history_years: Number(get("credit_history_years", 1.0)),
      collateral_value: Number(get("collateral_value", 0)),
      intake_mode: "document",
      intake_transcript: `Document Intake — ${documents.length} document(s): ${documents.map((d) => d.filename).join(", ")}`,
      audit_consent: Boolean(get("audit_consent", false)),
      audit_gender: get("audit_gender", "prefer_not_say"),
      audit_social_group: get("audit_social_group", ""),
      audit_geography_tier: get("audit_geography_tier", "tier1")
    };
  };

  // ── Submit ───────────────────────────────────────────────
  const handleSubmit = async () => {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const payload = buildIntakePayload();
      const response = await submitApplicantIntake(payload);
      setSubmittedResponse(response);
      setStep("submitted");
      onSubmitted(response);
    } catch (err: any) {
      setSubmitError(err.message || "Submission failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  // ── Reset ─────────────────────────────────────────────────
  const handleReset = () => {
    setDocuments([]);
    setAnalysisResult(null);
    setManualInputs({});
    setSubmittedResponse(null);
    setSubmitError(null);
    setUploadError(null);
    setStep("upload");
  };

  // ─────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-[#E3E8E5] overflow-hidden">
      {/* Header */}
      <div className="bg-[#172C3D] px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#28766B] flex items-center justify-center">
            <Upload size={16} className="text-white" />
          </div>
          <div>
            <h2 className="font-serif font-bold text-white text-base">Document Intake</h2>
            <p className="text-[11px] text-[#A0B2C0] mt-0.5">
              Upload financial documents — we'll extract and verify your details automatically
            </p>
          </div>
        </div>
      </div>

      <div className="p-6">
        <Stepper current={step} />

        {/* ─────── STEP 1: UPLOAD ─────── */}
        {step === "upload" && (
          <div className="space-y-5">
            {/* Drop Zone */}
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                isDragging
                  ? "border-[#28766B] bg-[#28766B]/5"
                  : "border-[#CBD5E0] hover:border-[#28766B]/60 hover:bg-[#F8FAFC]"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.png,.jpg,.jpeg,.webp,.tiff"
                className="hidden"
                onChange={handleFileInput}
              />
              {uploading ? (
                <div className="flex flex-col items-center gap-3">
                  <Loader2 size={32} className="text-[#28766B] animate-spin" />
                  <p className="text-sm text-[#718096] font-medium">Processing document…</p>
                </div>
              ) : (
                <>
                  <Upload size={36} className="mx-auto text-[#A0AEC0] mb-3" />
                  <p className="text-sm font-semibold text-[#172C3D]">
                    Drag & drop documents here, or{" "}
                    <span className="text-[#28766B] underline underline-offset-2">browse files</span>
                  </p>
                  <p className="text-xs text-[#A0AEC0] mt-1">
                    PDF, PNG, JPG, WEBP • Max 20 MB per file
                  </p>
                </>
              )}
            </div>

            {/* Supported Document Types */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {(["salary_slip", "bank_statement", "pan_card", "aadhaar_card"] as const).map((type) => {
                const m = docMeta(type);
                return (
                  <div key={type} className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-medium ${m.bg} ${m.color}`}>
                    {m.icon}
                    {m.label}
                  </div>
                );
              })}
            </div>

            {/* Uploaded Documents List */}
            {documents.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-[#172C3D]">
                    Uploaded Documents ({documents.length})
                  </h3>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="text-xs text-[#28766B] font-semibold hover:underline flex items-center gap-1"
                  >
                    <Upload size={13} /> Add More
                  </button>
                </div>
                {documents.map((doc) => (
                  <DocumentCard
                    key={doc.doc_id}
                    doc={doc}
                    onRemove={() => removeDocument(doc.doc_id)}
                  />
                ))}
              </div>
            )}

            {uploadError && (
              <div className="flex items-start gap-2 p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700">
                <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                {uploadError}
              </div>
            )}

            <div className="flex items-center justify-between pt-2">
              <p className="text-xs text-[#A0AEC0] flex items-center gap-1.5">
                <Info size={13} />
                Identity data (Aadhaar, PAN) is masked and never used in credit scoring
              </p>
              <button
                type="button"
                disabled={documents.length === 0 || uploading || analyzing}
                onClick={handleAnalyze}
                className="flex items-center gap-2 px-5 py-2 bg-[#28766B] text-white rounded-lg text-sm font-semibold shadow hover:bg-[#1f5f55] transition disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {analyzing ? (
                  <>
                    <Loader2 size={15} className="animate-spin" /> Analysing…
                  </>
                ) : (
                  <>
                    Analyse & Continue <ArrowRight size={15} />
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* ─────── STEP 2: MISSING FIELDS ─────── */}
        {step === "missing-fields" && analysisResult && (
          <div className="space-y-5">
            {/* Summary banner */}
            <div className="bg-[#F0F9F6] border border-[#A7D7CF] rounded-xl px-4 py-3 flex items-center gap-3">
              <CheckCircle2 size={18} className="text-[#28766B] shrink-0" />
              <div>
                <p className="text-sm font-semibold text-[#172C3D]">
                  {analysisResult.extracted_field_count} fields extracted from {analysisResult.document_count} document
                  {analysisResult.document_count !== 1 ? "s" : ""}
                </p>
                <p className="text-xs text-[#718096] mt-0.5">
                  Consistency score:{" "}
                  <span
                    className={`font-bold ${
                      analysisResult.consistency_score >= 0.8
                        ? "text-[#28766B]"
                        : analysisResult.consistency_score >= 0.5
                        ? "text-amber-600"
                        : "text-rose-600"
                    }`}
                  >
                    {Math.round(analysisResult.consistency_score * 100)}%
                  </span>
                </p>
              </div>
            </div>

            {/* Conflicts */}
            {analysisResult.conflicts?.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-2">
                <div className="flex items-center gap-2 text-amber-700 font-semibold text-sm">
                  <AlertTriangle size={15} />
                  Data Conflicts Detected
                </div>
                {analysisResult.conflicts.map((c, i) => (
                  <div key={i} className="text-xs text-amber-800 flex items-start gap-2">
                    <span className="font-bold shrink-0">{c.field}:</span>
                    <span>
                      {c.values.map((v, vi) => `"${v}" (${c.sources[vi] || "doc"})`).join(" vs ")}
                    </span>
                  </div>
                ))}
                <p className="text-[11px] text-amber-600 mt-1">
                  Please verify the values below and enter the correct information.
                </p>
              </div>
            )}

            {/* Candidate Disambiguation Card: When multiple individuals detected */}
            {analysisResult.candidate_names && analysisResult.candidate_names.length > 1 && (
              <div className="bg-[#F0FDF4] border border-[#86EFAC] rounded-xl p-4 space-y-3">
                <div className="flex items-center gap-2 text-[#166534] font-semibold text-sm">
                  <UserCheck size={16} />
                  Multiple Individuals Detected — Please Confirm Applicant
                </div>
                <p className="text-xs text-[#15803D]">
                  Our NLP engine detected multiple names in your uploaded documents (such as approving authority, DDO, HR signatory, or employee). Please select the actual loan applicant:
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {analysisResult.candidate_names.map((cand, ci) => {
                    const isSelected = (manualInputs.applicant_name || analysisResult.merged_fields?.applicant_name) === cand.name;
                    return (
                      <button
                        key={ci}
                        type="button"
                        onClick={() => setManual("applicant_name", cand.name)}
                        className={`p-2.5 rounded-lg border text-left text-xs font-medium transition flex items-center justify-between ${
                          isSelected
                            ? "bg-[#28766B] text-white border-[#28766B] shadow-sm"
                            : "bg-white text-[#172C3D] border-[#CBD5E1] hover:border-[#28766B]"
                        }`}
                      >
                        <div>
                          <div className="font-bold">{cand.name}</div>
                          <div className={`text-[10px] ${isSelected ? "text-white/80" : "text-[#64748B]"}`}>
                            Role: {cand.role.toUpperCase()} • {cand.supporting_label}
                          </div>
                        </div>
                        {isSelected && <CheckCircle2 size={16} className="text-white shrink-0 ml-2" />}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Mathematical Balance Validation Badges */}
            {analysisResult.math_validations && analysisResult.math_validations.length > 0 && (
              <div className="space-y-2">
                {analysisResult.math_validations.map((mv, mvi) => (
                  <div
                    key={mvi}
                    className={`rounded-xl px-4 py-2.5 border text-xs flex items-center gap-2 ${
                      mv.math_validated
                        ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                        : mv.discrepancy_flag
                        ? "bg-amber-50 border-amber-200 text-amber-800"
                        : "bg-slate-50 border-slate-200 text-slate-700"
                    }`}
                  >
                    {mv.math_validated ? (
                      <CheckCircle2 size={15} className="text-emerald-600 shrink-0" />
                    ) : (
                      <AlertTriangle size={15} className="text-amber-600 shrink-0" />
                    )}
                    <span>{mv.message}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Extracted values summary (read-only) */}
            {Object.keys(analysisResult.merged_fields || {}).length > 0 && (
              <div>
                <h3 className="text-xs font-bold text-[#172C3D] uppercase tracking-wide mb-2">
                  Extracted from Documents
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {Object.entries(analysisResult.merged_fields)
                    .filter(([, v]) => v !== null && v !== undefined && v !== "")
                    .slice(0, 15)
                    .map(([k, v]) => (
                      <div key={k} className="bg-[#F8FAFC] border border-[#E3E8E5] rounded-lg px-3 py-2">
                        <p className="text-[10px] text-[#A0AEC0] uppercase tracking-wide">{k.replace(/_/g, " ")}</p>
                        <p className="text-xs font-semibold text-[#2D3748] truncate">
                          {typeof v === "number" ? `₹${v.toLocaleString("en-IN")}` : String(v)}
                        </p>
                      </div>
                    ))}
                </div>
              </div>
            )}

            {/* Missing fields form */}
            {analysisResult.missing_fields?.length > 0 && (
              <div>
                <h3 className="text-xs font-bold text-[#172C3D] uppercase tracking-wide mb-3">
                  Please provide the missing details
                  <span className="text-rose-500 ml-1">({analysisResult.missing_fields.filter((f) => f.required).length} required)</span>
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {analysisResult.missing_fields.map((field) => (
                    <div key={field.field_key}>
                      <label className="block text-xs font-semibold text-[#2D3748] mb-1">
                        {field.label}
                        {field.required && <span className="text-rose-500 ml-0.5">*</span>}
                      </label>
                      {field.description && (
                        <p className="text-[11px] text-[#718096] mb-1">{field.description}</p>
                      )}
                      {field.field_type === "select" && field.options ? (
                        <select
                          value={manualInputs[field.field_key] ?? ""}
                          onChange={(e) => setManual(field.field_key, e.target.value)}
                          className="w-full border border-[#E3E8E5] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#28766B]/40 focus:border-[#28766B] transition bg-white"
                        >
                          <option value="">Select…</option>
                          {field.options.map((o) => (
                            <option key={o.value} value={o.value}>{o.label}</option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type={field.field_type}
                          value={manualInputs[field.field_key] ?? ""}
                          onChange={(e) =>
                            setManual(
                              field.field_key,
                              field.field_type === "number" ? Number(e.target.value) : e.target.value
                            )
                          }
                          placeholder={field.placeholder}
                          className="w-full border border-[#E3E8E5] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#28766B]/40 focus:border-[#28766B] transition"
                        />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Loan request fields (always ask) */}
            <div>
              <h3 className="text-xs font-bold text-[#172C3D] uppercase tracking-wide mb-3">Loan Request</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-[#2D3748] mb-1">Requested Loan Amount (₹)<span className="text-rose-500 ml-0.5">*</span></label>
                  <input
                    type="number"
                    value={manualInputs.requested_amount ?? analysisResult.merged_fields?.requested_amount ?? ""}
                    onChange={(e) => setManual("requested_amount", Number(e.target.value))}
                    placeholder="e.g. 300000"
                    className="w-full border border-[#E3E8E5] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#28766B]/40 focus:border-[#28766B] transition"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#2D3748] mb-1">Tenure (Months)<span className="text-rose-500 ml-0.5">*</span></label>
                  <select
                    value={manualInputs.tenure_months ?? analysisResult.merged_fields?.tenure_months ?? "24"}
                    onChange={(e) => setManual("tenure_months", Number(e.target.value))}
                    className="w-full border border-[#E3E8E5] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#28766B]/40 focus:border-[#28766B] transition bg-white"
                  >
                    {[6, 12, 18, 24, 36, 48, 60, 84].map((m) => (
                      <option key={m} value={m}>{m} months</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#2D3748] mb-1">Loan Purpose</label>
                  <select
                    value={manualInputs.loan_purpose ?? analysisResult.merged_fields?.loan_purpose ?? "personal"}
                    onChange={(e) => setManual("loan_purpose", e.target.value)}
                    className="w-full border border-[#E3E8E5] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#28766B]/40 focus:border-[#28766B] transition bg-white"
                  >
                    {[
                      { value: "personal", label: "Personal" },
                      { value: "home_improvement", label: "Home Improvement" },
                      { value: "education", label: "Education" },
                      { value: "medical", label: "Medical" },
                      { value: "vehicle", label: "Vehicle" },
                      { value: "debt_consolidation", label: "Debt Consolidation" },
                      { value: "business", label: "Business" },
                      { value: "other", label: "Other" }
                    ].map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#2D3748] mb-1">Existing EMIs (₹/month)</label>
                  <input
                    type="number"
                    value={manualInputs.existing_emis ?? analysisResult.merged_fields?.existing_emis ?? "0"}
                    onChange={(e) => setManual("existing_emis", Number(e.target.value))}
                    placeholder="0"
                    className="w-full border border-[#E3E8E5] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#28766B]/40 focus:border-[#28766B] transition"
                  />
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <button
                type="button"
                onClick={() => setStep("upload")}
                className="flex items-center gap-1.5 px-4 py-2 border border-[#E3E8E5] rounded-lg text-sm font-semibold text-[#718096] hover:bg-[#F7F8F5] transition"
              >
                <ArrowLeft size={14} /> Back
              </button>
              <button
                type="button"
                disabled={!(
                  (manualInputs.requested_amount || analysisResult.merged_fields?.requested_amount) &&
                  (manualInputs.tenure_months || analysisResult.merged_fields?.tenure_months)
                )}
                onClick={() => setStep("review")}
                className="flex items-center gap-2 px-5 py-2 bg-[#28766B] text-white rounded-lg text-sm font-semibold shadow hover:bg-[#1f5f55] transition disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Review Application <ArrowRight size={14} />
              </button>
            </div>
          </div>
        )}

        {/* ─────── STEP 3: REVIEW ─────── */}
        {step === "review" && analysisResult && (
          <div className="space-y-5">
            <div className="bg-[#F0F9F6] border border-[#A7D7CF] rounded-xl px-4 py-3 flex items-start gap-3">
              <Eye size={16} className="text-[#28766B] mt-0.5 shrink-0" />
              <p className="text-sm text-[#2D3748]">
                Please review the information below before submitting. You can go back to make corrections.
              </p>
            </div>

            {/* Documents used */}
            <div>
              <h3 className="text-xs font-bold text-[#172C3D] uppercase tracking-wide mb-3">Documents Processed</h3>
              <div className="space-y-2">
                {documents.map((doc) => {
                  const m = docMeta(doc.detected_category);
                  return (
                    <div key={doc.doc_id} className="flex items-center gap-3 p-3 bg-[#F8FAFC] border border-[#E3E8E5] rounded-lg text-xs">
                      <div className={`px-2 py-1 rounded border flex items-center gap-1 ${m.bg} ${m.color} font-medium`}>
                        {m.icon} {m.label}
                      </div>
                      <span className="flex-1 text-[#2D3748] font-medium truncate">{doc.filename}</span>
                      <span className={`font-semibold ${doc.confidence_score >= 0.7 ? "text-[#28766B]" : "text-amber-600"}`}>
                        {Math.round(doc.confidence_score * 100)}% confidence
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Application summary table */}
            <div>
              <h3 className="text-xs font-bold text-[#172C3D] uppercase tracking-wide mb-3">Application Summary</h3>
              {(() => {
                const p = buildIntakePayload();
                const rows: { label: string; value: string; source: "document" | "manual" | "profile" }[] = [
                  { label: "Applicant Name", value: p.applicant_name, source: "profile" },
                  { label: "Contact Email", value: p.contact_email || "—", source: "profile" },
                  { label: "Contact Phone", value: p.contact_phone || "—", source: "profile" },
                  { label: "Age", value: `${p.age} years`, source: "manual" },
                  { label: "Employment Type", value: p.employment_type, source: "document" },
                  { label: "Employment Duration", value: `${p.employment_duration_months} months`, source: "manual" },
                  { label: "Monthly Income", value: `₹${p.monthly_income.toLocaleString("en-IN")}`, source: "document" },
                  { label: "Existing EMIs", value: `₹${p.existing_emis.toLocaleString("en-IN")}/mo`, source: p.existing_emis > 0 ? "document" : "manual" },
                  { label: "Requested Amount", value: `₹${p.requested_amount.toLocaleString("en-IN")}`, source: "manual" },
                  { label: "Tenure", value: `${p.tenure_months} months`, source: "manual" },
                  { label: "Loan Purpose", value: p.loan_purpose, source: "manual" },
                  { label: "Dependents", value: String(p.dependents), source: "manual" },
                  { label: "Residence Type", value: p.residence_type, source: "manual" },
                  { label: "Credit History", value: `${p.credit_history_years} years`, source: "manual" }
                ];
                return (
                  <div className="border border-[#E3E8E5] rounded-xl overflow-hidden">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-[#F8FAFC] border-b border-[#E3E8E5]">
                          <th className="text-left px-4 py-2.5 text-xs font-bold text-[#718096] uppercase tracking-wide">Field</th>
                          <th className="text-left px-4 py-2.5 text-xs font-bold text-[#718096] uppercase tracking-wide">Value</th>
                          <th className="text-left px-4 py-2.5 text-xs font-bold text-[#718096] uppercase tracking-wide">Source</th>
                        </tr>
                      </thead>
                      <tbody>
                        {rows.map((row, i) => (
                          <tr key={i} className={i % 2 === 0 ? "bg-white" : "bg-[#F8FAFC]"}>
                            <td className="px-4 py-2.5 text-xs text-[#718096] font-medium">{row.label}</td>
                            <td className="px-4 py-2.5 text-xs text-[#2D3748] font-semibold">{row.value}</td>
                            <td className="px-4 py-2.5">
                              <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                                row.source === "document"
                                  ? "bg-blue-50 text-blue-700 border-blue-200"
                                  : row.source === "profile"
                                  ? "bg-violet-50 text-violet-700 border-violet-200"
                                  : "bg-slate-50 text-slate-600 border-slate-200"
                              }`}>
                                {row.source === "document" ? "📄 Document" : row.source === "profile" ? "👤 Profile" : "✏️ Entered"}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                );
              })()}
            </div>

            {/* Audit consent */}
            <div className="bg-[#F8FAFC] border border-[#E3E8E5] rounded-xl p-4">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={Boolean(manualInputs.audit_consent)}
                  onChange={(e) => setManual("audit_consent", e.target.checked)}
                  className="mt-0.5 w-4 h-4 accent-[#28766B]"
                />
                <span className="text-xs text-[#718096] leading-relaxed">
                  I consent to anonymised fairness auditing of this application for research purposes. Demographic data is quarantined from credit decisions and used only to monitor model bias.
                </span>
              </label>
            </div>

            {submitError && (
              <div className="flex items-start gap-2 p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700">
                <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                {submitError}
              </div>
            )}

            <div className="flex items-center justify-between pt-2">
              <button
                type="button"
                onClick={() => setStep("missing-fields")}
                className="flex items-center gap-1.5 px-4 py-2 border border-[#E3E8E5] rounded-lg text-sm font-semibold text-[#718096] hover:bg-[#F7F8F5] transition"
              >
                <Edit3 size={14} /> Edit Details
              </button>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={submitting}
                className="flex items-center gap-2 px-6 py-2.5 bg-[#28766B] text-white rounded-lg text-sm font-bold shadow hover:bg-[#1f5f55] transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? (
                  <>
                    <Loader2 size={15} className="animate-spin" /> Submitting…
                  </>
                ) : (
                  <>
                    <Send size={15} /> Submit Application
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* ─────── STEP 4: SUBMITTED ─────── */}
        {step === "submitted" && submittedResponse && (
          <div className="space-y-5">
            <RecommendationCard
              response={submittedResponse}
              onReset={handleReset}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentIntake;

