import {
  ApplicantIntakeForm,
  ApplicantResponse,
  OfficerAppSummary,
  SystemHealth,
  FairnessMetrics,
  AuthUser,
  AuthResponse,
  ApplicantAppHistoryItem,
  StressBaselineResponse,
  StressFullResponse,
  StressScenarioResult,
  StressProjectionResponse,
  StressCustomRequest,
  StressProjectionRequest,
  StressReportResponse
} from "./types";

const BASE_URL = window.location.origin.includes("localhost:5173") 
  ? "http://127.0.0.1:8000/api" 
  : "/api";

export function getAuthToken(role: "applicant" | "officer" = "applicant"): string | null {
  try {
    if (role === "officer") {
      return sessionStorage.getItem("fairlend_officer_token") || localStorage.getItem("fairlend_officer_token");
    }
    return localStorage.getItem("fairlend_applicant_token") || sessionStorage.getItem("fairlend_applicant_token");
  } catch {
    return null;
  }
}

export function authHeaders(role: "applicant" | "officer" = "applicant"): Record<string, string> {
  const token = getAuthToken(role);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ==========================================
// Authentication APIs
// ==========================================

export async function loginUser(
  email: string, 
  password: string, 
  expectedRole?: "applicant" | "officer"
): Promise<AuthResponse> {
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, expected_role: expectedRole })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Authentication failed" }));
    throw new Error(err.detail || "Authentication failed");
  }
  return res.json();
}

export async function registerApplicant(
  fullName: string, 
  email: string, 
  phone: string, 
  password: string
): Promise<AuthResponse> {
  const res = await fetch(`${BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ full_name: fullName, email, phone, password })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Registration failed" }));
    throw new Error(err.detail || "Registration failed");
  }
  return res.json();
}

export async function getCurrentUser(token?: string): Promise<AuthUser> {
  const headers: Record<string, string> = token 
    ? { Authorization: `Bearer ${token}` } 
    : authHeaders("applicant");

  const res = await fetch(`${BASE_URL}/auth/me`, { headers });
  if (!res.ok) throw new Error("Session invalid or expired");
  return res.json();
}

export async function getMyApplications(): Promise<ApplicantAppHistoryItem[]> {
  const res = await fetch(`${BASE_URL}/auth/my-applications`, {
    headers: { ...authHeaders("applicant") }
  });
  if (!res.ok) throw new Error("Failed to fetch applications");
  return res.json();
}

export async function logoutUser(): Promise<void> {
  try {
    await fetch(`${BASE_URL}/auth/logout`, {
      method: "POST",
      headers: { ...authHeaders("applicant") }
    });
  } catch (e) {
    // ignore
  }
}

// ==========================================
// Platform APIs
// ==========================================

export async function getHealth(): Promise<SystemHealth> {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

export async function submitApplicantIntake(data: ApplicantIntakeForm): Promise<ApplicantResponse> {
  const res = await fetch(`${BASE_URL}/intake/submit`, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      ...authHeaders("applicant")
    },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Submission failed" }));
    throw new Error(err.detail || "Submission failed");
  }
  return res.json();
}

export async function getApplicantStatus(id: string): Promise<ApplicantResponse> {
  const res = await fetch(`${BASE_URL}/intake/${id}`, {
    headers: { ...authHeaders("applicant") }
  });
  if (!res.ok) throw new Error("Failed to fetch application status");
  return res.json();
}

export async function getExplanation(id: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/explain/${id}`, {
    headers: { ...authHeaders("applicant") }
  });
  if (!res.ok) throw new Error("Failed to fetch explanation");
  return res.json();
}

export async function uploadDocument(formData: FormData): Promise<any> {
  const res = await fetch(`${BASE_URL}/documents/upload`, {
    method: "POST",
    headers: { ...authHeaders("applicant") },
    body: formData
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}

// ==========================================
// Officer Command Center APIs
// ==========================================

export async function listOfficerApplications(statusFilter?: string): Promise<{ total: number; applications: OfficerAppSummary[] }> {
  const url = statusFilter && statusFilter !== "all" 
    ? `${BASE_URL}/officer/applications?status_filter=${statusFilter}` 
    : `${BASE_URL}/officer/applications`;
  const res = await fetch(url, {
    headers: { ...authHeaders("officer") }
  });
  if (!res.ok) {
    if (res.status === 401 || res.status === 403) {
      throw new Error("Unauthorized officer access. Please sign in.");
    }
    throw new Error("Failed to fetch applications");
  }
  return res.json();
}

export async function getOfficerAppDetail(id: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/officer/applications/${id}`, {
    headers: { ...authHeaders("officer") }
  });
  if (!res.ok) throw new Error("Failed to fetch application details");
  return res.json();
}

export async function submitOfficerDecision(id: string, decision: string, reason_code: string, notes?: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/officer/applications/${id}/decision`, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      ...authHeaders("officer")
    },
    body: JSON.stringify({ decision, reason_code, officer_notes: notes, officer_id: "officer_demo" })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Decision submission failed" }));
    throw new Error(err.detail || "Decision submission failed");
  }
  return res.json();
}

