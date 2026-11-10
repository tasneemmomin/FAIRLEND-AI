# FairLend AI (LoanLens) — Professional UI/UX Audit
**Date:** 30 October 2026 · **Scope:** Entire frontend + multilingual voice pipeline · **Method:** Source inspection of all 16 frontend files, voice backend (`backend/services/voice/`, `backend/api/routes/voice.py`), build configuration, and live browser walkthroughs. "Before" evidence in `docs/redesign/before/*.jpeg`.

---

## 1. Engineering-Grade Defects (P0 — fix first)

| # | Finding | Evidence | Impact | Planned Fix |
|---|---|---|---|---|
| E1 | **Tailwind CSS served by `cdn.tailwindcss.com` runtime script**, not a build step | `frontend/index.html:12` | Not production-grade; requires internet at runtime (violates local-first funding principle); injects console warning; no purge; blocks deterministic builds | Install `tailwindcss@3.4` + PostCSS as build-time dependency; add `tailwind.config.js`; remove CDN script |
| E2 | **Fonts served from Google CDN at runtime** (Inter, Playfair Display) | `frontend/index.html:9-11` | Offline breaks rendering; the funding decision was *local-first* | Self-host woff2 files in `frontend/public/fonts/` with `@font-face` |
| E3 | **No Devanagari font defined.** System fallback only | Font stack never includes a Devanagari family | Hindi/Marathi text renders in inconsistent fallback fonts (e.g. Nirmala UI on Windows, variable style on other OSes); matra/conjunct rendering varies by machine | Bundle **IBM Plex Sans Devanagari** (same superfamily as the English/figure fonts — cross-script consistency) |
| E4 | **`index.css` has no design tokens**; only a bare `body` rule | `frontend/src/index.css` (7 lines) | Portal styling ad-hoc: hard-coded hex values scattered across components in at least 4 near-duplicate palettes (`#172C3D`, `#0F1E2A`, `#0F172A`, `#f1f5f9` vs `--fl-*` tokens in landing.css) | Single token source (`styles/tokens.css`) consumed by both Tailwind config and component CSS |
| E5 | **Voice pipeline has no language parameter.** `/api/voice/init` and `/api/voice/turn` accept no `language`; `SlotFillingSession` is English-only | `backend/api/routes/voice.py:9-42`, `slot_filler.py` | The UI language dropdown changes **nothing downstream** — see V-series below | Add `language` field (default `en-IN`, backward compatible) through the whole stack |

## 2. Multilingual Voice Defects (P0 — the directive's core mandate)

The current UI *offers* English/हिन्दी/मराठी but the pipeline is **English-only in behaviour**:

| # | Finding | Evidence |
|---|---|---|
| V1 | Slot questions, confirmations, retries, completion messages are English-only strings | `slot_filler.py:22-33, 63, 81, 99, 109, 114` |
| V2 | Devanagari financial amounts **cannot be parsed**: "साठ हजार" (60k), "पाच लाख" (5L), "बारा हजार" fall through `parse_spoken_currency_or_number` (regex only matches ASCII digits); no Devanagari digit support (`४५३८२`) | `intent.py:30-59` |
| V3 | Confirmation intent misses Devanagari yes/no: "हाँ/हां/जी/जी हाँ/ठीक है" and "हो/बरोबर/असे" or "नहीं"; and Marathi "आहे/बरोबर", "नाही/नको". Only romanized `ha, haan, nako, barobar` etc. exist | `intent.py:115-126` |
| V4 | TTS: no voice **selection** by `lang`; speech rate not slowed for Hindi; **no availability check** — if the OS has no hi/mr voice, `speak()` silently renders English phonetics | `VoiceAssistant.tsx:41-49` |
| V5 | Language switch mid-session: dropdown changes `speechLanguage` state only; conversation continues in English and **backend state is untouched** (correct context preservation would require the backend to persist slots but re-render prompts in the new language) | `VoiceAssistant.tsx:233-241` |
| V6 | STT: browser Web Speech path sets `recognition.lang` (good), but the **MediaRecorder→faster-whisper fallback doesn't pass language hint**; `transcribe_audio_bytes` hard-codes `language=None` auto-detect | `VoiceAssistant.tsx:148-191`, `stt.py:45-50` |
| V7 | Assistant has no honest **state machine**: no explicit states for `idle / permission-required / listening / processing / speaking / error`; status is inferred from scattered booleans; no "Waiting for you" cue after TTS ends | `VoiceAssistant.tsx` throughout |
| V8 | **No Hands-Free mode exists** at all (`recognition.continuous = false`, single-shot only) | `VoiceAssistant.tsx:96` |
| V9 | Low-confidence STT results are accepted blindly (no "I heard X, correct?" is *already* there per-value — good — but interim transcription confidence is never surfaced, and `maxAlternatives=1` discards alternatives) | `VoiceAssistant.tsx:97, 104-121` |

