# FairLend AI — Frontend Enhancement Report

**Date:** 31 October 2026 · **Scope:** design-system rebuild, multilingual voice UI, honesty fixes, build hardening · **Evidence:** `docs/redesign/before/` vs `docs/redesign/after/` · **Companion docs:** `UI_UX_AUDIT.md`, `DESIGN_SYSTEM.md`, `VOICE_LANGUAGE_TEST_REPORT.md`

---

## 1. What changed, in one paragraph

The frontend was rebuilt on a **build-time design system** (Tailwind v3 compiled by Vite, zero runtime CDNs), a **three-script type system** (IBM Plex Sans + IBM Plex Sans Devanagari + IBM Plex Mono, self-hosted), and a **fully language-aware voice assistant** whose prompts, confirmations, number parsing, chips, consent text and TTS voice all follow the selected language — with context preserved across mid-conversation switches. Existing workflows, routes, API contracts and identity were preserved: nothing was re-architected, only fixed at the root cause and re-skinned.

---

## 2. Engineering defects fixed (audit E1–E5)

| # | Defect | Fix | Verification |
|---|---|---|---|
| E1 | Tailwind loaded from `cdn.tailwindcss.com` at runtime | `tailwindcss@3.4.17` + `postcss` + `autoprefixer` installed as dev deps; `tailwind.config.cjs` + `postcss.config.cjs`; CDN `<script>` removed | `dist/assets/index-*.css` = 64.5 kB (11.5 kB gzip) generated at build; `document.querySelector("script[src*='cdn.tailwindcss']")` → `null` in browser |
| E2 | Fonts fetched from Google Fonts at runtime | 23 woff2 subsets (812 KiB) self-hosted in `frontend/public/fonts/`, declared in `src/styles/fonts.css` with `unicode-range` preserved | `GET /fonts/plex-devanagari-400-devanagari.woff2` → 200, 77,448 bytes; `document.fonts.status === "loaded"` |
| E3 | No Devanagari font — OS fallback | IBM Plex Sans Devanagari 400/500/600/700 bundled and placed second in every font stack; `.deva` class sets `line-height: 1.8`, `font-style: normal` | Computed `font-family` on Hindi headings resolves to Plex Sans Devanagari; Hindi chat renders with correct matras in screenshots |
| E4 | No design tokens; 4 competing palettes | Single token source `src/index.css` (`--fla-*`), mirrored into Tailwind theme; landing `--fl-*` mapped onto the same palette | New components use tokens only; audit's `#172C3D / #0F1E2A / #0F172A` palette drift removed from new code |
| E5 | Voice API had no `language` parameter | `language` added to `/api/voice/init`, `/api/voice/turn`, `/api/voice/transcribe` (optional, default `en-IN`, backward compatible) | 181 backend tests green, including backward-compatibility tests with no `language` field |

Additional build fix discovered during the work: `package.json` is ESM, so PostCSS/Tailwind configs must be `.cjs` (documented in `DESIGN_SYSTEM.md`).

---

## 3. Voice assistant rewrite

`frontend/src/components/VoiceAssistant.tsx` was rewritten (not patched) around an explicit state machine:

- **States:** `idle · permission_required · listening · processing · speaking · error`, each with a localized label in all three languages and a colour+text status dot (never colour alone).
- **Language selector** is a single control that simultaneously sets: STT locale (`recognition.lang`), backend response language, TTS voice, chip labels, consent text, placeholder and hint text. A mid-conversation change issues a language-only turn so the backend re-asks the current slot in the new language and explicitly confirms captured context is preserved.
- **TTS:** voice chosen by exact locale then base language; rate 0.92 for hi/mr; **availability is checked** and, when the OS has no matching voice, an honest amber banner states that responses will display correctly but may be read with the default English voice or skipped (observed live: *"No Marathi speech voice is installed on this device…"*).
- **Hands-Free mode:** continuous turn-taking — listening resumes automatically after TTS ends; `no-speech` is treated as benign and restarts quietly; toggling off stops capture.
- **Low-confidence transcript:** confidence < 0.45 shows a "low confidence — please confirm" badge on the live transcript, on top of the per-value verbal confirmation.
- **Fallback path:** Web Speech API unavailable → MediaRecorder → `/api/voice/transcribe` with the selected language hint; if faster-whisper is not installed, the UI reports the model as offline instead of pretending.
- **Accessibility:** emoji removed from chips (Lucide icons), `aria-pressed` on toggles, `role="alert"` on warnings, per-message `lang` attributes, bottom-anchored chat.

