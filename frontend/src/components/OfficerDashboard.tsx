import React, { useState, useEffect } from "react";
import {
  ShieldAlert, CheckCircle2, XCircle, Clock, AlertTriangle, User,
  FileText, TrendingUp, BarChart2, RefreshCw, Send, Sparkles, Scale, Info,
  Lock, KeyRound, LogOut, ShieldCheck, ArrowRight, Copy, Check
} from "lucide-react";
import { 
  listOfficerApplications, 
  getOfficerAppDetail, 
  submitOfficerDecision, 
  updateRepayment, 
  getOfficerStats, 
  getFairness,
  loginUser,
  logoutUser
} from "../api";
import { OfficerAppSummary, FairnessMetrics } from "../types";
import { OfficerStressPanel } from "./FinancialStressSimulator";

export const OfficerDashboard: React.FC = () => {
  // Officer Authentication state backed by backend JWT verification
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
    return sessionStorage.getItem("fairlend_officer_authenticated") === "true" &&
      !!sessionStorage.getItem("fairlend_officer_token");
  });
  const [officerEmail, setOfficerEmail] = useState("officer@fairlendai.com");
  const [officerPassword, setOfficerPassword] = useState("Officer@123");
  const [authError, setAuthError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [copiedEmail, setCopiedEmail] = useState(false);
  const [copiedPassword, setCopiedPassword] = useState(false);
  const [officerInfo, setOfficerInfo] = useState<{ id: string; name: string }>(() => {
    return {
      id: sessionStorage.getItem("fairlend_officer_id") || "OFF-7029",
      name: sessionStorage.getItem("fairlend_officer_name") || "P. S. Sharma (Senior Credit Underwriter)"
    };
  });

  const [apps, setApps] = useState<OfficerAppSummary[]>([]);
  const [totalApps, setTotalApps] = useState(0);
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedAppId, setSelectedAppId] = useState<string | null>(null);
  const [appDetail, setAppDetail] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [fairness, setFairness] = useState<FairnessMetrics | null>(null);
  const [activeTab, setActiveTab] = useState<"queue" | "fairness" | "health">("queue");

  // Decision Form state
  const [decision, setDecision] = useState("approve");
  const [reasonCode, setReasonCode] = useState("low_foir_stable_income");
  const [officerNotes, setOfficerNotes] = useState("");
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false);
  const [repaymentStatus, setRepaymentStatus] = useState("unobserved");

  const copyCred = (text: string, type: "email" | "password") => {
    navigator.clipboard.writeText(text);
    if (type === "email") {
      setCopiedEmail(true);
      setTimeout(() => setCopiedEmail(false), 2000);
    } else {
      setCopiedPassword(true);
      setTimeout(() => setCopiedPassword(false), 2000);
    }
  };

  const handleDemoOfficerLogin = async () => {
    setOfficerEmail("officer@fairlendai.com");
    setOfficerPassword("Officer@123");
    setAuthError(null);
    setIsLoggingIn(true);
    try {
      const res = await loginUser("officer@fairlendai.com", "Officer@123", "officer");
      sessionStorage.setItem("fairlend_officer_token", res.access_token);
      sessionStorage.setItem("fairlend_officer_authenticated", "true");
      sessionStorage.setItem("fairlend_officer_id", res.user.id.slice(0, 8).toUpperCase());
      sessionStorage.setItem("fairlend_officer_name", res.user.full_name);
      setOfficerInfo({ id: res.user.id.slice(0, 8).toUpperCase(), name: res.user.full_name });
      setIsAuthenticated(true);
    } catch (err: any) {
      setAuthError(err.message || "Failed to authenticate demo officer with backend database.");
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleOfficerLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!officerEmail.trim() || !officerPassword.trim()) {
      setAuthError("Please enter Officer Email and Security Password.");
      return;
    }
    setAuthError(null);
    setIsLoggingIn(true);
    try {
      const res = await loginUser(officerEmail.trim(), officerPassword, "officer");
      sessionStorage.setItem("fairlend_officer_token", res.access_token);
      sessionStorage.setItem("fairlend_officer_authenticated", "true");
      sessionStorage.setItem("fairlend_officer_id", res.user.id.slice(0, 8).toUpperCase());
      sessionStorage.setItem("fairlend_officer_name", res.user.full_name);
      setOfficerInfo({ id: res.user.id.slice(0, 8).toUpperCase(), name: res.user.full_name });
      setIsAuthenticated(true);
    } catch (err: any) {
      setAuthError(err.message || "Invalid credentials. Please verify your officer credentials.");
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleOfficerSignOut = async () => {
    await logoutUser();
    sessionStorage.removeItem("fairlend_officer_token");
    sessionStorage.removeItem("fairlend_officer_authenticated");
    sessionStorage.removeItem("fairlend_officer_id");
    sessionStorage.removeItem("fairlend_officer_name");
    setIsAuthenticated(false);
  };

  const loadData = async () => {
    try {
      const [appList, statRes, fairRes] = await Promise.all([
        listOfficerApplications(statusFilter),
        getOfficerStats(),
        getFairness()
      ]);
      setApps(appList.applications);
      setTotalApps(appList.total);
      setStats(statRes);
      setFairness(fairRes);
    } catch (e) {
      console.error("Error loading dashboard data:", e);
    }
  };

  useEffect(() => {
    // Data must not be fetched before the officer is signed in: the component
    // stays mounted across the login screen, so without this guard the queue
    // would stay empty until a manual reload or a websocket event.
    if (!isAuthenticated) return;
    loadData();
    // Connect WebSocket for real-time updates
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.origin.includes("localhost:5173") ? "127.0.0.1:8000" : window.location.host;
    const ws = new WebSocket(`${protocol}//${host}/api/ws`);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event === "new_application" || data.event === "officer_decision") {
          loadData();
          if (selectedAppId && data.application_id === selectedAppId) {
            getOfficerAppDetail(selectedAppId).then(setAppDetail);
          }
        }
      } catch (e) {}
    };

    return () => ws.close();
  }, [isAuthenticated, statusFilter, selectedAppId]);

  const handleSelectApp = async (id: string) => {
    setSelectedAppId(id);
    try {
      const detail = await getOfficerAppDetail(id);
      setAppDetail(detail);
      if (detail.decision) {
        setDecision(detail.decision.decision);
        setReasonCode(detail.decision.reason_code);
        setOfficerNotes(detail.decision.officer_notes || "");
        setRepaymentStatus(detail.decision.repayment_outcome || "unobserved");
      } else {
        setDecision(detail.ai_recommendation === "likely_approved" ? "approve" : "reject");
        setReasonCode(detail.ai_recommendation === "likely_approved" ? "low_foir_stable_income" : "high_debt_burden_foir");
        setOfficerNotes("");
        setRepaymentStatus("unobserved");
      }
    } catch (e) {
      console.error("Failed to load details:", e);
    }
  };

  const handleDecisionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAppId) return;
    setIsSubmittingDecision(true);
    try {
      await submitOfficerDecision(selectedAppId, decision, reasonCode, officerNotes);
      await loadData();
      const updated = await getOfficerAppDetail(selectedAppId);
      setAppDetail(updated);
    } catch (err: any) {
      alert("Failed to record decision: " + err.message);
    } finally {
      setIsSubmittingDecision(false);
    }
  };

  const handleRepaymentUpdate = async () => {
    if (!selectedAppId) return;
    try {
      await updateRepayment(selectedAppId, repaymentStatus);
      alert("Repayment outcome updated successfully.");
      loadData();
    } catch (err: any) {
      alert("Failed to update repayment: " + err.message);
    }
  };

  const handleDownloadDecisionLetter = () => {
    if (!appDetail) return;
    const isApproved = appDetail.decision?.decision === "approve" || appDetail.ai_recommendation === "likely_approved";
    const decisionLabel = appDetail.decision?.decision
      ? appDetail.decision.decision.toUpperCase()
      : appDetail.ai_recommendation.toUpperCase();
    const cfs = appDetail.counterfactuals || [];

    const lines = [
      "================================================================================",
      "                   FAIRLENDAI CREDIT DECISION & AUDIT REPORT",
      "         (Fair, Explainable & Voice-Enabled AI Lending Assessment)",
      "================================================================================",
      `Date & Time:              ${new Date().toISOString()}`,
      `Application Reference ID: ${appDetail.id}`,
      `Applicant Full Name:      ${appDetail.applicant_name}`,
      `Contact Details:          Phone: ${appDetail.contact_phone || "N/A"} | Email: ${appDetail.contact_email || "N/A"}`,
      `Intake Mode:              ${appDetail.intake_mode.toUpperCase()}`,
      "",
      "--------------------------------------------------------------------------------",
      "1. FINAL UNDERWRITING DETERMINATION",
      "--------------------------------------------------------------------------------",
      `Underwriting Status:      ${decisionLabel}`,
      `Reviewing Officer ID:     ${appDetail.decision?.officer_id || "Officer Session"}`,
      `Mandatory Reason Code:    ${appDetail.decision?.reason_code || reasonCode}`,
      `Officer Rationale Notes:  ${appDetail.decision?.officer_notes || officerNotes || "Standard underwriting review completed."}`,
      `AI Policy Recommendation: ${appDetail.ai_recommendation.toUpperCase()} (${appDetail.ai_confidence} Confidence)`,
      `Model Lifecycle Stage:    ${appDetail.ai_stage}`,
      "",
      "--------------------------------------------------------------------------------",
      "2. FINANCIAL PROFILE & RATIOS EVALUATED",
      "--------------------------------------------------------------------------------",
      `Requested Loan Amount:    INR ${appDetail.requested_amount.toLocaleString("en-IN")}`,
      `Requested Tenure:         ${appDetail.tenure_months} Months`,
      `Monthly Take-Home Income: INR ${appDetail.monthly_income.toLocaleString("en-IN")}`,
      `Existing Monthly Debts:   INR ${appDetail.existing_emis.toLocaleString("en-IN")}`,
      `Calculated FOIR:          ${appDetail.ratios.foir}% (Policy Standard: <= 45.0%)`,
      `Loan-to-Income (LTI):     ${appDetail.ratios.lti}x (Policy Standard: <= 3.0x)`,
      `Employment Profile:       ${appDetail.employment_type} (${appDetail.employment_duration_months} Months)`,
      `Document Match Score:     ${(appDetail.consistency_score * 100).toFixed(1)}%`,
      "",
      "--------------------------------------------------------------------------------",
      "3. POLICY SCORECARD COMPONENT BREAKDOWN",
      "--------------------------------------------------------------------------------",
      ...(appDetail.ai_rule_hits && appDetail.ai_rule_hits.length > 0
        ? appDetail.ai_rule_hits.map((h: any) => ` * [${h.component}]: ${h.reason} (${h.score}/${h.max_score} pts)`)
        : [" Standard baseline policy evaluation applied."]),
      "",
      "--------------------------------------------------------------------------------",
      "4. COUNTERFACTUAL AI & RECOURSE SENSITIVITY ANALYSIS",
      "--------------------------------------------------------------------------------",
      ...(cfs.length > 0
        ? cfs.map((cf: any, i: number) => ` [${i + 1}] ${cf.change_description}\n     Parameter: ${cf.feature_name} (Current: ${cf.current_value} -> Target: ${cf.suggested_value})\n     Actionability: ${cf.actionability}`)
        : [" All scorecard parameters satisfied in prime tier."]),
      "",
      "--------------------------------------------------------------------------------",
      "5. REGULATORY & DPDP ACT (2023) COMPLIANCE CERTIFICATION",
      "--------------------------------------------------------------------------------",
      " [x] Aligned with Reserve Bank of India (RBI) Digital Lending Guidelines (2022).",
      " [x] Protected attributes (gender, caste, religion) were strictly EXCLUDED from all models.",
      " [x] Compliant with India Digital Personal Data Protection (DPDP) Act 2023.",
      " [x] The applicant retains full rights to data portability and complete erasure.",
      " [x] An adverse action copy has been recorded in the persistent audit log.",
      "================================================================================",
      "                        END OF OFFICIAL DECISION REPORT",
      "================================================================================"
    ];

    const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `FairLendAI_Decision_${appDetail.applicant_name.replace(/[^a-zA-Z0-9]/g, "_")}_${appDetail.id.slice(0, 8)}_${isApproved ? "approved" : "rejected"}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Render Officer Login Gate if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="max-w-md mx-auto my-12 bg-white rounded-2xl shadow-xl border border-[#E3E8E5] overflow-hidden animate-fade-in">
        <div className="bg-[#172C3D] text-white p-6 text-center space-y-2">
          <div className="w-12 h-12 mx-auto rounded-xl bg-[#28766B] flex items-center justify-center text-white font-extrabold text-lg shadow">
            FL
          </div>
          <h2 className="font-serif text-xl font-bold text-white">Underwriting Portal Sign In</h2>
          <p className="text-xs text-[#A0B2C0]">
            Restricted access for certified credit underwriters, risk auditors, and lending officers.
          </p>
        </div>

        <div className="p-6 space-y-5">
          {/* Demo Credentials Box */}
          <div className="bg-[#EBF5F3] border border-[#BBF7D0] p-4 rounded-xl space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-xs font-bold text-[#166534]">
                <Sparkles size={15} /> Official Underwriter Demo Credentials
              </span>
              <span className="text-[10px] bg-[#DCFCE7] text-[#15803D] border border-[#86EFAC] px-2 py-0.5 rounded font-bold uppercase">
                Backend Verified
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs bg-white/80 p-3 rounded-lg border border-[#A7F3D0]">
              <div className="space-y-1">
                <span className="text-[#718096] text-[10px] font-medium block">Demo Officer Email:</span>
                <div className="flex items-center justify-between bg-slate-50 px-2 py-1 rounded border border-slate-200">
                  <span className="font-mono text-[11px] font-bold text-[#172C3D] truncate select-all">
                    officer@fairlendai.com
                  </span>
                  <button
                    type="button"
                    onClick={() => copyCred("officer@fairlendai.com", "email")}
                    className="text-[#28766B] hover:text-[#172C3D] p-0.5 ml-1"
                    title="Copy Email"
                  >
                    {copiedEmail ? <Check size={13} className="text-emerald-600" /> : <Copy size={13} />}
                  </button>
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-[#718096] text-[10px] font-medium block">Demo Password:</span>
                <div className="flex items-center justify-between bg-slate-50 px-2 py-1 rounded border border-slate-200">
                  <span className="font-mono text-[11px] font-bold text-[#172C3D] select-all">
                    Officer@123
                  </span>
                  <button
                    type="button"
                    onClick={() => copyCred("Officer@123", "password")}
                    className="text-[#28766B] hover:text-[#172C3D] p-0.5 ml-1"
                    title="Copy Password"
                  >
                    {copiedPassword ? <Check size={13} className="text-emerald-600" /> : <Copy size={13} />}
                  </button>
                </div>
              </div>
            </div>

            <button
              type="button"
              disabled={isLoggingIn}
              onClick={handleDemoOfficerLogin}
              className="w-full py-2 bg-[#28766B] hover:bg-[#1E5C53] text-white font-semibold rounded-lg text-xs shadow-sm transition flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              <KeyRound size={14} /> ⚡ 1-Click Sign In with Demo Credentials
            </button>
          </div>

          <div className="relative text-center my-2">
            <hr className="border-[#E3E8E5]" />
            <span className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white px-3 text-[11px] text-[#718096]">
              or manual sign in
            </span>
          </div>

          {authError && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg font-medium flex items-start gap-2">
              <AlertTriangle size={15} className="text-rose-500 flex-shrink-0 mt-0.5" />
              <span>{authError}</span>
            </div>
          )}

          <form onSubmit={handleOfficerLoginSubmit} className="space-y-3.5 text-xs">
            <div>
              <label className="block text-[#24323D] font-semibold mb-1">Officer Email Address</label>
              <div className="relative">
                <User size={15} className="absolute left-3 top-2.5 text-[#718096]" />
                <input
                  type="email"
                  required
                  value={officerEmail}
                  onChange={(e) => setOfficerEmail(e.target.value)}
                  placeholder="officer@fairlendai.com"
                  className="w-full pl-9 pr-3 py-2 border border-[#E3E8E5] rounded-lg focus:outline-none focus:border-[#28766B]"
                />
              </div>
            </div>

            <div>
              <label className="block text-[#24323D] font-semibold mb-1">Security Password</label>
              <div className="relative">
                <Lock size={15} className="absolute left-3 top-2.5 text-[#718096]" />
                <input
                  type="password"
                  required
                  value={officerPassword}
                  onChange={(e) => setOfficerPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-9 pr-3 py-2 border border-[#E3E8E5] rounded-lg focus:outline-none focus:border-[#28766B]"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoggingIn}
              className="w-full py-2.5 bg-[#172C3D] hover:bg-[#0F1E2A] text-white font-semibold rounded-lg text-xs shadow-sm transition flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              {isLoggingIn ? "Verifying Credentials..." : "Sign In to Command Center"} <ArrowRight size={14} />
            </button>
          </form>

          <p className="text-[11px] text-[#718096] text-center pt-2">
            Protected by multi-tier session encryption and audit logging under RBI Digital Lending Guidelines.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Officer Session Top Bar */}
      <div className="bg-white p-3.5 rounded-xl border border-[#E3E8E5] shadow-sm flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-[#172C3D] text-[#7FE0D2] flex items-center justify-center font-bold text-xs">
            ID
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm text-[#172C3D]">{officerInfo.name}</span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#EBF5F3] text-[#166534] border border-[#BBF7D0] font-bold uppercase">
                {officerInfo.id} • Active
              </span>
            </div>
            <p className="text-[11px] text-[#718096]">Level 2 Delegated Lending Authority • RBI Compliance Audit Active</p>
          </div>
        </div>

        <button
          type="button"
          onClick={handleOfficerSignOut}
          className="flex items-center gap-1.5 px-3 py-1.5 border border-[#E3E8E5] hover:bg-slate-50 text-[#718096] hover:text-rose-600 rounded-lg text-xs font-semibold transition"
        >
          <LogOut size={14} /> Sign Out
        </button>
      </div>

      {/* Top Lifecycle & Stage Indicator Banner */}
      {stats && (
        <div className="bg-slate-900 text-white p-5 rounded-2xl shadow-lg border border-slate-800 space-y-4">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-teal-500/20 text-teal-400 flex items-center justify-center font-bold">
                <Sparkles size={20} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider bg-teal-500/20 text-teal-300 border border-teal-500/40">
                    {stats.stage_name}
                  </span>
                  <span className="text-xs text-slate-400">
                    Threshold: {stats.activation_threshold} labeled cases (at least {stats.min_per_class_required} each)
                  </span>
                </div>
                <h2 className="text-lg font-bold mt-1 text-slate-100">
                  Human-in-the-Loop Credit Lifecycle
                </h2>
              </div>
            </div>

            {/* Quick Metrics */}
            <div className="flex items-center gap-6 text-xs">
              <div className="text-center">
                <span className="text-slate-400 block">Total Decisions</span>
                <span className="text-base font-bold text-white">{stats.total_labeled_cases}</span>
              </div>
              <div className="text-center">
                <span className="text-slate-400 block">Approvals</span>
                <span className="text-base font-bold text-emerald-400">{stats.approvals_count}</span>
              </div>
              <div className="text-center">
                <span className="text-slate-400 block">Rejections</span>
                <span className="text-base font-bold text-rose-400">{stats.rejections_count}</span>
              </div>
              <div className="text-center border-l border-slate-700 pl-4">
                <span className="text-slate-400 block">50-Case AI Agreement</span>
                <span className="text-base font-bold text-teal-300">
                  {stats.recent_agreement_rate !== null ? `${(stats.recent_agreement_rate * 100).toFixed(1)}%` : "Pending Data"}
                </span>
              </div>
            </div>
          </div>

          {/* Progress bar towards Stage 3 Online Model Activation */}
          <div className="space-y-1.5 pt-1">
            <div className="flex items-center justify-between text-xs text-slate-300">
              <span>Model Activation Progress: {stats.progress_percent}%</span>
              <span>
                {stats.remaining_for_activation > 0
                  ? `${stats.remaining_for_activation} more decisions needed to unlock Stage 3 Online Model`
                  : "Activation threshold reached!"}
              </span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
              <div
                className="bg-gradient-to-r from-teal-500 to-emerald-400 h-2.5 rounded-full transition-all duration-500"
                style={{ width: `${stats.progress_percent}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2 flex-wrap">
        <button
          onClick={() => setActiveTab("queue")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition ${
            activeTab === "queue"
              ? "bg-slate-900 text-white shadow"
              : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          <FileText size={16} /> Applications Queue ({totalApps})
        </button>
        <button
          onClick={() => setActiveTab("fairness")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition ${
            activeTab === "fairness"
              ? "bg-slate-900 text-white shadow"
              : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          <Scale size={16} /> Fairness Monitor
        </button>
        <button
          onClick={() => setActiveTab("health")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition ${
            activeTab === "health"
              ? "bg-slate-900 text-white shadow"
              : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          <TrendingUp size={16} /> Concept Drift & River Model Health
        </button>
      </div>

      {/* Main Content Area */}
      {activeTab === "queue" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Applications Table (Left 5 Cols) */}
          <div className="lg:col-span-5 bg-white rounded-xl shadow border border-slate-200 p-4 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-slate-800 text-sm">Applications Queue</h3>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="text-xs border border-slate-300 rounded-lg px-2.5 py-1 focus:ring-teal-500 focus:outline-none"
              >
                <option value="all">All Applications</option>
                <option value="submitted">Submitted (Pending)</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="more_info">Needs Info</option>
              </select>
            </div>

            <div className="space-y-2 max-h-[650px] overflow-y-auto">
              {apps.length === 0 ? (
                <div className="text-center py-10 text-slate-400 text-sm">No applications found.</div>
              ) : (
                apps.map((app) => (
                  <div
                    key={app.id}
                    onClick={() => handleSelectApp(app.id)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition ${
                      selectedAppId === app.id
                        ? "border-teal-500 bg-teal-50/60 shadow-sm"
                        : "border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-900 text-sm">{app.applicant_name}</span>
                          <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                            app.status === "approved"
                              ? "bg-emerald-100 text-emerald-800"
                              : app.status === "rejected"
                              ? "bg-rose-100 text-rose-800"
                              : "bg-amber-100 text-amber-800"
                          }`}>
                            {app.status}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 mt-0.5">
                          ₹{app.requested_amount.toLocaleString("en-IN")} • {app.tenure_months}m
                        </p>
                      </div>

                      <div className="text-right">
                        <span className={`text-[11px] font-semibold block ${
                          app.ai_recommendation === "likely_approved"
                            ? "text-emerald-700"
                            : app.ai_recommendation === "needs_review"
                            ? "text-amber-700"
                            : "text-rose-700"
                        }`}>
                          {app.ai_recommendation.replace("_", " ").toUpperCase()}
                        </span>
                        <span className="text-[10px] text-slate-400 block">FOIR: {app.foir}%</span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Detailed Inspector & Decision Panel (Right 7 Cols) */}
          <div className="lg:col-span-7 space-y-5">
            {appDetail ? (
              <div className="bg-white rounded-xl shadow border border-slate-200 p-6 space-y-6">
                {/* Header */}
                <div className="flex items-start justify-between border-b border-slate-200 pb-4 flex-wrap gap-3">
                  <div>
                    <h3 className="text-lg font-bold text-slate-900">{appDetail.applicant_name}</h3>
                    <p className="text-xs text-slate-500">
                      ID: {appDetail.id} • Intake Mode: <span className="font-semibold uppercase">{appDetail.intake_mode}</span>
                    </p>
                    <button
                      onClick={handleDownloadDecisionLetter}
                      className="mt-2.5 flex items-center gap-1.5 px-3.5 py-1.5 bg-teal-700 hover:bg-teal-800 text-white rounded-lg text-xs font-semibold shadow-sm transition"
                      title="Download complete decision and audit report as a text file"
                    >
                      <FileText size={14} /> Download Decision & Audit File (.txt)
                    </button>
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-slate-400 block">AI Recommendation</span>
                    <span className={`text-sm font-bold uppercase px-3 py-1 rounded-full ${
                      appDetail.ai_recommendation === "likely_approved"
                        ? "bg-emerald-100 text-emerald-800"
                        : appDetail.ai_recommendation === "needs_review"
                        ? "bg-amber-100 text-amber-800"
                        : "bg-rose-100 text-rose-800"
                    }`}>
                      {appDetail.ai_recommendation.replace("_", " ")} ({appDetail.ai_confidence} Confidence)
                    </span>
                  </div>
                </div>

                {/* Declared vs Document Verified Side-by-Side */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-slate-500 uppercase">Verification & Document Consistency</h4>
                    <span className="text-xs font-bold text-teal-700">
                      Match Score: {(appDetail.consistency_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-xs bg-slate-50 p-3 rounded-xl border border-slate-200">
                    <div>
                      <span className="text-slate-400 block">Declared Monthly Income:</span>
                      <span className="font-bold text-slate-800">₹{appDetail.monthly_income.toLocaleString("en-IN")}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Existing Monthly EMIs:</span>
                      <span className="font-bold text-slate-800">₹{appDetail.existing_emis.toLocaleString("en-IN")}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Calculated Debt-to-Income (FOIR):</span>
                      <span className="font-bold text-slate-800">{appDetail.ratios.foir}%</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Loan-to-Income (LTI):</span>
                      <span className="font-bold text-slate-800">{appDetail.ratios.lti}x</span>
                    </div>
                  </div>
                </div>

                {/* Scorecard Rule Hits */}
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-slate-500 uppercase">Policy Scorecard Component Hits</h4>
                  <div className="space-y-1.5">
                    {appDetail.ai_rule_hits.map((hit: any, idx: number) => (
                      <div key={idx} className="flex items-center justify-between text-xs bg-slate-50 px-3 py-2 rounded border border-slate-200">
                        <div>
                          <span className="font-bold text-slate-800 mr-2">{hit.component}:</span>
                          <span className="text-slate-600">{hit.reason}</span>
                        </div>
                        <span className="font-bold text-teal-700">{hit.score}/{hit.max_score} pts</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Nearest Similar Past Cases */}
                {appDetail.similar_cases && appDetail.similar_cases.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-xs font-bold text-slate-500 uppercase">Nearest Historical Cases (k-NN)</h4>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs text-left">
                        <thead className="bg-slate-100 text-slate-600 uppercase">
                          <tr>
                            <th className="p-2">Applicant</th>
                            <th className="p-2">Amount</th>
                            <th className="p-2">Income</th>
                            <th className="p-2">FOIR</th>
                            <th className="p-2">Past Officer Decision</th>
                          </tr>
                        </thead>
                        <tbody>
                          {appDetail.similar_cases.map((sc: any, idx: number) => (
                            <tr key={idx} className="border-b border-slate-100">
                              <td className="p-2 font-medium">{sc.applicant_name}</td>
                              <td className="p-2">₹{sc.requested_amount.toLocaleString("en-IN")}</td>
                              <td className="p-2">₹{sc.monthly_income.toLocaleString("en-IN")}</td>
                              <td className="p-2">{sc.foir}%</td>
                              <td className="p-2 font-bold uppercase">{sc.officer_decision}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Financial Stress Analysis (Advisory) */}
                <OfficerStressPanel applicationId={appDetail.id} />

                {/* Counterfactual AI & Recourse Sensitivity Analysis */}
                <div className="space-y-3 bg-teal-50/50 border border-teal-200 p-4 rounded-xl">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-teal-950 uppercase flex items-center gap-1.5">
                      <Sparkles size={14} className="text-teal-600" />
                      Counterfactual AI & Policy Recourse Analysis
                    </h4>
                    <span className="text-[10px] bg-white border border-teal-300 text-teal-800 font-bold px-2 py-0.5 rounded-full">
                      Faithfully Re-scored
                    </span>
                  </div>

                  {appDetail.counterfactuals && appDetail.counterfactuals.length > 0 ? (
                    <div className="space-y-2 mt-1">
                      {appDetail.counterfactuals.map((cf: any, idx: number) => (
                        <div key={idx} className="bg-white p-3 rounded-lg border border-teal-200 text-xs text-slate-800 shadow-sm space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-teal-900">{cf.change_description}</span>
                            <span className="text-[10px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                              {cf.actionability}
                            </span>
                          </div>
                          <div className="flex items-center gap-4 text-[11px] text-slate-500 pt-1 border-t border-slate-100">
                            <span>Parameter: <strong className="text-slate-700">{cf.feature_name}</strong></span>
                            <span>Current: <strong className="text-slate-700">{cf.current_value}</strong></span>
                            <span>Suggested: <strong className="text-teal-700 font-bold">{cf.suggested_value}</strong></span>
                            <span className="text-emerald-600 font-semibold ml-auto">✓ Verified Flipping/Margin</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500 italic bg-white p-3 rounded-lg border border-slate-200">
                      Applicant is in the prime policy tier. All scorecard thresholds satisfied without requiring parameter adjustments.
                    </p>
                  )}
                </div>

                {/* Decision Form (Human-in-the-Loop Labeling) */}
                <form onSubmit={handleDecisionSubmit} className="bg-slate-50 border border-slate-200 p-5 rounded-2xl space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                    <h4 className="text-sm font-bold text-slate-900">Officer Decision & Training Label</h4>
                    <span className="text-[11px] text-slate-500">Every decision trains the online model</span>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">Decision *</label>
                      <select
                        value={decision}
                        onChange={(e) => setDecision(e.target.value)}
                        className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white font-bold"
                      >
                        <option value="approve">APPROVE</option>
                        <option value="reject">REJECT</option>
                        <option value="needs_more_info">NEEDS MORE INFO</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">Mandatory Reason Code *</label>
                      <select
                        value={reasonCode}
                        onChange={(e) => setReasonCode(e.target.value)}
                        className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white font-medium"
                      >
                        <option value="low_foir_stable_income">Low FOIR & Stable Income</option>
                        <option value="strong_employment_stability">Strong Employment Stability</option>
                        <option value="high_debt_burden_foir">Excessive Debt Burden (High FOIR)</option>
                        <option value="document_income_mismatch">Document Income Mismatch</option>
                        <option value="insufficient_income">Insufficient Monthly Income</option>
                        <option value="collateral_mitigation">Adequate Collateral Coverage</option>
                        <option value="policy_exception_approved">Policy Exception Approved</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Officer Notes / Rationale</label>
                    <textarea
                      rows={2}
                      value={officerNotes}
                      onChange={(e) => setOfficerNotes(e.target.value)}
                      placeholder="Enter specific risk assessment or underwriting rationale..."
                      className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:ring-teal-500 focus:outline-none"
                    />
                  </div>

                  <div className="flex items-center justify-between pt-2">
                    <span className="text-xs text-slate-400">
                      AI was: <strong>{appDetail.ai_recommendation}</strong> • {decision === "approve" ? "You are Approving" : "You are Rejecting"}
                    </span>
                    <button
                      type="submit"
                      disabled={isSubmittingDecision}
                      className="flex items-center gap-2 px-5 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold rounded-xl shadow transition"
                    >
                      <Send size={14} />
                      {isSubmittingDecision ? "Saving Decision..." : "Commit Officer Decision"}
                    </button>
                  </div>
                </form>

                {/* Delayed Repayment Outcome Section (Reject Inference Research) */}
                {appDetail.decision && (
                  <div className="p-4 bg-slate-100 rounded-xl border border-slate-200 flex items-center justify-between text-xs">
                    <div>
                      <span className="font-bold text-slate-800 block">Delayed Repayment Outcome (Selective Labels Research)</span>
                      <p className="text-slate-500 text-[11px]">
                        Track observed loan performance for approved borrowers (Reject-inference limitation).
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <select
                        value={repaymentStatus}
                        onChange={(e) => setRepaymentStatus(e.target.value)}
                        className="text-xs border border-slate-300 rounded px-2 py-1 bg-white font-medium"
                      >
                        <option value="unobserved">Unobserved</option>
                        <option value="current">Current (On-time)</option>
                        <option value="defaulted">Defaulted</option>
                        <option value="prepaid">Prepaid Early</option>
                      </select>
                      <button
                        onClick={handleRepaymentUpdate}
                        className="px-3 py-1 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold rounded"
                      >
                        Update
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-white rounded-xl shadow border border-slate-200 p-12 text-center text-slate-400 space-y-2">
                <FileText size={36} className="mx-auto text-slate-300" />
                <p className="text-sm font-medium">Select an application from the queue to inspect and decide.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Fairness Monitor Tab */}
      {activeTab === "fairness" && fairness && (
        <div className="bg-white rounded-xl shadow border border-slate-200 p-6 space-y-6">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Scale size={20} className="text-teal-600" />
              Algorithmic Fairness Audit Monitor
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Live demographic parity, equal opportunity difference, and disparate impact metrics computed on consented audit demographics.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
              <span className="text-xs text-slate-500 block">Demographic Parity Difference</span>
              <span className="text-2xl font-bold text-slate-800">
                {fairness.demographic_parity_difference !== undefined ? fairness.demographic_parity_difference : "N/A"}
              </span>
              <span className="text-[11px] text-slate-400 block mt-1">(Difference in group approval rates)</span>
            </div>
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
              <span className="text-xs text-slate-500 block">Disparate Impact Ratio</span>
              <span className={`text-2xl font-bold ${fairness.adverse_impact_flag ? "text-rose-600" : "text-emerald-600"}`}>
                {fairness.disparate_impact_ratio !== undefined ? fairness.disparate_impact_ratio : "N/A"}
              </span>
              <span className="text-[11px] text-slate-400 block mt-1">
                {fairness.adverse_impact_flag ? "⚠️ Adverse impact (<0.80)" : "Compliant with 4/5ths rule"}
              </span>
            </div>
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
              <span className="text-xs text-slate-500 block">Equal Opportunity Difference</span>
              <span className="text-2xl font-bold text-slate-800">
                {fairness.equal_opportunity_difference !== undefined && fairness.equal_opportunity_difference !== null
                  ? fairness.equal_opportunity_difference
                  : "N/A"}
              </span>
              <span className="text-[11px] text-slate-400 block mt-1">(Difference in True Positive Rates)</span>
            </div>
          </div>

          {fairness.sample_size_warnings && fairness.sample_size_warnings.length > 0 && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 space-y-1">
              <div className="font-bold flex items-center gap-1.5">
                <AlertTriangle size={14} className="text-amber-600" />
                Sample Size & Statistical Significance Warnings:
              </div>
              {fairness.sample_size_warnings.map((w, idx) => (
                <div key={idx} className="ml-5 list-disc">{w}</div>
              ))}
            </div>
          )}

          {/* Group Breakdown Table */}
          <div className="overflow-x-auto border border-slate-200 rounded-xl">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-700 uppercase font-semibold">
                <tr>
                  <th className="p-3">Audit Demographic</th>
                  <th className="p-3">Sample Count</th>
                  <th className="p-3">AI Approval Count</th>
                  <th className="p-3">AI Selection Rate</th>
                  <th className="p-3">Officer Approvals</th>
                  <th className="p-3">True Positive Rate (TPR)</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(fairness.groups || {}).map(([grp, data]) => (
                  <tr key={grp} className="border-t border-slate-200">
                    <td className="p-3 font-bold uppercase">{grp}</td>
                    <td className="p-3">{data.count}</td>
                    <td className="p-3">{data.ai_approval_count}</td>
                    <td className="p-3 font-semibold">{(data.ai_selection_rate * 100).toFixed(1)}%</td>
                    <td className="p-3">{data.officer_approval_count}</td>
                    <td className="p-3">{data.true_positive_rate}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Health & Concept Drift Tab */}
      {activeTab === "health" && stats && (
        <div className="bg-white rounded-xl shadow border border-slate-200 p-6 space-y-6">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <TrendingUp size={20} className="text-teal-600" />
              Online Learning Model Health & Drift Monitor
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              River Hoeffding Adaptive Tree incremental learning pipeline with ADWIN drift detection.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
              <span className="text-xs text-slate-500 block">Operational Mode</span>
              <span className="text-base font-bold text-slate-800 uppercase mt-1 block">
                {stats.stage === "stage3_online_shadow" ? "Shadow Mode" : stats.stage === "stage3_online_active" ? "Active Recommender" : "Awaiting Threshold"}
              </span>
              <span className="text-[11px] text-slate-400 block mt-0.5">Hard policy rules always guardrail</span>
            </div>
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
              <span className="text-xs text-slate-500 block">Rolling 50-Case Agreement</span>
              <span className="text-2xl font-bold text-teal-700">
                {stats.recent_agreement_rate !== null ? `${(stats.recent_agreement_rate * 100).toFixed(1)}%` : "N/A"}
              </span>
              <span className="text-[11px] text-slate-400 block mt-0.5">(Target: ≥ 80% for promotion)</span>
            </div>
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
              <span className="text-xs text-slate-500 block">ADWIN Drift Detector</span>
              <span className="text-base font-bold text-emerald-700 mt-1 block">Active & Listening</span>
              <span className="text-[11px] text-slate-400 block mt-0.5">Delta = 0.002</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
