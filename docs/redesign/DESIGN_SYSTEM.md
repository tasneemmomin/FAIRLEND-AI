# FairLend AI — Design System v2.0

**Status:** implemented · **Scope:** entire frontend (`frontend/`) · **Single token source:** `frontend/src/index.css` (`--fla-*`) with the landing page's legacy layer (`frontend/src/landing.css`, `--fl-*`) mapped onto the same values.

---

## 1. Design principles

1. **Institutional trust over trend.** Navy/teal DNA retained (continuity for existing users) but formalised into tokens. No decorative gradients, no glassmorphism.
2. **Figures are the product.** Every ₹ amount, score, ratio and ID is set in a tabular monospaced face so columns align and digits never jitter during live recalculation.
3. **One superfamily, three scripts.** IBM Plex Sans (Latin UI) + IBM Plex Sans Devanagari (हिन्दी/मराठी) + IBM Plex Mono (figures). Same skeleton, so Hindi and English sit on the same baseline and optical weight.
4. **Honesty is a visual style.** Demo badges, "recommendation not decision" notes, consent banners and unavailable-feature warnings are first-class components — not footnotes.
5. **Quiet chrome, loud data.** Borders are hairlines; shadows are layered but low-contrast; colour is reserved for state (pass / refer / decline, listening / speaking / error).

---

## 2. Colour tokens

| Token | Value | Use |
|---|---|---|
| `--fla-ink` | `#0B1F2A` | deepest surface, hero, primary button on light |
| `--fla-navy-900` | `#0F2231` | portal header chrome, dark panels |
| `--fla-navy-800` | `#173247` | raised dark surface (header controls) |
| `--fla-teal-700` | `#0C655C` | primary action, user message bubble |
| `--fla-teal-600` | `#0E766B` | hover / secondary action |
| `--fla-teal-500` | `#148A7F` | focus ring, active accent |
| `--fla-teal-100` | `#E3F2EF` | consent banner, subtle brand tint |
| `--fla-paper` | `#F6F7F4` | app background (warm, not grey) |
| `--fla-card` | `#FFFFFF` | cards, inputs, assistant bubbles |
| `--fla-border` | `#E4E8E4` | 1px hairlines |
| `--fla-text` | `#23313C` | body text |
| `--fla-text-secondary` | `#5C6B78` | labels, metadata |
| `--fla-text-muted` | `#8B98A4` | hints, disabled |

**Semantic states** (each with text / background / border triple, AA on paper and on navy):

| State | Text | Background | Border |
|---|---|---|---|
| Positive / approve | `#0B734B` | `#E8F6EE` | `#B7E2C6` |
| Caution / refer | `#92600C` | `#FBF3E4` | `#EAD3A2` |
| Negative / decline | `#B23A3A` | `#FBEDEC` | `#F0C4C2` |

Contrast: body text on paper = 11.6:1; teal-700 on white = 6.4:1; amber-900 on amber-bg = 6.1:1; white on navy-900 = 15.2:1.

---

## 3. Typography

### Families (self-hosted, `frontend/public/fonts/`, 23 woff2 subsets, 812 KiB)

| Role | Family | Weights |
|---|---|---|
| UI / body / headings | IBM Plex Sans | 400, 500, 600, 700 |
| Hindi & Marathi | IBM Plex Sans Devanagari | 400, 500, 600, 700 |
| Figures, IDs, policy codes | IBM Plex Mono | 400, 500, 600 |

Declared in `frontend/src/styles/fonts.css` with `unicode-range` preserved, so Latin pages never download Devanagari glyphs and vice-versa.

### Scale

| Step | Size / line-height | Weight | Use |
|---|---|---|---|
| Display | 3.4 rem / 1.15 | 600 | landing hero only |
| H1 | 2 rem / 1.25 | 600 | portal page titles |
| H2 | 1.375 rem / 1.3 | 600 | section titles |
| H3 | 1.0625 rem / 1.4 | 600 | card titles |
| Body | 0.875 rem / 1.6 | 400 | default |
| Label | 0.75 rem / 1.4 | 500 | field labels, metadata |
| Micro | 0.6875 rem / 1.35 | 600, `+0.06em` tracking, uppercase | section eyebrows only (max 1 per screen region) |
| Figure | 0.875 rem, `font-feature-settings: "tnum" 1` | 500/600 | all money and metrics |