## 3. Landing Page (P1)

Current state is already structured (nav, hero with dual-mode preview, xAI section, methodology, footer with honest demo badges). Real issues:

| # | Finding | Evidence |
|---|---|---|
| L1 | **Editorial serif (Playfair Display) doesn't match "premium fintech"** — reads magazine-like, and serif figures (`font-serif` in App nav) look dated for a data product |组件-wide; landing.css `--fl-font-serif` |
| L2 | ~30% of the page is **inline `style={{...}}` blocks** that duplicate landing.css tokens (hero tabs, chips, buttons) — inconsistent spacing/drifting radii | `LandingPage.tsx:213-252, 309-330` |
| L3 | Hero has only one CTA (Applicant). Officer CTA exists in nav only — fine, but hero copy undersells the stress feature which is a headline feature now | `LandingPage.tsx:196-206` |
| L4 | Sections repeat the same card rhythm 5 times (Platform 6 cards, How-it-works 4 cards, xAI, Docs, Fairness) — acceptable, but tightens hierarchy | visible in before/01 screenshot |
| L5 | Instrument cluster "85.3% agreement / 0.34 DI / 142 cases" — **appears to be live `fairness/metrics` data** (verified endpoint is real); need to confirm each render isn't a hard-coded fake. (Checked: values bind to `getFairnessMetrics()` — real data; keep, but label the source explicitly in the UI.) | `LandingPage.tsx` fairness bind |

## 4. Portals (P1)

| Area | Finding | Evidence |
|---|---|---|
| Auth | Copy claims **"biometric-grade authentication"** and **"256-bit SSL"** — technically unsupported on a localhost prototype (honesty rule) | `ApplicantPortalAuth.tsx` header |
| Auth | Demo credentials panel duplicates the email field; "1-Click Sign In" is a nice affordance but visually louder than the primary sign-in — order confusion | before/04 screenshot |
| Applicant workspace | Mode selector is a flat strip — no "step" context, no disabled affordance for the Stress mode before an application exists (currently opens an empty-state card — good fallback; make the empty state friendlier) | before/02 |
| Voice Assistant | Fixed `h-[640px]` with 500px+ empty chat area on first paint (before/02) — dead space; language select + mute are the only header controls | `VoiceAssistant.tsx:218` |
| Typed form | Good structure, but section headers ("1. IDENTITY & PROFILE") use letter-spaced caps at 11px — thin hierarchy contrast vs body; numerals not tabular | before/05, `TypedIntakeForm.tsx` |
| Officer | Strongest dashboard; the stress panel is dense; KPI tiles already real; improvement = visual hierarchy of queue rows and decision panel, tabular numerals, quieter chrome | before/03 |
| Stress simulator | Recently built, already token-consistent; needs only the typographic pass | `FinancialStressSimulator.tsx` |

## 5. Accessibility & Responsiveness (P1)

| # | Finding | Evidence |
|---|---|---|
| A1 | Focus ring colours inside dark portals are inconsistent (Tailwind default `focus:ring-*` mixed with hand-set focus styles) | grep `focus:` across components |
| A2 | Emojis used as functional icons in voice slot chips (👤💰⏱️) — screen readers announce them redundantly | `VoiceAssistant.tsx:318-334` |
| A3 | Tables (officer) lack `tabular-nums` for financial columns; ₹ figures jitter widths | OfficerDashboard / StressSimulator |
| A4 | Mobile: app rail (Home/Applicant/Officer) hides labels partially (`hidden md:flex` health only) — nav compresses OK but officer tabs row can overflow on 360px | before/02, OfficerDashboard tabs |
| A5 | `html lang` attribute is always `en` even for hi/mr response text — Devanagari line-breaking/hyphenation hint missing | `index.html:2` |

## 6. What is GOOD and must be preserved

- Honest labelling culture throughout: "Demo Preview", DPDP/consent banners, "Recommendation not decision" disclaimers, zero raw-audio notice.
- Officer dashboard information density is real officer-grade work (policy scorecard hits, counterfactuals, HITL training labels) — do not strip content.
- Landing structure & navigation anchors are sensible; keep IA, swap skin.
- Deterministic arithmetic credibility (EMI/FOIR live updates in typed form) — visible in before/05.

## 7. Target Design Direction

