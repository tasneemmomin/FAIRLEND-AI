# Voice & Language Test Report — English (en-IN), हिन्दी (hi-IN), मराठी (mr-IN)

**Date:** 31 October 2026 · **Build:** `index-CdVzoTe-.js` / backend `backend.api.app` · **Scope:** multilingual voice pipeline, end-to-end

This report separates **what was actually executed** from **what could not be executed in this environment**. No microphone or speech-synthesis result is claimed unless it was produced by the running system.

---

## 1. Verification matrix

| Layer | Method | Status |
|---|---|---|
| Language registry & aliases | Automated tests (`backend/tests/test_voice_multilingual.py`) | ✅ executed |
| Number / currency parsing (3 languages, romanised + Devanagari) | Automated tests + live UI turns | ✅ executed |
| Confirmation intents (yes/no in 3 languages) | Automated tests + live UI turns | ✅ executed |
| Categorical slots (employment / purpose / residence) | Automated tests + live UI turns | ✅ executed |
| Slot questions & messages per language | Automated tests + live UI rendering | ✅ executed |
| Full intake flows (Hindi, Marathi) through the **real UI** | Browser-driven typed turns against the live server | ✅ executed |
| Mid-conversation language switch (context preservation) | Live UI + API tests | ✅ executed |
| TTS voice availability detection | Live UI (browser) | ✅ executed (reported **unavailable** — see §5) |
| Browser SpeechRecognition (microphone) | Not exercisable in the automated harness | ⚠️ not executed |
| faster-whisper transcription | Model not installed in this venv | ⚠️ not executed (UI reports offline) |
| Audio output quality of Hindi/Marathi TTS | No hi/mr system voice installed | ⚠️ not verifiable here |

**Backend suite:** `181 passed` (`pytest backend/tests`, 16–19 s). Voice-specific: `93 passed`.

---

## 2. Reference phrases from the directive — measured results

All values below are the actual outputs of `parse_spoken_currency_or_number` / `parse_duration_months` (unit-tested and, where marked UI, observed in the live browser session).

| Utterance | Language | Expected | Actual | Verified in |
|---|---|---|---|---|
| "Meri monthly salary 60 hazaar rupaye hai" | en/hi romanised | 60,000 | **60000** | test + UI (English run) |
| "साठ हजार रुपये" | hi | 60,000 | **60000** → spoken back "₹60,000 रुपये" | test + UI (Hindi run) |
| "माझा मासिक पगार साठ हजार रुपये आहे" | mr | 60,000 | **60000** → "मला ₹60,000 रुपये ऐकलं" | test + UI (Marathi run) |
| "बारा हजार" / "माझ्यावर बारा हजार रुपयांचा EMI आहे" | hi / mr | 12,000 | **12000** | test + UI (both runs) |
| "पाँच लाख" / "मला पाच लाख रुपयांचे कर्ज हवे आहे" | hi / mr | 500,000 | **500000** → "₹5,00,000" | test + UI (both runs) |
| "₹45,382" / "₹४५,३८२" | en / hi | 45,382 | **45382** | test |
| "50k", "4.5 lakh", "1.2 crore" | en | 50,000 / 450,000 / 12,000,000 | exact | test |
| "अट्ठाईस" (age) | hi | 28 | **28** → "मैंने 28 साल सुना" | UI (Hindi run) |
| "तीस" (age) | mr | 30 | **30** → "मला 30 वर्षे ऐकलं" | UI (Marathi run) |
| "दो साल" / "दोन वर्षे" | hi / mr | 24 months | **24** → "2 साल" / "2 वर्षे" | UI |
| "तीस छह महीने" | hi | 36 months | **36** → "3 साल" | UI (Hindi run) |
| "चोवीस महिने" | mr | 24 months | **24** → "2 वर्षे" | UI (Marathi run) |
| "नौकरी" / "नोकरी" | hi / mr | salaried | salaried, spoken back **"नौकरी" / "नोकरी"** | UI |
| "पढ़ाई" / "शिक्षण" | hi / mr | education | education, spoken back **"पढ़ाई" / "शिक्षण"** | UI |
| "किराए का" / "भाड्याने" | hi / mr | rented | rented, spoken back **"किराए का" / "भाड्याने"** | UI |
| "हाँ" / "जी" / "हां" | hi | yes | yes | test + UI |
| "हो" / "बरोबर" / "आहे" | mr | yes | yes | test + UI |
| "नहीं" / "नाही" / "नको" | hi / mr | no | no | test |
| "पता नहीं" | hi | unclear/negative | treated as negative → re-asks the slot | test |

---

## 3. Live UI run — Hindi (20 turns, all slots)

Session driven through the real React UI against `http://127.0.0.1:8001`; language selected via the UI dropdown (not by calling the API directly).

