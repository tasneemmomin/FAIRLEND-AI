/**
 * Financial Stress Simulator — "Understand Your Future Financial Position"
 *
 * Premium interactive dashboard for assumption-based financial stress
 * exploration. All displayed calculations mirror the deterministic backend
 * engine (backend/services/financial_stress) exactly; hypothetical values are
 * NEVER persisted into application records.
 */
import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowLeftRight,
  BarChart3,
  Briefcase,
  Calendar,
  Download,
  FileCheck2,
  GraduationCap,
  HeartPulse,
  Info,
  LineChart,
  RefreshCcw,
  ShieldCheck,
  SlidersHorizontal,
  TrendingDown,
  Wallet,
  Zap
} from "lucide-react";
import {
  getStressScenarios,
  getStressReport,
  runStressProjection,
  recordStressAssessment
} from "../api";
import type {
  StressFullResponse,
  StressProjectionResponse,
  StressScenarioResult,
  StressReportResponse,
  StressInputs
} from "../types";

const INR = (n: number | undefined | null): string => {
  if (n === undefined || n === null || isNaN(n)) return "₹0";
  const sign = n < 0 ? "-" : "";
  return `${sign}₹${Math.abs(Math.round(n)).toLocaleString("en-IN")}`;
};
const PCT = (n: number | undefined | null, d = 1): string =>
  n === undefined || n === null || isNaN(n) ? "0%" : `${n.toFixed(d)}%`;

type StressKey = "STABLE" | "REDUCED_BUFFER" | "ELEVATED_STRESS" | "NEGATIVE_BALANCE" | "INSUFFICIENT_DATA";

const STRESS_STYLE: Record<StressKey, { label: string; color: string; chip: string; text: string }> = {
  STABLE: { label: "Stable Under Assumptions", color: "#16a34a", chip: "bg-emerald-50 border-emerald-300", text: "text-emerald-800" },
  REDUCED_BUFFER: { label: "Reduced Financial Buffer", color: "#ca8a04", chip: "bg-amber-50 border-amber-300", text: "text-amber-800" },
  ELEVATED_STRESS: { label: "Elevated Financial Stress", color: "#ea580c", chip: "bg-orange-50 border-orange-300", text: "text-orange-800" },
  NEGATIVE_BALANCE: { label: "Negative Monthly Balance", color: "#dc2626", chip: "bg-rose-50 border-rose-300", text: "text-rose-700" },
  INSUFFICIENT_DATA: { label: "Insufficient Information", color: "#64748b", chip: "bg-slate-100 border-slate-300", text: "text-slate-600" }
};

function classifyClient(remaining: number, income: number): StressKey {
  if (remaining <= 0) return "NEGATIVE_BALANCE";
  // Zero/negative income (e.g. full job-loss simulation) with money still left
  // is never "insufficient data" — it simply means living on reserves.
  if (!income || income <= 0) return "ELEVATED_STRESS";
  const ratio = remaining / income;
  if (ratio <= 0.1) return "ELEVATED_STRESS";
  if (ratio <= 0.2) return "REDUCED_BUFFER";
  return "STABLE";
}

/** Exact mirror of the backend deterministic formulas. */
function computeScenarioLive(
  base: StressInputs,
  incomeReductionPct: number,
  expenseIncreasePct: number,
  additional: number,
  emiOverride: number | null
): StressScenarioResult {
  const r = (v: number) => Math.round(v * 100) / 100;
  const ni = r(base.monthly_income * Math.max(0, 1 - incomeReductionPct / 100));
  const exp = r(base.monthly_expenses * (1 + expenseIncreasePct / 100));
  const existing = r(base.existing_emis + additional);
  const emi = emiOverride !== null ? r(emiOverride) : base.proposed_emi;
  const remaining = r(ni - existing - exp - emi);
  const foir = ni > 0 ? r(((existing + emi) / ni) * 100) : 0;
  const stress = classifyClient(remaining, ni);
  return {
    scenario_name: "Hypothetical",
    net_income: ni,
    existing_emis: existing,
    monthly_expenses: exp,
    proposed_emi: emi,
    disposable_income: r(ni - existing - exp),
    remaining_balance: remaining,
    total_emi_burden: r(existing + emi),
    foir,
    stress_indicator: stress,
    stress_label: STRESS_STYLE[stress].label,
    stress_color: STRESS_STYLE[stress].color,
    explanation: ""
  };
}

// ---------------------------------------------------------------------------
// One-tap life-situation presets (the "Quick Check" strip)
// Each preset maps to the exact same 4 knobs the custom controls use.
// ---------------------------------------------------------------------------

interface LifePreset {
  key: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  title: string;
  desc: string;
  income: number;   // % income reduction
  expense: number;  // % expense increase
  addl: number;     // extra EMI rupees
  emi: number | null;
}

const LIFE_PRESETS: LifePreset[] = [
  { key: "normal",   icon: ShieldCheck,    title: "Normal Month",        desc: "Today's situation — no change",            income: 0,   expense: 0,  addl: 0,    emi: null },
  { key: "jobloss3", icon: Briefcase,      title: "Job Loss (3 months)", desc: "Income stops completely for the month",    income: 100, expense: 0,  addl: 0,    emi: null },
  { key: "paycut30", icon: TrendingDown,   title: "Income Dropped 30%",  desc: "Pay cut, bonus loss, business slowdown",   income: 30,  expense: 0,  addl: 0,    emi: null },
  { key: "medical",  icon: HeartPulse,     title: "Medical / Emergency", desc: "Family expenses rise by 25%",              income: 0,   expense: 25, addl: 0,    emi: null },
  { key: "newemi",   icon: GraduationCap,  title: "New Commitment",      desc: "One more loan EMI of ₹5,000 / month",      income: 0,   expense: 0,  addl: 5000, emi: null },
  { key: "worst",    icon: AlertTriangle,  title: "Worst Case",          desc: "Pay cut 60% + expenses +25% + ₹5,000 EMI", income: 60,  expense: 25, addl: 5000, emi: null }
];

// ---------------------------------------------------------------------------
// Reusable UI atoms
// ---------------------------------------------------------------------------

