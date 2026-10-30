import React, { useState } from "react";
import { CheckCircle2, AlertCircle, XCircle, Volume2, Download, Trash2, ShieldCheck, ChevronRight, FileText, Sparkles } from "lucide-react";
import { ApplicantResponse } from "../types";
import { exportPrivacyData, deletePrivacyData } from "../api";

interface RecommendationCardProps {
  response: ApplicantResponse;
  onReset: () => void;
}

export const RecommendationCard: React.FC<RecommendationCardProps> = ({ response, onReset }) => {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [privacyMessage, setPrivacyMessage] = useState<string | null>(null);

  const getStatusBadge = () => {
    switch (response.recommendation_code) {
      case "likely_approved":
        return {
          bg: "bg-emerald-50 border-emerald-300 text-emerald-900",
          icon: <CheckCircle2 size={32} className="text-emerald-600" />,
          pill: "bg-emerald-600 text-white",
          label: "Likely to be approved"
        };
      case "needs_review":
        return {
          bg: "bg-amber-50 border-amber-300 text-amber-900",
          icon: <AlertCircle size={32} className="text-amber-600" />,
          pill: "bg-amber-600 text-white",
          label: "Needs more review"
        };
      case "unlikely_approved":
      default:
        return {
          bg: "bg-rose-50 border-rose-300 text-rose-900",
          icon: <XCircle size={32} className="text-rose-600" />,
          pill: "bg-rose-600 text-white",
          label: "Unlikely to be approved right now"
        };
    }
  };

  const badge = getStatusBadge();

  const handleReadAloud = () => {
    if (!("speechSynthesis" in window)) return;
    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    const reasonsText = response.reasons.join(". ");
    const cfText = response.counterfactuals.map((c) => c.change_description).join(". ");
    const fullSpeech = `Your loan assessment status is: ${badge.label}. Confidence: ${response.confidence}. Why we think this: ${reasonsText}. ${cfText ? "What could change this result: " + cfText : ""}`;

    const utterance = new SpeechSynthesisUtterance(fullSpeech);
    utterance.rate = 0.95;
    utterance.lang = "en-IN";
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    setIsSpeaking(true);
    window.speechSynthesis.speak(utterance);
  };

  const handleExportData = async () => {
    try {
      const data = await exportPrivacyData(response.application_id);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `FairLendAI_Application_${response.application_id}.json`;
      a.click();
      setPrivacyMessage("Your personal data file has been downloaded (DPDP Act right to portability).");
    } catch (e: any) {
      setPrivacyMessage("Failed to export data: " + e.message);
    }
  };

  const handleDeleteData = async () => {
    if (!confirm("Are you sure you want to permanently erase your personal data under the DPDP Act 2023?")) return;
    try {
      await deletePrivacyData(response.application_id);
      setPrivacyMessage("Your personal identifying data has been permanently erased from active storage.");
    } catch (e: any) {
      setPrivacyMessage("Failed to erase data: " + e.message);
    }
  };

  const handleDownloadSummaryText = () => {
    const isApproved = response.recommendation_code === "likely_approved";
    const statusLabel = isApproved ? "LIKELY APPROVED" : "NEEDS MORE REVIEW";
    const cfs = response.counterfactuals || [];
    
    const lines = [
      "================================================================================",
      "                    FAIRLENDAI APPLICANT DECISION SUMMARY",
      "              (Explainable & Voice-Enabled AI Loan Assessment — FairLendAI)",
      "================================================================================",
      `Date & Time:              ${new Date().toISOString()}`,
      `Application Reference ID: ${response.application_id}`,
      `Applicant Full Name:      ${response.applicant_name}`,
      `Recommendation Status:    ${statusLabel}`,
      `Confidence Level:         ${response.confidence.toUpperCase()}`,
      "",
      "--------------------------------------------------------------------------------",
      "1. KEY FINANCIAL PROFILE EVALUATED",
      "--------------------------------------------------------------------------------",
      `Debt-to-Income (FOIR):    ${response.foir_percentage}% (Policy Benchmark: under 45%)`,
      `Loan-to-Income Ratio:     ${response.loan_to_income_ratio}x yearly income (Policy Benchmark: under 3x)`,
      `Document Match Score:     ${Math.round(response.consistency_score * 100)}% consistency (Declared vs Document)`,
      "",
      "--------------------------------------------------------------------------------",
      "2. WHY WE THINK THIS (EXPLAINABLE REASONS)",
      "--------------------------------------------------------------------------------",
      ...response.reasons.map((r, i) => ` [${i + 1}] ${r}`),
      "",
      "--------------------------------------------------------------------------------",
      "3. COUNTERFACTUAL AI & RECOURSE SENSITIVITY ADVICE",
      "--------------------------------------------------------------------------------",
      ...(cfs.length > 0
        ? cfs.map((cf, i) => ` [${i + 1}] ${cf.change_description}\n     Category: ${cf.actionability}`)
        : [" Prime financial standing across all evaluated scorecard metrics."]),
      "",
      "--------------------------------------------------------------------------------",
      "4. REGULATORY & STATUTORY COMPLIANCE NOTICE",
      "--------------------------------------------------------------------------------",
      " * Evaluated strictly in accordance with RBI Digital Lending Guidelines (2022).",
      " * Protected attributes (gender, caste, religion) were never collected or used as credit features.",
      " * Fully compliant with India Digital Personal Data Protection (DPDP) Act 2023.",
      " * Underwriting officer retains sole final discretion. You have the right to request a human review.",
      "================================================================================",
      "                       END OF APPLICANT DECISION SUMMARY",
      "================================================================================"
    ];

    const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `FairLendAI_Decision_${response.application_id.slice(0, 8)}_${isApproved ? "approved" : "review"}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-slate-200 overflow-hidden space-y-6 p-6 md:p-8">
      {/* Header Banner */}
      <div className={`p-6 rounded-2xl border ${badge.bg} flex flex-col md:flex-row items-start md:items-center justify-between gap-4`}>
        <div className="flex items-center gap-4">
          {badge.icon}
          <div>
            <div className="flex items-center gap-2.5">
              <span className={`text-xs px-3 py-1 rounded-full font-bold uppercase tracking-wider ${badge.pill}`}>
                {badge.label}
              </span>
              <span className="text-xs bg-white/80 border border-slate-300 px-2.5 py-0.5 rounded-full font-medium text-slate-700">
                {response.confidence} Confidence
              </span>
            </div>
            <h2 className="text-xl font-bold mt-1 text-slate-900">{response.applicant_name}</h2>
            <p className="text-xs text-slate-600 mt-0.5">Application ID: {response.application_id}</p>
          </div>
        </div>

        <button
          onClick={handleReadAloud}
          className="flex items-center gap-2 px-4 py-2 bg-white hover:bg-slate-50 text-slate-800 text-sm font-semibold rounded-xl border border-slate-300 shadow-sm transition"
        >
          <Volume2 size={18} className={isSpeaking ? "text-teal-600 animate-pulse" : "text-slate-600"} />
          {isSpeaking ? "Stop Reading" : "Hear Explanation Aloud"}
        </button>
      </div>

      {/* Key Plain-English Numbers */}
      <div className="grid grid-cols-3 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200 text-center">
        <div>
          <span className="text-xs text-slate-500 block">Monthly Debt Payments</span>
          <span className="text-lg font-bold text-slate-800">{response.foir_percentage}% of income</span>
          <span className="text-[11px] text-slate-400 block">(Target: under 45%)</span>
        </div>
        <div>
          <span className="text-xs text-slate-500 block">Loan Burden</span>
          <span className="text-lg font-bold text-slate-800">{response.loan_to_income_ratio}x yearly income</span>
          <span className="text-[11px] text-slate-400 block">(Target: under 3x)</span>
        </div>
        <div>
          <span className="text-xs text-slate-500 block">Document Verification</span>
          <span className="text-lg font-bold text-teal-700">{(response.consistency_score * 100).toFixed(0)}% match</span>
          <span className="text-[11px] text-slate-400 block">(Declared vs Salary Slip)</span>
        </div>
      </div>

      {/* Why We Think This */}
      <div className="space-y-3">
        <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <ShieldCheck size={20} className="text-teal-600" />
          Why we think this (Assessment Factors)
        </h3>
        <ul className="space-y-2">
          {response.reasons.map((reason, idx) => (
            <li key={idx} className="flex items-start gap-2.5 text-sm text-slate-700 bg-slate-50 p-3 rounded-xl border border-slate-200">
              <ChevronRight size={16} className="text-teal-600 flex-shrink-0 mt-0.5" />
              <span>{reason}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* What Could Change This Result (Counterfactual Advice) */}
      {response.counterfactuals && response.counterfactuals.length > 0 && (
        <div className="space-y-3 bg-teal-50/60 border border-teal-200 p-5 rounded-2xl">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-teal-950 flex items-center gap-2">
              <Sparkles size={18} className="text-teal-600" />
              {response.recommendation_code === "likely_approved"
                ? "Counterfactual AI: Borrowing Headroom & Sensitivity Advice"
                : "Counterfactual AI: What Could Change This Result (Actionable Recourse)"}
            </h3>
            <span className="text-[11px] font-bold text-teal-700 bg-white border border-teal-200 px-2.5 py-0.5 rounded-full">
              Faithfully Verified
            </span>
          </div>
          <p className="text-xs text-teal-800">
            {response.recommendation_code === "likely_approved"
              ? "Based on our algorithmic policy rules, here is how you can maximize your borrowing power or save interest:"
              : "Based on our algorithmic policy rules, making one of these realistic changes would likely move this application to an approval:"}
          </p>
          <div className="space-y-2.5 mt-2">
            {response.counterfactuals.map((cf, idx) => (
              <div key={idx} className="bg-white p-3.5 rounded-xl border border-teal-200 shadow-sm text-sm text-slate-800 flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-teal-600 text-white flex items-center justify-center font-bold text-xs flex-shrink-0 mt-0.5">
                  {idx + 1}
                </div>
                <div>
                  <p className="font-semibold text-teal-900">{cf.change_description}</p>
                  <span className="text-xs text-slate-500 mt-0.5 block">{cf.actionability}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Adverse Action Notice */}
      <div className="p-4 bg-slate-100 rounded-xl text-xs text-slate-600 border border-slate-200 space-y-1">
        <span className="font-bold text-slate-800 block">Adverse Action & Officer Discretion Notice:</span>
        <p>
          This is an automated AI recommendation. You have the right to request a full manual review by a human loan officer.
          If your application is declined, you are entitled to receive written principal reasons.
        </p>
      </div>

      {/* DPDP Act 2023 Privacy Actions & Document Download */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-slate-200">
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={handleDownloadSummaryText}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-teal-600 hover:bg-teal-700 text-white rounded-lg shadow-sm transition"
            title="Download full decision summary text file"
          >
            <FileText size={14} /> Download Decision Summary (.txt)
          </button>
          <button
            onClick={handleExportData}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition"
            title="Download personal data (DPDP Act right to portability)"
          >
            <Download size={14} /> Export My Data (JSON)
          </button>
          <button
            onClick={handleDeleteData}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-rose-50 hover:bg-rose-100 text-rose-700 rounded-lg transition"
            title="Erase personal data (DPDP Act right to erasure)"
          >
            <Trash2 size={14} /> Erase My Data
          </button>
        </div>

        <button
          onClick={onReset}
          className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg shadow transition"
        >
          Submit Another Application
        </button>
      </div>

      {privacyMessage && (
        <div className="p-2.5 bg-teal-50 border border-teal-200 text-teal-900 text-xs rounded-lg text-center font-medium">
          {privacyMessage}
        </div>
      )}
    </div>
  );
};