| # | Assistant (Hindi) | Applicant answer | Result |
|---|---|---|---|
| — | *(English session)* → dropdown switched to हिन्दी | — | "अब हम हिन्दी में बात करेंगे। अब तक दर्ज की गई जानकारी सुरक्षित है।" |
| 1 | नमस्ते! … कृपया अपना पूरा नाम बताइए। | मेरा नाम रोहित वर्मा है | "मैंने रोहित वर्मा सुना। क्या यह सही है?" |
| 2 | — | हाँ | धन्यवाद! आपकी उम्र कितनी है? |
| 3 | — | अट्ठाईस | "मैंने 28 साल सुना। क्या यह सही है?" |
| 4 | — | हाँ | आपकी मुख्य रोज़गार कैटेगरी क्या है? … |
| 5 | — | नौकरी | "मैंने नौकरी सुना। क्या यह सही है?" |
| 6 | — | हाँ | आप अपनी मौजूदा नौकरी या व्यापार में कितने समय से हैं? |
| 7 | — | दो साल | "मैंने 2 साल सुना। क्या यह सही है?" |
| 8 | — | हाँ | आपकी मासिक औसत टेक-होम सैलरी या आमदनी कितनी है? |
| 9 | — | साठ हजार रुपये | "मैंने ₹60,000 रुपये सुना। क्या यह सही है?" |
| 10 | — | हाँ | क्या आपकी कोई मौजूदा मासिक EMI या किस्त चल रही है? |
| 11 | — | बारह हजार | "मैंने ₹12,000 रुपये सुना। क्या यह सही है?" |
| 12 | — | हाँ | आप कितनी राशि का लोन चाहते हैं? |
| 13 | — | पाँच लाख | "मैंने ₹5,00,000 रुपये सुना। क्या यह सही है?" |
| 14 | — | हाँ | आप यह लोन कितने महीनों या सालों में चुकाना चाहेंगे? |
| 15 | — | तीस छह महीने | "मैंने 3 साल सुना। क्या यह सही है?" |
| 16 | — | हाँ | इस लोन का उद्देश्य क्या है? … |
| 17 | — | पढ़ाई | "मैंने पढ़ाई सुना। क्या यह सही है?" |
| 18 | — | हाँ | आप अपने घर में कैसे रहते हैं — अपना, किराए का, या पारिवारिक? |
| 19 | — | किराए का | "मैंने किराए का सुना। क्या यह सही है?" |
| 20 | — | हाँ | धन्यवाद! सभी जानकारी दर्ज कर ली गई है। कृपया स्क्रीन पर अपनी जानकारी जाँच कर सबमिट करें। |

Captured chips (Hindi): नाम: रोहित वर्मा · उम्र: 28 · रोज़गार: नौकरी · नौकरी अवधि: 2 साल · आमदनी: ₹60,000 · मौजूदा EMI: ₹12,000 · लोन: ₹5,00,000 · अवधि: 3 साल · उद्देश्य: पढ़ाई · आवास: किराए का.

**Defects found and fixed during this run**
1. Categorical values were echoed as internal English enums ("मैंने salaried सुना") → localized labels (`CATEGORY_LABELS` + frontend `valueLabels`).
2. "किराए का" — the exact phrase offered by the Hindi prompt — failed to parse (lexicon had only "किराया") → added "किराए / किराये / किराएदार / भाड्याचे".
3. Chip labels only covered 4 of 10 slots ("age: 28") → all slots localized.
4. Language switch appended "मुझे ठीक से समझ नहीं आया" before the re-asked question → clean switch path added.

---

## 4. Live UI run — Marathi (19 turns, all slots)

| # | Assistant (Marathi) | Applicant answer | Result |
|---|---|---|---|
| — | dropdown → मराठी | — | "आता आपण मराठी मध्ये बोलू. आत्तापर्यंत नोंदवलेली माहिती सुरक्षित आहे. नमस्कार! …" |
| 1 | नमस्कार! … पूर्ण नाव सांगा. | माझं नाव मोहिनी देशमुख आहे | "मला मोहिनी देशमुख ऐकलं. हे बरोबर आहे का?" |
| 2 | — | हो | धन्यवाद! तुमचे वय किती आहे? |
| 3 | — | तीस | "मला 30 वर्षे ऐकलं." |
| 4 | — | हो | तुमचा मुख्य व्यवसायाचा प्रकार काय आहे? |
| 5 | — | नोकरी | "मला नोकरी ऐकलं." |
| 6 | — | हो | तुम्ही … किती वर्षे आहात? |
| 7 | — | दोन वर्षे | "मला 2 वर्षे ऐकलं." |
| 8 | — | हो | तुमचा मासिक सरासरी … उत्पन्न किती आहे? |
| 9 | — | **माझा मासिक पगार साठ हजार रुपये आहे** | "मला ₹60,000 रुपये ऐकलं." |
| 10 | — | हो | तुमच्यावर सध्या कोणती मासिक EMI …? |
| 11 | — | **माझ्यावर बारा हजार रुपयांचा EMI आहे** | "मला ₹12,000 रुपये ऐकलं." |
| 12 | — | हो | तुम्हाला किती रक्कम कर्ज हवे आहे? |
| 13 | — | **मला पाच लाख रुपयांचे कर्ज हवे आहे** | "मला ₹5,00,000 रुपये ऐकलं." |
| 14 | — | हो | तुम्ही हे कर्ज किती महिन्यांत किंवा वर्षांत फेडाल? |
| 15 | — | चोवीस महिने | "मला 2 वर्षे ऐकलं." |
| 16 | — | हो | या कर्जाचा उद्देश्य काय आहे? |
| 17 | — | शिक्षण | "मला शिक्षण ऐकलं." |
| 18 | — | हो | तुम्ही तुमच्या घरात कसे राहता — स्वतःचे, भाड्याने, कौटुंबिक? |
| 19 | — | भाड्याने | "मला भाड्याने ऐकलं." → हो → "धन्यवाद! सर्व माहिती नोंदवली गई आहे…" |