function MetricCard({
  label, value, sublabel, tone = "slate", source
}: { label: string; value: string; sublabel?: string; tone?: "slate" | "teal" | "red" | "amber"; source?: string }) {
  const tones: Record<string, string> = {
    slate: "text-[#172C3D]",
    teal: "text-[#28766B]",
    red: "text-rose-600",
    amber: "text-amber-600"
  };
  const sourceLabels: Record<string, string> = {
    verified_intake: "Verified Intake",
    estimated_assumption: "Estimated Assumption",
    computed_from_terms: "Computed from Loan Terms",
    policy_configuration: "Policy Configuration"
  };
  return (
    <div className="bg-white rounded-xl border border-[#E3E8E5] p-3.5 shadow-sm min-w-0">
      <p className="text-[10px] font-bold uppercase tracking-wide text-[#718096] truncate">{label}</p>
      <p className={`text-lg font-bold mt-0.5 truncate ${tones[tone]}`}>{value}</p>
      {sublabel && <p className="text-[10px] text-[#718096] mt-0.5 truncate">{sublabel}</p>}
      {source && (
        <span className={`inline-block mt-1.5 text-[9px] font-bold px-1.5 py-0.5 rounded-full border uppercase ${
          source === "verified_intake" ? "bg-emerald-50 text-emerald-700 border-emerald-200" :
          source === "estimated_assumption" ? "bg-amber-50 text-amber-700 border-amber-200" :
          "bg-slate-50 text-slate-500 border-slate-200"
        }`}>
          {sourceLabels[source] || source}
        </span>
      )}
    </div>
  );
}