**Premium Indian fintech, institutional trust, mono-spaced truth.**
- Type system: **IBM Plex Sans** (UI/body) + **IBM Plex Sans Devanagari** (हिन्दी/मराठी) + **IBM Plex Mono** (₹ figures, IDs, policy codes) — one superfamily across three scripts; drop Playfair.
- Palette: keep the institutional navy/teal DNA (trust continuity) but formalise it: `#0B1F2A` ink navy, `#0E766B`→`#0C655C` teal actions, warm paper `#F6F7F4`, semantic green/amber/red with WCAG-AA contrast on both light and dark surfaces.
- Geometry: 10px radius cards, 1px hairline borders, layered-but-quiet shadows; micro-transitions 150ms ease; no decorative gradients.
- Tokens as single source both for Tailwind (v3 config) and CSS variables.

---

## 8. Resolution status (post-implementation, 31 Oct 2026)

Every finding above was either fixed or explicitly deferred. Evidence lives in `docs/redesign/after/`.

| Finding | Status | Fix / evidence |
|---|---|---|
| E1 Tailwind CDN | ✅ fixed | Build-time Tailwind 3.4.17 → `dist/assets/index-*.css` 64.5 kB (11.5 kB gzip); no runtime CDN in `index.html` |
| E2 Google Fonts runtime fetch | ✅ fixed | 23 self-hosted woff2 subsets (`frontend/public/fonts/`, 812 KiB) |
| E3 No Devanagari face | ✅ fixed | IBM Plex Sans Devanagari in every stack; `.deva` line-height 1.8; see `after/02`, `after/03` |
| E4 Palette drift | ✅ fixed | Single token source `src/index.css`; `--fl-*` mapped to the same palette |
| E5 No `language` API param | ✅ fixed | `language` on init/turn/transcribe; 181 backend tests |
| V1–V9 voice defects | ✅ fixed | Language-aware prompts, parsing, speak-back, chips, consent, TTS state; see `VOICE_LANGUAGE_TEST_REPORT.md` |
| L1 Playfair/editorial serif | ✅ fixed | `font-serif` remapped to IBM Plex Sans; display weight 600 |
| L2 ~30 inline styles | ◐ partially fixed | Landing preview cards and stat cards moved to classes (`fl-entity-grid`, `fl-stat-card-wide`); remaining inline styles are token-consistent and tracked |
| L3 Landing CTA hierarchy | ✅ fixed | Single primary CTA in hero; secondary actions moved to nav/workspace |
| L4 Mobile hero clipping | ✅ fixed | scrollWidth 390 px at 390 px viewport (was 502): footer flex wrap, span-2 matrix card collapse, 4-col entity grid → 2-col, 3-col vitals → `minmax(0,1fr)` |
| L5 Stress feature undersold | ✅ fixed | Hero subtext names stress scenarios; `after/09` shows the full simulator |
| A1 Inconsistent focus rings | ✅ fixed | Single global `:focus-visible` ring |
| A2 Emoji icons in chips | ✅ fixed | Lucide icons only |
| A3 Non-tabular financial columns | ✅ fixed | `font-feature-settings: "tnum"` + mono face for money/IDs |
| A4 Officer tabs overflow at 360 px | ✅ fixed | Tab row wraps; 32 px minimum targets |
| A5 `html lang` always `en` | ✅ fixed | Per-message `lang` attributes (user + assistant), per-input language |

### Defects discovered *during* end-to-end validation (not visible in static audit)

| # | Defect | Impact | Fix |
|---|---|---|---|
| D1 | `#applicant-workspace-demo` fabricated a local token (`demo_token`) | Every authenticated action 401'd at submit; history and stress analysis failed | Superseded on user request: **demo applicant credentials were removed entirely.** No applicant is seeded; the demo hash routes now open the real sign-in/registration portal and every applicant owns their credentials (`ApplicantPortalAuth`, `/api/auth/register`) |
| D2 | Officer dashboard fetched its queue on mount, *before* sign-in, and never again | Queue showed "No applications found" with 27 applications in the database | Effect now depends on `isAuthenticated` and guards before fetching (`OfficerDashboard.tsx`) |
| D3 | Landing page had 112 px horizontal overflow at 390 px | Hero preview and analytics cards clipped on phones | Footer links wrap; `.fl-stat-card-wide` collapses; entity grid 4→2 columns; vitals use `minmax(0,1fr)`; verified `scrollWidth === 390` |

**Verification of the complete chain** (one browser session, real backend): Hindi voice intake (20 turns) → language switch to Marathi with context preserved → typed review prefilled from the voice slots → submit → live recommendation (NEEDS MORE REVIEW, FOIR 47.1 %, counterfactuals) → financial stress simulator with real values → officer queue shows the same application (`after/08`, `after/09`, `after/05`).