### Rules

- **Never** set Devanagari in italic (`font-style: normal` enforced in `.deva`); Devanagari line-height is `1.8` vs `1.6` for Latin because of matra clearance.
- Money always renders as `₹` + Indian grouping (`5,00,000`, `1,20,00,000`) using `format_inr()` on the backend and `toLocaleString("en-IN")` on the client — never `5,000,00` style grouping.
- Uppercase micro-labels are limited to eyebrows; form section headers use sentence case at 0.8125 rem/600 for better hierarchy contrast (audit finding A3/typed-form fix).
- `lang` attribute is set per message bubble and per input so the browser applies correct line-breaking and hyphenation to Hindi/Marathi text.

---

## 4. Space, radius, elevation, motion

- **Spacing:** 8 px base — 4, 8, 12, 16, 24, 32, 48. Card padding 16–24; section rhythm 48–64.
- **Radius:** `6px` controls · `10px` cards · `14px` panels · `999px` pills. Chat bubbles keep a 2 px "tail" corner (`rounded-tl-sm` / `rounded-tr-sm`).
- **Elevation:** `--fla-shadow-card` (resting) and `--fla-shadow-hover` (hover only). Nothing else.
- **Motion:** `150ms ease` for hover/focus/state; spinners only for genuine async. `prefers-reduced-motion` collapses all animation to 0.01 ms.

---

## 5. Components

| Component | Specification |
|---|---|
| **Primary button** | teal-700 bg, white text, 600 weight, `10px` radius, 12/20 padding, hover teal-600, disabled 40% opacity |
| **Secondary button** | white bg, 1px `--fla-border`, text `--fla-text`, hover paper bg |
| **Card** | white, 1px border, `10px` radius, `--fla-shadow-card`; header row separated by hairline |
| **Status pill** | semantic triple (text/bg/border), 0.6875 rem/600, `999px`, dot prefix optional |
| **Field** | white, 1px border, `6px` radius, 0.875 rem, focus ring 2 px teal-500 + offset 2 px |
| **Voice status indicator** | 10 px dot + label: emerald (idle/ready), pulsing emerald (listening), pulsing amber (processing), pulsing teal (speaking), red (error) — colour is never the only signal, the label always names the state |
| **Captured-value chip** | white, hairline, `6px` radius, label in secondary + value in mono; amounts emphasised in teal-700 |
| **Consent banner** | teal-100 bg, teal-700 text, checkbox + explicit scope sentence + regime badge |
| **Honest warning** | amber triple, warning icon, `role="alert"`, names the missing capability and the fallback |
| **KPI tile** | label (label size, secondary) → value (mono, 1.5 rem, 600) → delta/state pill |
| **Table** | header row 0.6875 rem/600 uppercase secondary; numeric columns `text-right` + `tabular-nums`; row hover paper |

---

## 6. Accessibility contract

- Focus: single global `:focus-visible` ring (2 px teal-500, 2 px offset) — no per-component ring colours.
- Colour never carries meaning alone: every semantic state has a text label and/or icon with `aria-hidden` on the decorative part.
- Functional icons are Lucide SVGs (no emoji in controls); emoji removed from voice chips (audit A2).
- `aria-live="polite"` on the conversation log; `role="alert"` on warnings; `aria-pressed` on toggles; `aria-label` on icon-only buttons.
- Minimum target 32×32 px for icon buttons, 40 px for primary controls; the officer tab row wraps rather than overflowing at 360 px.

---

## 7. Implementation map

| Concern | File |
|---|---|
| Tokens, base typography, focus, scrollbars, reduced motion | `frontend/src/index.css` |
| `@font-face` declarations (self-hosted) | `frontend/src/styles/fonts.css` |
| Font binaries | `frontend/public/fonts/*.woff2` |
| Tailwind theme mapping (colours, font stacks, shadows) | `frontend/tailwind.config.cjs` |
| PostCSS pipeline (no CDN) | `frontend/postcss.config.cjs` |
| Landing page tokens (`--fl-*`, mapped to the same palette) | `frontend/src/landing.css` |

**Prohibited patterns:** runtime CSS/font CDNs, hard-coded hex values in new components (use tokens or the Tailwind theme), `font-serif` for headings, tabular figures replaced by proportional digits in tables.
