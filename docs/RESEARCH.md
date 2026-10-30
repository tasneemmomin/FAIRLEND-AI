# LoanLens Research & Architectural Grounding
**Literature-Grounded Rationale for Real-Time, Explainable, Voice-Enabled Credit Decision Systems**

---

## 1. Streaming Machine Learning & Online Concept Drift

### 1.1 The Cold-Start Dilemma in Credit Underwriting
In traditional credit risk modeling, batch machine learning assumes an abundance of pre-existing, identically distributed historical records ($X \sim \mathcal{D}$). In a novel, non-extractive credit system, no historical dataset is assumed or bundled. The system must commence cold with an interpretable, policy-driven rule baseline before gradually handing control to statistical learning.

### 1.2 Incremental Learning with River
To adapt to continuously arriving applicant records without retraining over the full historical corpus, LoanLens employs the **River** online learning ecosystem:
- **Montiel, J., Halford, M., Mastelini, S. M., Bolmier, G., Sourty, R., Vaysse, R., Zouitine, A., Gomes, H. M., Read, J., Abdessalem, T., & Bifet, A. (2021).** *River: machine learning for streaming data in Python.* Journal of Machine Learning Research, 22(110), 1-8.
- River enables strict $O(1)$ memory consumption and sub-millisecond per-sample model updates via `learn_one(x, y)` following the **test-then-train** (prequential) protocol.

### 1.3 Tree Inducers for Streaming Credit Data
- **Gomes, H. M., Bifet, A., Read, J., Barddal, J. P., Enembreck, F., Pfahringer, B., Holmes, G., & Abdessalem, T. (2017).** *Adaptive random forests for evolving data stream classification.* Machine Learning, 106(9), 1469-1495.
- LoanLens uses the **Hoeffding Adaptive Tree (HAT)** and Adaptive Random Forest (ARF). Hoeffding trees exploit the Hoeffding bound (additive Chernoff bound) to guarantee that an asymptotic split choice matches a batch decision with confidence $1 - \delta$, using only a minimal stream sample window (grace period).

### 1.4 Concept Drift Detection via ADWIN
Credit environments undergo both sudden macro-economic shifts (e.g., benchmark interest rate adjustments) and gradual seasonal shifts in applicant profiles:
- **Gama, J., Žliobaitė, I., Bifet, A., Pechenizkiy, M., & Bouchachia, A. (2014).** *A survey on concept drift adaptation.* ACM Computing Surveys (CSUR), 46(4), 1-37.
- LoanLens implements **ADWIN (Adaptive Windowing)**:
  - **Bifet, A., & Gavalda, R. (2007).** *Learning from time-changing data with adaptive windowing.* In Proceedings of the 2007 SIAM international conference on data mining (pp. 443-448).
  - ADWIN maintains a variable-length sliding window of recent prediction residuals, splitting the window into sub-windows to test the null hypothesis that sub-window means are identical. When the difference exceeds the statistical threshold, drift is flagged, triggering structural adaptation and logging an immutable drift event.

---

## 2. Explainable Artificial Intelligence (XAI) & Actionable Recourse

### 2.1 Feature Attributions
For technical underwriters and compliance audits, understanding marginal feature impact is legally required under adverse action notice mandates:
- **Lundberg, S. M., & Lee, S. I. (2017).** *A unified approach to interpreting model predictions.* Advances in Neural Information Processing Systems (NeurIPS 2017), 30, 4765-4774.
- In LoanLens, feature contributions are represented as signed additive perturbations relative to neutral policy benchmarks, decomposing score deviations into intuitive positive and negative forces.