Backend counterpart (`backend/services/voice/`):
- `intent.py`: whitespace-token parsing (Devanagari matras are not `\w`), Devanagari digits, Indian currency words (`साठ हजार`, `पाच लाख`, `12 हजार`, `50k`, `₹45,382`), compound numbers 21–99 in Hindi and Marathi, confirmations (`हाँ/जी/ठीक/हो/बरोबर/नाही/नको`), categorical vocabulary for employment/purpose/residence, Indian digit grouping.
- `languages.py`: slot questions and message templates per language.
- `slot_filler.py`: language persisted in session state, localized speak-back (including category names), clean switch announcement without a spurious "didn't catch that".

---

## 4. Honesty fixes (no fabricated capability claims)

| Location | Before | After |
|---|---|---|
| Auth page subtitle | "Secure, biometric-grade authentication…" | "Secure sign-in and registration for borrowers & loan applicants." |
| Auth page badge | "256-bit SSL • DPDP Act 2023 Compliant" | "Encrypted in transit & at rest • DPDP Act 2023 Compliant" |
| TTS | silent English phonetics for Hindi text | explicit device-voice availability warning + documented fallback |
| STT fallback | silent failure | explicit "local speech model is offline" message |
| Landing hero | undersold the stress feature | one supporting paragraph naming languages + stress scenarios (reuses existing `.fl-hero-subtext` class) |

---

## 5. Visual system changes (before → after)

- **Type:** Playfair Display (editorial serif) → IBM Plex Sans/Devanagari/Mono. `font-serif` remapped so legacy headings inherit the new system without touching every component.
- **Colour:** ad-hoc hexes → tokenised navy/teal on warm paper `#F6F7F4`, semantic green/amber/red with AA contrast.
- **Figures:** all money/IDs in tabular mono with Indian grouping; chat chips show `₹5,00,000`, `₹60,000`, `₹12,000`.
- **Surfaces:** 10 px radius cards, 1 px hairlines, two-level shadows, 150 ms transitions, reduced-motion support.
- **Voice panel:** explicit status line, honest warning strip, localized consent row, localized placeholder, bottom-anchored conversation, labelled Hands-Free toggle.

---

## 6. Regression & build evidence

| Check | Result |
|---|---|
| `pytest backend/tests` | **181 passed** (88 pre-existing + 93 voice/multilingual) |
| `npx tsc --noEmit` | clean |
| `npm run build` | success — 477.3 kB JS (127.2 kB gzip), 64.9 kB CSS (11.6 kB gzip) |
| Runtime CDN references | none (`index.html` has no external script/link) |
| Fonts | served from `/fonts/*`, `document.fonts.status = loaded` |
| Hindi flow through live UI | 20 turns, all slots captured, fully Hindi |
| Marathi flow through live UI | 19 turns, directive money phrases parsed exactly |
| Mid-conversation language switch | prompts + chips + consent switch language; captured slots intact |
| End-to-end chain (voice → submit → officer) | Hindi intake completed, switched to Marathi (context kept), typed form prefilled from voice slots, submitted, live recommendation returned (NEEDS MORE REVIEW, FOIR 47.1 %), stress simulator loaded the same application, officer queue listed it (`after/08`, `after/09`, `after/05`) |
| Mobile layout | landing `scrollWidth === 390` at a 390 px viewport (no horizontal overflow) |

