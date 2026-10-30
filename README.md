# LoanLens — Real-Time, Explainable, Voice-Enabled Loan Decision Assistant

A local-first, fintech-compliance-aware web application where loan applicants interact with a conversational voice assistant and upload financial documents. The system extracts structured data, evaluates credit policy scorecards, generates plain-English explanations and actionable counterfactual advice, and provides loan officers with a real-time decision dashboard.

**Zero Static Dataset**: The machine learning model is trained **strictly on data collected live from applicants and loan officer decisions in this system**. There is NO pre-existing CSV, public dataset, or synthetic training data anywhere in the repository.

---

## ⚡ Quick Start

```batch
double-click run.bat
```

Or from the command line:
```bash
python launcher.py
```

The launcher will automatically:
1. Create and manage a local Python virtual environment (`.venv`).
2. Verify dependency hashes (`requirements.txt`).
3. Verify the local quantized speech-to-text model (`faster-whisper` on CPU).
4. Initialize the SQLite database schema (`data/loanlens.db`).
5. Verify/serve the compiled React frontend single-port bundle.
6. Start the FastAPI server on port `8000` and open both the **Applicant Portal** (`http://127.0.0.1:8000/`) and **Officer Dashboard** (`http://127.0.0.1:8000/#officer`).

### CLI Options:
```bash
python launcher.py --help
  --port PORT          # Custom port (default: 8000)
  --reset-db           # Drop and recreate database tables
  --no-browser         # Do not auto-launch web browser
  --officer-only       # Open only the officer dashboard in browser
```

---

## 🏗️ Architecture & Core Features

### 1. Three-Stage Cold-Start Lifecycle
Because a statistical model cannot train on zero samples, LoanLens implements a transparent 3-stage lifecycle:
- **Stage 1 (Policy Engine)**: Transparent, configurable rule scorecard (`config/policy_rules.yaml`) evaluating standard credit measures: Fixed Obligation to Income Ratio (FOIR/DTI), Loan-to-Income (LTI), employment duration, and document consistency.
- **Stage 2 (Human-in-the-Loop Labeling)**: Every officer decision (`approve`, `reject`, `needs_more_info`) with a mandatory reason code is recorded as a ground-truth training label. The UI tracks distance to the activation threshold (default: $N = 100$ labeled cases, $\ge 20$ per class).
- **Stage 3 (Online Learning & Shadow Mode)**: An incremental `river` model (StandardScaler + Hoeffding Adaptive Tree) trains via `learn_one` on each decision. Operates in **Shadow Mode** first, gated by $\ge 80\%$ officer agreement and Brier calibration before promotion. Hard policy rules remain permanent safety guardrails.

### 2. Conversational Voice Assistant
- Local, offline speech-to-text with `faster-whisper` running on CPU (quantized `int8`).
- Conversational slot-filling flow: prompts one question at a time, reads questions aloud via browser `SpeechSynthesis`, and confirms captured numbers verbally ("I heard 45,000 rupees. Is that correct?").
- Robust Indian numbering & currency parsing ("4.5 lakh", "50k", "forty five thousand").
- Instant typed-input fallback and editable review form before submission. Zero raw audio persistence (transcripts only per DPDP Act).

### 3. Document Intelligence & Consistency Cross-Check
- Drag-and-drop upload for PDF, PNG, and JPG salary slips and bank statements.
- Local extraction using `pdfplumber` and OCR to capture employee name, employer, monthly salary, and average balance.
- Computes a **Consistency Score** comparing declared income against extracted document values; flags mismatches to applicant and officer.
- Encrypted storage at rest using symmetric Fernet encryption (`data/loanlens.key`).

### 4. Dual Explainability & Actionable Recourse
- **Applicant View (Grade 6-8 Reading Level)**:
  - Plain-English status: *"Likely to be approved / Needs more review / Unlikely to be approved right now"*.
  - *"Why we think this"*: 3-5 intuitive sentences free of technical jargon (no SHAP, logit, coefficient, feature).
  - *"What could change this result"*: Actionable counterfactual advice with immutable locks (age, gender, credit history locked).
  - Audited against the Flesch-Kincaid Grade Level formula ($\text{FKGL} \le 8.0$).
  - Option to hear explanations read aloud via browser TTS.
- **Officer View**:
  - Signed feature attributions chart, rule hits breakdown, nearest similar historical cases, counterfactual matrix, and ADWIN drift monitor.

