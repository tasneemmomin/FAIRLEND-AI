import React, { useState } from "react";
import { Send, Calculator, Shield, HelpCircle } from "lucide-react";
import { ApplicantIntakeForm, ApplicantResponse } from "../types";
import { submitApplicantIntake } from "../api";

interface TypedIntakeFormProps {
  initialValues?: Partial<ApplicantIntakeForm>;
  transcript?: string;
  consistencyScore?: number;
  onSubmitted: (response: ApplicantResponse) => void;
}

export const TypedIntakeForm: React.FC<TypedIntakeFormProps> = ({
  initialValues = {},
  transcript,
  consistencyScore = 1.0,
  onSubmitted,
}) => {
  const [formData, setFormData] = useState<ApplicantIntakeForm>({
    applicant_name: initialValues.applicant_name || "",
    contact_phone: initialValues.contact_phone || "",
    contact_email: initialValues.contact_email || "",
    age: initialValues.age || 28,
    employment_type: initialValues.employment_type || "salaried",
    employment_duration_months: initialValues.employment_duration_months || 24,
    monthly_income: initialValues.monthly_income || 50000,
    existing_emis: initialValues.existing_emis || 0,
    requested_amount: initialValues.requested_amount || 200000,
    tenure_months: initialValues.tenure_months || 24,
    loan_purpose: initialValues.loan_purpose || "personal",
    dependents: initialValues.dependents || 0,
    residence_type: initialValues.residence_type || "rented",
    credit_history_years: initialValues.credit_history_years || 1.0,
    collateral_value: initialValues.collateral_value || 0,
    intake_mode: transcript ? "voice" : "typed",
    intake_transcript: transcript,
    audit_consent: false,
    audit_gender: "prefer_not_say",
    audit_social_group: "",
    audit_geography_tier: "tier1"
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Live estimated EMI calculation: E = P * r * (1+r)^n / ((1+r)^n - 1)
  const calculateEstimatedEmi = () => {
    const P = formData.requested_amount;
    const n = formData.tenure_months;
    if (P <= 0 || n <= 0) return 0;
    const r = 0.105 / 12.0;
    const emi = P * r * Math.pow(1 + r, n) / (Math.pow(1 + r, n) - 1);
    return Math.round(emi);
  };

  const estimatedEmi = calculateEstimatedEmi();
  const estimatedFoir = formData.monthly_income > 0 
    ? Math.round(((formData.existing_emis + estimatedEmi) / formData.monthly_income) * 100) 
    : 0;

  const handleChange = (field: keyof ApplicantIntakeForm, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.applicant_name.trim()) {
      setErrorMessage("Please enter your full name.");
      return;
    }
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      const response = await submitApplicantIntake(formData);
      onSubmitted(response);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to submit application");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-md border border-slate-200 p-6 space-y-6">
      <div>
        <h3 className="text-lg font-bold text-slate-900">Application Information & Financial Profile</h3>
        <p className="text-xs text-slate-500 mt-0.5">
          Verify or update your details before submitting for instantaneous policy evaluation.
        </p>
      </div>

      {errorMessage && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-lg font-medium">
          {errorMessage}
        </div>
      )}

      {/* Personal & Contact Section */}
      <div className="space-y-3">
        <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">1. Identity & Profile</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name *</label>
            <input
              type="text"
              required
              value={formData.applicant_name}
              onChange={(e) => handleChange("applicant_name", e.target.value)}
              className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-teal-500 focus:outline-none"
              placeholder="e.g. Rahul Sharma"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Age (Years) *</label>
            <input
              type="number"
              required
              min={18}
              max={100}
              value={formData.age}
              onChange={(e) => handleChange("age", parseInt(e.target.value) || 18)}
              className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-teal-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Residence Type</label>
            <select
              value={formData.residence_type}
              onChange={(e) => handleChange("residence_type", e.target.value)}
              className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-teal-500 focus:outline-none"
            >
              <option value="owned">Owned Home</option>
              <option value="rented">Rented Accommodation</option>
              <option value="ancestral">Family / Ancestral Residence</option>
            </select>
          </div>
        </div>
      </div>

      {/* Employment & Earnings */}
      <div className="space-y-3 pt-4 border-t border-slate-200">
        <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">2. Employment & Income</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Employment Type</label>
            <select
              value={formData.employment_type}
              onChange={(e) => handleChange("employment_type", e.target.value)}
              className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-teal-500 focus:outline-none"
            >
              <option value="salaried">Salaried Employee</option>
              <option value="self_employed">Self-Employed Professional</option>
              <option value="business">Business Owner / Merchant</option>
              <option value="gig_contract">Gig / Contract Worker</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Duration in Current Role (Months)</label>
            <input
              type="number"
              min={0}
              value={formData.employment_duration_months}
              onChange={(e) => handleChange("employment_duration_months", parseInt(e.target.value) || 0)}
              className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-teal-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Monthly Take-Home Income (₹) *</label>
            <input
              type="number"
              required
              min={0}
              value={formData.monthly_income}
              onChange={(e) => handleChange("monthly_income", parseFloat(e.target.value) || 0)}
              className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-teal-500 focus:outline-none"
            />
          </div>
        </div>
      </div>

      {/* Loan Request & Obligations */}
      <div className="space-y-3 pt-4 border-t border-slate-200">
        <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">3. Loan Requirement & Existing Debts</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Requested Loan Amount (₹) *</label>
            <input
              type="number"
              required
              min={0}
              value={formData.requested_amount}
              onChange={(e) => handleChange("requested_amount", parseFloat(e.target.value) || 0)}
              className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-teal-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Repayment Tenure (Months) *</label>
            <input
              type="number"
              required
              min={6}
              max={360}
              value={formData.tenure_months}
              onChange={(e) => handleChange("tenure_months", parseInt(e.target.value) || 12)}
              className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-teal-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Existing Monthly EMIs (₹)</label>
            <input
              type="number"
              min={0}
              value={formData.existing_emis}
              onChange={(e) => handleChange("existing_emis", parseFloat(e.target.value) || 0)}
              className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-teal-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Loan Purpose</label>
            <select
              value={formData.loan_purpose}
              onChange={(e) => handleChange("loan_purpose", e.target.value)}
              className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-teal-500 focus:outline-none"
            >
              <option value="home">Home Purchase / Renovation</option>
              <option value="education">Higher Education</option>
              <option value="personal">Personal / Family</option>
              <option value="business">Business Expansion</option>
              <option value="vehicle">Vehicle Purchase</option>
              <option value="medical">Medical Treatment</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Credit History (Years)</label>
            <input
              type="number"
              min={0}
              step={0.5}
              value={formData.credit_history_years}
              onChange={(e) => handleChange("credit_history_years", parseFloat(e.target.value) || 0)}
              className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-teal-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Collateral / Asset Value (₹)</label>
            <input
              type="number"
              min={0}
              step={10000}
              value={formData.collateral_value}
              onChange={(e) => handleChange("collateral_value", parseFloat(e.target.value) || 0)}
              className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-teal-500 focus:outline-none"
            />
          </div>
        </div>
      </div>

      {/* Live Financial Metrics Banner */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Calculator className="text-teal-600" size={24} />
          <div>
            <span className="text-xs text-slate-500 block">Estimated Monthly Installment (EMI)</span>
            <span className="text-base font-bold text-slate-800">₹{estimatedEmi.toLocaleString("en-IN")}/month</span>
          </div>
        </div>
        <div className="text-right">
          <span className="text-xs text-slate-500 block">Estimated Debt-to-Income (FOIR)</span>
          <span className={`text-base font-bold ${
            estimatedFoir <= 45 ? "text-emerald-700" : estimatedFoir <= 55 ? "text-amber-700" : "text-rose-700"
          }`}>
            {estimatedFoir}%
          </span>
          <span className="text-[11px] text-slate-400 block">{estimatedFoir <= 45 ? "(Within healthy limit)" : "(High debt burden)"}</span>
        </div>
      </div>

      {/* Consents & DPDP Act Checkboxes */}
      <div className="space-y-3 pt-4 border-t border-slate-200">
        <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">4. Consents & Regulatory Declarations</h4>
        
        <label className="flex items-start gap-2.5 cursor-pointer text-xs text-slate-700">
          <input
            type="checkbox"
            required
            defaultChecked
            className="mt-0.5 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
          />
          <span>
            <strong>Required Consent:</strong> I confirm that the information provided is accurate and consent to credit policy scoring under India's Digital Personal Data Protection (DPDP) Act 2023.
          </span>
        </label>

        {/* Separate Demographic Consent for Fairness Auditing Only */}
        <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
          <label className="flex items-start gap-2.5 cursor-pointer text-xs text-slate-700">
            <input
              type="checkbox"
              checked={formData.audit_consent}
              onChange={(e) => handleChange("audit_consent", e.target.checked)}
              className="mt-0.5 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
            />
            <span>
              <strong>Optional Research Consent:</strong> I consent to provide voluntary demographic attributes solely for algorithmic fairness auditing. <em>(These attributes are stored apart from loan features and are strictly never used as model inputs).</em>
            </span>
          </label>

          {formData.audit_consent && (
            <div className="grid grid-cols-3 gap-3 pt-2">
              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-0.5">Gender (Audit only)</label>
                <select
                  value={formData.audit_gender}
                  onChange={(e) => handleChange("audit_gender", e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded px-2 py-1"
                >
                  <option value="female">Female</option>
                  <option value="male">Male</option>
                  <option value="non_binary">Non-binary</option>
                  <option value="prefer_not_say">Prefer not to say</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-0.5">Geography Tier</label>
                <select
                  value={formData.audit_geography_tier}
                  onChange={(e) => handleChange("audit_geography_tier", e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded px-2 py-1"
                >
                  <option value="metro">Metro</option>
                  <option value="tier1">Tier 1 City</option>
                  <option value="tier2">Tier 2/3 Town</option>
                  <option value="rural">Rural</option>
                </select>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex justify-end pt-4">
        <button
          type="submit"
          disabled={isSubmitting}
          className="flex items-center gap-2 px-6 py-2.5 bg-teal-600 hover:bg-teal-700 text-white text-sm font-bold rounded-xl shadow transition disabled:opacity-50"
        >
          <Send size={16} />
          {isSubmitting ? "Evaluating Application..." : "Submit Application for AI Recommendation"}
        </button>
      </div>
    </form>
  );
};