Captured chips (Marathi): नाव: मोहिनी देशमुख · वय: 30 · व्यवसाय: नोकरी · नोकरीचा कालावधी: 2 वर्षे · उत्पन्न: ₹60,000 · सध्याचे EMI: ₹12,000 · कर्ज: ₹5,00,000 · मुदत: 2 वर्षे · उद्देश: शिक्षण · निवास: भाड्याने. See `docs/redesign/after/03-applicant-voice-marathi.jpeg`.

**Defect found and fixed during this run**
- "चोवीस महिने" (24 months) was rejected: only tens existed in the lexicon. Added full **compound numbers 21–99** for Hindi and Marathi (e.g. अट्ठाईस, चोवीस, छत्तीस, एकोणऐंशी, नव्व्याण्णव), with tests.

---

## 5. Text-to-speech: availability is checked, not assumed

`VoiceAssistant.tsx` implements `pickVoice(lang)` (exact locale → base language) and `checkVoiceAvailability(lang)`:

- On language change and on `voiceschanged`, the app enumerates `speechSynthesis.getVoices()`.
- If no voice matches the selected base language (`hi`, `mr`), an amber `role="alert"` banner is displayed.

**Observed in this environment (real output, not simulated):**

> "No Marathi speech voice is installed on this device. Responses will display correctly, but may be read with the default (English) voice or silently skipped."

and equivalently for Hindi. This is the honest behaviour required: the app states the limitation and continues in text. Speech rate is 0.92 for hi/mr, 1.0 for English; `onstart`/`onend`/`onerror` drive the `speaking` state so Hands-Free resumes listening correctly even when synthesis fails.

**Not verified here:** the acoustic quality of Hindi/Marathi playback, because no such system voice exists in this environment. Installing the OS language pack (Windows: Settings → Time & language → Language → हिन्दी/मराठी → Speech) enables it with no code change.

---

## 6. Speech-to-text: what is configured vs what was exercised

| Path | Configuration | Exercised here |
|---|---|---|
| Web Speech API | `recognition.lang = selected locale` (`en-IN`/`hi-IN`/`mr-IN`), `interimResults`, `maxAlternatives = 1`, confidence captured | ❌ microphone input cannot be produced by the automated harness |
| MediaRecorder → `/api/voice/transcribe` | `FormData` includes `language`; backend maps to whisper code (`en`/`hi`/`mr`) and forces it | ⚠️ endpoint reachable, but `faster-whisper` is **not installed** in this venv → returns `error: "Local speech recognition model not initialized…"`, which the UI surfaces verbatim |

Consequently, **no claim is made about recognition accuracy for live speech**. What *is* verified: locale enforcement is wired end-to-end, and every parsed value is confirmed verbally before it is stored, so a mis-recognition cannot be silently accepted.

To verify locally: install the model (`pip install faster-whisper`) and speak the phrases in §2 — the pipeline will force the selected language.

---

## 7. Language switching (context preservation) — verified

| Check | Evidence |
|---|---|
| Switch at slot 0 (English → हिन्दी) | Prompt re-issued in Hindi; "अब तक दर्ज की गई जानकारी सुरक्षित है" |
| Switch mid-confirmation (hi → mr) via API | `language: mr-IN` returned; `session_state.language` = `mr-IN`; pending value re-confirmed in Marathi |
| Switch after completion | "आपकी जानकारी पहले ही पूरी दर्ज हो चुकी है…" / Marathi equivalent, chips relabelled, values intact |
| Slots preserved | `filled_slots` unchanged across all switches (asserted in tests) |
| One control drives everything | Dropdown updates STT locale, TTS voice, response language, chip labels, consent text, placeholder |

---

## 8. How to reproduce

```bash
# backend
.venv\Scripts\python.exe -m pytest backend\tests\test_voice_multilingual.py -q   # 93 passed
.venv\Scripts\python.exe -m pytest backend\tests -q                              # 181 passed

# app
.venv\Scripts\python.exe -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8001
# open http://127.0.0.1:8001/#applicant-workspace-demo, select हिन्दी/मराठी,
# type: "मेरा नाम रोहित वर्मा है" … "साठ हजार रुपये" … "पाँच लाख"
```
