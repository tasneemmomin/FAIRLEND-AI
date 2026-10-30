# LoanLens Live Demonstration Script & Presentation Guide

This script guides a live demonstration or examiner evaluation of the LoanLens platform.

---

## 1. Quick Start & Startup Verification

1. **Launch the Application**:
   - Double-click `run.bat` (or in terminal: `python launcher.py`).
   - The launcher creates/verifies `.venv`, checks requirements hash, verifies the faster-whisper speech model, initializes SQLite tables, compiles/verifies the frontend production bundle, waits for `/api/health`, and opens the browser.
2. **Confirm Single-Port Availability**:
   - Applicant Portal: `http://127.0.0.1:8000/`
   - Officer Dashboard: `http://127.0.0.1:8000/#officer`
3. **Verify Zero Static Dataset Compliance**:
   - Point out that there is **no bundled CSV, no synthetic dataset, and no external training data** anywhere in the repository.
   - Point out the header banner: **Stage 1: Policy Scorecard (0 labeled cases)**.

---

## 2. Walkthrough: Applicant Intake Flow

### Option A: Voice Assistant Flow
1. Click **Voice Assistant Intake**.
2. Check the microphone consent box: *"I consent to microphone voice capture for application slot-filling."*
3. Click the **Microphone** icon.
4. Speak: *"My name is Priya Patel"*.
   - The assistant asks confirmation: *"I heard Priya Patel. Is that correct?"*
5. Speak: *"Yes, that is correct"*.
   - The assistant acknowledges and proceeds to the next slot: *"What is your age in years?"*
6. Answer subsequent questions:
   - Age: *"30"*
   - Employment: *"Salaried"*
   - Duration: *"3 years"*
   - Monthly Income: *"85 thousand rupees"*
   - Existing EMIs: *"5 thousand"*
   - Loan Amount: *"3 lakh"* (demonstrates Indian currency parsing)
   - Tenure: *"24 months"*
   - Purpose: *"Home renovation"*
   - Residence: *"Owned home"*
7. Click **Review & Edit Form** to inspect the captured entries.

### Option B: Document Upload & Cross-Verification
1. On the right panel, locate the **Document Verification & OCR** card.
2. Upload a sample salary slip (PDF or image).
3. Watch the system extract the employer name, employee name, and verified net salary.
4. Note the **Consistency Score Badge** (e.g., 95% match) and the presence of any variance flags.

---

## 3. Walkthrough: AI Recommendation & Plain-English Explainability

1. Click **Submit Application for AI Recommendation**.
2. **Inspect the Applicant View**:
   - **Headline Status Card**: *"Likely to be approved"* with *"High Confidence"*.
   - **Financial Metrics**: Debt-to-income (FOIR) percentage, Loan burden (LTI), Document verification match.
   - **"Why we think this"**: 3-5 simple sentences written at a Grade 6-8 reading level with zero technical jargon.
   - **"What could change this result"**: Actionable, honest counterfactual advice with immutable locks respected.
   - Click **Hear Explanation Aloud** to listen to the browser SpeechSynthesis audio playback.
3. **Demonstrate DPDP Act 2023 Compliance**:
   - Click **Export My Data (JSON)** to download a complete machine-readable portable record.
   - Click **Erase My Personal Data** to demonstrate cryptographic erasure of PII.

---

## 4. Walkthrough: Officer Dashboard & Human-in-the-Loop Labeling

1. Switch to the **Officer Dashboard** tab (or open `http://127.0.0.1:8000/#officer`).
2. Point out the **Live Applications Queue**:
   - The newly submitted application appears immediately via real-time WebSocket push.
3. Click on the applicant to open the **Detailed Inspector**:
   - **Verification Table**: Side-by-side comparison of declared vs OCR extracted income.
   - **Scorecard Breakdown**: Itemized rule hits with individual points.
   - **Signed Feature Attributions**: Visualizing positive and negative contributions.
   - **Nearest Similar Cases**: k-NN historical comparison.
4. **Record Officer Decision (Ground-Truth Label)**:
   - Select: `APPROVE` or `REJECT`.
   - Select a mandatory **Reason Code** (e.g., `Low FOIR & Stable Income`).
   - Enter optional notes.
   - Click **Commit Officer Decision**.
5. **Observe Incremental Learning & Stage Progression**:
   - The decision immediately updates the application status in the database.
   - The decision triggers `learn_one` in the `river` online model.
   - The progress bar increments toward the Stage 3 activation threshold ($N=100$).
   - Switch back to the applicant page: observe that the page updated live with the officer decision!

---

## 5. Walkthrough: Compliance, Fairness & Concept Drift

1. **Fairness Monitor Tab**:
   - View live Demographic Parity Difference, Equal Opportunity Difference, and Disparate Impact Ratio.
   - Highlight the **Sample Size Warning** (flags groups with $N < 10$ cases to prevent premature conclusions).
2. **Concept Drift & Model Health Tab**:
   - View the ADWIN drift detection status and rolling 50-case officer agreement rate.
   - Explain the promotion gate: the incremental model remains in Shadow Mode until $\ge 80\%$ agreement and Brier score $\le 0.25$ are achieved.