### 5. Regulatory Compliance & Fairness
- **Demographic Exclusions**: Protected attributes (gender, caste, religion) are never used as model inputs. Collected separately under explicit consent solely for fairness monitoring.
- **Fairness Monitor**: Computes Demographic Parity Difference, Equal Opportunity Difference, and Disparate Impact Ratio with sample-size warnings.
- **DPDP Act 2023 Compliance**: Consent capture, purpose limitation, machine-readable data export (JSON), and complete personal data erasure.
- **RBI Digital Lending Guidelines (2022)**: Key Fact Statement (KFS) disclosures and explicit notice that all AI outputs are "Recommendations"; the human Loan Officer is the sole and final decision-maker.

---

## 🧪 Verification & Test Suite

All system modules are thoroughly tested with 100% passing tests:

```bash
.venv\Scripts\python.exe -m pytest backend/tests -v
```

Test coverage includes:
- `test_parsing.py`: Currency ("4.5 lakh", "50k"), number, duration, and intent parsing.
- `test_ocr.py`: Document extraction and consistency cross-checking.
- `test_policy.py`: Credit scorecard rules, FOIR/LTI ratios, and hard rejection rules.
- `test_online_model.py`: River streaming pipeline `learn_one`, shadow agreement, and Brier scoring.
- `test_counterfactual.py`: Actionable search, immutable attribute locks, and faithfulness re-scoring.
- `test_plain_english.py`: Flesch-Kincaid reading level ($\le 8.0$) and jargon absence audit.
- `test_fairness.py`: Demographic parity, equal opportunity, and sample size warnings.
- `test_fixtures.py`: Isolated hand-crafted test fixtures (exactly 6 cases, max 10 allowed, excluded from training).

---

## 📁 Repository Structure

```
loanlens/
├── run.bat                         # Windows launcher
├── launcher.py                     # Python environment, DB init, server runner
├── requirements.txt                # Python dependencies
├── README.md                       # Documentation & quick start
├── config/
│   ├── policy_rules.yaml           # Credit policy rules (FOIR, LTI, stability)
│   ├── phrase_dictionary.yaml      # Plain-English explanation templates
│   └── immutable_features.yaml     # Protected/locked attribute definitions
├── backend/
│   ├── core/                       # Settings, Fernet encryption, security
│   ├── db/                         # SQLAlchemy models, SQLite engine, migrations
│   ├── models/                     # Pydantic schemas
│   ├── services/
│   │   ├── voice/                  # faster-whisper STT, intent, slot filler
│   │   ├── ocr/                    # pdfplumber extractor, consistency checker
│   │   ├── intake/                 # Application intake & snapshot service
│   │   ├── features/               # Feature vector normalization
│   │   ├── policy_engine/          # Rule scorecard evaluator
│   │   ├── online_model/           # River incremental pipeline & ADWIN drift
│   │   ├── explain/                # Signed feature attributions
│   │   ├── counterfactual/         # Constrained search & faithfulness validator
│   │   ├── plain_english/          # Template translator & Flesch-Kincaid scorer
│   │   ├── fairness/               # Disparate impact & group parity monitor
│   │   └── audit/                  # Audit logging & DPDP export/deletion
│   ├── api/                        # FastAPI routes & WebSocket hub
│   └── tests/                      # Pytest unit & integration test suite
├── frontend/
│   ├── src/
│   │   ├── components/             # VoiceAssistant, TypedForm, DocumentUploader, etc.
│   │   ├── api.ts                  # REST API & WebSocket client
│   │   ├── types.ts                # TypeScript interface definitions
│   │   └── App.tsx                 # Main application & portal routing
│   ├── dist/                       # Compiled production bundle (single-port served)
│   └── package.json
└── docs/
    ├── RESEARCH.md                 # Literature citations (River, SHAP, Wachter, DPDP)
    ├── LIMITATIONS.md              # Cold start, selective labels, OCR/voice limits
    ├── EVALUATION.md               # Prequential protocol, calibration, user studies
    ├── DECISIONS.md                # Architectural decision records (ADR)
    ├── ARCHITECTURE.md             # Architecture diagrams (Mermaid)
    └── DEMO_SCRIPT.md              # Step-by-step presentation walkthrough
```

---

## ⚖️ Legal & Academic Disclaimer

LoanLens is an experimental research prototype for explainable, voice-assisted lending evaluation. It is NOT a registered Non-Banking Financial Company (NBFC) or licensed banking software. All automated recommendations require human underwriting review and final decision commitment.
