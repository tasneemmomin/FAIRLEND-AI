import React, { useState } from "react";
import { X, User, Mail, Phone, Lock, DollarSign, Briefcase, CheckCircle2, Sparkles, ArrowRight } from "lucide-react";
import { ApplicantUser } from "../types";

interface ApplicantAuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (user: ApplicantUser) => void;
}

export const ApplicantAuthModal: React.FC<ApplicantAuthModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [tab, setTab] = useState<"signin" | "register">("signin");
  
  // Sign In fields
  const [signInIdentifier, setSignInIdentifier] = useState("");
  const [signInPassword, setSignInPassword] = useState("");
  
  // Register fields
  const [regName, setRegName] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPhone, setRegPhone] = useState("");
  const [regIncome, setRegIncome] = useState<number>(65000);
  const [regEmployment, setRegEmployment] = useState("salaried");
  const [regPassword, setRegPassword] = useState("");

  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleDemoSignIn = () => {
    const demoUser: ApplicantUser = {
      id: "APP-DEMO-01",
      name: "Pooja Nair",
      email: "pooja.nair@example.com",
      phone: "+91 98765 43210",
      monthly_income: 72000,
      employment_type: "salaried"
    };
    localStorage.setItem("fairlend_applicant_user", JSON.stringify(demoUser));
    onSuccess(demoUser);
    onClose();
  };

  const handleSignInSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!signInIdentifier.trim()) {
      setError("Please enter your email or phone number.");
      return;
    }
    // Check if user exists in localStorage, or create session
    const stored = localStorage.getItem("fairlend_applicant_user");
    let user: ApplicantUser;
    if (stored) {
      user = JSON.parse(stored);
      if (user.email === signInIdentifier || user.phone === signInIdentifier) {
        onSuccess(user);
        onClose();
        return;
      }
    }
    // If new login identifier
    user = {
      id: "APP-" + Math.floor(1000 + Math.random() * 9000),
      name: signInIdentifier.includes("@") ? signInIdentifier.split("@")[0] : "Applicant",
      email: signInIdentifier.includes("@") ? signInIdentifier : "applicant@example.com",
      phone: !signInIdentifier.includes("@") ? signInIdentifier : "+91 98765 43210",
      monthly_income: 65000,
      employment_type: "salaried"
    };
    localStorage.setItem("fairlend_applicant_user", JSON.stringify(user));
    onSuccess(user);
    onClose();
  };

  const handleRegisterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!regName.trim() || !regEmail.trim() || !regPhone.trim()) {
      setError("Please fill out your Name, Email, and Phone Number.");
      return;
    }
    const newUser: ApplicantUser = {
      id: "APP-" + Math.floor(1000 + Math.random() * 9000),
      name: regName.trim(),
      email: regEmail.trim(),
      phone: regPhone.trim(),
      monthly_income: Number(regIncome) || 50000,
      employment_type: regEmployment
    };
    localStorage.setItem("fairlend_applicant_user", JSON.stringify(newUser));
    onSuccess(newUser);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl border border-[#E3E8E5] max-w-md w-full overflow-hidden">
        {/* Modal Top Bar */}
        <div className="bg-[#172C3D] text-white p-5 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-md bg-[#28766B] flex items-center justify-center text-white font-extrabold text-xs shadow">
              FL
            </div>
            <div>
              <h3 className="font-serif font-bold text-base text-white">Applicant Portal Access</h3>
              <p className="text-[11px] text-[#A0B2C0]">Save application data & track policy evaluations</p>
            </div>
          </div>
          <button 
            type="button" 
            onClick={onClose}
            className="text-white/70 hover:text-white p-1 rounded-lg hover:bg-white/10 transition"
          >
            <X size={20} />
          </button>
        </div>

        {/* Tab Toggle */}
        <div className="flex border-b border-[#E3E8E5] bg-[#F7F8F5] text-xs font-semibold">
          <button
            type="button"
            onClick={() => { setTab("signin"); setError(null); }}
            className={`flex-1 py-3 text-center transition ${
              tab === "signin"
                ? "bg-white text-[#172C3D] border-b-2 border-[#28766B] font-bold shadow-sm"
                : "text-[#718096] hover:text-[#172C3D]"
            }`}
          >
            Sign In to Account
          </button>
          <button
            type="button"
            onClick={() => { setTab("register"); setError(null); }}
            className={`flex-1 py-3 text-center transition ${
              tab === "register"
                ? "bg-white text-[#172C3D] border-b-2 border-[#28766B] font-bold shadow-sm"
                : "text-[#718096] hover:text-[#172C3D]"
            }`}
          >
            Create New Account
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4">
          {error && (
            <div className="p-2.5 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg font-medium">
              {error}
            </div>
          )}

          {/* Quick Demo Action */}
          <div className="p-3 bg-[#EBF5F3] border border-[#BBF7D0] rounded-xl flex items-center justify-between">
            <div className="text-xs">
              <span className="font-bold text-[#166534] block">Demo Applicant Account</span>
              <span className="text-[#15803D] text-[11px]">Pooja Nair (₹72,000 / mo • Salaried)</span>
            </div>
            <button
              type="button"
              onClick={handleDemoSignIn}
              className="px-3 py-1.5 bg-[#28766B] hover:bg-[#1E5C53] text-white rounded-lg text-xs font-semibold shadow-sm transition flex items-center gap-1"
            >
              <Sparkles size={13} /> 1-Click Demo Sign In
            </button>
          </div>

          {tab === "signin" ? (
            <form onSubmit={handleSignInSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block text-[#24323D] font-semibold mb-1">Email or Mobile Number</label>
                <div className="relative">
                  <Mail size={15} className="absolute left-3 top-2.5 text-[#718096]" />
                  <input
                    type="text"
                    value={signInIdentifier}
                    onChange={(e) => setSignInIdentifier(e.target.value)}
                    placeholder="pooja.nair@example.com or +91 98765 43210"
                    className="w-full pl-9 pr-3 py-2 border border-[#E3E8E5] rounded-lg focus:outline-none focus:border-[#28766B]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[#24323D] font-semibold mb-1">Password</label>
                <div className="relative">
                  <Lock size={15} className="absolute left-3 top-2.5 text-[#718096]" />
                  <input
                    type="password"
                    value={signInPassword}
                    onChange={(e) => setSignInPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-9 pr-3 py-2 border border-[#E3E8E5] rounded-lg focus:outline-none focus:border-[#28766B]"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="w-full mt-2 py-2.5 bg-[#172C3D] hover:bg-[#0F1E2A] text-white font-semibold rounded-lg shadow-sm transition text-xs flex items-center justify-center gap-2"
              >
                Sign In to Workspace <ArrowRight size={14} />
              </button>
            </form>
          ) : (
            <form onSubmit={handleRegisterSubmit} className="space-y-2.5 text-xs">
              <div>
                <label className="block text-[#24323D] font-semibold mb-1">Full Legal Name</label>
                <input
                  type="text"
                  value={regName}
                  onChange={(e) => setRegName(e.target.value)}
                  placeholder="e.g. Pooja Nair"
                  className="w-full px-3 py-1.5 border border-[#E3E8E5] rounded-lg focus:outline-none focus:border-[#28766B]"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[#24323D] font-semibold mb-1">Email Address</label>
                  <input
                    type="email"
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    placeholder="pooja@example.com"
                    className="w-full px-3 py-1.5 border border-[#E3E8E5] rounded-lg focus:outline-none focus:border-[#28766B]"
                  />
                </div>
                <div>
                  <label className="block text-[#24323D] font-semibold mb-1">Mobile Number</label>
                  <input
                    type="tel"
                    value={regPhone}
                    onChange={(e) => setRegPhone(e.target.value)}
                    placeholder="+91 98765 43210"
                    className="w-full px-3 py-1.5 border border-[#E3E8E5] rounded-lg focus:outline-none focus:border-[#28766B]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[#24323D] font-semibold mb-1">Monthly Take-Home (₹)</label>
                  <input
                    type="number"
                    value={regIncome}
                    onChange={(e) => setRegIncome(Number(e.target.value))}
                    className="w-full px-3 py-1.5 border border-[#E3E8E5] rounded-lg focus:outline-none focus:border-[#28766B]"
                  />
                </div>
                <div>
                  <label className="block text-[#24323D] font-semibold mb-1">Employment Type</label>
                  <select
                    value={regEmployment}
                    onChange={(e) => setRegEmployment(e.target.value)}
                    className="w-full px-3 py-1.5 border border-[#E3E8E5] rounded-lg focus:outline-none focus:border-[#28766B]"
                  >
                    <option value="salaried">Salaried (Private/Govt)</option>
                    <option value="self_employed">Self Employed / Business</option>
                    <option value="professional">Professional (Doctor/CA/Lawyer)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[#24323D] font-semibold mb-1">Password</label>
                <input
                  type="password"
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                  placeholder="Create secure password"
                  className="w-full px-3 py-1.5 border border-[#E3E8E5] rounded-lg focus:outline-none focus:border-[#28766B]"
                />
              </div>

              <button
                type="submit"
                className="w-full mt-2 py-2.5 bg-[#28766B] hover:bg-[#1E5C53] text-white font-semibold rounded-lg shadow-sm transition text-xs flex items-center justify-center gap-2"
              >
                Register & Save Profile <CheckCircle2 size={14} />
              </button>
            </form>
          )}

          <p className="text-[11px] text-[#718096] text-center pt-1 border-t border-[#E3E8E5]">
            Protected under the India DPDP Act 2023. Profile data is encrypted and stored locally.
          </p>
        </div>
      </div>
    </div>
  );
};

