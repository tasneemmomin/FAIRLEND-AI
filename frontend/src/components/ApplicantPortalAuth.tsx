import React, { useState } from "react";
import { 
  User, 
  Mail, 
  Phone, 
  Lock, 
  Eye, 
  EyeOff, 
  ArrowRight, 
  ShieldCheck, 
  CheckCircle2, 
  AlertTriangle,
  HelpCircle,
  X
} from "lucide-react";
import { loginUser, registerApplicant } from "../api";
import { ApplicantUser } from "../types";

interface ApplicantPortalAuthProps {
  onSuccess: (user: ApplicantUser) => void;
  onReturnHome: () => void;
  initialTab?: "login" | "register";
  securityNotice?: string | null;
}

export const ApplicantPortalAuth: React.FC<ApplicantPortalAuthProps> = ({
  onSuccess,
  onReturnHome,
  initialTab = "login",
  securityNotice = null
}) => {
  const [activeTab, setActiveTab] = useState<"login" | "register">(initialTab);

  // Login form state
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);

  // Registration form state
  const [regFullName, setRegFullName] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPhone, setRegPhone] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regConfirmPassword, setRegConfirmPassword] = useState("");
  const [showRegPassword, setShowRegPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [agreeConsent, setAgreeConsent] = useState(true);

  // UI status
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [showForgotModal, setShowForgotModal] = useState(false);

  // Handle Login submission
  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const email = loginEmail.trim().toLowerCase();
    if (!email || !loginPassword) {
      setErrorMessage("Please enter both your email address and password.");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await loginUser(email, loginPassword, "applicant");
      const storage = rememberMe ? localStorage : sessionStorage;
      storage.setItem("fairlend_applicant_token", res.access_token);
      
      const appUser: ApplicantUser = {
        id: res.user.id,
        name: res.user.full_name,
        email: res.user.email,
        phone: res.user.phone || "",
        monthly_income: 65000,
        employment_type: "salaried",
        token: res.access_token
      };
      storage.setItem("fairlend_applicant_user", JSON.stringify(appUser));
      onSuccess(appUser);
    } catch (err: any) {
      setErrorMessage(err.message || "Invalid credentials. Please verify your email and password.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Registration submission
  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const fullName = regFullName.trim();
    const email = regEmail.trim().toLowerCase();
    const phone = regPhone.trim();

    if (!fullName || !email || !phone || !regPassword || !regConfirmPassword) {
      setErrorMessage("All registration fields are required.");
      return;
    }

    if (fullName.length < 2) {
      setErrorMessage("Please enter your full legal name (minimum 2 characters).");
      return;
    }

    const emailRegex = /^[\w\.-]+@[\w\.-]+\.\w+$/;
    if (!emailRegex.test(email)) {
      setErrorMessage("Please provide a valid email address (e.g. yourname@example.com).");
      return;
    }

    const digitsOnly = phone.replace(/\D/g, "");
    if (digitsOnly.length < 10) {
      setErrorMessage("Please provide a valid 10-digit mobile number.");
      return;
    }

    if (regPassword.length < 8) {
      setErrorMessage("Password must be at least 8 characters long.");
      return;
    }

    if (!/[A-Za-z]/.test(regPassword) || !/[0-9]/.test(regPassword)) {
      setErrorMessage("Password must contain at least one letter and one number.");
      return;
    }

    if (regPassword !== regConfirmPassword) {
      setErrorMessage("Passwords do not match. Please re-enter your password confirmation.");
      return;
    }

    if (!agreeConsent) {
      setErrorMessage("You must agree to the DPDP Act credit assessment consent to register.");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await registerApplicant(fullName, email, phone, regPassword);
      setSuccessMessage("Account created successfully! Entering your personal loan workspace...");
      
      const storage = localStorage;
      storage.setItem("fairlend_applicant_token", res.access_token);
      
      const appUser: ApplicantUser = {
        id: res.user.id,
        name: res.user.full_name,
        email: res.user.email,
        phone: res.user.phone || phone,
        monthly_income: 60000,
        employment_type: "salaried",
        token: res.access_token
      };
      storage.setItem("fairlend_applicant_user", JSON.stringify(appUser));
      
      setTimeout(() => {
        onSuccess(appUser);
      }, 700);
    } catch (err: any) {
      setErrorMessage(err.message || "Registration failed. An account with this email may already exist.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex flex-col justify-center items-center py-10 px-4 sm:px-6">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl border border-[#E3E8E5] overflow-hidden animate-fade-in">
        
        {/* Institutional Header */}
        <div className="bg-[#172C3D] text-white p-6 text-center space-y-2 relative">
          <div className="w-12 h-12 mx-auto rounded-xl bg-[#28766B] flex items-center justify-center text-white font-extrabold text-lg shadow">
            FL
          </div>
          <h2 className="font-serif text-2xl font-bold tracking-tight text-white">
            Applicant Portal
          </h2>
          <p className="text-xs text-[#A0B2C0] max-w-xs mx-auto">
            Secure sign-in and registration for borrowers & loan applicants.
          </p>

          <div className="pt-2 flex items-center justify-center gap-2 text-[11px] text-[#7FE0D2]">
            <ShieldCheck size={14} />
            <span>Encrypted in transit &amp; at rest • DPDP Act 2023 Compliant</span>
          </div>
        </div>

        {/* Security Notification Banner if redirected */}
        {securityNotice && (
          <div className="p-3 bg-amber-50 border-b border-amber-200 text-amber-800 text-xs flex items-center gap-2 px-6">
            <AlertTriangle size={15} className="text-amber-600 flex-shrink-0" />
            <span>{securityNotice}</span>
          </div>
        )}

        {/* Tab Switcher: Login vs Registration */}
        <div className="flex border-b border-[#E3E8E5] bg-[#F7F8F5]">
          <button
            type="button"
            onClick={() => { setActiveTab("login"); setErrorMessage(null); }}
            className={`flex-1 py-3 text-xs font-bold transition border-b-2 ${
              activeTab === "login"
                ? "border-[#28766B] text-[#172C3D] bg-white shadow-sm"
                : "border-transparent text-[#718096] hover:text-[#172C3D]"
            }`}
          >
            Applicant Sign In
          </button>
          <button
            type="button"
            onClick={() => { setActiveTab("register"); setErrorMessage(null); }}
            className={`flex-1 py-3 text-xs font-bold transition border-b-2 ${
              activeTab === "register"
                ? "border-[#28766B] text-[#172C3D] bg-white shadow-sm"
                : "border-transparent text-[#718096] hover:text-[#172C3D]"
            }`}
          >
            New Registration
          </button>
        </div>

        <div className="p-6 space-y-5">
          {/* Feedback messages */}
          {errorMessage && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-xl flex items-start gap-2">
              <AlertTriangle size={16} className="text-rose-600 flex-shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          {successMessage && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-xl flex items-center gap-2">
              <CheckCircle2 size={16} className="text-emerald-600 flex-shrink-0" />
              <span>{successMessage}</span>
            </div>
          )}

          {/* =============================================================
              TAB A: APPLICANT LOGIN
              ============================================================= */}
          {activeTab === "login" ? (
            <div className="space-y-4">
              {/* Form */}
              <form onSubmit={handleLoginSubmit} className="space-y-3.5 text-xs">
                <div>
                  <label className="block text-[#24323D] font-semibold mb-1">Email Address</label>
                  <div className="relative">
                    <Mail size={15} className="absolute left-3 top-2.5 text-[#718096]" />
                    <input
                      type="email"
                      required
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                      placeholder="e.g. rahul.sharma@example.com"
                      className="w-full pl-9 pr-3 py-2 border border-[#E3E8E5] rounded-lg focus:outline-none focus:border-[#28766B] text-xs"
                    />
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="block text-[#24323D] font-semibold">Password</label>
                    <button
                      type="button"
                      onClick={() => setShowForgotModal(true)}
                      className="text-[11px] text-[#28766B] hover:underline"
                    >
                      Forgot Password?
                    </button>
                  </div>
                  <div className="relative">
                    <Lock size={15} className="absolute left-3 top-2.5 text-[#718096]" />
                    <input
                      type={showLoginPassword ? "text" : "password"}
                      required
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full pl-9 pr-9 py-2 border border-[#E3E8E5] rounded-lg focus:outline-none focus:border-[#28766B] text-xs"
                    />
                    <button
                      type="button"
                      onClick={() => setShowLoginPassword(!showLoginPassword)}
                      className="absolute right-3 top-2.5 text-[#718096] hover:text-[#172C3D]"
                      title={showLoginPassword ? "Hide password" : "Show password"}
                    >
                      {showLoginPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-1">
                  <label className="flex items-center gap-2 cursor-pointer select-none text-[11px] text-[#718096]">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="rounded border-[#E3E8E5] text-[#28766B] focus:ring-[#28766B]"
                    />
                    <span>Remember my session on this device</span>
                  </label>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full py-2.5 bg-[#172C3D] hover:bg-[#0F1E2A] text-white font-semibold rounded-lg text-xs shadow transition flex items-center justify-center gap-1.5 disabled:opacity-50"
                >
                  {isSubmitting ? "Authenticating..." : "Sign In to Applicant Workspace"} <ArrowRight size={14} />
                </button>
              </form>

              <div className="text-center pt-2">
                <span className="text-[11px] text-[#718096]">
                  Don't have an account yet?{" "}
                  <button
                    type="button"
                    onClick={() => { setActiveTab("register"); setErrorMessage(null); }}
                    className="text-[#28766B] font-bold hover:underline"
                  >
                    Register here →
                  </button>
                </span>
              </div>
            </div>
          ) : (
            /* =============================================================
               TAB B: APPLICANT REGISTRATION
               ============================================================= */
            <form onSubmit={handleRegisterSubmit} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-[#24323D] font-semibold mb-1">Full Legal Name *</label>
                <div className="relative">
                  <User size={15} className="absolute left-3 top-2.5 text-[#718096]" />
                  <input
                    type="text"
                    required
                    value={regFullName}
                    onChange={(e) => setRegFullName(e.target.value)}
                    placeholder="e.g. Rahul Sharma"
                    className="w-full pl-9 pr-3 py-2 border border-[#E3E8E5] rounded-lg focus:outline-none focus:border-[#28766B] text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[#24323D] font-semibold mb-1">Email Address *</label>
                <div className="relative">
                  <Mail size={15} className="absolute left-3 top-2.5 text-[#718096]" />
                  <input
                    type="email"
                    required
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    placeholder="e.g. rahul.sharma@example.com"
                    className="w-full pl-9 pr-3 py-2 border border-[#E3E8E5] rounded-lg focus:outline-none focus:border-[#28766B] text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[#24323D] font-semibold mb-1">Mobile Phone Number *</label>
                <div className="relative">
                  <Phone size={15} className="absolute left-3 top-2.5 text-[#718096]" />
                  <input
                    type="tel"
                    required
                    value={regPhone}
                    onChange={(e) => setRegPhone(e.target.value)}
                    placeholder="+91 98765 43210"
                    className="w-full pl-9 pr-3 py-2 border border-[#E3E8E5] rounded-lg focus:outline-none focus:border-[#28766B] text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#24323D] font-semibold mb-1">Password *</label>
                  <div className="relative">
                    <input
                      type={showRegPassword ? "text" : "password"}
                      required
                      value={regPassword}
                      onChange={(e) => setRegPassword(e.target.value)}
                      placeholder="Min 8 chars"
                      className="w-full pr-8 pl-3 py-2 border border-[#E3E8E5] rounded-lg focus:outline-none focus:border-[#28766B] text-xs"
                    />
                    <button
                      type="button"
                      onClick={() => setShowRegPassword(!showRegPassword)}
                      className="absolute right-2.5 top-2.5 text-[#718096] hover:text-[#172C3D]"
                    >
                      {showRegPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-[#24323D] font-semibold mb-1">Confirm Password *</label>
                  <div className="relative">
                    <input
                      type={showConfirmPassword ? "text" : "password"}
                      required
                      value={regConfirmPassword}
                      onChange={(e) => setRegConfirmPassword(e.target.value)}
                      placeholder="Re-enter"
                      className="w-full pr-8 pl-3 py-2 border border-[#E3E8E5] rounded-lg focus:outline-none focus:border-[#28766B] text-xs"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-2.5 top-2.5 text-[#718096] hover:text-[#172C3D]"
                    >
                      {showConfirmPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>
                </div>
              </div>

              <div className="text-[10px] text-[#718096] bg-slate-50 p-2.5 rounded-lg border border-slate-200 space-y-1">
                <span className="font-bold text-[#172C3D] block">Password Security Policy:</span>
                <ul className="list-disc pl-4 space-y-0.5 text-[#718096]">
                  <li className={regPassword.length >= 8 ? "text-emerald-700 font-semibold" : ""}>
                    At least 8 characters
                  </li>
                  <li className={/[A-Za-z]/.test(regPassword) && /[0-9]/.test(regPassword) ? "text-emerald-700 font-semibold" : ""}>
                    Contains letters and numbers
                  </li>
                </ul>
              </div>

              {/* Consent checkbox */}
              <label className="flex items-start gap-2 cursor-pointer select-none text-[11px] text-[#718096] pt-1">
                <input
                  type="checkbox"
                  required
                  checked={agreeConsent}
                  onChange={(e) => setAgreeConsent(e.target.checked)}
                  className="rounded border-[#E3E8E5] text-[#28766B] focus:ring-[#28766B] mt-0.5"
                />
                <span>
                  I confirm the accuracy of my details and consent to automated credit policy evaluation under India's Digital Personal Data Protection (DPDP) Act 2023.
                </span>
              </label>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-2.5 bg-[#28766B] hover:bg-[#1E5C53] text-white font-semibold rounded-lg text-xs shadow transition flex items-center justify-center gap-1.5 disabled:opacity-50"
              >
                {isSubmitting ? "Creating Account..." : "Create Account & Enter Workspace"} <ArrowRight size={14} />
              </button>

              <div className="text-center pt-2">
                <span className="text-[11px] text-[#718096]">
                  Already have an account?{" "}
                  <button
                    type="button"
                    onClick={() => { setActiveTab("login"); setErrorMessage(null); }}
                    className="text-[#28766B] font-bold hover:underline"
                  >
                    Sign in here →
                  </button>
                </span>
              </div>
            </form>
          )}

          <div className="border-t border-[#E3E8E5] pt-3 text-center">
            <button
              type="button"
              onClick={onReturnHome}
              className="text-xs text-[#718096] hover:text-[#172C3D] transition font-medium"
            >
              ← Return to FairLendAI Homepage
            </button>
          </div>
        </div>
      </div>

      {/* Forgot Password Modal */}
      {showForgotModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-white rounded-2xl shadow-2xl border border-[#E3E8E5] max-w-sm w-full p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-bold text-[#172C3D]">
                <HelpCircle size={18} className="text-[#28766B]" />
                Password Reset Instructions
              </div>
              <button 
                type="button"
                onClick={() => setShowForgotModal(false)}
                className="text-[#718096] hover:text-[#172C3D]"
              >
                <X size={18} />
              </button>
            </div>
            <p className="text-xs text-[#718096] leading-relaxed">
              For security reasons under the DPDP Act 2023, automated self-service password reset is governed by multi-factor underwriter verification.
            </p>
            <div className="bg-[#F7F8F5] p-3 rounded-xl border border-[#E3E8E5] text-xs text-[#172C3D] space-y-1">
              <strong>Need immediate access?</strong>
              <p className="text-[11px] text-[#718096]">
                You can create a new account in 30 seconds using the <strong>New Registration</strong> tab.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowForgotModal(false)}
              className="w-full py-2 bg-[#172C3D] text-white text-xs font-semibold rounded-lg"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

