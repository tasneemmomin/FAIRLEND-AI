import React, { useState, useEffect } from "react";
import { 
  Mic, 
  FileText, 
  LayoutDashboard, 
  Shield, 
  Building2, 
  User, 
  Home, 
  ArrowLeft, 
  LogIn, 
  LogOut, 
  Sparkles, 
  Clock, 
  CheckCircle2, 
  XCircle, 
  AlertCircle,
  ShieldCheck,
  FolderOpen
} from "lucide-react";
import { VoiceAssistant } from "./components/VoiceAssistant";
import { DocumentUploader } from "./components/DocumentUploader";
import { TypedIntakeForm } from "./components/TypedIntakeForm";
import { DocumentIntake } from "./components/DocumentIntake";
import { RecommendationCard } from "./components/RecommendationCard";
import { OfficerDashboard } from "./components/OfficerDashboard";
import { LandingPage, PRODUCT_NAME } from "./components/LandingPage";
import { ApplicantPortalAuth } from "./components/ApplicantPortalAuth";
import { ApplicantResponse, ApplicantIntakeForm, SystemHealth, ApplicantUser } from "./types";
import { getHealth, getCurrentUser, getMyApplications, logoutUser } from "./api";
import "./landing.css";

export function App() {
  const [applicantUser, setApplicantUser] = useState<ApplicantUser | null>(() => {
    try {
      const stored = localStorage.getItem("fairlend_applicant_user") || sessionStorage.getItem("fairlend_applicant_user");
      const token = localStorage.getItem("fairlend_applicant_token") || sessionStorage.getItem("fairlend_applicant_token");
      if (stored && token) {
        const u = JSON.parse(stored);
        u.token = token;
        return u;
      }
      return null;
    } catch {
      return null;
    }
  });

  const [activePortal, setActivePortal] = useState<"landing" | "applicant-auth" | "applicant" | "officer">(() => {
    if (typeof window !== "undefined") {
      const hash = window.location.hash;
      if (hash === "#officer") return "officer";
      if (hash === "#applicant-portal" || hash === "#applicant-auth" || hash === "#login" || hash === "#register") return "applicant-auth";
      if (hash === "#applicant") {
        const token = localStorage.getItem("fairlend_applicant_token") || sessionStorage.getItem("fairlend_applicant_token");
        return token ? "applicant" : "applicant-auth";
      }
    }
    return "landing";
  });

  const [securityNotice, setSecurityNotice] = useState<string | null>(() => {
    if (typeof window !== "undefined" && window.location.hash === "#applicant") {
      const token = localStorage.getItem("fairlend_applicant_token") || sessionStorage.getItem("fairlend_applicant_token");
      if (!token) return "Authentication Required: Please sign in or register to access the personal loan workspace.";
    }
    return null;
  });

  const [applicantMode, setApplicantMode] = useState<"voice" | "typed" | "document">("voice");
  const [submittedResponse, setSubmittedResponse] = useState<ApplicantResponse | null>(null);
  const [voiceFormPrefill, setVoiceFormPrefill] = useState<Partial<ApplicantIntakeForm>>({});
  const [voiceTranscript, setVoiceTranscript] = useState<string>("");
  const [extractedDocData, setExtractedDocData] = useState<any>(null);
  const [consistencyScore, setConsistencyScore] = useState<number>(1.0);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [applicantHistory, setApplicantHistory] = useState<any[]>(() => {
    try {
      const stored = localStorage.getItem("fairlend_applicant_history");
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  // Verify stored session token on mount with backend
  useEffect(() => {
    const token = localStorage.getItem("fairlend_applicant_token") || sessionStorage.getItem("fairlend_applicant_token");
    if (token) {
      getCurrentUser(token)
        .then((verified) => {
          setApplicantUser((prev) => ({
            id: verified.id,
            name: verified.full_name,
            email: verified.email,
            phone: verified.phone || (prev ? prev.phone : ""),
            monthly_income: prev?.monthly_income || 65000,
            employment_type: prev?.employment_type || "salaried",
            token: token
          }));
        })
        .catch(() => {
          // Token expired or invalid: clear session
          localStorage.removeItem("fairlend_applicant_token");
          localStorage.removeItem("fairlend_applicant_user");
          sessionStorage.removeItem("fairlend_applicant_token");
          sessionStorage.removeItem("fairlend_applicant_user");
          setApplicantUser(null);
        });
    }
  }, []);

  // Sync hash routing and protect workspace routes
  useEffect(() => {
    const syncHash = () => {
      const hash = window.location.hash;
      if (hash === "#officer") {
        setActivePortal("officer");
        setSecurityNotice(null);
      } else if (hash === "#applicant-portal" || hash === "#applicant-auth" || hash === "#login" || hash === "#register") {
        setActivePortal("applicant-auth");
      } else if (hash === "#applicant-workspace-demo") {
        const demo: ApplicantUser = {
          id: "APP-DEMO-01",
          name: "Pooja Nair",
          email: "applicant@fairlendai.com",
          phone: "+91 98765 43210",
          monthly_income: 72000,
          employment_type: "salaried",
          token: "demo_token"
        };
        localStorage.setItem("fairlend_applicant_user", JSON.stringify(demo));
        setApplicantUser(demo);
        setActivePortal("applicant");
        setSecurityNotice(null);
      } else if (hash === "#applicant-document-demo" || hash === "#document-intake-demo") {
        const demo: ApplicantUser = {
          id: "APP-DEMO-01",
          name: "Pooja Nair",
          email: "applicant@fairlendai.com",
          phone: "+91 98765 43210",
          monthly_income: 72000,
          employment_type: "salaried",
          token: "demo_token"
        };
        localStorage.setItem("fairlend_applicant_user", JSON.stringify(demo));
        setApplicantUser(demo);
        setActivePortal("applicant");
        setApplicantMode("document");
        setSecurityNotice(null);
      } else if (hash === "#applicant") {
        const token = localStorage.getItem("fairlend_applicant_token") || sessionStorage.getItem("fairlend_applicant_token");
        if (!token && !applicantUser) {
          // Unauthenticated user trying to enter workspace directly: block and redirect to auth
          setActivePortal("applicant-auth");
          setSecurityNotice("Authentication Required: Please sign in or register to access the personal loan workspace.");
        } else {
          setActivePortal("applicant");
          setSecurityNotice(null);
        }
      } else {
        setActivePortal("landing");
        setSecurityNotice(null);
      }
    };

    syncHash();
    window.addEventListener("hashchange", syncHash);
    getHealth().then(setHealth).catch(console.error);

    return () => window.removeEventListener("hashchange", syncHash);
  }, []);

  // Fetch applicant application history from database when authenticated
  useEffect(() => {
    if (applicantUser) {
      getMyApplications()
        .then((apps) => {
          if (apps && Array.isArray(apps) && apps.length > 0) {
            const mapped = apps.map((a) => ({
              id: a.id,
              date: new Date(a.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }),
              name: a.applicant_name,
              recommendation: a.ai_recommendation === "likely_approved" ? "Likely to be approved" : a.ai_recommendation === "needs_review" ? "Needs more review" : "Unlikely to be approved right now",
              code: a.ai_recommendation,
              confidence: a.ai_confidence,
              foir: a.foir,
              amount: a.requested_amount,
              tenure: a.tenure_months
            }));
            setApplicantHistory(mapped);
            localStorage.setItem("fairlend_applicant_history", JSON.stringify(mapped));
          }
        })
        .catch(() => {});
    }
  }, [applicantUser]);

  // Pre-fill form when user profile is loaded
  useEffect(() => {
    if (applicantUser) {
      setVoiceFormPrefill((prev) => ({
        ...prev,
        applicant_name: prev.applicant_name || applicantUser.name,
        contact_email: prev.contact_email || applicantUser.email,
        contact_phone: prev.contact_phone || applicantUser.phone,
        monthly_income: prev.monthly_income || applicantUser.monthly_income || 65000,
        employment_type: prev.employment_type || applicantUser.employment_type || "salaried"
      }));
    }
  }, [applicantUser]);

  const handleNavigate = (portal: "landing" | "applicant" | "officer", mode?: "voice" | "typed" | "document") => {
    if (portal === "officer") {
      window.location.hash = "#officer";
      setActivePortal("officer");
      setSecurityNotice(null);
    } else if (portal === "applicant") {
      const token = localStorage.getItem("fairlend_applicant_token") || sessionStorage.getItem("fairlend_applicant_token");
      if (!applicantUser && !token) {
        // Not authenticated: navigate to dedicated Applicant Authentication page
        window.location.hash = "#applicant-portal";
        setActivePortal("applicant-auth");
        setSecurityNotice(null);
      } else {
        // Authenticated: open workspace
        window.location.hash = "#applicant";
        setActivePortal("applicant");
        setSecurityNotice(null);
      }
      if (mode) setApplicantMode(mode);
    } else {
      window.location.hash = "";
      setActivePortal("landing");
      setSecurityNotice(null);
    }
  };

  const handleAuthSuccess = (user: ApplicantUser) => {
    setApplicantUser(user);
    setSecurityNotice(null);
    window.location.hash = "#applicant";
    setActivePortal("applicant");
  };

  const handleSignOut = async () => {
    await logoutUser();
    localStorage.removeItem("fairlend_applicant_token");
    localStorage.removeItem("fairlend_applicant_user");
    sessionStorage.removeItem("fairlend_applicant_token");
    sessionStorage.removeItem("fairlend_applicant_user");
    setApplicantUser(null);
    setVoiceFormPrefill({});
    setSubmittedResponse(null);
    setSecurityNotice(null);
    window.location.hash = "#applicant-portal";
    setActivePortal("applicant-auth");
  };

  const handleVoiceCompleted = (slots: Partial<ApplicantIntakeForm>, transcript: string) => {
    setVoiceFormPrefill(slots);
    setVoiceTranscript(transcript);
    setApplicantMode("typed"); // Switch to review form
  };

  const handleDocumentExtracted = (extracted: any, score: number) => {
    setExtractedDocData(extracted);
    setConsistencyScore(score);
    if (extracted.monthly_salary) {
      setVoiceFormPrefill((prev) => ({
        ...prev,
        monthly_income: prev.monthly_income || extracted.monthly_salary
      }));
    }
    if (extracted.extracted_name) {
      setVoiceFormPrefill((prev) => ({
        ...prev,
        applicant_name: prev.applicant_name || extracted.extracted_name
      }));
    }
  };

  const handleApplicationSubmitted = (response: ApplicantResponse) => {
    setSubmittedResponse(response);
    const record = {
      id: response.application_id,
      date: new Date().toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }),
      name: response.applicant_name,
      recommendation: response.recommendation,
      code: response.recommendation_code,
      confidence: response.confidence,
      foir: response.foir_percentage,
      amount: voiceFormPrefill.requested_amount || 200000,
      tenure: voiceFormPrefill.tenure_months || 24
    };
    const updated = [record, ...applicantHistory];
    setApplicantHistory(updated);
    localStorage.setItem("fairlend_applicant_history", JSON.stringify(updated));
  };

  // Render Landing Page at root
  if (activePortal === "landing") {
    return <LandingPage onNavigate={handleNavigate} />;
  }

  // Render Internal Portals
  return (
    <div className="min-h-screen bg-[#F7F8F5] text-[#24323D] flex flex-col font-sans">
      {/* Navigation Bar for Internal Portals */}
      <header className="bg-[#172C3D] text-white border-b border-white/10 sticky top-0 z-50 shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <button 
            type="button"
            onClick={() => handleNavigate("landing")}
            className="flex items-center gap-3 text-left bg-transparent border-0 cursor-pointer p-0 text-white hover:opacity-90 transition"
            aria-label={`${PRODUCT_NAME} - Return to Home`}
          >
            <div className="w-9 h-9 rounded-md bg-[#28766B] flex items-center justify-center text-white font-extrabold text-sm shadow" aria-hidden="true">
              FL
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg tracking-tight font-serif">{PRODUCT_NAME}</span>
                <span className="text-[10px] bg-[#28766B]/30 text-[#7FE0D2] border border-[#28766B]/40 px-2 py-0.5 rounded-full font-bold uppercase tracking-wider">
                  Responsible AI
                </span>
              </div>
              <p className="text-[11px] text-[#A0B2C0]">Explainable Credit Assessment & Fairness Monitoring</p>
            </div>
          </button>

          {/* Portal Switcher & Health Status */}
          <div className="flex items-center gap-3 sm:gap-4">
            {health && (
              <div className="hidden md:flex items-center gap-2 px-3 py-1 bg-[#0F1E2A] rounded-lg text-xs border border-white/10">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" aria-hidden="true" />
                <span className="text-slate-300">{health.current_stage_label}</span>
              </div>
            )}

            <div className="bg-[#0F1E2A] p-1 rounded-lg flex items-center gap-1 border border-white/10">
              <button
                type="button"
                onClick={() => handleNavigate("landing")}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-[#A0B2C0] hover:text-white transition"
                title="Return to Landing Page"
              >
                <Home size={14} aria-hidden="true" /> Home
              </button>
              <button
                type="button"
                onClick={() => handleNavigate("applicant")}
                className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-xs font-semibold transition ${
                  activePortal === "applicant" || activePortal === "applicant-auth"
                    ? "bg-[#28766B] text-white shadow"
                    : "text-[#A0B2C0] hover:text-white"
                }`}
              >
                <User size={14} aria-hidden="true" /> {applicantUser ? "Applicant Workspace" : "Applicant Portal"}
              </button>
              <button
                type="button"
                onClick={() => handleNavigate("officer")}
                className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-xs font-semibold transition ${
                  activePortal === "officer"
                    ? "bg-[#28766B] text-white shadow"
                    : "text-[#A0B2C0] hover:text-white"
                }`}
              >
                <LayoutDashboard size={14} aria-hidden="true" /> Officer Portal
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Body */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        {activePortal === "applicant-auth" || (!applicantUser && activePortal === "applicant") ? (
          /* Dedicated Applicant Authentication Interface */
          <ApplicantPortalAuth
            onSuccess={handleAuthSuccess}
            onReturnHome={() => handleNavigate("landing")}
            initialTab={typeof window !== "undefined" && window.location.hash === "#register" ? "register" : "login"}
            securityNotice={securityNotice}
          />
        ) : activePortal === "applicant" && applicantUser ? (
          /* Dedicated Applicant Workspace (Strictly Authenticated) */
          <div className="space-y-6">
            {/* Authenticated Applicant Profile Bar */}
            <div className="bg-white p-3.5 rounded-xl border border-[#E3E8E5] shadow-sm flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-[#28766B] text-white flex items-center justify-center font-bold text-sm shadow">
                  {applicantUser.name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-[#172C3D]">{applicantUser.name}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#ECFDF5] text-[#065F46] border border-[#A7F3D0] font-bold uppercase flex items-center gap-1">
                      <ShieldCheck size={12} /> Authenticated Applicant
                    </span>
                  </div>
                  <p className="text-[11px] text-[#718096]">
                    {applicantUser.email} • {applicantUser.phone} • {applicantUser.employment_type ? applicantUser.employment_type.toUpperCase() : "SALARIED"}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {applicantHistory.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setShowHistory(!showHistory)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition border ${
                      showHistory
                        ? "bg-[#172C3D] text-white border-[#172C3D]"
                        : "border-[#E3E8E5] hover:bg-slate-50 text-[#172C3D]"
                    }`}
                  >
                    <Clock size={13} className="inline mr-1" />
                    {showHistory ? "Back to Form" : `My Applications (${applicantHistory.length})`}
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleSignOut}
                  className="px-3 py-1.5 text-rose-600 hover:bg-rose-50 border border-rose-200 rounded-lg text-xs font-semibold transition flex items-center gap-1"
                >
                  <LogOut size={13} /> Sign Out
                </button>
              </div>
            </div>

            {/* Past Applications Modal/View if toggled */}
            {showHistory && (
              <div className="bg-white rounded-xl shadow-sm border border-[#E3E8E5] p-5 space-y-3">
                <div className="flex items-center justify-between border-b border-[#E3E8E5] pb-2">
                  <h3 className="font-serif font-bold text-base text-[#172C3D]">Saved Applications History</h3>
                  <button 
                    type="button"
                    onClick={() => setShowHistory(false)}
                    className="text-xs text-[#28766B] font-semibold hover:underline"
                  >
                    ← Start New Application
                  </button>
                </div>
                <div className="space-y-2">
                  {applicantHistory.map((item, idx) => (
                    <div key={idx} className="p-3 bg-[#F8FAFC] border border-[#E3E8E5] rounded-lg flex items-center justify-between text-xs">
                      <div>
                        <div className="flex items-center gap-2">
                          <strong className="text-[#172C3D]">{item.name}</strong>
                          <span className="text-[#718096]">ID: {item.id}</span>
                        </div>
                        <p className="text-[#718096] text-[11px] mt-0.5">
                          ₹{Number(item.amount).toLocaleString("en-IN")} • {item.tenure} Months • Submitted on {item.date}
                        </p>
                      </div>
                      <div className="text-right">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                          item.code === "likely_approved"
                            ? "bg-[#ECFDF5] text-[#065F46] border border-[#A7F3D0]"
                            : "bg-[#FFFBEB] text-[#92400E] border border-[#FDE68A]"
                        }`}>
                          {item.recommendation}
                        </span>
                        <span className="block text-[11px] text-[#718096] mt-0.5">FOIR: {item.foir}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Active Submission Result or Intake Form */}
            {submittedResponse ? (
              <RecommendationCard
                response={submittedResponse}
                onReset={() => {
                  setSubmittedResponse(null);
                  setVoiceFormPrefill(applicantUser ? {
                    applicant_name: applicantUser.name,
                    contact_email: applicantUser.email,
                    contact_phone: applicantUser.phone,
                    monthly_income: applicantUser.monthly_income || 65000,
                    employment_type: applicantUser.employment_type || "salaried"
                  } : {});
                  setVoiceTranscript("");
                  setApplicantMode("voice");
                }}
              />
            ) : (
              <div className="space-y-6">
                {/* Mode Selector */}
                <div className="bg-white p-3 rounded-xl shadow-sm border border-[#E3E8E5] flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <button
                      type="button"
                      onClick={() => setApplicantMode("voice")}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition ${
                        applicantMode === "voice"
                          ? "bg-[#28766B] text-white shadow"
                          : "text-[#718096] hover:bg-[#F7F8F5]"
                      }`}
                    >
                      <Mic size={16} aria-hidden="true" /> Voice Assistant Intake
                    </button>
                    <button
                      type="button"
                      onClick={() => setApplicantMode("typed")}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition ${
                        applicantMode === "typed"
                          ? "bg-[#28766B] text-white shadow"
                          : "text-[#718096] hover:bg-[#F7F8F5]"
                      }`}
                    >
                      <FileText size={16} aria-hidden="true" /> Typed Form Intake
                    </button>
                    <button
                      type="button"
                      onClick={() => setApplicantMode("document")}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition ${
                        applicantMode === "document"
                          ? "bg-[#28766B] text-white shadow"
                          : "text-[#718096] hover:bg-[#F7F8F5]"
                      }`}
                    >
                      <FolderOpen size={16} aria-hidden="true" /> Document Intake
                    </button>
                  </div>

                  <span className="text-xs text-[#718096] hidden sm:inline">
                    Step 1: Intake & Documents • Step 2: Instant Policy Recommendation
                  </span>
                </div>

                {/* Intake Content Based on Selected Mode */}
                {applicantMode === "document" ? (
                  <div className="max-w-4xl mx-auto">
                    <DocumentIntake
                      applicantUser={applicantUser}
                      onSubmitted={handleApplicationSubmitted}
                    />
                  </div>
                ) : (
                  /* Two-Column Grid: Intake Left, Document Upload Right */
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                    <div className="lg:col-span-7">
                      {applicantMode === "voice" ? (
                        <VoiceAssistant onFormReady={handleVoiceCompleted} />
                      ) : (
                        <TypedIntakeForm
                          initialValues={voiceFormPrefill}
                          transcript={voiceTranscript}
                          consistencyScore={consistencyScore}
                          onSubmitted={handleApplicationSubmitted}
                        />
                      )}
                    </div>

                    <div className="lg:col-span-5 space-y-6">
                      <DocumentUploader
                        declaredIncome={voiceFormPrefill.monthly_income}
                        declaredName={voiceFormPrefill.applicant_name}
                        onExtracted={handleDocumentExtracted}
                      />

                      {/* Security & Regulatory Feature Card */}
                      <div className="bg-white rounded-xl shadow-sm border border-[#E3E8E5] p-5 space-y-3">
                        <div className="flex items-center gap-2 text-[#172C3D] font-bold text-sm">
                          <Shield size={18} className="text-[#28766B]" aria-hidden="true" />
                          Safe & Responsible Lending Architecture
                        </div>
                        <ul className="text-xs text-[#718096] space-y-2">
                          <li className="flex items-start gap-2">
                            <span className="text-[#28766B] font-bold" aria-hidden="true">•</span>
                            <span><strong>Zero Raw Audio Storage:</strong> Audio recordings are discarded immediately after local transcription.</span>
                          </li>
                          <li className="flex items-start gap-2">
                            <span className="text-[#28766B] font-bold" aria-hidden="true">•</span>
                            <span><strong>Demographic Quarantine:</strong> Gender, caste, and religion are strictly quarantined from all credit scoring models.</span>
                          </li>
                          <li className="flex items-start gap-2">
                            <span className="text-[#28766B] font-bold" aria-hidden="true">•</span>
                            <span><strong>DPDP Act 2023 Compliant:</strong> You have full statutory rights to export machine-readable data or permanently erase personal records.</span>
                          </li>
                        </ul>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          /* Officer Command Center */
          <OfficerDashboard />
        )}
      </main>

      {/* Footer & RBI Regulatory Notice */}
      <footer className="bg-[#0F1E2A] text-[#A0B2C0] text-xs py-6 border-t border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-2 text-center">
          <p className="font-semibold text-slate-300">
            {PRODUCT_NAME} — Compliant with RBI Digital Lending Guidelines (2022) & India DPDP Act (2023)
          </p>
          <p className="max-w-3xl mx-auto text-[11px] text-slate-500">
            Disclaimer: This application is an educational and academic research prototype for explainable, voice-enabled credit assessment. 
            All AI outputs are classified strictly as "Recommendations"; the designated human Loan Officer is the sole and final decision-maker. 
            No static or historical dataset is bundled or used for training.
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