### 2.2 Counterfactual Explanations & Algorithmic Recourse
Rather than merely telling a rejected applicant *why* they were turned down, ethical lending requires providing *actionable recourse*—the minimal, realistic alterations that invert the adverse recommendation:
- **Wachter, S., Mittelstadt, B., & Russell, C. (2017).** *Counterfactual explanations without opening the black box: Automated decisions and the GDPR.* Harvard Journal of Law & Technology, 31(2), 841-887.
- **Mothilal, R. K., Sharma, A., & Tan, C. (2020).** *Explaining machine learning classifiers through diverse counterfactual explanations.* In Proceedings of the 2020 Conference on Fairness, Accountability, and Transparency (FAccT '20), 607-617.
- **Ustun, B., Spangher, A., & Liu, Y. (2019).** *Actionable recourse in linear classification.* In Proceedings of the Conference on Fairness, Accountability, and Transparency (FAT* '19), 10-19.

### 2.3 Feasibility, Monotonicity & Faithfulness Guarantees
LoanLens addresses known defects in naive counterfactual algorithms:
1. **Immutable Attribute Locks**: Attributes such as age, gender, caste, religion, and historical credit length are strictly locked ($x_j' = x_j$).
2. **Directional Monotonicity**: An applicant cannot be told to earn less money or have shorter employment duration. Only directional improvements are proposed (e.g., decrease requested loan amount, extend repayment tenure, pay down existing EMIs).
3. **Deterministic Faithfulness Check**: Every generated counterfactual candidate is re-evaluated through the operational credit policy and online model pipeline. If $f(x') \neq \text{likely\_approved}$, the candidate is discarded.

### 2.4 Readability & Plain-English Translation
- Standard XAI systems generate cryptic jargon ("SHAP value +0.32", "Log-odds shift").
- In LoanLens, all applicant-facing explanations are translated via a human-reviewed, deterministic template dictionary (`config/phrase_dictionary.yaml`).
- Explanations are mathematically audited for reading comprehension against the **Flesch-Kincaid Grade Level formula**:
  $$\text{FKGL} = 0.39 \left(\frac{\text{total words}}{\text{total sentences}}\right) + 11.8 \left(\frac{\text{total syllables}}{\text{total words}}\right) - 15.59$$
- All delivered applicant explanations maintain $\text{FKGL} \le 8.0$, ensuring clarity for borrowers without financial engineering backgrounds.

---

## 3. The Selective Labels / Reject Inference Limitation

### 3.1 Unobserved Counterfactuals in Credit Scoring
A fundamental research challenge in algorithmic underwriting is **selective labeling** (also known as the *reject inference* problem):
- **Lakkaraju, H., Kleinberg, J., Leskovec, J., Ludwig, J., & Mullainathan, S. (2017).** *The selective labels problem: Evaluating algorithmic predictions in the presence of unobservables.* In Proceedings of the 23rd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining, 275-284.
- In credit operations, default labels ($Y \in \{0, 1\}$) are only observed for approved applicants who receive funds and proceed to repay or default. Rejected applicants have unobserved repayment capability.
- Consequently, supervised models trained solely on approved applicant repayment data suffer from severe selection bias.

### 3.2 LoanLens Mitigation & Delayed Labeling
LoanLens tackles this challenge through:
1. **Policy Scorecard as Prior**: Grounding early-stage decisions in standard prudential credit guidelines (FOIR, LTI, employment stability) rather than biased historical approvals.
2. **Officer Decisions as Intermediate Ground Truth**: Every officer action (`approve`, `reject`, `needs_more_info`) forms the supervised label stream for the online model, ensuring the model learns institutional risk appetite.
3. **Delayed Repayment Outcome Field**: Officers can retroactively record loan repayment outcomes (`current`, `defaulted`, `prepaid`) as longitudinal evidence matures.

---

## 4. Algorithmic Fairness & Group Parity

### 4.1 Group Fairness Criteria
- **Hardt, M., Price, E., & Srebro, N. (2016).** *Equality of opportunity in supervised learning.* Advances in Neural Information Processing Systems (NeurIPS 2016), 29, 3315-3323.
- LoanLens tracks three primary statutory fairness indicators:
  1. **Demographic Parity Difference (DPD)**:
     $$\Delta_{\text{DP}} = \max_{a, b} |P(\hat{Y}=1 | A=a) - P(\hat{Y}=1 | A=b)|$$
  2. **Disparate Impact Ratio (DIR)** (Four-Fifths Rule):
     $$\text{DIR} = \frac{\min_a P(\hat{Y}=1 | A=a)}{\max_a P(\hat{Y}=1 | A=a)}$$
     A ratio below $0.80$ triggers an adverse impact warning.
  3. **Equal Opportunity Difference (EOD)**:
     $$\Delta_{\text{EO}} = |P(\hat{Y}=1 | Y=1, A=a) - P(\hat{Y}=1 | Y=1, A=b)|$$

### 4.2 Decoupled Demographic Auditing
- In strict adherence to anti-discrimination principles, protected demographic attributes (gender, caste, religion) are **never** included in the model feature vector or policy scorecard.
- Demographics are collected voluntarily under explicit separate consent, solely to compute post-hoc fairness metrics for the compliance dashboard.

---

## 5. Voice Intake & Low-Literacy Usability

### 5.1 Speech Recognition with Whisper
- **Radford, A., Kim, J. W., Xu, T., Brockman, G., McLeavey, C., & Sutskever, I. (2023).** *Robust speech recognition via large-scale weak supervision.* International Conference on Machine Learning (ICML 2023), PMLR 202:28492-28518.
- LoanLens utilizes `faster-whisper` (utilizing CTranslate2) running locally on CPU in 8-bit quantized precision, eliminating dependency on third-party cloud audio APIs.
- Conversational slot-filling ensures high usability for semi-literate or vernacular borrowers by speaking each question aloud and verifying captured values through affirmative verbal confirmation ("I heard 45,000 rupees. Is that correct?").

---

## 6. Regulatory Frameworks & Compliance

### 6.1 India Digital Personal Data Protection (DPDP) Act 2023
- **Purpose Limitation & Data Minimization**: Intake data is processed strictly for credit assessment.
- **Right to Portability & Erasure**: Implemented via dedicated endpoints (`/api/privacy/export` and `/api/privacy/delete`), enabling complete machine-readable exports and cryptographic anonymization of identifying personal records.
- **Zero Raw Audio Retention**: Raw voice audio is processed in memory or ephemeral temporary storage and deleted immediately upon transcription.

### 6.2 Reserve Bank of India (RBI) Digital Lending Guidelines (2022)
- **Key Fact Statement (KFS)**: Standardized disclosure of all financial commitments, estimated monthly installments, and annual percentage benchmarks before applicant commitment.
- **Human-in-the-Loop Precedence**: Clear labeling that automated system outputs represent "Recommendations"; licensed underwriting officers retain final credit authority.