export async function updateRepayment(id: string, repayment_outcome: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/officer/applications/${id}/repayment`, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      ...authHeaders("officer")
    },
    body: JSON.stringify({ repayment_outcome })
  });
  if (!res.ok) throw new Error("Repayment update failed");
  return res.json();
}

export async function getOfficerStats(): Promise<any> {
  const res = await fetch(`${BASE_URL}/officer/stats`, {
    headers: { ...authHeaders("officer") }
  });
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}

export async function getFairness(): Promise<FairnessMetrics> {
  const res = await fetch(`${BASE_URL}/fairness/metrics`);
  if (!res.ok) throw new Error("Failed to fetch fairness metrics");
  return res.json();
}

export async function exportPrivacyData(id: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/privacy/export/${id}`, { 
    method: "POST",
    headers: { ...authHeaders("applicant") }
  });
  if (!res.ok) throw new Error("Export failed");
  return res.json();
}

export async function deletePrivacyData(id: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/privacy/delete/${id}`, { 
    method: "POST",
    headers: { ...authHeaders("applicant") }
  });
  if (!res.ok) throw new Error("Deletion failed");
  return res.json();
}

export async function initVoice(language?: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/voice/init`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ language: language || "en-IN" })
  });
  if (!res.ok) throw new Error("Failed to initialize voice session");
  return res.json();
}

export async function processVoiceTurn(userUtterance: string, sessionState?: any, language?: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/voice/turn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_utterance: userUtterance,
      session_state: sessionState,
      language: language || "en-IN"
    })
  });
  if (!res.ok) throw new Error("Turn failed");
  return res.json();
}

export async function transcribeAudioBlob(blob: Blob, language: string = "en-IN"): Promise<{ text: string; language: string; confidence: number; error?: string }> {
  const formData = new FormData();
  formData.append("audio", blob, "voice.wav");
  formData.append("language", language); // selected-language enforcement for faster-whisper
  const res = await fetch(`${BASE_URL}/voice/transcribe`, {
    method: "POST",
    body: formData
  });
  if (!res.ok) throw new Error("Speech-to-text failed");
  return res.json();
}

// ==========================================
// Document Intake APIs
// ==========================================

export async function uploadIntakeDocument(formData: FormData): Promise<any> {
  const res = await fetch(`${BASE_URL}/documents/intake-upload`, {
    method: "POST",
    headers: { ...authHeaders("applicant") },
    body: formData
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}

export async function analyzeIntakeDocuments(documents: any[], applicantProfile?: any): Promise<any> {
  const res = await fetch(`${BASE_URL}/documents/analyze-intake`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders("applicant") },
    body: JSON.stringify({ documents, applicant_profile: applicantProfile })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Analysis failed" }));
    throw new Error(err.detail || "Analysis failed");
  }
  return res.json();
}

// ==========================================
// Financial Stress Simulator APIs
// ==========================================

export type StressRole = "applicant" | "officer";

export async function getStressBaseline(applicationId: string, role: StressRole = "applicant"): Promise<StressBaselineResponse> {
  const res = await fetch(`${BASE_URL}/stress/applications/${applicationId}/baseline`, {
    headers: { ...authHeaders(role) }
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Failed to load baseline financial position");
  return res.json();
}

export async function getStressScenarios(applicationId: string, role: StressRole = "applicant"): Promise<StressFullResponse> {
  const res = await fetch(`${BASE_URL}/stress/applications/${applicationId}/scenarios`, {
    headers: { ...authHeaders(role) }
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Failed to load stress scenarios");
  return res.json();
}

export async function runStressCustomScenario(
  applicationId: string,
  payload: StressCustomRequest,
  role: StressRole = "applicant"
): Promise<StressScenarioResult> {
  const res = await fetch(`${BASE_URL}/stress/applications/${applicationId}/custom`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(role) },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Custom scenario failed");
  return res.json();
}

export async function runStressProjection(
  applicationId: string,
  payload: StressProjectionRequest,
  role: StressRole = "applicant"
): Promise<StressProjectionResponse> {
  const res = await fetch(`${BASE_URL}/stress/applications/${applicationId}/projection`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(role) },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Projection failed");
  return res.json();
}

export async function getStressReport(applicationId: string, role: StressRole = "applicant"): Promise<StressReportResponse> {
  const res = await fetch(`${BASE_URL}/stress/applications/${applicationId}/report`, {
    headers: { ...authHeaders(role) }
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Report export failed");
  return res.json();
}

export async function recordStressAssessment(applicationId: string, assessmentNote: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/stress/applications/${applicationId}/assessment`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders("officer") },
    body: JSON.stringify({ assessment_note: assessmentNote })
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Failed to record assessment");
  return res.json();
}

export async function getStressConfig(): Promise<any> {
  const res = await fetch(`${BASE_URL}/stress/config`);
  if (!res.ok) throw new Error("Config requires authentication");
  return res.json();
}
