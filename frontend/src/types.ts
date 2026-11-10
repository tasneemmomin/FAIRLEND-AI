export interface ApplicantIntakeForm {
  applicant_name: string;
  contact_phone?: string;
  contact_email?: string;
  age: number;
  employment_type: string;
  employment_duration_months: number;
  monthly_income: number;
  existing_emis: number;
  requested_amount: number;
  tenure_months: number;
  loan_purpose: string;
  dependents: number;
  residence_type: string;
  credit_history_years: number;
  collateral_value: number;
  intake_mode: "typed" | "voice" | "document";
  intake_transcript?: string;
  audit_consent: boolean;
  audit_gender?: string;
  audit_social_group?: string;
  audit_geography_tier?: string;
}

export interface CounterfactualItem {
  feature_name: string;
  current_value: any;
  suggested_value: any;
  change_description: string;
  actionability: string;
  is_faithful: boolean;
}

export interface ApplicantResponse {
  application_id: string;
  created_at: string;
  applicant_name: string;
  status: string;
  recommendation: string;
  recommendation_code: string;
  confidence: string;
  stage: string;
  plain_english_summary: string;
  reasons: string[];
  counterfactuals: CounterfactualItem[];
  foir_percentage: number;
  loan_to_income_ratio: number;
  consistency_score: number;
}

export interface OfficerAppSummary {
  id: string;
  created_at: string;
  applicant_name: string;
  requested_amount: number;
  tenure_months: number;
  monthly_income: number;
  foir: number;
  consistency_score: number;
  ai_recommendation: string;
  ai_confidence: string;
  ai_stage: string;
  status: string;
  has_decision: boolean;
  officer_decision?: string;
  reason_code?: string;
}

export interface SystemHealth {
  status: string;
  app_name: string;
  version: string;
  database_connected: boolean;
  total_applications: number;
  labeled_cases: number;
  activation_threshold: number;
  min_per_class_required: number;
  approvals_count: number;
  rejections_count: number;
  current_stage: string;
  current_stage_label: string;
  shadow_agreement_rate?: number;
  model_promoted: boolean;
}

export interface FairnessMetrics {
  total_audit_cases: number;
  status: string;
  demographic_parity_difference?: number;
  disparate_impact_ratio?: number;
  equal_opportunity_difference?: number;
  adverse_impact_flag?: boolean;
  sample_size_warnings: string[];
  groups: Record<string, {
    count: number;
    ai_approval_count: number;
    ai_selection_rate: number;
    officer_approval_count: number;
    true_positive_rate: any;
  }>;
}

export interface ApplicantUser {
  id: string;
  name: string;
  email: string;
  phone: string;
  monthly_income?: number;
  employment_type?: string;
  token?: string;
}

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  phone?: string;
  role: "applicant" | "officer";
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export interface ApplicantAppHistoryItem {
  id: string;
  created_at: string;
  applicant_name: string;
  requested_amount: number;
  tenure_months: number;
  monthly_income: number;
  foir: number;
  ai_recommendation: string;
  ai_confidence: string;
  status: string;
}

export interface ExtractedSalaryDetails {
  employee_name?: string | null;
  employer_name?: string | null;
  employee_id?: string | null;
  designation?: string | null;
  salary_month?: string | null;
  basic_pay?: number | null;
  grade_pay?: number | null;
  dearness_allowance?: number | null;
  hra?: number | null;
  other_allowances?: number | null;
  gross_salary?: number | null;
  provident_fund?: number | null;
  nps?: number | null;
  professional_tax?: number | null;
  income_tax?: number | null;
  insurance?: number | null;
  other_deductions?: number | null;
  total_deductions?: number | null;
  net_salary?: number | null;
}

export interface ExtractedBankDetails {
  account_holder_name?: string | null;
  bank_name?: string | null;
  account_number_masked?: string | null;
  statement_period?: string | null;
  opening_balance?: number | null;
  closing_balance?: number | null;
  total_credits?: number | null;
  total_debits?: number | null;
  detected_salary_credits?: number | null;
  detected_monthly_emis?: number | null;
}

export interface ExtractedIdentityDetails {
  pan_number_masked?: string | null;
  aadhaar_number_masked?: string | null;
  dob?: string | null;
  gender?: string | null;
}

export interface UploadedDocumentItem {
  doc_id: string;
  filename: string;
  doc_type: "salary_slip" | "bank_statement" | "pan_card" | "aadhaar_card" | "other_financial";
  detected_category: string;
  confidence_score: number;
  extracted_data: {
    extracted_name?: string | null;
    employer_name?: string | null;
    monthly_salary?: number | null;
    average_bank_balance?: number | null;
    total_credits?: number | null;
    total_debits?: number | null;
    document_type: string;
    salary_details?: ExtractedSalaryDetails;
    bank_details?: ExtractedBankDetails;
    identity_details?: ExtractedIdentityDetails;
    field_confidence?: Record<string, string>;
    all_extracted_fields?: Record<string, any>;
    raw_text_snippet?: string;
  };
  mismatch_flags?: any[];
  preview_url?: string;
  applicant_verified?: boolean;
  applicant_corrections?: Record<string, any>;
}

