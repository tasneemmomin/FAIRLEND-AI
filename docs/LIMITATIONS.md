# LoanLens System Limitations & Risk Disclosures

This document details the operational, algorithmic, and regulatory limitations of the LoanLens architecture.

---

## 1. Cold-Start & Initial Heuristic Bias (Stage 1)
- **Problem**: When deployed with zero historical data ($N=0$), the system cannot perform statistical inference. It relies entirely on the pre-configured Policy Rule Scorecard (`config/policy_rules.yaml`).
- **Limitation**: Hard policy rules encode traditional banking orthodoxies (e.g., FOIR $\le 45\%$, tenure limits). These rules may inadvertently exclude creditworthy informal-economy workers who lack conventional documentation or structured salary slips.
- **Mitigation**: The policy engine is explicitly designed as a configurable YAML file that risk committees can adjust. Furthermore, officers retain full override authority.

## 2. Small-Data Instability in Incremental Streams (Stage 2)
- **Problem**: Between $N=1$ and $N=100$ labeled cases, online machine learning models exhibit high variance and sample-order sensitivity.
- **Limitation**: A sequence of unrepresentative approvals or rejections early in the stream can skew tree split criteria.
- **Mitigation**: Stage 3 models operate in **Shadow Mode** by default. They are only promoted to active recommenders after surpassing minimum sample gates ($N \ge 100$, $\ge 20$ per class) and meeting calibration benchmarks (rolling 50-case agreement $\ge 80\%$, Brier score $\le 0.25$).

## 3. The Selective Labels / Reject Inference Dilemma
- **Problem**: In credit operations, ground-truth repayment performance ($Y \in \{\text{paid}, \text{default}\}$) is only observable for applicants who are approved and funded. Rejected applicants never receive a loan, making their counterfactual repayment capacity unobservable.
- **Limitation**: Supervised models trained on officer approval decisions learn to mimic the *officer's approval behavior* rather than predicting true repayment capability.
- **Mitigation**: The system supports delayed outcome updates via `/api/officer/applications/{id}/repayment`. However, because outcomes for rejected applicants remain unobserved, true reject-inference remains an open research problem requiring semi-supervised or domain-adaptation techniques.

## 4. Optical Character Recognition (OCR) Boundaries
- **Problem**: Document extraction relies on `pdfplumber` for digital PDFs and local OCR engines for scanned images.
- **Limitation**: Documents featuring complex multi-column layouts, low-resolution mobile photographs ($<150$ DPI), watermarks, or handwritten entries may yield extraction omissions or erroneous numeric parsing.
- **Mitigation**: Extracted values are displayed side-by-side with original document previews, and a Consistency Score is computed. Mismatches are flagged to the applicant and officer for manual verification rather than causing automated rejections.

## 5. Speech Recognition & Acoustic Vulnerabilities
- **Problem**: Speech-to-text relies on a quantized `faster-whisper` model executing on consumer CPUs.
- **Limitation**: In the presence of heavy acoustic reverberation, loud street/ambient noise, or heavily accented multilingual utterances, word error rates (WER) increase.
- **Mitigation**: The conversational dialogue requires explicit user confirmation for every extracted numerical value ("I heard 45,000 rupees. Is that correct?"). A fallback typed input box is available on-screen at all times.

## 6. Automation Bias & Underwriter Complacency
- **Problem**: Over time, human loan officers may exhibit *automation bias*—uncritically accepting AI recommendations without thorough independent underwriting.
- **Limitation**: Inadvertent automation bias could entrench existing biases or policy errors present in the scoring model.
- **Mitigation**: All AI outputs are labeled prominently as "Recommendations" rather than "Decisions". Officers are mandated to select a structured Reason Code and provide free-text notes for every decision. System audits track officer-AI agreement rates to detect rubber-stamping behavior.

## 7. Research Prototype Scope
- **Notice**: LoanLens is an academic and product engineering research prototype. It does not constitute a certified banking software platform under the Reserve Bank of India (RBI) licensing framework. It is intended for controlled evaluation of explainability, online learning, and voice-assisted intake workflows.
