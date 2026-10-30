import React, { useState } from "react";
import { UploadCloud, FileText, CheckCircle2, AlertTriangle, RefreshCw } from "lucide-react";
import { uploadDocument } from "../api";

interface DocumentUploaderProps {
  declaredIncome?: number;
  declaredName?: string;
  onExtracted: (extracted: any, consistencyScore: number) => void;
}

export const DocumentUploader: React.FC<DocumentUploaderProps> = ({
  declaredIncome,
  declaredName,
  onExtracted,
}) => {
  const [docType, setDocType] = useState("salary_slip");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    await processUpload(file);
  };

  const handleDrop = async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      await processUpload(e.dataTransfer.files[0]);
    }
  };

  const processUpload = async (file: File) => {
    setIsUploading(true);
    setErrorMessage(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("doc_type", docType);
    if (declaredIncome) formData.append("declared_income", declaredIncome.toString());
    if (declaredName) formData.append("declared_name", declaredName);

    try {
      const res = await uploadDocument(formData);
      setUploadResult(res);
      onExtracted(res.extracted_data, res.consistency_score);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to process document");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-md border border-slate-200 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-slate-800 text-base">Document Verification & OCR</h3>
          <p className="text-xs text-slate-500">Upload salary slip or bank statement for automatic cross-verification.</p>
        </div>
        <select
          value={docType}
          onChange={(e) => setDocType(e.target.value)}
          className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 focus:ring-teal-500 focus:outline-none"
        >
          <option value="salary_slip">Salary Slip</option>
          <option value="bank_statement">Bank Statement</option>
          <option value="id_proof">Identity Proof</option>
        </select>
      </div>

      {/* Drag and Drop Zone */}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        className="border-2 border-dashed border-slate-300 hover:border-teal-500 rounded-xl p-6 text-center cursor-pointer transition bg-slate-50 hover:bg-slate-100 flex flex-col items-center justify-center gap-2 relative"
      >
        <input
          type="file"
          accept=".pdf,.png,.jpg,.jpeg"
          onChange={handleFileChange}
          disabled={isUploading}
          className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
        />
        {isUploading ? (
          <div className="flex flex-col items-center gap-2">
            <RefreshCw className="animate-spin text-teal-600" size={32} />
            <p className="text-sm font-medium text-slate-700">Extracting fields and verifying consistency...</p>
          </div>
        ) : (
          <>
            <UploadCloud className="text-teal-600" size={36} />
            <p className="text-sm font-medium text-slate-700">
              Drag & drop document here, or <span className="text-teal-600 underline">browse</span>
            </p>
            <p className="text-xs text-slate-400">PDF, PNG, or JPG (Max 10MB) - Encrypted at rest</p>
          </>
        )}
      </div>

      {errorMessage && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-lg flex items-center gap-2">
          <AlertTriangle size={16} className="text-rose-600 flex-shrink-0" />
          {errorMessage}
        </div>
      )}

      {/* Upload & Extraction Summary */}
      {uploadResult && (
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-200 pb-2">
            <div className="flex items-center gap-2">
              <FileText size={18} className="text-teal-600" />
              <span className="text-sm font-semibold text-slate-800">{uploadResult.filename}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">Consistency Score:</span>
              <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold ${
                uploadResult.consistency_score >= 0.85
                  ? "bg-emerald-100 text-emerald-800"
                  : uploadResult.consistency_score >= 0.70
                  ? "bg-amber-100 text-amber-800"
                  : "bg-rose-100 text-rose-800"
              }`}>
                {(uploadResult.consistency_score * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          {/* Extracted Fields Grid */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <span className="text-slate-400 block">Extracted Name:</span>
              <span className="font-semibold text-slate-700">{uploadResult.extracted_data.extracted_name || "Not detected"}</span>
            </div>
            <div>
              <span className="text-slate-400 block">Employer:</span>
              <span className="font-semibold text-slate-700">{uploadResult.extracted_data.employer_name || "Not detected"}</span>
            </div>
            <div>
              <span className="text-slate-400 block">Verified Monthly Salary:</span>
              <span className="font-semibold text-teal-700">
                {uploadResult.extracted_data.monthly_salary ? `₹${uploadResult.extracted_data.monthly_salary.toLocaleString("en-IN")}` : "Not detected"}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block">Average Balance / Credits:</span>
              <span className="font-semibold text-slate-700">
                {uploadResult.extracted_data.average_bank_balance
                  ? `₹${uploadResult.extracted_data.average_bank_balance.toLocaleString("en-IN")}`
                  : uploadResult.extracted_data.total_credits
                  ? `₹${uploadResult.extracted_data.total_credits.toLocaleString("en-IN")}`
                  : "Not detected"}
              </span>
            </div>
          </div>

          {/* Mismatch Flags */}
          {uploadResult.mismatch_flags && uploadResult.mismatch_flags.length > 0 && (
            <div className="mt-2 space-y-1.5 border-t border-slate-200 pt-2">
              {uploadResult.mismatch_flags.map((flag: any, idx: number) => (
                <div key={idx} className="flex items-start gap-2 text-xs text-amber-900 bg-amber-50 p-2 rounded border border-amber-200">
                  <AlertTriangle size={14} className="text-amber-600 flex-shrink-0 mt-0.5" />
                  <span>{flag.message}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