function StressBadge({ level }: { level: StressKey }) {
  const s = STRESS_STYLE[level];
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full border text-[10px] font-bold uppercase tracking-wide ${s.chip} ${s.text}`}>
      <Activity size={11} /> {s.label}
    </span>
  );
}

/** Horizontal bar comparing scenarios by remaining monthly balance. */
function BalanceComparisonChart({ scenarios, baseline }: { scenarios: StressScenarioResult[]; baseline: number }) {
  const maxAbs = Math.max(1, ...scenarios.map((s) => Math.abs(s.remaining_balance)), Math.abs(baseline));
  return (
    <div className="space-y-2">
      {scenarios.map((s, i) => {
        const w = Math.max(2, (Math.abs(s.remaining_balance) / maxAbs) * 100);
        const color = STRESS_STYLE[s.stress_indicator as StressKey]?.color || "#64748b";
        return (
          <div key={i} className="flex items-center gap-2 text-xs">
            <span className="w-44 shrink-0 truncate text-[#718096]" title={s.scenario_name}>{s.scenario_name}</span>
            <div className="flex-1 h-5 bg-[#F1F4F2] rounded-md overflow-hidden relative">
              <div
                className="h-full rounded-md transition-all duration-500"
                style={{ width: `${w}%`, backgroundColor: color }}
              />
              {baseline < 0 && (
                <div className="absolute inset-y-0 border-l-2 border-dashed border-[#172C3D]/40" style={{ left: `${(baseline / maxAbs) * 100}%` }} />
              )}
            </div>
            <span className={`w-20 text-right font-bold ${s.remaining_balance < 0 ? "text-rose-600" : "text-[#172C3D]"}`}>
              {INR(s.remaining_balance)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

/** FOIR comparison bars against the documented 35/45/55 policy bands. */
function FoirComparison({ scenarios }: { scenarios: StressScenarioResult[] }) {
  return (
    <div className="space-y-2">
      {scenarios.map((s, i) => {
        const w = Math.min(100, s.foir);
        const band = s.foir <= 35 ? "#16a34a" : s.foir <= 45 ? "#ca8a04" : s.foir <= 55 ? "#ea580c" : "#dc2626";
        return (
          <div key={i} className="flex items-center gap-2 text-xs">
            <span className="w-44 shrink-0 truncate text-[#718096]" title={s.scenario_name}>{s.scenario_name}</span>
            <div className="flex-1 h-4 bg-[#F1F4F2] rounded-md relative overflow-hidden">
              {/* policy band guides at 35% / 45% / 55% of a 100% FOIR scale */}
              <div className="absolute inset-y-0" style={{ left: "35%", width: 1, background: "#94a3b8" }} />
              <div className="absolute inset-y-0" style={{ left: "45%", width: 1, background: "#94a3b8" }} />
              <div className="absolute inset-y-0" style={{ left: "55%", width: 1, background: "#94a3b8" }} />
              <div className="h-full rounded-md transition-all duration-500" style={{ width: `${w}%`, backgroundColor: band }} />
            </div>
            <span className="w-16 text-right font-bold text-[#172C3D]">{PCT(s.foir)}</span>
          </div>
        );
      })}
      <p className="text-[10px] text-[#718096] pt-1">
        Vertical guides: documented policy FOIR bands at 35% (safe), 45% (moderate) and 55% (high).
      </p>
    </div>
  );
}

/** SVG line chart of projected monthly remaining balance. */
function ProjectionChart({ projection }: { projection: StressProjectionResponse }) {
  const rows = projection.monthly;
  if (!rows.length) return null;
  const W = 560; const H = 190; const PAD = 34;
  const values = rows.map((m) => m.remaining_balance);
  const min = Math.min(0, ...values); const max = Math.max(0, ...values);
  const range = max - min || 1;
  const x = (i: number) => PAD + (i * (W - PAD * 2)) / Math.max(1, rows.length - 1);
  const y = (v: number) => H - PAD - ((v - min) * (H - PAD * 2)) / range;
  const pts = values.map((v, i) => `${x(i)},${y(v)}`).join(" ");
  const zeroY = y(0);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Projected monthly remaining balance">
      {/* stress zone (below zero) */}
      <rect x={PAD} y={zeroY} width={W - PAD * 2} height={Math.max(0, H - PAD - zeroY)} fill="#FEE2E2" opacity={0.55} />
      <line x1={PAD} y1={zeroY} x2={W - PAD} y2={zeroY} stroke="#dc2626" strokeDasharray="4 3" strokeWidth={1} />
      <text x={W - PAD + 2} y={zeroY + 3} fontSize={9} fill="#dc2626">0</text>
      {[max, min].map((v, i) => (
        <text key={i} x={PAD - 4} y={y(v) + 3} fontSize={9} fill="#718096" textAnchor="end">{INR(v)}</text>
      ))}
      <polyline points={pts} fill="none" stroke="#28766B" strokeWidth={2.5} strokeLinejoin="round" />
      {rows.map((m, i) => (
        <g key={m.month}>
          <circle cx={x(i)} cy={y(m.remaining_balance)} r={2.5}
            fill={STRESS_STYLE[m.stress_indicator as StressKey]?.color || "#28766B"} />
          {i % Math.ceil(rows.length / 12) === 0 && (
            <text x={x(i)} y={H - 8} fontSize={8} fill="#718096" textAnchor="middle">M{m.month}</text>
          )}
        </g>
      ))}
    </svg>
  );
}

function ScenarioTable({ scenarios }: { scenarios: StressScenarioResult[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs text-left border-collapse">
        <thead>
          <tr className="bg-[#F1F4F2] text-[10px] uppercase text-[#718096]">
            <th className="p-2">Scenario</th>
            <th className="p-2 text-right">Income</th>
            <th className="p-2 text-right">Obligations</th>
            <th className="p-2 text-right">Expenses</th>
            <th className="p-2 text-right">Remaining</th>
            <th className="p-2 text-right">FOIR</th>
            <th className="p-2">Indicator</th>
          </tr>
        </thead>
        <tbody>
          {scenarios.map((s, i) => (
            <tr key={i} className="border-b border-[#EDF1EE] hover:bg-[#F7F8F5] transition">
              <td className="p-2 font-medium text-[#172C3D] max-w-[210px]">
                {s.scenario_name}
                {s.hypothetical && <span className="ml-1 text-[9px] font-bold text-amber-700 bg-amber-50 border border-amber-200 px-1 rounded">HYPOTHETICAL</span>}
              </td>
              <td className="p-2 text-right">{INR(s.net_income)}</td>
              <td className="p-2 text-right">{INR(s.existing_emis + s.proposed_emi)}</td>
              <td className="p-2 text-right">{INR(s.monthly_expenses)}</td>
              <td className={`p-2 text-right font-bold ${s.remaining_balance < 0 ? "text-rose-600" : "text-[#172C3D]"}`}>
                {INR(s.remaining_balance)}
              </td>
              <td className="p-2 text-right">{PCT(s.foir)}</td>
              <td className="p-2">
                <span className="inline-flex items-center gap-1" style={{ color: s.stress_color }}>
                  <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: s.stress_color }} />
                  {s.stress_indicator.replace("_", " ")}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main applicant simulator
// ---------------------------------------------------------------------------

const MAX_SLIDER = { income: 50, expense: 150 };

export function FinancialStressSimulator({
  applicationId,
  role = "applicant"
}: {
  applicationId: string;
  role?: "applicant" | "officer";
}) {
  const [data, setData] = useState<StressFullResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"sandbox" | "projection">("sandbox");

  // Live hypothetical controls
  const [incomeStress, setIncomeStress] = useState(0);
  const [expenseStress, setExpenseStress] = useState(0);
  const [additional, setAdditional] = useState(0);
  const [emiAdjust, setEmiAdjust] = useState<number | null>(null);
  const [activePreset, setActivePreset] = useState<string | null>("normal");

  // Projection assumptions
  const [projIncomeChange, setProjIncomeChange] = useState(0);
  const [projExpenseGrowth, setProjExpenseGrowth] = useState(0);
  const [projAdditional, setProjAdditional] = useState(0);
  const [projection, setProjection] = useState<StressProjectionResponse | null>(null);
  const [projLoading, setProjLoading] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const [report, setReport] = useState<StressReportResponse | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getStressScenarios(applicationId, role);
      setData(res);
      setProjection(res.default_projection);
    } catch (e: any) {
      setError(e.message || "Failed to load stress analysis");
    } finally {
      setLoading(false);
    }
  }, [applicationId, role]);

  useEffect(() => {
    setIncomeStress(0); setExpenseStress(0); setAdditional(0); setEmiAdjust(null);
    setActivePreset("normal");
    load();
  }, [load]);

  const base = data?.inputs;
  const live = useMemo(() => {
    if (!data) return null;
    return computeScenarioLive(data.inputs, incomeStress, expenseStress, additional, emiAdjust);
  }, [data, incomeStress, expenseStress, additional, emiAdjust]);

  /** Per-preset live verdicts (so each card shows its own outcome before you tap). */
  const presetResults = useMemo(() => {
    if (!data) return [] as Array<LifePreset & StressScenarioResult>;
    return LIFE_PRESETS.map((p) => Object.assign({}, p,
      computeScenarioLive(data.inputs, p.income, p.expense, p.addl, p.emi))) as Array<LifePreset & StressScenarioResult>;
  }, [data]);

  const comparisonScenarios: StressScenarioResult[] = useMemo(() => {
    if (!data) return [];
    return [data.scenario_a_current, ...data.scenario_b_income_reduction.slice(0, 4),
            ...data.scenario_e_combined];
  }, [data]);

  const allPredefined: StressScenarioResult[] = useMemo(() => {
    if (!data) return [];
    return [
      data.scenario_a_current,
      ...data.scenario_b_income_reduction,
      ...data.scenario_c_expense_increase,
      ...data.scenario_d_additional_obligations,
      ...data.scenario_e_combined
    ];
  }, [data]);

  const runProjection = async () => {
    if (!data) return;
    setProjLoading(true);
    try {
      const res = await runStressProjection(applicationId, {
        monthly_income_change_pct: projIncomeChange,
        expense_growth_pct: projExpenseGrowth,
        additional_obligation: projAdditional,
        months: 12
      }, role);
      setProjection(res);
    } catch (e) {
      console.error(e);
    } finally {
      setProjLoading(false);
    }
  };

  const resetScenario = () => {
    setIncomeStress(0); setExpenseStress(0); setAdditional(0); setEmiAdjust(null);
    setActivePreset("normal");
  };

  /** One-tap: apply a life-situation preset to the exact same 4 controls. */
  const applyPreset = (p: LifePreset) => {
    setIncomeStress(p.income); setExpenseStress(p.expense);
    setAdditional(p.addl); setEmiAdjust(p.emi);
    setActivePreset(p.key);
  };

  const downloadReport = async () => {
    if (!data) return;
    try {
      const rep = showReport && report ? report : await getStressReport(applicationId, role);
      if (!showReport) { setReport(rep); setShowReport(true); }
      const esc = (s: any) => String(s ?? "").replace(/[<>&]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" }[c] as string));
      const rows = (list: StressScenarioResult[]) => list.map((s) =>
        `<tr><td>${esc(s.scenario_name)}</td><td>${INR(s.net_income)}</td><td>${INR(s.monthly_expenses)}</td><td>${INR(s.existing_emis + s.proposed_emi)}</td><td><b>${INR(s.remaining_balance)}</b></td><td>${PCT(s.foir)}</td><td>${esc(s.stress_label)}</td></tr>`
      ).join("");
      const projRows = rep.monthly_projection.monthly.map((m) =>
        `<tr><td>M${m.month}</td><td>${INR(m.income)}</td><td>${INR(m.expenses)}</td><td>${INR(m.existing_emis + m.proposed_emi)}</td><td>${INR(m.remaining_balance)}</td><td>${INR(m.cumulative_buffer)}</td></tr>`
      ).join("");
      const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Financial Stress Report</title>
<style>body{font-family:Georgia,serif;max-width:900px;margin:40px auto;color:#24323D;padding:0 20px}
h1{color:#172C3D;border-bottom:3px solid #28766B;padding-bottom:8px}h2{color:#28766B;margin-top:28px;font-size:15px;text-transform:uppercase;letter-spacing:.5px}
table{width:100%;border-collapse:collapse;font-size:12px}th,td{border:1px solid #E3E8E5;padding:6px 8px;text-align:left}
th{background:#F1F4F2;text-transform:uppercase;font-size:10px;color:#718096}.note{background:#FFFBEB;border:1px solid #FDE68A;padding:10px;font-size:12px;border-radius:6px}
.meta{font-size:12px;color:#718096}</style></head><body>
<h1>Financial Stress Analysis Report</h1>
<p class="meta">Applicant: <b>${esc(rep.applicant_name)}</b> &nbsp;•&nbsp; Application ID: ${esc(rep.application_id)}<br/>
Generated: ${esc(rep.generated_at)} • Calculation version: ${esc(rep.calc_version)}</p>
<div class="note"><b>Important:</b> ${esc(rep.important_disclaimer)}</div>
<h2>Loan Under Analysis</h2>
<p class="meta">Requested: ${INR(rep.loan_terms.requested_amount)} • Tenure: ${rep.loan_terms.tenure_months} months • Assumed interest: ${rep.loan_terms.interest_rate_pct}% p.a. • Proposed EMI: <b>${INR(rep.loan_terms.proposed_emi)}</b></p>
<h2>Baseline (Current Financial Condition)</h2>
<p>${esc(rep.baseline.explanation)}</p>
<h2>Income Reduction Scenarios</h2><table><tr><th>Scenario</th><th>Income</th><th>Expenses</th><th>EMIs</th><th>Remaining</th><th>FOIR</th><th>Indicator</th></tr>${rows(rep.income_reduction_scenarios)}</table>
<h2>Expense Increase Scenarios</h2><table><tr><th>Scenario</th><th>Income</th><th>Expenses</th><th>EMIs</th><th>Remaining</th><th>FOIR</th><th>Indicator</th></tr>${rows(rep.expense_increase_scenarios)}</table>
<h2>Additional Obligation Scenarios (Hypothetical)</h2><table><tr><th>Scenario</th><th>Income</th><th>Expenses</th><th>EMIs</th><th>Remaining</th><th>FOIR</th><th>Indicator</th></tr>${rows(rep.additional_obligation_scenarios)}</table>
<h2>Combined Stress Scenarios</h2><table><tr><th>Scenario</th><th>Income</th><th>Expenses</th><th>EMIs</th><th>Remaining</th><th>FOIR</th><th>Indicator</th></tr>${rows(rep.combined_scenarios)}</table>
<h2>Worst Case Summary</h2><p class="meta">${esc(rep.worst_case_summary.worst_scenario_name)} → remaining balance ${INR(rep.worst_case_summary.worst_remaining_balance)} (${INR(rep.worst_case_summary.worst_relative_to_baseline)} vs baseline).</p>
<h2>12-Month Assumption-Based Projection</h2>
<table><tr><th>Month</th><th>Income</th><th>Expenses</th><th>EMIs</th><th>Remaining</th><th>Cumulative Buffer</th></tr>${projRows}</table>
<p class="meta">${esc(rep.monthly_projection.disclaimer)}</p>
<p class="meta" style="margin-top:32px;border-top:1px solid #E3E8E5;padding-top:8px">FairLend AI — Financial Stress Early-Warning &amp; Future Scenario Intelligence • Report ID: ${esc(rep.report_id)}</p>
</body></html>`;
      const blob = new Blob([html], { type: "text/html" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `FairLendAI_Stress_Report_${rep.application_id.slice(0, 8)}.html`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      setError(e.message || "Report export failed");
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-[#E3E8E5] p-10 text-center text-sm text-[#718096]">
        <RefreshCcw size={18} className="animate-spin mx-auto mb-2 text-[#28766B]" /> Loading Financial Stress Simulator…
      </div>
    );
  }
  if (error || !data || !base) {
    return (
      <div className="bg-rose-50 border border-rose-200 rounded-xl p-6 text-sm text-rose-700">
        <AlertTriangle size={16} className="inline mr-2" /> {error || "No data available"}
        <button onClick={load} className="ml-3 underline font-semibold">Retry</button>
      </div>
    );
  }

  const isInsufficient = base.insufficient_income_data;
  const worst = data.worst_case_summary;

  return (
    <div className="space-y-5" data-testid="financial-stress-simulator">
      {/* Header */}
      <div className="bg-gradient-to-r from-[#172C3D] to-[#0F1E2A] rounded-xl p-5 text-white shadow-md">
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <div className="flex items-center gap-2">
              <LineChart size={20} className="text-[#7FE0D2]" />
              <h3 className="font-serif font-bold text-lg">Financial Stress Simulator</h3>
            </div>
            <p className="text-xs text-[#A0B2C0] mt-1 max-w-2xl">
              Explore how your affordability could change under hypothetical financial conditions.
              These are <strong className="text-[#7FE0D2]">what-if assumptions only</strong> — they never change your actual application.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] bg-white/10 border border-white/20 px-2 py-1 rounded-full">
              Calc v{data.calc_version}
            </span>
            <button
              type="button"
              onClick={downloadReport}
              className="flex items-center gap-1.5 bg-[#28766B] hover:bg-[#22665c] text-white px-3.5 py-2 rounded-lg text-xs font-semibold shadow transition"
            >
              <Download size={13} /> Download Scenario Report
            </button>
          </div>
        </div>
      </div>

      {isInsufficient && (
        <div className="bg-slate-100 border border-slate-300 rounded-xl p-4 text-sm text-slate-700">
          <Info size={15} className="inline mr-2" />
          <strong>Insufficient Information:</strong> monthly income data is missing or zero, so reliable
          stress indicators cannot be produced for this application.
        </div>
      )}

      {/* A. Financial Overview */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-bold text-[#718096] uppercase tracking-wide">A. Current Financial Overview</h4>
          <StressBadge level={data.scenario_a_current.stress_indicator as StressKey} />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <MetricCard label="Net Monthly Income" value={INR(base.monthly_income)} source={base.data_sources.monthly_income} />
          <MetricCard label="Existing EMI Obligations" value={INR(base.existing_emis)} source={base.data_sources.existing_emis} />
          <MetricCard label="Monthly Expenses" value={INR(base.monthly_expenses)} source={base.data_sources.monthly_expenses}
            sublabel={base.data_sources.monthly_expenses === "estimated_assumption" ? "40% of income (documented default)" : undefined} />
          <MetricCard label="Proposed EMI" value={INR(base.proposed_emi)} source={base.data_sources.proposed_emi}
            sublabel={`${INR(base.requested_amount)} • ${base.tenure_months}m @ ${base.interest_rate_pct}%`} />
          <MetricCard label="Remaining Monthly Balance" tone={data.scenario_a_current.remaining_balance >= 0 ? "teal" : "red"}
            value={INR(data.scenario_a_current.remaining_balance)} sublabel="After all obligations" />
          <MetricCard label="FOIR" tone={data.scenario_a_current.foir > 45 ? "red" : data.scenario_a_current.foir > 35 ? "amber" : "teal"}
            value={PCT(data.scenario_a_current.foir)} sublabel="Debt-to-income incl. proposed EMI" />
        </div>
        <div className="bg-white border border-[#E3E8E5] rounded-xl p-4 text-xs text-[#3A4C5A] leading-relaxed">
          <BarChart3 size={13} className="inline mr-1.5 text-[#28766B]" /> {data.scenario_a_current.explanation}
        </div>
      </section>

      {/* Tabs */}
      <div className="bg-white rounded-xl border border-[#E3E8E5] shadow-sm overflow-hidden">
        <div className="flex border-b border-[#E3E8E5]">
          {([["sandbox", "Stress Scenario Controls", SlidersHorizontal], ["projection", "12-Month Projection", Calendar]] as const).map(([key, label, Icon]) => (
            <button
              key={key}
              type="button"
              onClick={() => setTab(key as "sandbox" | "projection")}
              className={`flex items-center gap-1.5 px-5 py-3 text-xs font-bold transition ${
                tab === key ? "text-[#28766B] border-b-2 border-[#28766B] bg-[#F7F8F5]" : "text-[#718096] hover:text-[#172C3D]"
              }`}
            >
              <Icon size={14} /> {label}
            </button>
          ))}
        </div>

        {/* B/C. Stress sandbox */}
        {tab === "sandbox" && (
          <div className="p-5 space-y-5">
            {/* Quick Check — one-tap life situations */}
            <div className="space-y-2.5">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <h4 className="text-xs font-bold text-[#718096] uppercase tracking-wide flex items-center gap-1.5">
                  <Zap size={13} className="text-[#28766B]" /> Quick Check — pick a life situation
                </h4>
                <p className="text-[10px] text-[#A0B2C0]">Tap a card to see instantly what happens that month</p>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5">
                {presetResults.map((p) => {
                  const style = STRESS_STYLE[p.stress_indicator as StressKey] || STRESS_STYLE.STABLE;
                  const isActive = activePreset === p.key;
                  return (
                    <button key={p.key} type="button" onClick={() => applyPreset(p)}
                      className={`text-left rounded-xl border p-3 transition shadow-sm hover:shadow-md ${
                        isActive ? "border-[#28766B] ring-1 ring-[#28766B]/50 bg-[#F0F7F5]" : "border-[#E3E8E5] bg-white"
                      }`}>
                      <div className="flex items-start justify-between gap-2">
                        <p.icon size={16} className={isActive ? "text-[#28766B]" : "text-[#718096]"} />
                        <span className="text-[11px] font-bold" style={{ color: style.color }}>
                          {p.remaining_balance < 0 ? INR(p.remaining_balance) : `+${INR(p.remaining_balance)}`}
                        </span>
                      </div>
                      <p className="text-xs font-bold text-[#172C3D] mt-1.5 leading-tight">{p.title}</p>
                      <p className="text-[10px] text-[#718096] mt-0.5 leading-snug">{p.desc}</p>
                      <span className={`inline-block mt-1.5 text-[9px] font-bold px-1.5 py-0.5 rounded-full border ${style.chip} ${style.text}`}>
                        {style.label}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              {/* Controls */}
              <div className="space-y-4">
                <h4 className="text-xs font-bold text-[#718096] uppercase tracking-wide">
                  Fine-tune (Custom / Advanced)
                </h4>
                <p className="text-[10px] text-[#A0B2C0] -mt-2.5">
                  Move any control below and the cards above deselect automatically.
                </p>

                <div>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <label className="font-semibold text-[#172C3D] flex items-center gap-1.5" htmlFor="incomeSlider">
                      <TrendingDown size={13} className="text-amber-600" /> Income Reduction
                    </label>
                    <span className="font-bold text-[#172C3D]">{incomeStress.toFixed(0)}%</span>
                  </div>
                  <input id="incomeSlider" type="range" min={0} max={MAX_SLIDER.income} step={1} value={incomeStress}
                    onChange={(e) => { setActivePreset(null); setIncomeStress(Number(e.target.value)); }}
                    className="w-full accent-[#28766B]" />
                  <div className="flex justify-between text-[9px] text-[#A0B2C0]"><span>0%</span><span>50%</span></div>
                </div>

                <div>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <label className="font-semibold text-[#172C3D] flex items-center gap-1.5" htmlFor="expenseSlider">
                      <ArrowLeftRight size={13} className="text-amber-600" /> Expense Increase
                    </label>
                    <span className="font-bold text-[#172C3D]">{expenseStress.toFixed(0)}%</span>
                  </div>
                  <input id="expenseSlider" type="range" min={0} max={MAX_SLIDER.expense} step={1} value={expenseStress}
                    onChange={(e) => { setActivePreset(null); setExpenseStress(Number(e.target.value)); }}
                    className="w-full accent-[#28766B]" />
                  <div className="flex justify-between text-[9px] text-[#A0B2C0]"><span>0%</span><span>150%</span></div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-semibold text-[#172C3D] flex items-center gap-1.5" htmlFor="addlInput">
                      <Wallet size={13} className="text-amber-600" /> Additional Obligation
                    </label>
                    <input id="addlInput" type="number" min={0} step={500} value={additional}
                      onChange={(e) => { setActivePreset(null); setAdditional(Math.max(0, Number(e.target.value) || 0)); }}
                      className="mt-1 w-full border border-[#E3E8E5] rounded-lg px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-[#28766B]/40" />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-[#172C3D] flex items-center gap-1.5" htmlFor="emiInput">
                      <RefreshCcw size={13} className="text-amber-600" /> Proposed EMI (₹)
                    </label>
                    <input id="emiInput" type="number" min={0} step={100} placeholder={`${INR(base.proposed_emi)} (original)`}
                      value={emiAdjust === null ? "" : emiAdjust}
                      onChange={(e) => { setActivePreset(null); setEmiAdjust(e.target.value === "" ? null : Math.max(0, Number(e.target.value) || 0)); }}
                      className="mt-1 w-full border border-[#E3E8E5] rounded-lg px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-[#28766B]/40" />
                  </div>
                </div>

                <button type="button" onClick={resetScenario}
                  className="flex items-center gap-1.5 border border-[#E3E8E5] hover:bg-[#F7F8F5] px-3.5 py-2 rounded-lg text-xs font-semibold text-[#172C3D] transition">
                  <RefreshCcw size={12} /> Reset to Original Scenario
                </button>
                <p className="text-[10px] text-[#A0B2C0]">
                  Values update instantly and remain strictly hypothetical. Nothing is saved to your application record.
                </p>
              </div>

              {/* Live result panel */}
              {live && (
                <div className="bg-[#F7F8F5] border border-[#E3E8E5] rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold uppercase tracking-wide text-[#718096]">Your Hypothetical Position</h4>
                    <StressBadge level={live.stress_indicator as StressKey} />
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="bg-white rounded-lg border border-[#E3E8E5] p-2.5">
                      <span className="text-[10px] text-[#718096] uppercase">Adjusted Income</span>
                      <p className="font-bold text-sm text-[#172C3D]">{INR(live.net_income)}</p>
                    </div>
                    <div className="bg-white rounded-lg border border-[#E3E8E5] p-2.5">
                      <span className="text-[10px] text-[#718096] uppercase">Total EMI Burden</span>
                      <p className="font-bold text-sm text-[#172C3D]">{INR(live.total_emi_burden)}</p>
                    </div>
                    <div className="bg-white rounded-lg border border-[#E3E8E5] p-2.5">
                      <span className="text-[10px] text-[#718096] uppercase">Monthly Expenses</span>
                      <p className="font-bold text-sm text-[#172C3D]">{INR(live.monthly_expenses)}</p>
                    </div>
                    <div className={`rounded-lg border p-2.5 ${live.remaining_balance < 0 ? "bg-rose-50 border-rose-200" : "bg-emerald-50/70 border-emerald-200"}`}>
                      <span className={`text-[10px] uppercase ${live.remaining_balance < 0 ? "text-rose-600" : "text-emerald-700"}`}>Remaining Balance</span>
                      <p className={`font-bold text-sm ${live.remaining_balance < 0 ? "text-rose-700" : "text-emerald-800"}`}>{INR(live.remaining_balance)}</p>
                    </div>
                    <div className="bg-white rounded-lg border border-[#E3E8E5] p-2.5 col-span-2">
                      <span className="text-[10px] text-[#718096] uppercase">FOIR</span>
                      <div className="flex items-center gap-2">
                        <p className="font-bold text-sm text-[#172C3D]">{PCT(live.foir)}</p>
                        <div className="flex-1 h-2.5 bg-[#F1F4F2] rounded-full max-w-52">
                          <div className="h-full rounded-full transition-all duration-500"
                            style={{
                              width: `${Math.min(100, live.foir)}%`,
                              backgroundColor: live.foir <= 35 ? "#16a34a" : live.foir <= 45 ? "#ca8a04" : live.foir <= 55 ? "#ea580c" : "#dc2626"
                            }} />
                        </div>
                      </div>
                    </div>
                  </div>
                  <p className="text-[11px] text-[#3A4C5A] leading-relaxed bg-white border border-[#E3E8E5] rounded-lg p-2.5">
                    {live.remaining_balance < 0
                      ? `Under these assumptions, monthly outflow would exceed income by ${INR(-live.remaining_balance)} — the proposed EMI would not be affordable.`
                      : `Under these assumptions, a monthly surplus of ${INR(live.remaining_balance)} would remain after all obligations (FOIR ${PCT(live.foir)}).`}
                  </p>
                </div>
              )}
            </div>

            {/* D/E comparison — predefined scenarios */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-[#718096] uppercase tracking-wide">Scenario Comparison (predefined)</h4>
              <div className="bg-white border border-[#E3E8E5] rounded-xl p-4"><BalanceComparisonChart scenarios={comparisonScenarios} baseline={data.scenario_a_current.remaining_balance} /></div>
              <div className="bg-white border border-[#E3E8E5] rounded-xl p-4"><ScenarioTable scenarios={allPredefined} /></div>
              <div className="bg-white border border-[#E3E8E5] rounded-xl p-4 space-y-1">
                <h5 className="text-[10px] font-bold uppercase text-[#718096] pb-1">FOIR Comparison Across Scenarios</h5>
                <FoirComparison scenarios={comparisonScenarios} />
              </div>
            </div>

            {/* Early-warning summary */}
            {worst && (
              <div className="bg-white border border-[#E3E8E5] rounded-xl p-4 space-y-1.5">
                <h4 className="text-xs font-bold text-[#718096] uppercase tracking-wide flex items-center gap-1.5">
                  <AlertTriangle size={13} className="text-amber-600" /> Financial Stress Indicators — What Causes the Warning
                </h4>
                <p className="text-xs text-[#3A4C5A]">
                  Under the most negative predefined assumption set,{" "}
                  <strong>{worst.worst_scenario_name}</strong>, your monthly balance would become{" "}
                  <strong className={worst.worst_remaining_balance < 0 ? "text-rose-600" : "text-[#172C3D]"}>
                    {INR(worst.worst_remaining_balance)}
                  </strong>{" "}
                  ({worst.worst_relative_to_baseline < 0 ? "a decline" : "a change"} of {INR(Math.abs(worst.worst_relative_to_baseline))} versus today's {INR(worst.baseline_remaining_balance)}).
                </p>
                <ul className="text-xs text-[#3A4C5A] list-disc pl-5 space-y-0.5">
                  {data.scenario_a_current.explanation && allPredefined.length > 0 && (
                    <li>Baseline FOIR today: <strong>{PCT(data.scenario_a_current.foir)}</strong>; it rises as income falls in every reduction scenario.</li>
                  )}
                  {base.data_sources.monthly_expenses === "estimated_assumption" && (
                    <li>Monthly expenses are an <strong>estimated assumption</strong> (40% of your stated income). Providing verified expense figures would sharpen this analysis.</li>
                  )}
                  {base.existing_emis > 0 && (
                    <li>Existing EMI obligations of <strong>{INR(base.existing_emis)}/month</strong> already committed before this loan.</li>
                  )}
                </ul>
                <p className="text-[10px] text-[#718096]">
                  These indicators follow documented calculation rules on hypothetical data. They are not statistically validated probabilities of loan default.
                </p>
              </div>
            )}
          </div>
        )}

        {/* E. Projection */}
        {tab === "projection" && projection && (
          <div className="p-5 space-y-4">
            <div className="flex items-start justify-between flex-wrap gap-3">
              <div>
                <h4 className="text-xs font-bold text-[#718096] uppercase tracking-wide">Assumption-Based Monthly Projection (12 months)</h4>
                <p className="text-[10px] text-[#A0B2C0] mt-0.5">
                  Transparent what-if projection — not a statistically trained forecast.
                </p>
              </div>
              <span className="text-[10px] bg-amber-50 text-amber-700 border border-amber-200 px-2 py-1 rounded-full font-bold">
                HYPOTHETICAL ASSUMPTIONS
              </span>
            </div>

            {/* Projection controls */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 items-end bg-[#F7F8F5] border border-[#E3E8E5] rounded-xl p-4">
              <div>
                <label className="text-[10px] font-bold uppercase text-[#718096]" htmlFor="projIncome">Income Change / Month %</label>
                <input id="projIncome" type="number" step={0.5} min={-100} max={100} value={projIncomeChange}
                  onChange={(e) => setProjIncomeChange(Number(e.target.value) || 0)}
                  className="mt-1 w-full border border-[#E3E8E5] rounded-lg px-2.5 py-1.5 text-xs" />
              </div>
              <div>
                <label className="text-[10px] font-bold uppercase text-[#718096]" htmlFor="projExpense">Expense Growth / Month %</label>
                <input id="projExpense" type="number" step={0.5} min={0} max={100} value={projExpenseGrowth}
                  onChange={(e) => setProjExpenseGrowth(Math.max(0, Number(e.target.value) || 0))}
                  className="mt-1 w-full border border-[#E3E8E5] rounded-lg px-2.5 py-1.5 text-xs" />
              </div>
              <div>
                <label className="text-[10px] font-bold uppercase text-[#718096]" htmlFor="projAddl">New Obligation (₹/mo)</label>
                <input id="projAddl" type="number" step={500} min={0} value={projAdditional}
                  onChange={(e) => setProjAdditional(Math.max(0, Number(e.target.value) || 0))}
                  className="mt-1 w-full border border-[#E3E8E5] rounded-lg px-2.5 py-1.5 text-xs" />
              </div>
              <button type="button" onClick={runProjection} disabled={projLoading}
                className="flex items-center justify-center gap-1.5 bg-[#28766B] hover:bg-[#22665c] disabled:opacity-50 text-white px-3.5 py-2 rounded-lg text-xs font-semibold transition">
                <Activity size={13} /> {projLoading ? "Projecting…" : "Run Projection"}
              </button>
            </div>

            <div className="bg-white border border-[#E3E8E5] rounded-xl p-4">
              <ProjectionChart projection={projection} />
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3 text-xs">
                <div className="bg-[#F7F8F5] rounded-lg p-2.5">
                  <span className="text-[10px] text-[#718096] uppercase">Final Cumulative Buffer</span>
                  <p className={`font-bold ${projection.final_cumulative_buffer < 0 ? "text-rose-600" : "text-emerald-700"}`}>{INR(projection.final_cumulative_buffer)}</p>
                </div>
                <div className="bg-[#F7F8F5] rounded-lg p-2.5">
                  <span className="text-[10px] text-[#718096] uppercase">Stress Emerges</span>
                  <p className="font-bold text-[#172C3D]">
                    {projection.insufficient_data ? "Insufficient Info" : projection.months_to_stress === null ? "Not within 12 months" : `Month ${(projection.months_to_stress ?? 0) + 1}`}
                  </p>
                </div>
                <div className="bg-[#F7F8F5] rounded-lg p-2.5">
                  <span className="text-[10px] text-[#718096] uppercase">Assumed Income Change</span>
                  <p className="font-bold text-[#172C3D]">{PCT(projection.assumptions.monthly_income_change_pct)}/mo</p>
                </div>
                <div className="bg-[#F7F8F5] rounded-lg p-2.5">
                  <span className="text-[10px] text-[#718096] uppercase">Assumed Expense Growth</span>
                  <p className="font-bold text-[#172C3D]">{PCT(projection.assumptions.expense_growth_pct)}/mo</p>
                </div>
              </div>
            </div>

            <div className="bg-white border border-[#E3E8E5] rounded-xl p-4 overflow-x-auto">
              <ScenarioTable scenarios={projection.monthly.map((m) => ({
                scenario_name: `Month ${m.month}`,
                net_income: m.income,
                existing_emis: m.existing_emis,
                monthly_expenses: m.expenses,
                proposed_emi: m.proposed_emi,
                disposable_income: 0,
                remaining_balance: m.remaining_balance,
                total_emi_burden: m.existing_emis + m.proposed_emi,
                foir: m.foir,
                stress_indicator: m.stress_indicator,
                stress_label: m.stress_label,
                stress_color: m.stress_color,
                explanation: "",
                hypothetical: true
              }))} />
            </div>

            <div className="bg-[#F7F8F5] border border-[#E3E8E5] rounded-xl p-4 text-xs text-[#3A4C5A] leading-relaxed">
              <FileCheck2 size={13} className="inline mr-1.5 text-[#28766B]" /> {projection.explanation}
            </div>
          </div>
        )}
      </div>

      <div className="bg-white/70 border border-[#E3E8E5] rounded-xl p-3 text-[10px] text-[#718096] leading-relaxed">
        <ShieldCheck size={12} className="inline mr-1 text-[#28766B]" />
        Every number above is produced by FairLend's deterministic financial simulation engine
        (calculation version {data.calc_version}). Applicant-verified values come from your own application
        record; all hypothetical values are simulated in isolation and never saved to your file.
        Scenario analysis is informational and does not influence the automated credit recommendation,
        nor does it promise any approval decision.
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Officer stress analysis panel (loans officer application review page)
// ---------------------------------------------------------------------------

export function OfficerStressPanel({ applicationId }: { applicationId: string }) {
  const [data, setData] = useState<StressFullResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [recordedMsg, setRecordedMsg] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [showDetail, setShowDetail] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getStressScenarios(applicationId, "officer")
      .then((res) => { if (!cancelled) setData(res); })
      .catch((e) => { if (!cancelled) setError(e.message || "Failed to load stress analysis"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [applicationId]);

  const recordAssessment = async () => {
    if (!data || note.trim().length < 3) return;
    setSaving(true);
    try {
      await recordStressAssessment(applicationId, note.trim());
      setRecordedMsg("Assessment recorded to the audit log (advisory only).");
      setNote("");
    } catch (e: any) {
      setRecordedMsg(`Failed: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-3 bg-teal-50/50 border border-teal-200 p-4 rounded-xl text-xs text-slate-500">
        <h4 className="text-xs font-bold text-teal-950 uppercase flex items-center gap-1.5">
          <LineChart size={14} className="text-teal-600" /> Financial Stress Analysis
        </h4>
        Loading scenario engine…
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="space-y-3 bg-amber-50 border border-amber-200 p-4 rounded-xl text-xs text-amber-800">
        <h4 className="text-xs font-bold text-amber-950 uppercase flex items-center gap-1.5">
          <AlertTriangle size={14} /> Financial Stress Analysis — unavailable
        </h4>
        {error}
      </div>
    );
  }

  const cur = data.scenario_a_current;
  const worst = data.worst_case_summary;

  return (
    <div className="space-y-3 bg-teal-50/50 border border-teal-200 p-4 rounded-xl">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold text-teal-950 uppercase flex items-center gap-1.5">
          <LineChart size={14} className="text-teal-600" />
          Financial Stress Analysis (Advisory)
        </h4>
        <button
          onClick={() => setShowDetail(!showDetail)}
          className="text-[10px] bg-white border border-teal-300 text-teal-800 font-bold px-2 py-1 rounded-full hover:bg-teal-100 transition"
        >
          {showDetail ? "Hide Scenario Detail" : "View All Scenarios"}
        </button>
      </div>

      {/* Baseline metric strip */}
      <div className="grid grid-cols-3 md:grid-cols-6 gap-2 text-xs">
        <div className="bg-white p-2.5 rounded-lg border border-slate-200">
          <span className="text-[9px] text-slate-400 uppercase block">Net Income</span>
          <span className="font-bold text-slate-800">{INR(data.inputs.monthly_income)}</span>
        </div>
        <div className="bg-white p-2.5 rounded-lg border border-slate-200">
          <span className="text-[9px] text-slate-400 uppercase block">Total EMIs</span>
          <span className="font-bold text-slate-800">{INR(cur.total_emi_burden)}</span>
        </div>
        <div className="bg-white p-2.5 rounded-lg border border-slate-200">
          <span className="text-[9px] text-slate-400 uppercase block">Expenses</span>
          <span className="font-bold text-slate-800">
            {INR(data.inputs.monthly_expenses)}
            <span className={`block text-[8px] font-bold uppercase ${data.inputs.data_sources.monthly_expenses === "verified_intake" ? "text-emerald-600" : "text-amber-600"}`}>
              {data.inputs.data_sources.monthly_expenses === "verified_intake" ? "verified" : "assumed 40%"}
            </span>
          </span>
        </div>
        <div className="bg-white p-2.5 rounded-lg border border-slate-200">
          <span className="text-[9px] text-slate-400 uppercase block">Proposed EMI</span>
          <span className="font-bold text-slate-800">{INR(data.inputs.proposed_emi)}</span>
        </div>
        <div className={`p-2.5 rounded-lg border ${cur.remaining_balance < 0 ? "bg-rose-50 border-rose-200" : "bg-white border-slate-200"}`}>
          <span className="text-[9px] text-slate-400 uppercase block">Remaining Balance</span>
          <span className={`font-bold ${cur.remaining_balance < 0 ? "text-rose-600" : "text-slate-800"}`}>{INR(cur.remaining_balance)}</span>
        </div>
        <div className="bg-white p-2.5 rounded-lg border border-slate-200">
          <span className="text-[9px] text-slate-400 uppercase block">FOIR (with loan)</span>
          <span className="font-bold text-slate-800">{PCT(cur.foir)}</span>
        </div>
      </div>

      {/* Worst case + explanation */}
      <div className="bg-white p-3 rounded-lg border border-teal-200 text-xs text-slate-800 space-y-1.5">
        <p>
          <strong>Worst predefined scenario:</strong> {worst.worst_scenario_name} →{" "}
          <strong className={worst.worst_remaining_balance < 0 ? "text-rose-600" : ""}>
            {INR(worst.worst_remaining_balance)}
          </strong>{" "}
          remaining monthly balance ({INR(worst.worst_relative_to_baseline)} vs baseline), FOIR rises as income falls.
        </p>
        <p className="text-slate-600">{cur.explanation}</p>
        <p className="text-[10px] text-slate-400">
          Advisory scenario intelligence only — it never automatically approves or rejects applications.
          The human officer retains sole final decision authority. {data.disclaimer}
        </p>
      </div>

      {showDetail && (
        <div className="space-y-2">
          <div className="bg-white border border-teal-200 rounded-lg p-3"><ScenarioTable scenarios={[
            data.scenario_a_current,
            ...data.scenario_b_income_reduction,
            ...data.scenario_c_expense_increase,
            ...data.scenario_d_additional_obligations,
            ...data.scenario_e_combined
          ]} /></div>
          <div className="bg-white border border-teal-200 rounded-lg p-3">
            <h5 className="text-[10px] font-bold uppercase text-slate-500 pb-1">12-Month Projection (Default Assumptions)</h5>
            <ProjectionChart projection={data.default_projection} />
          </div>
        </div>
      )}

      {/* Officer assessment recording */}
      <div className="bg-white p-3 rounded-lg border border-teal-200 space-y-2">
        <label className="text-[10px] font-bold uppercase text-slate-500 block" htmlFor="stressNote">
          Record Your Assessment (stored to audit log; advisory only)
        </label>
        <textarea
          id="stressNote"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="e.g., Income reduction of 15% combined with verified expenses leaves an adequate buffer; applicant's industry shows stable demand."
          rows={2}
          className="w-full border border-slate-200 rounded-lg px-2.5 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30"
        />
        <div className="flex items-center gap-3">
          <button
            onClick={recordAssessment}
            disabled={saving || note.trim().length < 3}
            className="flex items-center gap-1.5 bg-teal-700 hover:bg-teal-800 disabled:opacity-40 text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold transition"
          >
            <FileCheck2 size={12} /> {saving ? "Recording…" : "Record Assessment"}
          </button>
          {recordedMsg && <span className="text-[10px] font-semibold text-teal-700">{recordedMsg}</span>}
        </div>
      </div>
    </div>
  );
}