export interface MissingFieldDefinition {
  field_key: keyof ApplicantIntakeForm;
  label: string;
  field_type: "text" | "number" | "select" | "tel" | "email";
  required: boolean;
  placeholder?: string;
  description: string;
  options?: { value: string; label: string }[];
  default_value?: any;
}

// ==========================================
// Financial Stress Simulator types
// ==========================================

export interface StressDataSources {
  [key: string]: string;
}

export interface StressInputs {
  monthly_income: number;
  existing_emis: number;
  monthly_expenses: number;
  requested_amount: number;
  tenure_months: number;
  proposed_emi: number;
  interest_rate_pct: number;
  data_sources: StressDataSources;
  insufficient_income_data: boolean;
}

export interface StressScenarioResult {
  scenario_name: string;
  net_income: number;
  existing_emis: number;
  monthly_expenses: number;
  proposed_emi: number;
  disposable_income: number;
  remaining_balance: number;
  total_emi_burden: number;
  expense_burden_ratio?: number;
  foir: number;
  stress_indicator: string;
  stress_label: string;
  stress_color: string;
  explanation: string;
  variation_pct?: number;
  income_reduction_pct?: number;
  expense_increase_pct?: number;
  additional_obligation?: number;
  obligation_type?: string;
  hypothetical?: boolean;
  custom_inputs?: {
    income_reduction_pct: number;
    expense_increase_pct: number;
    additional_obligation: number;
    proposed_emi: number;
  };
}

export interface StressMetrics {
  disposable_income: number;
  remaining_balance: number;
  total_emi_burden: number;
  expense_burden_ratio: number;
  foir: number;
  foir_risk_band: string;
  stress_indicator: string;
  stress_label: string;
  stress_color: string;
  stress_description: string;
  explanation: string;
  overall_assessment: string;
  key_factors: string[];
  calc_version: string;
  insufficient_income_data: boolean;
}

export interface StressBaselineResponse {
  application_id: string;
  calc_version: string;
  inputs: StressInputs;
  metrics: StressMetrics;
}

export interface StressFullResponse {
  application_id: string;
  calc_version: string;
  config_version: number;
  inputs: StressInputs;
  scenario_a_current: StressScenarioResult;
  scenario_b_income_reduction: StressScenarioResult[];
  scenario_c_expense_increase: StressScenarioResult[];
  scenario_d_additional_obligations: StressScenarioResult[];
  scenario_e_combined: StressScenarioResult[];
  worst_case_summary: {
    worst_scenario_name: string;
    worst_remaining_balance: number;
    baseline_remaining_balance: number;
    worst_relative_to_baseline: number;
  };
  default_projection: StressProjectionResponse;
  disclaimer: string;
}

export interface StressProjectionMonth {
  month: number;
  income: number;
  expenses: number;
  existing_emis: number;
  proposed_emi: number;
  total_outflow: number;
  remaining_balance: number;
  cumulative_buffer: number;
  stress_indicator: string;
  stress_label: string;
  stress_color: string;
  foir: number;
}

export interface StressProjectionResponse {
  projection_months: number;
  assumptions: {
    monthly_income_change_pct: number;
    expense_growth_pct: number;
    additional_obligation: number;
  };
  monthly: StressProjectionMonth[];
  months_to_stress: number | null;
  final_cumulative_buffer: number;
  insufficient_data: boolean;
  explanation: string;
  disclaimer: string;
  hypothetical?: boolean;
}

export interface StressCustomRequest {
  income_reduction_pct: number;
  expense_increase_pct: number;
  additional_obligation: number;
  proposed_emi?: number | null;
}

export interface StressProjectionRequest {
  monthly_income_change_pct: number;
  expense_growth_pct: number;
  additional_obligation: number;
  months: number;
}

export interface StressReportResponse {
  report_id: string;
  generated_at: string;
  application_id: string;
  applicant_name: string;
  loan_terms: Record<string, number>;
  data_sources: StressDataSources;
  calc_version: string;
  baseline: StressScenarioResult;
  income_reduction_scenarios: StressScenarioResult[];
  expense_increase_scenarios: StressScenarioResult[];
  additional_obligation_scenarios: StressScenarioResult[];
  combined_scenarios: StressScenarioResult[];
  worst_case_summary: StressFullResponse["worst_case_summary"];
  monthly_projection: StressProjectionResponse;
  important_disclaimer: string;
}


