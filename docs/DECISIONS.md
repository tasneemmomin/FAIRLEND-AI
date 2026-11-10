# Architectural Decision Records (ADR) — LoanLens

This document records the architectural and engineering decisions made during the design and construction of LoanLens, favoring local-first, free-to-run, and compliance-aware choices.

---

## ADR 01: Zero Static Dataset & Pure Streaming Data Model
- **Context**: Standard ML projects bundle static historical CSV datasets (e.g., Kaggle loan datasets). However, real-world deployment of novel lending products begins with zero historical labeled records.
- **Decision**: Zero pre-existing CSV or public datasets are included in the repository or downloaded at runtime. Training data is constructed strictly from real-time applicant submissions and loan officer decision events (`learn_one`).
- **Consequences**: Avoids dataset leakage, synthetic data artifacts, and copyright concerns; requires a three-stage cold-start lifecycle.

## ADR 02: Three-Stage Cold-Start Lifecycle
- **Context**: A machine learning model cannot produce valid statistical predictions from zero samples.
- **Decision**: Implement a 3-stage progression:
  1. *Stage 1 (Policy Engine)*: Scorecard based on banking credit policies (FOIR, LTI, stability).
  2. *Stage 2 (Human-in-the-Loop Labeling)*: Officers review applications and record decisions (`approve`, `reject`, `needs_more_info`), building training labels.
  3. *Stage 3 (Online Learning & Shadow Mode)*: Streaming `river` model trains incrementally. Operates in Shadow Mode first, gated by $\ge 80\%$ officer agreement and Brier calibration before promotion. Hard policy rules remain permanent safety guardrails.
- **Consequences**: Transparent system evolution visible to the officer and user at all times.

## ADR 03: Local-First Database Architecture (SQLite via SQLAlchemy)
- **Context**: The application must run locally on Windows without requiring paid managed cloud databases (e.g., MongoDB Atlas, AWS RDS).
- **Decision**: Use SQLite with SQLAlchemy ORM using standard ANSI SQL datatypes (DateTime, String, Float, Text, JSON) so the engine can be swapped for PostgreSQL in enterprise environments via `DATABASE_URL`.
- **Consequences**: Zero cloud setup, fast local reads/writes, zero infrastructure cost.

## ADR 04: Field-Level Cryptographic Security for PII
- **Context**: India's DPDP Act 2023 mandates high standards for protecting digital personal data.
- **Decision**: Implement symmetric field-level encryption using Python's `cryptography.fernet.Fernet`. A local 256-bit key is generated and stored securely in `data/loanlens.key`. Applicant names, phone numbers, and email addresses are encrypted before insertion into the database.
- **Consequences**: Protection against database snooping; authorized officers can view decrypted data only through authenticated API layers.

## ADR 05: Deterministic Template Engine for Plain-English Explanations
- **Context**: General-purpose LLMs can hallucinate financial figures, output inconsistent explanations, or produce non-auditable text.
- **Decision**: Use deterministic, human-reviewed template dictionaries (`config/phrase_dictionary.yaml`) driven by exact mathematical metrics (FOIR, LTI, consistency). Audit reading levels using the Flesch-Kincaid Grade Level formula to guarantee Grade 6-8 comprehension.
- **Consequences**: 100% auditable, consistent, reproducible explanations with zero API latency or token cost.

## ADR 06: Local CPU Speech-to-Text via Quantized Faster-Whisper
- **Context**: Requiring paid cloud speech APIs (Google Cloud Speech, OpenAI Whisper API) violates local-first, zero-paid-API constraints.
- **Decision**: Use `faster-whisper` (CTranslate2) running the `base` model in 8-bit integer quantization on CPU. Provide an instantaneous typed-input fallback on the screen if audio hardware or microphone access is unavailable.
- **Consequences**: Completely offline speech transcription with zero audio streaming to external clouds; respects borrower privacy.

## ADR 07: Single-Port Full-Stack Deployment
- **Context**: Managing separate ports for Vite frontend and FastAPI backend complicates local execution on Windows.
- **Decision**: The React frontend is compiled to `frontend/dist` and mounted as static assets inside FastAPI. The entire web application (Applicant Portal, Officer Dashboard, WebSocket, REST API) runs on a single port (default `8000`).
- **Consequences**: Double-clicking `run.bat` launches the complete full-stack system from a single URL (`http://127.0.0.1:8000`).

## ADR 08: Financial Stress Early-Warning & Future Scenario Intelligence
- **Context**: The existing platform evaluates only an applicant's *current* affordability. The loan officer and applicant had no transparent way to explore how affordability could change if income falls, expenses rise, or new obligations appear.
- **Decision**: Add a modular `financial_stress` service (deterministic, versioned calculation engine) with:
  1. A separate simulation engine (`calculations.py`, `scenarios.py`, `projections.py`, `stress_indicators.py`, `explanations.py`) that mirrors documented arithmetic — Disposable Income, Remaining Balance, Total EMI Burden, FOIR — with safe zero/missing-income handling.
  2. Scenarios A–F (current condition, income reduction 5–20%, expense increase 5–20%, additional obligations, combined shocks, user-customized) driven by admin-configurable, append-only versioned configuration (`StressScenarioConfig` table).
  3. A strictly assumption-based 12-month cash-flow projection (explicitly NOT a forecast; revisit only if validated historical data becomes available).
  4. Template-based explanations (no LLM in the calculation path), and worst-case summaries.
  5. Role-guarded APIs under `/api/stress/*`: applicants access only their own applications; officers access all; config writes officer-only; report exports and officer assessments are audit-logged.
- **Consequences**: Scenario simulation is fully isolated — hypothetical values NEVER modify the `applications` table. Indicators are clearly labelled "under assumptions" and are not statistically validated default probabilities. Officer stress analysis is advisory only; the human officer remains the sole decision-maker.
- **Audit fixes applied in the same pass**: `/api/explain/{id}` now enforces authentication + ownership (previously unauthenticated); officer decision payloads are now enum-validated (`approve|reject|needs_more_info`) so invalid values can no longer corrupt human-in-the-loop training labels.