### Screenshot index (`docs/redesign/after/`)

| File | What it shows |
|---|---|
| `01-landing.jpeg` | Full landing page, desktop 1440 px — new type system, tokenised palette, hero preview |
| `02-applicant-voice-hindi.jpeg` | Completed Hindi voice intake (20 turns, all 10 slots captured, chips in Hindi, Indian-grouped ₹ amounts) |
| `03-applicant-voice-marathi.jpeg` | Same session switched to Marathi — context preserved ("मला 3 वर्षे ऐकलं"), localized chips/consent, honest TTS-voice warning |
| `04-applicant-typed.jpeg` | Typed review form prefilled from the voice session's slots |
| `05-officer-dashboard.jpeg` | Officer queue after sign-in — real applications with recommendation, tenure, FOIR |
| `06-applicant-auth.jpeg` | Applicant sign-in / registration surface |
| `07-landing-mobile.jpeg` | Landing at 390 px — no horizontal overflow, no clipped cards |
| `08-applicant-recommendation.jpeg` | Live recommendation for the submitted application (NEEDS MORE REVIEW, FOIR, counterfactuals) |
| `09-applicant-stress-simulator.jpeg` | Financial stress simulator on the same application with real values and scenario table |

---

## 7. Defects found during end-to-end validation (fixed)

These were invisible in the static audit and only surfaced when the full workflow was driven through the real UI:

| # | Defect | Why it mattered | Fix |
|---|---|---|---|
| D1 | `#applicant-workspace-demo` created a **fabricated token** (`demo_token`) | Every authenticated action 401'd — submission failed with "Authentication required", so the demo could never reach a recommendation | Interim fix (real JWT exchange) was superseded on user request: the demo applicant account, its credentials and its 1-click login were **removed entirely**. The demo hash routes now land on the real sign-in/registration portal, and no applicant account is seeded — everyone registers their own credentials |
| D2 | Officer dashboard fetched data **on mount, before sign-in**, and never re-ran | Queue displayed "No applications found" while the database held 27 applications | Effect now guards on `isAuthenticated` and includes it in the dependency array (`OfficerDashboard.tsx`) |
| D3 | Landing page overflowed horizontally by **112 px at 390 px** | Hero preview and analytics cards were clipped on phones | Footer links wrap; `.fl-stat-card-wide` collapses to one column; entity grid 4→2 columns; vitals grid uses `minmax(0, 1fr)`; verified `scrollWidth === 390` |

A minor polish item from the same run: `age` and enum values in the captured-values chips were not localized ("age: 28", "salaried") — all ten slot labels and all categorical values are now localized in en/hi/mr.

---

## 8. Known limitations (stated honestly)

1. **Device TTS voices:** Hindi/Marathi system voices are not installed in the test environment; the UI says so. Installing OS language packs enables real speech output without code changes.
2. **Local STT model:** `faster-whisper` is not installed in this venv, so the MediaRecorder fallback reports "model offline". Browser Web Speech recognition remains the primary path and is locale-configured, but microphone input could not be exercised in the automated harness — see `VOICE_LANGUAGE_TEST_REPORT.md` for the exact scope of what was and was not verified.
3. **Inline styles in `LandingPage.tsx`:** ~30 inline style blocks remain (audit L2). They are token-consistent but not yet extracted into classes; scheduled as a follow-up refactor, not a functional risk.
4. **Sticky header in full-page screenshots:** a Chromium capture artifact (sticky elements paint at scroll offset); screenshots are taken with the header temporarily set to `static` so the evidence matches what users see.
5. **Voice recognition accuracy:** depends on the browser's Web Speech backend; the pipeline now enforces the selected locale and asks for verbal confirmation before storing any value, but STT quality itself is outside the app's control.
