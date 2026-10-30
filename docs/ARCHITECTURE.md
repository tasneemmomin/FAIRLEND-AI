# LoanLens Architecture Specification
**End-to-End System Design & Data Pipelines**

---

## 1. System Overview & Component Architecture

LoanLens is structured as a decoupled, local-first web application where a single FastAPI backend serves both the REST API, WebSocket streams, and the compiled React frontend application.

```mermaid
flowchart TD
    subgraph Client ["Client Browser (Single Port 8000)"]
        UI_Applicant["Applicant Portal (Voice & Form)"]
        UI_Officer["Officer Dashboard (Real-time Live Queue)"]
        UI_Audio["Web Audio / SpeechSynthesis (TTS)"]
    end

    subgraph Gateway ["FastAPI Gateway & WebSockets"]
        API_Intake["/api/intake"]
        API_Voice["/api/voice"]
        API_Docs["/api/documents"]
        API_Officer["/api/officer"]
        API_Explain["/api/explain"]
        API_Fairness["/api/fairness"]
        API_Privacy["/api/privacy"]
        WS_Hub["WebSocket Event Hub (/api/ws)"]
    end

    subgraph Intelligence ["LoanLens AI Services"]
        SRV_Whisper["STT Engine (faster-whisper CPU)"]
        SRV_OCR["Document Intelligence (pdfplumber + OCR)"]
        SRV_Policy["Credit Policy Scorecard (Stage 1)"]
        SRV_River["Online Learning Model (River HAT / ARF)"]
        SRV_Drift["ADWIN Concept Drift Monitor"]
        SRV_Explain["Dual Explainability & Counterfactual Search"]
        SRV_Fairness["Fairness & Disparate Impact Auditor"]
    end

    subgraph Storage ["Local Encrypted Storage"]
        DB[(SQLite Database via SQLAlchemy)]
        Vault["Encrypted Documents (/data/uploads)"]
        Models["River Pipeline Cache (/data/models)"]
    end

    UI_Applicant -->|Voice Audio| API_Voice
    UI_Applicant -->|Documents| API_Docs
    UI_Applicant -->|Form Submission| API_Intake
    UI_Officer -->|Approve/Reject| API_Officer

    API_Voice --> SRV_Whisper
    API_Docs --> SRV_OCR
    API_Intake --> SRV_Policy
    API_Officer --> SRV_River
    SRV_River --> SRV_Drift

    SRV_Policy --> SRV_Explain
    SRV_River --> SRV_Explain

    API_Intake --> DB
    API_Officer --> DB
    API_Docs --> Vault
    SRV_River --> Models

    API_Intake -->|Broadcast Event| WS_Hub
    API_Officer -->|Broadcast Decision| WS_Hub
    WS_Hub --> UI_Officer
    WS_Hub --> UI_Applicant
```

---

## 2. Cold-Start Three-Stage Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Stage1_PolicyEngine: Initial Deployment (0 Labels)
    
    state Stage1_PolicyEngine {
        description: Transparent Credit Policy Scorecard (YAML)
        metrics: FOIR, LTI, Employment Stability, Document Consistency
        output: Hard rule validation + Reasoned Recommendation
    }

    Stage1_PolicyEngine --> Stage2_HITL: First Officer Decisions Committed

    state Stage2_HITL {
        description: Human-in-the-Loop Labeling Pipeline
        tracking: Total Labeled Cases, Class Balance (Approvals vs Rejections)
        threshold: N >= 100 cases, at least 20 of each class
    }

    Stage2_HITL --> Stage3_ShadowMode: Threshold Met (N >= 100)

    state Stage3_ShadowMode {
        description: River Online ML Model in Shadow Evaluation
        validation: 50-Case Rolling Agreement >= 80%, Brier Score <= 0.25
        drift: ADWIN monitors streaming decision loss
    }

    Stage3_ShadowMode --> Stage3_ActiveRecommender: Gating Benchmarks Satisfied

    state Stage3_ActiveRecommender {
        description: Incremental Model is Active Recommender
        guardrails: Policy Engine Hard Rules remain absolute ceiling
    }
```

---

## 3. End-to-End Data Intake & Recommendation Flow

```mermaid
sequenceDiagram
    autonumber
    actor Applicant as Borrower
    participant WebUI as LoanLens Web UI
    participant Backend as FastAPI Server
    participant Engine as Policy & Explainability
    participant DB as SQLite DB
    actor Officer as Loan Officer
    participant River as River Online ML

    Applicant->>WebUI: Speak / Type loan details & upload salary slip
    WebUI->>Backend: POST /api/documents/upload
    Backend->>Backend: Extract OCR salary & compute consistency score
    Backend-->>WebUI: Return verified salary & consistency badge

    Applicant->>WebUI: Confirm application submission
    WebUI->>Backend: POST /api/intake/submit
    Backend->>Backend: Encrypt PII (Fernet)
    Backend->>Engine: Evaluate Credit Scorecard & Counterfactuals
    Engine-->>Backend: Return status, reasons, and faithful advice
    Backend->>DB: Save Application & FeatureSnapshot
    Backend-->>WebUI: Display Grade 6-8 Plain-English Card
    Backend-->>Officer: Broadcast "new_application" via WebSocket

    Officer->>WebUI: Open Officer Dashboard & inspect applicant
    Officer->>Backend: POST /api/officer/applications/{id}/decision (Approve/Reject)
    Backend->>DB: Save OfficerDecision record (Ground-truth label)
    Backend->>River: learn_one(feature_vector, label)
    River->>River: Update Hoeffding Tree & ADWIN drift detector
    Backend-->>WebUI: Broadcast "officer_decision" to applicant page
```

---

## 4. Database Entity-Relationship Architecture

```mermaid
erDiagram
    APPLICATIONS ||--o{ FEATURE_SNAPSHOTS : contains
    APPLICATIONS ||--o| OFFICER_DECISIONS : receives
    APPLICATIONS ||--o| FAIRNESS_AUDIT : has_optional
    APPLICATIONS ||--o{ AUDIT_LOGS : tracked_by

    APPLICATIONS {
        string id PK
        datetime created_at
        text applicant_name_enc
        text contact_phone_enc
        text contact_email_enc
        int age
        string employment_type
        int employment_duration_months
        float monthly_income
        float existing_emis
        float requested_amount
        int tenure_months
        string loan_purpose
        float consistency_score
        string status
        string ai_recommendation
        string ai_confidence
        string ai_stage
    }

    FEATURE_SNAPSHOTS {
        string id PK
        string application_id FK
        datetime created_at
        float foir
        float lti
        float disposable_income
        float consistency_score
        json feature_vector
    }

    OFFICER_DECISIONS {
        string id PK
        string application_id FK
        string officer_id
        string decision
        string reason_code
        text officer_notes
        boolean ai_agreed
        datetime decision_timestamp
        string repayment_outcome
    }

    FAIRNESS_AUDIT {
        string id PK
        string application_id FK
        boolean consent_given
        string gender
        string social_group
        string geography_tier
    }

    SYSTEM_DRIFT_EVENTS {
        string id PK
        datetime timestamp
        string detector_name
        float metric_value
        text message
        int total_cases_at_drift
    }

    AUDIT_LOGS {
        string id PK
        datetime timestamp
        string user_role
        string user_id
        string action
        string resource_id
        json details
    }
```
