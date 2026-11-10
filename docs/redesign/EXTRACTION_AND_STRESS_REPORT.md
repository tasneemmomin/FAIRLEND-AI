# Real-World Document Extraction & Stress Simulator — 1 Nov 2026

Scope of this change set: (1) document extraction behaves like a real bank reading
a real statement/slip/ID, (2) the Financial Stress Simulator got a one-tap
"Quick Check" so the math is self-explanatory.

## 1. Extraction hardening (`backend/services/ocr/extractor.py`)

Real Indian bank formats are no longer misread. Root-cause fixes, each with a
regression test in `backend/tests/test_nlp_document_extraction.py`:

| Real-world format | Old behaviour | New behaviour |
|---|---|---|
| Table header `... Closing Balance` followed by rows | the header's regex leaked across the newline and grabbed the next row's `01` (read `185,000` as `1`) | label→value gap is confined to the **same line** and cannot contain digits/dashes |
| `OPN BAL` row (SBI/HDFC passbook layout, no label-value pair) | opening balance missed | opening = last grouped/decimal token on the `OPN BAL` (or `B/F`) row |
| `Closing Balance : 348,600.40 Cr` | `Cr` suffix broke parsing or flipped nothing | `Cr` = positive, `Dr` = **negative** (`_clean_currency_signed`) |
| `ACH-8891` reference codes on EMI rows | reference number read as the EMI (`8900.0`) | per-line parsing; only comma-grouped/decimal tokens count as money; amounts below 500 discarded |
| 3–6 months of recurring salary credits | only the first credit counted | **median** of every qualifying salary credit + `salary_credit_count` (one-off festival bonus cannot distort it) |
| Recurring NACH/ACH EMIs | all EMIs **summed** (a 3-month window tripled the debt) | **mode** (most common amount) + `emi_debit_count` |
| e-Aadhaar printed as `XXXXXXXX1234` | mask not recognised | masked UIDAI form accepted directly, reported `XXXX-XXXX-1234` |
| `age` computed from hardcoded `2026` | wrong age from 2027 on | `date.today().year` |
| Bank header read as employer (`employer_name: HDFC BANK LTD`) | officer saw the bank as the applicant's employer | on bank statements a bank-like employer is cleared; only genuinely labelled employer fields survive |
| Salary as plain `85000` (test/legacy slips) | — | fallback token scan keeps simple formats working |

**Verified end-to-end through the live API** (register → login → upload a
generated HDFC-style PDF): closing `348600.40`, opening `185000`, salary median
`85000.0` (3 credits), EMI `12130.0` (3 debits), name `ZAIDA KHAN`,
`employer_name: None`.

## 2. Stress Simulator simplification (`frontend/src/components/FinancialStressSimulator.tsx`)

Real banks underwrite on a single stress moment; applicants think in life
situations. The sandbox tab now opens with a **Quick Check card strip** computed
with the *exact same* backend-mirrored formulas (`computeScenarioLive`):

- Normal Month · Job Loss (3 months) · Income Dropped 30% · Medical / Emergency
  · New Commitment (₹5,000 EMI) · Worst Case
- Each card shows its **own live verdict before you tap** (remaining balance +
  stress chip, colored by the same classification thresholds).
- One tap sets the four existing controls (income %, expense %, extra EMI,
  proposed-EMI override) — the custom sliders, projection, comparison table and
  report download all keep working unchanged; touching any control deselects
  the active card ("Custom / Advanced").
- `classifyClient` bug fixed: 0-income simulations (full job loss) previously
  returned "Insufficient Information"; now correctly reported as
  NEGATIVE_BALANCE / ELEVATED_STRESS.

## 3. Test status

`185 passed` (`181` pre-existing + `4` new: Cr/Dr table layout, salary-median
outlier rejection, Dr-negative balances, masked Aadhaar). `npx tsc --noEmit` and
`npm run build` clean.

## 3b. Microphone denial — precise diagnosis + one-tap recovery (VoiceAssistant)

Previously *every* mic denial showed the same blunt "Microphone access was
denied…" line. Root-cause fix: denials now run through a single handler that
probes the real permission state (`navigator.permissions.query({name:
"microphone"})`, Chrome/Edge) and reports the *actual* cause:

- site blocked → exact address-bar unlock instructions,
- browser-granted but attempt failed → Windows privacy / mic-in-use hint,
- prompt suppressed → one explicit `getUserMedia` retry in-context,
- `NotReadableError` → "mic busy (Zoom/Teams/recorder)",
- `NotFoundError` → "no mic detected".

Additions: a **Try Again** button on the warning bar (works without reload),
an automatic unlock listener that clears the warning the moment the user flips
permission to Allow, and the browser prompt now fires immediately when the DPDP
consent checkbox is ticked instead of on the first spoken phrase. App cannot
un-block a browser/OS setting by design — it now says exactly which one and
recovers live once the user changes it.

## 4. Honest limitations

- Image-format documents still depend on pytesseract/Windows OCR availability;
  the hardening above applies to the text layer (native PDFs and OCR output alike).
- Preset cards simulate *one month's* cash-flow exactly as the backend formulas
  do; a multi-month survival runway (savings depletion) is a future enhancement,
  not claimed here.
- Job-loss verdicts derive from the same deterministic formula, not from new
  underwriting policy; they are marked hypothetical in the UI, as before.
