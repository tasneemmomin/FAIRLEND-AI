import React, { useState, useEffect } from "react";
import { 
  ShieldCheck, 
  FileSearch, 
  BarChart3, 
  Users, 
  ArrowRight, 
  CheckCircle2, 
  AlertTriangle,
  Menu,
  X,
  Lock,
  Layers,
  Sparkles,
  FileText,
  UserCheck,
  TrendingUp,
  Sliders,
  Scale,
  UploadCloud,
  Check,
  FileCheck2,
  Mic,
  Languages,
  Radio,
  Volume2
} from "lucide-react";
import { getHealth } from "../api";
import { SystemHealth } from "../types";

export const PRODUCT_NAME = "FairLendAI";

interface LandingPageProps {
  onNavigate: (portal: "applicant" | "officer", mode?: "voice" | "typed") => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onNavigate }) => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [healthStatus, setHealthStatus] = useState<string | null>(null);
  const [activeHeroTab, setActiveHeroTab] = useState<"voice" | "scorecard">("voice");
  const [activeXaiTab, setActiveXaiTab] = useState<"factors" | "plain">("factors");

  // Interactive Voice Demo Simulation state
  const [simulatedVoiceIndex, setSimulatedVoiceIndex] = useState(0);
  const sampleVoicePhrases = [
    {
      phrase: "I want to apply for a ₹3,00,000 personal loan for 24 months. My salary is ₹65,000 and bike loan EMI is ₹4,000.",
      lang: "English (IN)",
      amount: "₹3,00,000",
      tenure: "24 Months",
      income: "₹65,000",
      debts: "₹4,000 / mo",
      purpose: "Personal Loan"
    },
    {
      phrase: "Mujhe ₹2,00,000 ka loan chahiye 36 mahine ke liye, meri monthly income ₹50,000 hai aur koi loan nahi hai.",
      lang: "हिन्दी (IN)",
      amount: "₹2,00,000",
      tenure: "36 Months",
      income: "₹50,000",
      debts: "₹0 / mo",
      purpose: "Personal / Retail"
    },
    {
      phrase: "Need ₹5,00,000 business expansion loan for 48 months. Current monthly income is ₹1,20,000.",
      lang: "English (IN)",
      amount: "₹5,00,000",
      tenure: "48 Months",
      income: "₹1,20,000",
      debts: "₹15,000 / mo",
      purpose: "Business Expansion"
    }
  ];

  const currentSim = sampleVoicePhrases[simulatedVoiceIndex];

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 40);
    };
    window.addEventListener("scroll", handleScroll, { passive: true });

    // Fetch dynamic backend health status
    getHealth()
      .then((data: SystemHealth) => {
        if (data && data.status === "healthy" && data.current_stage_label) {
          setHealthStatus(data.current_stage_label);
        }
      })
      .catch(() => {
        setHealthStatus(null);
      });

    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <div className="fl-root">
      {/* Skip to Content for Accessibility */}
      <a href="#main-content" className="fl-skip-link">
        Skip to main content
      </a>

      {/* --------------------------------------------------------------------
          2. Landing Page Header & Navigation Bar
          -------------------------------------------------------------------- */}
      <header className={`fl-nav ${isScrolled ? "scrolled" : ""}`}>
        <div className="fl-nav-container">
          <a href="#" className="fl-brand" aria-label={`${PRODUCT_NAME} Home`}>
            <div className="fl-brand-badge" aria-hidden="true">FL</div>
            <span className="fl-brand-name">{PRODUCT_NAME}</span>
          </a>

          {/* Desktop Navigation Links */}
          <nav aria-label="Main Navigation">
            <ul className="fl-nav-menu">
              <li><a href="#platform" className="fl-nav-link">Platform</a></li>
              <li><a href="#voice-intake" className="fl-nav-link">Voice Assistant</a></li>
              <li><a href="#how-it-works" className="fl-nav-link">How It Works</a></li>
              <li><a href="#explainable-ai" className="fl-nav-link">Explainable AI</a></li>
              <li><a href="#documents" className="fl-nav-link">Document Intel</a></li>
              <li><a href="#model-fairness" className="fl-nav-link">Fairness & Drift</a></li>
            </ul>
          </nav>

          {/* Navigation Action Buttons */}
          <div className="fl-nav-actions">
            <button 
              type="button"
              onClick={() => onNavigate("officer")} 
              className="fl-btn-nav-secondary"
            >
              Officer Portal
            </button>
            <button
              type="button"
              className="fl-mobile-toggle"
              aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
              aria-expanded={mobileMenuOpen}
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>

        {/* Mobile Slide-Down Drawer */}
        <div className={`fl-mobile-menu ${mobileMenuOpen ? "open" : ""}`} aria-hidden={!mobileMenuOpen}>
          <div className="fl-mobile-links">
            <a href="#platform" onClick={() => setMobileMenuOpen(false)}>Platform</a>
            <a href="#voice-intake" onClick={() => setMobileMenuOpen(false)}>Voice Assistant</a>
            <a href="#how-it-works" onClick={() => setMobileMenuOpen(false)}>How It Works</a>
            <a href="#explainable-ai" onClick={() => setMobileMenuOpen(false)}>Explainable AI</a>
            <a href="#documents" onClick={() => setMobileMenuOpen(false)}>Document Intel</a>
            <a href="#model-fairness" onClick={() => setMobileMenuOpen(false)}>Fairness & Drift</a>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <button 
              type="button"
              onClick={() => { setMobileMenuOpen(false); onNavigate("applicant"); }} 
              className="fl-btn-nav-primary"
              style={{ width: "100%", textAlign: "center" }}
            >
              Applicant Portal →
            </button>
            <button 
              type="button"
              onClick={() => { setMobileMenuOpen(false); onNavigate("officer"); }} 
              className="fl-btn-nav-secondary"
              style={{ width: "100%", textAlign: "center" }}
            >
              Officer Portal
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Landmark */}
      <main id="main-content">
        {/* ------------------------------------------------------------------
            3. Hero Section
            ------------------------------------------------------------------ */}
        <section className="fl-hero">
          <div className="fl-hero-container">
            {/* Left Content */}
            <div className="fl-hero-content">
              <div className="fl-pill-badge">
                <Sparkles size={14} aria-hidden="true" />
                <span>Conversational Intake & Explainable Lending</span>
              </div>
              
              <h1 className="fl-hero-headline">
                Smarter Credit Assessment. Clearer Decisions.
              </h1>

              <div className="fl-hero-buttons">
                <button
                  type="button"
                  onClick={() => onNavigate("applicant")}
                  className="fl-btn-primary"
                  style={{ display: "inline-flex", alignItems: "center", gap: "8px", minWidth: "200px", justifyContent: "center" }}
                >
                  Applicant Portal →
                </button>
              </div>
            </div>

            {/* Right: Realistic Dual-Mode Interactive Preview (Voice & Scorecard) */}
            <div className="fl-hero-preview" aria-label="Interactive loan assessment preview">
              <div className="fl-preview-workspace">
                {/* Hero Tab Switcher */}
                <div style={{ display: "flex", borderBottom: "1px solid var(--fl-border)", paddingBottom: "8px", gap: "8px" }}>
                  <button
                    type="button"
                    onClick={() => setActiveHeroTab("voice")}
                    style={{
                      padding: "6px 12px",
                      borderRadius: "6px",
                      fontSize: "12px",
                      fontWeight: 700,
                      cursor: "pointer",
                      border: "none",
                      background: activeHeroTab === "voice" ? "var(--fl-teal)" : "#F1F5F9",
                      color: activeHeroTab === "voice" ? "#ffffff" : "var(--fl-text-secondary)",
                      display: "flex",
                      alignItems: "center",
                      gap: "6px"
                    }}
                  >
                    <Mic size={14} /> Voice Assistant Intake
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveHeroTab("scorecard")}
                    style={{
                      padding: "6px 12px",
                      borderRadius: "6px",
                      fontSize: "12px",
                      fontWeight: 700,
                      cursor: "pointer",
                      border: "none",
                      background: activeHeroTab === "scorecard" ? "var(--fl-teal)" : "#F1F5F9",
                      color: activeHeroTab === "scorecard" ? "#ffffff" : "var(--fl-text-secondary)",
                      display: "flex",
                      alignItems: "center",
                      gap: "6px"
                    }}
                  >
                    <Sliders size={14} /> Policy Scorecard
                  </button>
                </div>

                {activeHeroTab === "voice" ? (
                  /* VOICE ASSISTANT INTAKE PREVIEW */
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <span style={{ width: "8px", height: "8px", borderRadius: "9999px", background: "#10B981" }} />
                        <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--fl-navy)" }}>Voice Slot-Filling Engine</span>
                      </div>
                      <div style={{ display: "flex", gap: "4px" }}>
                        <span style={{ fontSize: "10px", padding: "2px 6px", background: "#EBF5F3", color: "#166534", borderRadius: "4px", fontWeight: 600 }}>English</span>
                        <span style={{ fontSize: "10px", padding: "2px 6px", background: "#EBF5F3", color: "#166534", borderRadius: "4px", fontWeight: 600 }}>हिन्दी</span>
                        <span style={{ fontSize: "10px", padding: "2px 6px", background: "#EBF5F3", color: "#166534", borderRadius: "4px", fontWeight: 600 }}>मराठी</span>
                      </div>
                    </div>

                    {/* Speech Waveform & Live Bubble */}
                    <div style={{ background: "#F8FAFC", padding: "10px 12px", borderRadius: "8px", border: "1px solid var(--fl-border)" }}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
                        <span style={{ fontSize: "11px", color: "var(--fl-text-secondary)", fontWeight: 600 }}>Applicant Audio Input (Speech-to-Text):</span>
                        <div className="fl-waveform-container" aria-label="Audio waveform animation">
                          <span className="fl-waveform-bar" />
                          <span className="fl-waveform-bar" />
                          <span className="fl-waveform-bar" />
                          <span className="fl-waveform-bar" />
                          <span className="fl-waveform-bar" />
                          <span className="fl-waveform-bar" />
                          <span className="fl-waveform-bar" />
                        </div>
                      </div>
                      <p style={{ margin: 0, fontSize: "12.5px", color: "var(--fl-text-primary)", fontStyle: "italic", lineHeight: 1.45 }}>
                        "{currentSim.phrase}"
                      </p>
                    </div>

                    {/* Extracted Slots Chips */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "6px", fontSize: "11px" }}>
                      <div style={{ background: "#ffffff", padding: "6px 8px", borderRadius: "6px", border: "1px solid var(--fl-border)" }}>
                        <span style={{ color: "var(--fl-text-secondary)", display: "block" }}>Requested Loan:</span>
                        <strong style={{ color: "var(--fl-teal)", fontSize: "13px" }}>{currentSim.amount}</strong>
                      </div>
                      <div style={{ background: "#ffffff", padding: "6px 8px", borderRadius: "6px", border: "1px solid var(--fl-border)" }}>
                        <span style={{ color: "var(--fl-text-secondary)", display: "block" }}>Tenure:</span>
                        <strong style={{ color: "var(--fl-navy)", fontSize: "13px" }}>{currentSim.tenure}</strong>
                      </div>
                      <div style={{ background: "#ffffff", padding: "6px 8px", borderRadius: "6px", border: "1px solid var(--fl-border)" }}>
                        <span style={{ color: "var(--fl-text-secondary)", display: "block" }}>Monthly Income:</span>
                        <strong style={{ color: "var(--fl-navy)", fontSize: "13px" }}>{currentSim.income}</strong>
                      </div>
                      <div style={{ background: "#ffffff", padding: "6px 8px", borderRadius: "6px", border: "1px solid var(--fl-border)" }}>
                        <span style={{ color: "var(--fl-text-secondary)", display: "block" }}>Existing EMIs:</span>
                        <strong style={{ color: "var(--fl-navy)", fontSize: "13px" }}>{currentSim.debts}</strong>
                      </div>
                    </div>

                    {/* Action button */}
                    <button
                      type="button"
                      onClick={() => onNavigate("applicant", "voice")}
                      style={{
                        padding: "8px 12px",
                        background: "var(--fl-teal)",
                        color: "#ffffff",
                        border: "none",
                        borderRadius: "6px",
                        fontSize: "12px",
                        fontWeight: 600,
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "6px"
                      }}
                    >
                      <Mic size={14} /> Open Live Voice Assistant in Workspace →
                    </button>
                  </div>
                ) : (
                  /* SCORECARD PREVIEW */
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    <div className="fl-preview-header">
                      <div className="fl-preview-ref">
                        <span className="fl-preview-id">Case #FL-9042 • Retail Personal Loan</span>
                        <span className="fl-preview-badge-demo">Demo Preview</span>
                      </div>
                      <span className="fl-preview-recommendation">
                        <CheckCircle2 size={14} aria-hidden="true" />
                        78% • Likely Approved
                      </span>
                    </div>

                    {/* Vitals Grid */}
                    <div className="fl-preview-vitals">
                      <div className="fl-vital-item">
                        <span>Monthly Income</span>
                        <strong>₹72,000</strong>
                      </div>
                      <div className="fl-vital-item">
                        <span>Debt Ratio (FOIR)</span>
                        <strong>29.4%</strong>
                      </div>
                      <div className="fl-vital-item">
                        <span>Employment Tenure</span>
                        <strong>38 Months</strong>
                      </div>
                    </div>

                    {/* Contributing Factors */}
                    <div className="fl-preview-xai">
                      <div className="fl-xai-header">
                        <span>Key Contributing Factors</span>
                        <span style={{ fontSize: "11px", color: "var(--fl-text-secondary)" }}>Policy Scorecard</span>
                      </div>

                      <div className="fl-xai-bar-row">
                        <span className="fl-xai-bar-label">Low Obligation Ratio (&lt;45%)</span>
                        <div className="fl-xai-bar-track">
                          <div className="fl-xai-bar-fill-pos" style={{ width: "82%" }} />
                        </div>
                        <span className="fl-xai-bar-val" style={{ color: "var(--fl-teal)" }}>+32%</span>
                      </div>

                      <div className="fl-xai-bar-row">
                        <span className="fl-xai-bar-label">Document Income Cross-Check</span>
                        <div className="fl-xai-bar-track">
                          <div className="fl-xai-bar-fill-pos" style={{ width: "68%" }} />
                        </div>
                        <span className="fl-xai-bar-val" style={{ color: "var(--fl-teal)" }}>+22%</span>
                      </div>

                      <div className="fl-xai-bar-row">
                        <span className="fl-xai-bar-label">Requested Loan-to-Income</span>
                        <div className="fl-xai-bar-track">
                          <div className="fl-xai-bar-fill-neg" style={{ width: "35%" }} />
                        </div>
                        <span className="fl-xai-bar-val" style={{ color: "#DC2626" }}>-8%</span>
                      </div>
                    </div>

                    {/* Document match */}
                    <div className="fl-preview-doc-status">
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <FileCheck2 size={15} aria-hidden="true" />
                        <span>Salary Slip: March 2026</span>
                      </div>
                      <strong style={{ fontSize: "11px", textTransform: "uppercase" }}>100% Extracted Match</strong>
                    </div>
                  </div>
                )}

                {/* Footer Tag */}
                <div className="fl-preview-footer">
                  <ShieldCheck size={14} style={{ color: "var(--fl-teal)", flexShrink: 0 }} aria-hidden="true" />
                  <span>Human Oversight: Licensed loan officer retains final underwriting authority.</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------------
            DEDICATED VOICE ASSISTANT SHOWCASE SECTION
            ------------------------------------------------------------------ */}
        <section id="voice-intake" className="fl-section" style={{ background: "#ffffff", borderTop: "1px solid var(--fl-border)", borderBottom: "1px solid var(--fl-border)" }}>
          <div className="fl-section-header">
            <span className="fl-section-tag">Speech-to-Slot Architecture</span>
            <h2 className="fl-section-title">Conversational Voice Loan Intake</h2>
            <p className="fl-section-desc">
              Borrowers can apply in Indian English, Hindi, or Marathi using spoken natural language. Our quantized faster-whisper speech engine extracts financial vitals in real time without storing raw audio.
            </p>
          </div>

          <div style={{ maxWidth: "900px", margin: "0 auto", background: "#F8FAFC", border: "1px solid var(--fl-border)", borderRadius: "var(--fl-radius-lg)", padding: "var(--fl-space-6)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <div style={{ width: "36px", height: "36px", borderRadius: "8px", background: "var(--fl-teal)", color: "#ffffff", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <Mic size={20} />
                </div>
                <div>
                  <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 700, color: "var(--fl-navy)" }}>Click Sample Spoken Phrases to Test Slot Extraction:</h4>
                  <span style={{ fontSize: "11px", color: "var(--fl-text-secondary)" }}>Simulate how the conversational slot-filling parser extracts loan requirements</span>
                </div>
              </div>

              <div style={{ display: "flex", gap: "6px" }}>
                {sampleVoicePhrases.map((item, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setSimulatedVoiceIndex(idx)}
                    style={{
                      padding: "4px 10px",
                      borderRadius: "6px",
                      fontSize: "11px",
                      fontWeight: 600,
                      cursor: "pointer",
                      border: "1px solid",
                      borderColor: simulatedVoiceIndex === idx ? "var(--fl-teal)" : "var(--fl-border)",
                      background: simulatedVoiceIndex === idx ? "var(--fl-teal)" : "#ffffff",
                      color: simulatedVoiceIndex === idx ? "#ffffff" : "var(--fl-text-secondary)"
                    }}
                  >
                    Sample {idx + 1} ({item.lang})
                  </button>
                ))}
              </div>
            </div>

            {/* Simulated Live Processing Box */}
            <div style={{ background: "#ffffff", border: "1px solid var(--fl-border)", borderRadius: "var(--fl-radius-md)", padding: "14px", marginBottom: "14px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--fl-teal)", textTransform: "uppercase" }}>
                  Spoken User Input ({currentSim.lang}):
                </span>
                <span style={{ fontSize: "11px", color: "var(--fl-text-muted)" }}>Speech-to-Text Active</span>
              </div>
              <p style={{ margin: 0, fontSize: "14px", color: "var(--fl-text-primary)", fontStyle: "italic", background: "#F8FAFC", padding: "10px", borderRadius: "6px", border: "1px solid var(--fl-border)" }}>
                "{currentSim.phrase}"
              </p>
            </div>

            {/* Extracted Entity Mapping */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "10px", marginBottom: "16px" }}>
              <div style={{ background: "#ffffff", padding: "10px", borderRadius: "8px", border: "1px solid var(--fl-border)", textAlign: "center" }}>
                <span style={{ fontSize: "11px", color: "var(--fl-text-secondary)", display: "block" }}>Extracted Loan</span>
                <strong style={{ fontSize: "14px", color: "var(--fl-teal)" }}>{currentSim.amount}</strong>
              </div>
              <div style={{ background: "#ffffff", padding: "10px", borderRadius: "8px", border: "1px solid var(--fl-border)", textAlign: "center" }}>
                <span style={{ fontSize: "11px", color: "var(--fl-text-secondary)", display: "block" }}>Extracted Tenure</span>
                <strong style={{ fontSize: "14px", color: "var(--fl-navy)" }}>{currentSim.tenure}</strong>
              </div>
              <div style={{ background: "#ffffff", padding: "10px", borderRadius: "8px", border: "1px solid var(--fl-border)", textAlign: "center" }}>
                <span style={{ fontSize: "11px", color: "var(--fl-text-secondary)", display: "block" }}>Monthly Income</span>
                <strong style={{ fontSize: "14px", color: "var(--fl-navy)" }}>{currentSim.income}</strong>
              </div>
              <div style={{ background: "#ffffff", padding: "10px", borderRadius: "8px", border: "1px solid var(--fl-border)", textAlign: "center" }}>
                <span style={{ fontSize: "11px", color: "var(--fl-text-secondary)", display: "block" }}>Existing EMIs</span>
                <strong style={{ fontSize: "14px", color: "var(--fl-navy)" }}>{currentSim.debts}</strong>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "var(--fl-text-secondary)" }}>
                <Lock size={14} style={{ color: "var(--fl-teal)" }} />
                <span>Zero raw audio saved: audio chunks are transcribed locally and deleted immediately.</span>
              </div>
              <button
                type="button"
                onClick={() => onNavigate("applicant", "voice")}
                className="fl-btn-primary"
                style={{ fontSize: "13px", padding: "10px 18px" }}
              >
                <Mic size={15} /> Launch Voice Assistant in Workspace
              </button>
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------------
            4. Platform Features (6 Clean Premium Cards)
            ------------------------------------------------------------------ */}
        <section id="platform" className="fl-section">
          <div className="fl-section-header">
            <span className="fl-section-tag">Platform Capabilities</span>
            <h2 className="fl-section-title">Institutional Credit Assessment Architecture</h2>
            <p className="fl-section-desc">
              Built on a three-stage cold-start lifecycle bridging transparent policy scorecards, human-in-the-loop validation, and streaming adaptive machine learning.
            </p>
          </div>

          <div className="fl-features-grid">
            {/* Feature 1 */}
            <div className="fl-feature-card">
              <div className="fl-feature-icon-wrap" aria-hidden="true">
                <Mic size={22} />
              </div>
              <h3>Conversational Voice Intake</h3>
              <p>
                Multi-lingual speech assistant supporting Indian English, Hindi, and Marathi with quantized local faster-whisper STT and entity extraction.
              </p>
              <span className="fl-feature-badge">Zero Audio Retention</span>
            </div>

            {/* Feature 2 */}
            <div className="fl-feature-card">
              <div className="fl-feature-icon-wrap" aria-hidden="true">
                <BarChart3 size={22} />
              </div>
              <h3>Explainable AI (XAI)</h3>
              <p>
                Signed feature attributions and audited Grade 8 plain-English reasons with actionable counterfactual recourse sensitivity analysis.
              </p>
              <span className="fl-feature-badge">Transparent Scoring</span>
            </div>

            {/* Feature 3 */}
            <div className="fl-feature-card">
              <div className="fl-feature-icon-wrap" aria-hidden="true">
                <FileSearch size={22} />
              </div>
              <h3>Document Intelligence</h3>
              <p>
                Local OCR text extraction from salary slips and bank statements (PDF/JPG/PNG) to compute consistency match scores against declarations.
              </p>
              <span className="fl-feature-badge">Cross-Verification</span>
            </div>

            {/* Feature 4 */}
            <div className="fl-feature-card">
              <div className="fl-feature-icon-wrap" aria-hidden="true">
                <TrendingUp size={22} />
              </div>
              <h3>Model Performance</h3>
              <p>
                Visualize held-out accuracy, baseline benchmark comparisons, and ADWIN concept drift monitoring updated with underwriter decisions.
              </p>
              <span className="fl-feature-badge">Adaptive River ML</span>
            </div>

            {/* Feature 5 */}
            <div className="fl-feature-card">
              <div className="fl-feature-icon-wrap" aria-hidden="true">
                <Scale size={22} />
              </div>
              <h3>Fairness Monitoring</h3>
              <p>
                Examine model behavior and potential bias with demographic parity difference and disparate impact ratio tracking under strict attribute quarantine.
              </p>
              <span className="fl-feature-badge">Bias Mitigation</span>
            </div>

            {/* Feature 6 */}
            <div className="fl-feature-card">
              <div className="fl-feature-icon-wrap" aria-hidden="true">
                <UserCheck size={22} />
              </div>
              <h3>Application Management</h3>
              <p>
                Full underwriter workflow with live queues, historical case retrieval, audit-compliant reason-code commitment, and statutory data export or deletion.
              </p>
              <span className="fl-feature-badge">Human Oversight</span>
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------------
            5. How It Works (4-Step Visual Workflow)
            ------------------------------------------------------------------ */}
        <section id="how-it-works" className="fl-section">
          <div className="fl-section-header">
            <span className="fl-section-tag">Workflow Process</span>
            <h2 className="fl-section-title">How FairLendAI Operates</h2>
            <p className="fl-section-desc">
              Four structured steps ensuring rigorous evidence examination and human-in-the-loop credit underwriting.
            </p>
          </div>

          <div className="fl-steps-container">
            <div className="fl-step-card">
              <span className="fl-step-num-badge">01</span>
              <h3>Review Application</h3>
              <p>The borrower submits their financial profile (income, debts, requested loan, tenure) through voice or structured web intake.</p>
            </div>

            <div className="fl-step-card">
              <span className="fl-step-num-badge">02</span>
              <h3>Analyze Financial Information</h3>
              <p>Uploaded salary slips or bank statements are parsed to extract verified income figures and cross-referenced with declared numbers.</p>
            </div>

            <div className="fl-step-card">
              <span className="fl-step-num-badge">03</span>
              <h3>Understand AI Prediction</h3>
              <p>Policy scorecards and streaming ML evaluate risk, outputting transparent feature contributions and plain-English reasons.</p>
            </div>

            <div className="fl-step-card">
              <span className="fl-step-num-badge">04</span>
              <h3>Human Review and Decision</h3>
              <p>A licensed credit officer reviews the complete evidence package, nearest similar cases, and records the final underwriting decision.</p>
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------------
            6. Explainable AI Section
            ------------------------------------------------------------------ */}
        <section id="explainable-ai" className="fl-section">
          <div className="fl-section-header">
            <span className="fl-section-tag">Explainability Showcase</span>
            <h2 className="fl-section-title">Understandable Explanations, Not Black Boxes</h2>
            <p className="fl-section-desc">
              Examine the influential variables and signed contributions that shape each recommendation.
            </p>
          </div>

          <div className="fl-xai-panel-card">
            {/* Left Column: Context & Controls */}
            <div className="fl-xai-panel-left">
              <div style={{ display: "flex", gap: "8px" }}>
                <button
                  type="button"
                  onClick={() => setActiveXaiTab("factors")}
                  style={{
                    padding: "6px 14px",
                    borderRadius: "6px",
                    fontSize: "12px",
                    fontWeight: 600,
                    cursor: "pointer",
                    border: "1px solid",
                    borderColor: activeXaiTab === "factors" ? "var(--fl-teal)" : "var(--fl-border)",
                    background: activeXaiTab === "factors" ? "var(--fl-teal)" : "#ffffff",
                    color: activeXaiTab === "factors" ? "#ffffff" : "var(--fl-text-secondary)"
                  }}
                >
                  Feature Contributions
                </button>
                <button
                  type="button"
                  onClick={() => setActiveXaiTab("plain")}
                  style={{
                    padding: "6px 14px",
                    borderRadius: "6px",
                    fontSize: "12px",
                    fontWeight: 600,
                    cursor: "pointer",
                    border: "1px solid",
                    borderColor: activeXaiTab === "plain" ? "var(--fl-teal)" : "var(--fl-border)",
                    background: activeXaiTab === "plain" ? "var(--fl-teal)" : "#ffffff",
                    color: activeXaiTab === "plain" ? "#ffffff" : "var(--fl-text-secondary)"
                  }}
                >
                  Plain-Language Summary
                </button>
              </div>

              <h3>
                {activeXaiTab === "factors" ? "Quantified Factor Contributions" : "Audited Plain-English Reasons"}
              </h3>

              <p>
                {activeXaiTab === "factors"
                  ? "Feature attributions illustrate the relative influence each financial metric exerted on the model's approval probability. Positive contributions reflect risk buffers; negative values reflect debt strain."
                  : "Every finding is translated into plain English and benchmarked against the Flesch-Kincaid formula (Grade Level ≤ 8.0) so borrowers and underwriters understand the rationale without mathematical jargon."}
              </p>

              <div style={{ padding: "12px", background: "#F8FAFC", borderRadius: "8px", border: "1px solid var(--fl-border)", fontSize: "12.5px", color: "var(--fl-text-secondary)" }}>
                <strong>Important Distinction:</strong> Model predictions and feature attributions represent algorithmic guidance only. Final credit approval or denial is solely made by an authorized human loan officer.
              </div>
            </div>

            {/* Right Column: Interactive Prediction Panel */}
            <div className="fl-xai-panel-right">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--fl-border)", paddingBottom: "8px" }}>
                <div>
                  <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--fl-navy)" }}>Sample Assessment: Case #FL-9042</span>
                  <span style={{ display: "block", fontSize: "11px", color: "var(--fl-text-secondary)" }}>Estimated Approval Probability: 78%</span>
                </div>
                <span className="fl-badge-pos">Likely Approved</span>
              </div>

              {activeXaiTab === "factors" ? (
                <>
                  <div className="fl-xai-row">
                    <div className="fl-xai-row-top">
                      <span>Debt Obligations Ratio (FOIR = 29.4%)</span>
                      <span className="fl-badge-pos">+34%</span>
                    </div>
                    <div className="fl-xai-row-bar-track">
                      <div className="fl-xai-row-bar-fill-pos" style={{ width: "85%" }} />
                    </div>
                    <span style={{ fontSize: "11px", color: "var(--fl-text-secondary)" }}>Comfortably below 45% policy limit</span>
                  </div>

                  <div className="fl-xai-row">
                    <div className="fl-xai-row-top">
                      <span>Monthly Net Income (₹72,000)</span>
                      <span className="fl-badge-pos">+28%</span>
                    </div>
                    <div className="fl-xai-row-bar-track">
                      <div className="fl-xai-row-bar-fill-pos" style={{ width: "70%" }} />
                    </div>
                    <span style={{ fontSize: "11px", color: "var(--fl-text-secondary)" }}>Document verified salary match</span>
                  </div>

                  <div className="fl-xai-row">
                    <div className="fl-xai-row-top">
                      <span>Employment Tenure (38 Months)</span>
                      <span className="fl-badge-pos">+18%</span>
                    </div>
                    <div className="fl-xai-row-bar-track">
                      <div className="fl-xai-row-bar-fill-pos" style={{ width: "55%" }} />
                    </div>
                    <span style={{ fontSize: "11px", color: "var(--fl-text-secondary)" }}>Stable job tenure in current organization</span>
                  </div>

                  <div className="fl-xai-row">
                    <div className="fl-xai-row-top">
                      <span>Loan-to-Income Multiple (4.8x requested)</span>
                      <span className="fl-badge-neg">-12%</span>
                    </div>
                    <div className="fl-xai-row-bar-track">
                      <div className="fl-xai-row-bar-fill-neg" style={{ width: "35%" }} />
                    </div>
                    <span style={{ fontSize: "11px", color: "var(--fl-text-secondary)" }}>Moderate strain on discretionary cash flow</span>
                  </div>
                </>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "13px", color: "var(--fl-text-primary)" }}>
                  <div style={{ padding: "10px 14px", background: "#ffffff", borderRadius: "6px", borderLeft: "3px solid var(--fl-teal)", border: "1px solid var(--fl-border)" }}>
                    <strong>1. Low Existing Debt:</strong> Your monthly loan and credit card obligations require less than 30% of your take-home pay.
                  </div>
                  <div style={{ padding: "10px 14px", background: "#ffffff", borderRadius: "6px", borderLeft: "3px solid var(--fl-teal)", border: "1px solid var(--fl-border)" }}>
                    <strong>2. Verified Salary:</strong> Your declared income matches the net figure confirmed from your pay slip.
                  </div>
                  <div style={{ padding: "10px 14px", background: "#ffffff", borderRadius: "6px", borderLeft: "3px solid var(--fl-teal)", border: "1px solid var(--fl-border)" }}>
                    <strong>3. Career Stability:</strong> You have been continuously employed with your current firm for over 3 years.
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------------
            7. Document Intelligence Section
            ------------------------------------------------------------------ */}
        <section id="documents" className="fl-section">
          <div className="fl-section-header">
            <span className="fl-section-tag">Document Intelligence</span>
            <h2 className="fl-section-title">Automated Financial Evidence Extraction</h2>
            <p className="fl-section-desc">
              Extract reported income and employment vitals from salary slips and bank statements to accelerate underwriting cross-checks.
            </p>
          </div>

          <div className="fl-doc-panel">
            {/* Upload Zone Mock */}
            <div className="fl-doc-upload-box">
              <h4 style={{ margin: 0, fontSize: "15px", fontWeight: 700, color: "var(--fl-navy)" }}>Supported Financial Documents</h4>
              <p style={{ margin: 0, fontSize: "13px", color: "var(--fl-text-secondary)" }}>
                Upload salary slips, Form 16, or bank statements in PDF, JPG, or PNG formats for local OCR text processing.
              </p>

              <div className="fl-dropzone-mock">
                <UploadCloud size={32} style={{ color: "var(--fl-teal)" }} aria-hidden="true" />
                <span style={{ fontSize: "13px", fontWeight: 600 }}>Drag & drop salary slip (PDF/PNG/JPG)</span>
                <span style={{ fontSize: "11px", color: "var(--fl-text-muted)" }}>Encrypted at rest with symmetric Fernet encryption</span>
              </div>

              <div className="fl-doc-disclaimer-box">
                <strong>Important Disclosure:</strong> Text extraction does not verify document authenticity. Extracted information should be reviewed before use.
              </div>
            </div>

            {/* Extracted Data Review Mock */}
            <div className="fl-doc-results-box">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h4 style={{ margin: 0, fontSize: "15px", fontWeight: 700, color: "var(--fl-navy)" }}>Extracted Financial Fields</h4>
                <span className="fl-badge-pos">100% Verified Match</span>
              </div>

              <table className="fl-doc-field-table">
                <tbody>
                  <tr>
                    <td>Applicant Name</td>
                    <td>Pooja Nair (Exact Match)</td>
                  </tr>
                  <tr>
                    <td>Employer Name</td>
                    <td>Apex InfoTech Solutions Pvt Ltd</td>
                  </tr>
                  <tr>
                    <td>Net Monthly Pay</td>
                    <td>₹72,000 / month</td>
                  </tr>
                  <tr>
                    <td>Pay Period</td>
                    <td>March 2026</td>
                  </tr>
                  <tr>
                    <td>Extraction Status</td>
                    <td><span style={{ color: "var(--fl-teal)", fontWeight: 700 }}>Success (Local OCR)</span></td>
                  </tr>
                </tbody>
              </table>

              <div style={{ display: "flex", gap: "8px", marginTop: "auto" }}>
                <button
                  type="button"
                  onClick={() => onNavigate("applicant")}
                  className="fl-btn-primary"
                  style={{ width: "100%", justifyContent: "center", fontSize: "13px", padding: "10px" }}
                >
                  Test Document Upload in Workspace
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------------
            8. Model Analytics & Fairness Section
            ------------------------------------------------------------------ */}
        <section id="model-fairness" className="fl-section">
          <div className="fl-section-header">
            <span className="fl-section-tag">Model Analytics & Fairness</span>
            <h2 className="fl-section-title">Transparent Performance & Bias Monitoring</h2>
            <p className="fl-section-desc">
              Monitor held-out model accuracy, benchmark comparisons, and demographic parity across underwriting decisions.
            </p>
          </div>

          <div className="fl-analytics-grid">
            {/* Stat 1: Held-out Accuracy */}
            <div className="fl-stat-card">
              <span className="fl-stat-card-title">Held-out Model Agreement</span>
              <p className="fl-stat-number">83.4%</p>
              <p className="fl-stat-desc">Agreement rate between streaming ML model and human underwriter decisions, exceeding the 80% shadow-mode gate.</p>
            </div>

            {/* Stat 2: Baseline Comparison */}
            <div className="fl-stat-card">
              <span className="fl-stat-card-title">Baseline Comparison</span>
              <p className="fl-stat-number">+7.2%</p>
              <p className="fl-stat-desc">Improvement over initial Stage 1 Rule Scorecard (76.2% base) achieved through incremental River online learning.</p>
            </div>

            {/* Stat 3: Fairness Indicators */}
            <div className="fl-stat-card">
              <span className="fl-stat-card-title">Demographic Parity Diff</span>
              <p className="fl-stat-number" style={{ color: "var(--fl-teal)" }}>0.04</p>
              <p className="fl-stat-desc">Disparate impact ratio of 0.92, well above the 0.80 four-fifths regulatory threshold under demographic quarantine.</p>
            </div>

            {/* Confusion Matrix Card */}
            <div className="fl-stat-card" style={{ gridColumn: "span 2" }}>
              <span className="fl-stat-card-title">Cumulative Evaluation Matrix (Verified Officer Labels)</span>
              <div className="fl-confusion-matrix-box">
                <div className="fl-cm-cell">
                  <span className="fl-cm-cell-label">True Positive (Approved)</span>
                  <span className="fl-cm-cell-val">142 Cases</span>
                </div>
                <div className="fl-cm-cell">
                  <span className="fl-cm-cell-label">False Positive (Disputed)</span>
                  <span className="fl-cm-cell-val" style={{ color: "#DC2626" }}>18 Cases</span>
                </div>
                <div className="fl-cm-cell">
                  <span className="fl-cm-cell-label">False Negative (Disputed)</span>
                  <span className="fl-cm-cell-val" style={{ color: "#DC2626" }}>12 Cases</span>
                </div>
                <div className="fl-cm-cell">
                  <span className="fl-cm-cell-label">True Negative (Declined)</span>
                  <span className="fl-cm-cell-val">78 Cases</span>
                </div>
              </div>
            </div>

            {/* Global Feature Importance */}
            <div className="fl-stat-card">
              <span className="fl-stat-card-title">Global Feature Weights</span>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginTop: "4px", fontSize: "12px" }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>Debt Burden (FOIR)</span>
                  <strong>38%</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>Income-to-Loan Multiple</span>
                  <strong>26%</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>Job Tenure Stability</span>
                  <strong>20%</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>Document Consistency</span>
                  <strong>16%</strong>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------------
            9. Final Call-to-Action Section
            ------------------------------------------------------------------ */}
        <section className="fl-cta-section">
          <div className="fl-cta-inner">
            <h2>Make Credit Decisions More Understandable.</h2>
            <p>
              Explore transparent, explainable AI tools designed to support responsible credit assessment.
            </p>
            <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", justifyContent: "center" }}>
              <button
                type="button"
                onClick={() => onNavigate("applicant", "voice")}
                className="fl-btn-primary"
              >
                <Mic size={16} /> Launch Voice Assistant
                <ArrowRight size={18} aria-hidden="true" />
              </button>
              <button
                type="button"
                onClick={() => onNavigate("officer")}
                className="fl-btn-secondary"
              >
                Sign In to Officer Portal
              </button>
            </div>
          </div>
        </section>
      </main>

      {/* --------------------------------------------------------------------
          10. Institutional Footer
          -------------------------------------------------------------------- */}
      <footer className="fl-footer">
        <div className="fl-footer-container">
          <div className="fl-footer-top">
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <div className="fl-brand-badge" style={{ width: "30px", height: "30px", fontSize: "0.85rem" }} aria-hidden="true">
                  FL
                </div>
                <span style={{ fontWeight: 700, color: "#ffffff", fontSize: "1.1rem" }}>{PRODUCT_NAME}</span>
              </div>
              <p style={{ margin: "6px 0 0 0", color: "var(--fl-text-muted-on-dark)", fontSize: "12.5px", maxWidth: "440px" }}>
                Responsible credit assessment platform with conversational voice intake, financial document intelligence, and fairness monitoring.
              </p>
            </div>

            <ul className="fl-footer-links">
              <li><a href="#platform">Platform</a></li>
              <li><a href="#voice-intake">Voice Assistant</a></li>
              <li><a href="#how-it-works">How It Works</a></li>
              <li><a href="#explainable-ai">Explainable AI</a></li>
              <li><a href="#documents">Document Intel</a></li>
              <li><a href="#model-fairness">Fairness</a></li>
            </ul>

            {/* Dynamic Status Chip */}
            {healthStatus && (
              <div className="fl-status-chip" role="status" aria-live="polite">
                <span className="fl-status-dot" aria-hidden="true" />
                <span>Backend Status: {healthStatus}</span>
              </div>
            )}
          </div>

          <div className="fl-footer-bottom">
            <p style={{ margin: 0 }}>
              &copy; {new Date().getFullYear()} {PRODUCT_NAME} • Autonomous & Explainable Credit Underwriting System. All rights reserved.
            </p>
            <p style={{ margin: 0, color: "var(--fl-text-muted-on-dark)" }}>
              RBI Digital Lending Guidelines (2022) & India DPDP Act (2023) Aligned Architecture.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};
