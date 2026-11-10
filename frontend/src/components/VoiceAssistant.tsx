import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Mic, MicOff, Send, Volume2, VolumeX, CheckCircle, RefreshCw,
  Languages, AlertTriangle, Infinity as InfinityIcon, CircleStop,
} from "lucide-react";
import {
  initVoice, processVoiceTurn, transcribeAudioBlob,
} from "../api";
import { ApplicantIntakeForm } from "../types";

/* -------------------------------------------------------------------------- */
/*  Voice interaction state machine (directive §6 — always visible status)     */
/* -------------------------------------------------------------------------- */
type VoiceStatus =
  | "idle"                 // session ready, waiting for user action
  | "permission_required"  // mic consent not given / device denied
  | "listening"            // microphone open
  | "processing"           // STT / NLU turn in flight
  | "speaking"             // TTS playback
  | "error";               // recoverable failure, typed fallback offered

const STATUS_LABELS: Record<string, Record<string, string>> = {
  "en-IN": {
    idle: "Ready", permission_required: "Microphone consent required",
    listening: "Listening…", processing: "Understanding your answer…",
    speaking: "Speaking… tap to skip", error: "Something went wrong — you can type your answer",
  },
  "hi-IN": {
    idle: "तैयार", permission_required: "माइक्रोफ़ोन की अनुमति ज़रूरी है",
    listening: "सुन रहा हूँ…", processing: "आपका जवाब समझ रहा हूँ…",
    speaking: "बोल रहा हूँ… छोड़ने के लिए दबाएँ", error: "कुछ गड़बड़ हुई — आप लिखकर जवाब दे सकते हैं",
  },
  "mr-IN": {
    idle: "तयार", permission_required: "मायक्रोफोनची परवानगी आवश्यक",
    listening: "ऐकत आहे…", processing: "तुमचं उत्तर समजून घेत आहे…",
    speaking: "बोलत आहे… वगळण्यासाठी दाबा", error: "काहीतरी चूक झाली — तुम्ही लिहून उत्तर देऊ शकता",
  },
};

const LANG_NAMES: Record<string, string> = {
  "en-IN": "English",
  "hi-IN": "हिन्दी",
  "mr-IN": "मराठी",
};

interface VoiceAssistantProps {
  onFormReady: (data: Partial<ApplicantIntakeForm>, transcript: string) => void;
}

export const VoiceAssistant: React.FC<VoiceAssistantProps> = ({ onFormReady }) => {
  const [sessionState, setSessionState] = useState<any>(null);
  const [messages, setMessages] = useState<{ role: "assistant" | "user"; text: string; lang?: string }[]>([]);
  const [language, setLanguage] = useState<string>("en-IN");
  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const [handsFree, setHandsFree] = useState(false);
  const [typedInput, setTypedInput] = useState("");
  const [filledSlots, setFilledSlots] = useState<Record<string, any>>({});
  const [isComplete, setIsComplete] = useState(false);
  const [micConsent, setMicConsent] = useState(false);
  const [liveTranscript, setLiveTranscript] = useState("");
  const [liveConfidence, setLiveConfidence] = useState<number | null>(null);
  const [voiceWarning, setVoiceWarning] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const recognitionRef = useRef<any>(null);
  // refs mirror state for closures inside recognition event handlers
  const handsFreeRef = useRef(handsFree);
  const statusRef = useRef(status);
  const languageRef = useRef(language);

  useEffect(() => { handsFreeRef.current = handsFree; }, [handsFree]);
  useEffect(() => { statusRef.current = status; }, [status]);
  useEffect(() => { languageRef.current = language; }, [language]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, liveTranscript, status]);

  /* ---------------------------------------------------------------------- */
  /*  Session initialisation (language-aware)                                 */
  /* ---------------------------------------------------------------------- */
  useEffect(() => {
    let cancelled = false;
    initVoice("en-IN")
      .then((res) => {
        if (cancelled) return;
        setSessionState(res.session_state);
        setMessages([{ role: "assistant", text: res.assistant_message, lang: res.language }]);
      })
      .catch(console.error);
    return () => { cancelled = true; };
  }, []);
  /*  reporting when the device has no matching system voice installed.       */
  /* ---------------------------------------------------------------------- */
  const pickVoice = useCallback((lang: string): SpeechSynthesisVoice | null => {
    if (!("speechSynthesis" in window)) return null;
    const voices = window.speechSynthesis.getVoices();
    if (!voices || voices.length === 0) return null;
    const base = lang.split("-")[0]; // en / hi / mr
    const exact = voices.find((v) => v.lang.replace("_", "-").toLowerCase() === lang.toLowerCase());
    const byBase = voices.find((v) => v.lang.replace("_", "-").toLowerCase().startsWith(base));
    return exact || byBase || null;
  }, []);

  const checkVoiceAvailability = useCallback((lang: string) => {
    if (!("speechSynthesis" in window)) {
      setVoiceWarning("Speech synthesis is not available in this browser; responses are shown as text only.");
      return;
    }
    const loadThenCheck = () => {
      const base = lang.split("-")[0];
      const voices = window.speechSynthesis.getVoices() || [];
      const hasVoice = voices.some(
        (v) => v.lang.replace("_", "-").toLowerCase().startsWith(base)
      );
      if (hasVoice) {
        setVoiceWarning(null);
      } else if (base !== "en") {
        setVoiceWarning(
          LANG_NAMES[lang].startsWith("English")
            ? null
            : `No ${base === "hi" ? "Hindi" : "Marathi"} speech voice is installed on this device. Responses will display correctly, but may be read with the default (English) voice or silently skipped.`
        );
      }
    };
    if (window.speechSynthesis.getVoices().length > 0) loadThenCheck();
    else window.speechSynthesis.onvoiceschanged = loadThenCheck;
  }, []);

  useEffect(() => { checkVoiceAvailability(language); }, [language, checkVoiceAvailability]);

  const speak = useCallback((text: string, lang: string, onDone?: () => void) => {
    if (!ttsEnabled || !("speechSynthesis" in window)) {
      onDone?.();
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const voice = pickVoice(lang);
    if (voice) utterance.voice = voice;
    utterance.lang = lang;
    // Hindi/Marathi financial sentences read better slightly slower with any fallback voice
    utterance.rate = lang === "en-IN" ? 1.0 : 0.92;
    utterance.pitch = 1.0;
    utterance.onstart = () => setStatus("speaking");
    utterance.onend = () => {
      onDone?.();
    };
    utterance.onerror = () => {
      onDone?.();
    };
    window.speechSynthesis.speak(utterance);
  }, [ttsEnabled, pickVoice]);

  const skipSpeaking = () => {
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  };

  /* ---------------------------------------------------------------------- */
  /*  Conversation turn                                                       */
  /* ---------------------------------------------------------------------- */
  const handleTurn = useCallback(async (userText: string, force: boolean = false) => {
    if (!userText || !userText.trim()) {
      if (!force) return;
    }
    setStatus("processing");
    setLiveTranscript("");
    setLiveConfidence(null);
    const turnLanguage = languageRef.current;
    const turnSession = sessionState;
    if (userText && userText.trim()) {
      setMessages((prev) => [...prev, { role: "user", text: userText, lang: turnLanguage }]);
      setTypedInput("");
    }

    try {
      const res = await processVoiceTurn(userText || "", turnSession, turnLanguage);
      setSessionState(res.session_state);
      // Backend language is authoritative for all captured-slot state
      if (res.language && res.language !== turnLanguage) setLanguage(res.language);
      setFilledSlots(res.filled_slots);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: res.assistant_message, lang: res.language },
      ]);

      if (res.is_complete) setIsComplete(true);

      speak(res.assistant_message, res.language || turnLanguage, () => {
        setStatus("idle");
        // Hands-Free: resume listening automatically after TTS finishes
        if (handsFreeRef.current && !res.is_complete) {
          startListeningSafely();
        }
      });
    } catch (err: any) {
      setStatus("error");
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "I encountered an error processing that. Please try typing your answer." },
      ]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionState, speak]);

  /* ---------------------------------------------------------------------- */
  /*  Microphone permission — honest state probe + auto-unlock on allow       */
  /* ---------------------------------------------------------------------- */
  const micPermRef = useRef<{ state: string | null }>({ state: null });

  const probeMicPermission = useCallback(async (): Promise<string | null> => {
    try {
      const q = await (navigator.permissions as any).query({ name: "microphone" });
      micPermRef.current.state = q.state;
      return q.state;
    } catch {
      return null; // Permission API/mic name unsupported — fall back to generic messaging
    }
  }, []);

  /**
   * One handler for every mic-denial path with a PRECISE, actionable message:
   * - Site blocked (Chrome/Edge state "denied")   → address-bar icon instructions
   * - Browser allowed but attempt failed          → Windows privacy / mic-busy hint
   * - State "prompt" (dismissed/auto-suppressed)  → one explicit getUserMedia retry
   * The moment the user flips permission to Allow, the permissions listener
   * auto-clears the warning — no page reload needed.
   */
  const handleMicAccessFailure = useCallback(async (errorName?: string) => {
    setStatus("permission_required");
    if (errorName === "NotReadableError") {
      setVoiceWarning("Your microphone is busy — another app (Zoom, Teams, a recorder) is probably using it. Close that app, then press Try Again.");
      return;
    }
    if (errorName === "NotFoundError" || errorName === "DevicesNotFoundError") {
      setVoiceWarning("No microphone was detected. Connect one (or select it in your browser/system sound settings), then press Try Again.");
      return;
    }
    const state = await probeMicPermission();
    if (state === "denied") {
      setVoiceWarning("Microphone is blocked for this site. Click the lock/sliders icon next to the address bar → Microphone → Allow, then press Try Again. You can keep typing meanwhile.");
      return;
    }
    if (state === "granted") {
      setVoiceWarning("The browser allows the microphone, but the system or another app blocked it. Check Windows Settings → Privacy & Security → Microphone (allow apps), close apps that may use the mic, then press Try Again.");
      return;
    }
    // "prompt" or unknown: ONE explicit prompt attempt. If the user allows,
    // listening resumes immediately without a reload; if they block it, we show
    // the precise site-blocked message.
    try {
      const s = await navigator.mediaDevices.getUserMedia({ audio: true });
      s.getTracks().forEach((t) => t.stop());
      micPermRef.current.state = "granted";
      setVoiceWarning(null);
      setStatus("idle");
    } catch (err: any) {
      setVoiceWarning(
        err?.name === "NotReadableError" ? "Your microphone is busy — another app (Zoom, Teams, a recorder) is probably using it. Close that app, then press Try Again."
        : "Microphone access was blocked. Click the lock/sliders icon next to the address bar → Microphone → Allow, then press Try Again. You can keep typing meanwhile."
      );
    }
  }, [probeMicPermission]);

  // Auto-unlock: when the user flips the site permission to "Allow" (address
  // bar), the app recovers instantly instead of staying stuck until reload.
  useEffect(() => {
    let active = true;
    let handler: (() => void) | null = null;
    let query: any = null;
    (async () => {
      try {
        query = await (navigator.permissions as any).query({ name: "microphone" });
        if (!active || !query) return;
        micPermRef.current.state = query.state;
        handler = () => {
          micPermRef.current.state = query.state;
          if (query.state === "granted") {
            setVoiceWarning(null);
            setStatus((prev) => (prev === "permission_required" ? "idle" : prev));
          }
        };
        query.addEventListener("change", handler);
      } catch { /* unsupported — denial messages above still tell the user exactly what to do */ }
    })();
    return () => {
      active = false;
      try { if (handler && query) query.removeEventListener("change", handler); } catch { /* ignore */ }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ---------------------------------------------------------------------- */
  /*  Speech recognition (Web Speech API + MediaRecorder→whisper fallback)    */
  /* ---------------------------------------------------------------------- */
  const startListeningSafely = useCallback(() => {
    if (!micConsent) {
      setStatus("permission_required");
      return;
    }
    if (statusRef.current === "speaking") skipSpeaking();
    if (statusRef.current === "processing") return;

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      try {
        if (recognitionRef.current) {
          try { recognitionRef.current.abort(); } catch { /* ignore */ }
        }
        const recognition = new SpeechRecognition();
        recognitionRef.current = recognition;
        recognition.lang = languageRef.current;            // selected-language enforcement
        recognition.interimResults = true;
        recognition.continuous = false;                    // one utterance per turn (turn-based mode)
        recognition.maxAlternatives = 1;

        recognition.onstart = () => {
          setStatus("listening");
          setLiveTranscript("");
          setLiveConfidence(null);
        };

        recognition.onresult = (event: any) => {
          let interim = "";
          let final = "";
          let confidence: number | null = null;
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              final += event.results[i][0].transcript;
              confidence = typeof event.results[i][0].confidence === "number"
                ? event.results[i][0].confidence
                : null;
            } else {
              interim += event.results[i][0].transcript;
            }
          }
          if (interim) setLiveTranscript(interim);
          if (final && final.trim()) {
            setLiveConfidence(confidence);
            setStatus("processing");
            recognitionRef.current = null;
            // single submission per final result; no duplicates
            handleTurn(final.trim());
          }
        };

        recognition.onerror = (event: any) => {
          console.warn("SpeechRecognition event:", event.error);
          if (event.error === "not-allowed" || event.error === "service-not-allowed") {
            recognitionRef.current = null;
            handleMicAccessFailure();
            return;
          }
          if (event.error === "no-speech") {
            // benign in hands-free: restart once rather than failing
            if (handsFreeRef.current) {
              startListeningSafely();
              return;
            }
            setStatus("idle");
            setMessages((prev) => [
              ...prev,
              { role: "assistant", text: "I didn't hear any speech. Tap the microphone and try again, or type below." },
            ]);
            return;
          }
          // network / audio-capture / other: honest error + typed fallback
          setStatus("error");
          recognitionRef.current = null;
          if (!handsFreeRef.current) {
            setMessages((prev) => [
              ...prev,
              { role: "assistant", text: "Speech recognition hit a problem. You can still type your answer below." },
            ]);
          }
        };

        recognition.onend = () => {
          if (handsFreeRef.current && statusRef.current === "listening") {
            // recognition ended without a final result (silence): restart quietly
            startListeningSafely();
          } else if (statusRef.current === "listening") {
            setStatus("idle");
          }
        };

        recognition.start();
        return;
      } catch (err) {
        console.warn("SpeechRecognition init error, falling back to MediaRecorder:", err);
      }
    }

    // Fallback path: record and send to local faster-whisper
    startMediaRecorderFallback();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [micConsent, handleTurn, handleMicAccessFailure]);

  const startMediaRecorderFallback = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        stream.getTracks().forEach((track) => track.stop());
        setStatus("processing");
        try {
          // Selected-language enforcement: the transcription hint follows the UI locale
          const sttRes = await transcribeAudioBlob(audioBlob, languageRef.current);
          if (sttRes.text && sttRes.text.trim()) {
            if (sttRes.error) {
              // model unavailable → report honestly
              setMessages((prev) => [
                ...prev,
                { role: "assistant", text: "Local speech model is offline; using your typed input is recommended." },
              ]);
              setStatus("error");
              return;
            }
            setLiveTranscript(sttRes.text);
            await handleTurn(sttRes.text);
          } else {
            setMessages((prev) => [
              ...prev,
              { role: "assistant", text: "I could not hear any speech clearly. You can try speaking again or type your answer below." },
            ]);
            setStatus("idle");
          }
        } catch (e: any) {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", text: "Speech transcription was offline or interrupted. Please type your response below." },
          ]);
          setStatus("error");
        }
      };

      mediaRecorder.start();
      setStatus("listening");
      setLiveTranscript("");
      setVoiceWarning("Using the slower fallback recorder for this turn.");
    } catch (err: any) {
      handleMicAccessFailure(err?.name);
    }
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      try { recognitionRef.current.abort(); } catch { /* ignore */ }
      recognitionRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      try { mediaRecorderRef.current.stop(); } catch { /* ignore */ }
    }
  };

  const handleMicClick = () => {
    if (handsFree && status === "listening") {
      setHandsFree(false);
      handsFreeRef.current = false;
      stopListening();
      setStatus("idle");
      return;
    }
    if (status === "listening") {
      stopListening();
      setStatus("idle");
      return;
    }
    if (!micConsent) {
      setStatus("permission_required");
      return;
    }
    startListeningSafely();
  };

  /* ---------------------------------------------------------------------- */
  /*  Language switching — updates STT locale, TTS voice and response language */
  /*  in one step while keeping every captured value and the conversation.    */
  /* ---------------------------------------------------------------------- */
  const handleLanguageChange = (newLang: string) => {
    if (newLang === languageRef.current) return;
    setLanguage(newLang);
    languageRef.current = newLang;
    // Stop any in-flight listening/speaking on the old locale
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    if (recognitionRef.current) {
      try { recognitionRef.current.abort(); } catch { /* ignore */ }
      recognitionRef.current = null;
    }
  };

  // Language-only switch (runs whenever the dropdown changes): the backend is
  // asked to re-render the current slot question in the new language while it
  // explicitly confirms captured context is preserved (see languages.py).
  useEffect(() => {
    if (sessionState && languageRef.current !== sessionState.language) {
      (async () => {
        try {
          setStatus("processing");
          const res = await processVoiceTurn("", sessionState, languageRef.current);
          setSessionState(res.session_state);
          setFilledSlots(res.filled_slots);
          setMessages((prev) => [...prev, { role: "assistant", text: res.assistant_message, lang: res.language }]);
          speak(res.assistant_message, res.language || languageRef.current, () => {
            setStatus("idle");
            if (handsFreeRef.current) startListeningSafely();
          });
        } catch (e) {
          console.error(e);
          setStatus("error");
        }
      })();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language]);

  const handleApplyToForm = () => {
    const transcriptText = messages.map((m) => `${m.role.toUpperCase()}: ${m.text}`).join("\n");
    onFormReady(filledSlots, transcriptText);
  };

  /* ---------------------------------------------------------------------- */
  /*  Render                                                                  */
  /* ---------------------------------------------------------------------- */
  const statusLabel = STATUS_LABELS[language] || STATUS_LABELS["en-IN"];
  const isRecording = status === "listening";
  const capturedKeys = Object.keys(filledSlots);

  const slotChipLabels: Record<string, Record<string, string>> = {
    applicant_name: { "en-IN": "Name", "hi-IN": "नाम", "mr-IN": "नाव" },
    age: { "en-IN": "Age", "hi-IN": "उम्र", "mr-IN": "वय" },
    employment_type: { "en-IN": "Employment", "hi-IN": "रोज़गार", "mr-IN": "व्यवसाय" },
    employment_duration_months: { "en-IN": "Job tenure", "hi-IN": "नौकरी अवधि", "mr-IN": "नोकरीचा कालावधी" },
    monthly_income: { "en-IN": "Income", "hi-IN": "आमदनी", "mr-IN": "उत्पन्न" },
    existing_emis: { "en-IN": "Existing EMI", "hi-IN": "मौजूदा EMI", "mr-IN": "सध्याचे EMI" },
    requested_amount: { "en-IN": "Loan", "hi-IN": "लोन", "mr-IN": "कर्ज" },
    tenure_months: { "en-IN": "Tenure", "hi-IN": "अवधि", "mr-IN": "मुदत" },
    loan_purpose: { "en-IN": "Purpose", "hi-IN": "उद्देश्य", "mr-IN": "उद्देश" },
    residence_type: { "en-IN": "Residence", "hi-IN": "आवास", "mr-IN": "निवास" },
  };

  // Localised category names for chip values (mirrors backend CATEGORY_LABELS).
  const valueLabels: Record<string, Record<string, string>> = {
    salaried: { "en-IN": "Salaried", "hi-IN": "नौकरी", "mr-IN": "नोकरी" },
    business: { "en-IN": "Business", "hi-IN": "व्यापार", "mr-IN": "व्यवसाय" },
    self_employed: { "en-IN": "Self-Employed", "hi-IN": "स्वयं रोज़गार", "mr-IN": "स्वयंरोजगार" },
    gig_contract: { "en-IN": "Gig / Contract", "hi-IN": "ठेका / गिग", "mr-IN": "कंत्राटी काम" },
    home: { "en-IN": "Home", "hi-IN": "घर", "mr-IN": "घर" },
    education: { "en-IN": "Education", "hi-IN": "पढ़ाई", "mr-IN": "शिक्षण" },
    personal: { "en-IN": "Personal", "hi-IN": "पर्सनल", "mr-IN": "वैयक्तिक" },
    vehicle: { "en-IN": "Vehicle", "hi-IN": "वाहन", "mr-IN": "वाहन" },
    medical: { "en-IN": "Medical", "hi-IN": "इलाज", "mr-IN": "उपचार" },
    owned: { "en-IN": "Owned", "hi-IN": "अपना", "mr-IN": "स्वतःचे" },
    rented: { "en-IN": "Rented", "hi-IN": "किराए का", "mr-IN": "भाड्याने" },
    ancestral: { "en-IN": "Family", "hi-IN": "पारिवारिक", "mr-IN": "कौटुंबिक" },
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-[#E4E8E4] overflow-hidden flex flex-col h-[680px] font-sans">
      {/* Header */}
      <div className="bg-[#0F2231] text-white px-5 py-3.5 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
            status === "error" ? "bg-red-400"
            : status === "listening" ? "bg-emerald-400 animate-pulse"
            : status === "processing" ? "bg-amber-400 animate-pulse"
            : status === "speaking" ? "bg-teal-400 animate-pulse"
            : "bg-emerald-400"
          }`} aria-hidden="true" />
          <div className="min-w-0">
            <h3 className="font-semibold text-sm truncate">FairLend AI Voice Assistant</h3>
            <span className="text-[11px] text-[#8B98A4] tabular">{statusLabel[status] || statusLabel.idle}</span>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Language selector: single control updates STT locale, response language, TTS voice */}
          <div className="flex items-center gap-1.5 bg-[#173247] px-2.5 py-1.5 rounded-lg">
            <Languages size={13} className="text-[#7FD4C8]" aria-hidden="true" />
            <select
              aria-label="Select voice language"
              value={language}
              onChange={(e) => handleLanguageChange(e.target.value)}
              className="bg-transparent text-slate-200 text-xs focus:outline-none cursor-pointer"
            >
              <option value="en-IN" className="bg-white text-slate-900">English</option>
              <option value="hi-IN" className="bg-white text-slate-900 deva">हिन्दी</option>
              <option value="mr-IN" className="bg-white text-slate-900 deva">मराठी</option>
            </select>
          </div>

          <button
            onClick={() => setTtsEnabled(!ttsEnabled)}
            className="p-1.5 hover:bg-[#173247] rounded-lg text-slate-300 transition"
            title={ttsEnabled ? "Mute voice reading" : "Enable voice reading"}
            aria-pressed={ttsEnabled}
          >
            {ttsEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
          </button>
        </div>
      </div>

      {/* Honest device-voice availability notice + one-tap recovery */}
      {voiceWarning && (
        <div className="px-4 py-2 bg-[#FBF3E4] border-b border-[#EAD3A2] text-[11px] text-[#92600C] flex items-start gap-2" role="alert">
          <AlertTriangle size={13} className="mt-0.5 flex-shrink-0" aria-hidden="true" />
          <span className="min-w-0">{voiceWarning}</span>
          <button
            type="button"
            onClick={() => startListeningSafely()}
            className="ml-auto flex-shrink-0 flex items-center gap-1 border border-[#EAD3A2] bg-white/70 hover:bg-white rounded-full px-2.5 py-0.5 font-bold transition"
          >
            <RefreshCw size={11} /> Try Again
          </button>
        </div>
      )}

      {/* DPDP Consent Banner */}
      <div className="bg-[#E3F2EF] px-4 py-2 border-b border-[#C9E5DF] flex items-center justify-between text-xs text-[#0B4A43]">
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={micConsent}
            onChange={(e) => {
              setMicConsent(e.target.checked);
              if (e.target.checked) {
                // Trigger the real browser mic permission immediately (not on
                // the first phrase), so denial is caught early and precisely.
                navigator.mediaDevices.getUserMedia({ audio: true })
                  .then((s) => { s.getTracks().forEach((t) => t.stop()); setVoiceWarning(null); })
                  .catch((err: any) => handleMicAccessFailure(err?.name));
              }
              if (!e.target.checked && status === "listening") {
                stopListening();
                setStatus("idle");
              }
            }}
            className="rounded text-[#0C655C] focus:ring-[#148A7F] w-4 h-4 cursor-pointer"
          />
          <span className="font-medium">
            {language === "hi-IN"
              ? "मैं लोन आवेदन हेतु माइक्रोफ़ोन कैप्चर की सहमति देता/देती हूँ (कोई कच्चा ऑडियो संग्रहीत नहीं; DPDP अधिनियम अनुपालित)।"
              : language === "mr-IN"
                ? "मी कर्ज अर्जासाठी मायक्रोफोन कॅप्चरला संमती देतो/देते (कोणताही कच्चा ऑडिओ साठवला जात नाही; DPDP कायदा अनुपालित)."
                : "I consent to microphone capture for loan intake (Zero raw audio stored; DPDP Act compliant)."}
          </span>
        </label>
        <span className="text-[10px] text-[#0B4A43] bg-white/70 px-2 py-0.5 rounded-full font-semibold flex-shrink-0">
          DPDP 2023
        </span>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 bg-[#F6F7F4]/60 flex flex-col" aria-live="polite">
        <div className="mt-auto space-y-3">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === "assistant" ? "justify-start" : "justify-end"}`}
          >
            <div
              className={`max-w-[85%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                msg.role === "assistant"
                  ? "bg-white text-[#23313C] border border-[#E4E8E4] shadow-sm rounded-tl-sm"
                  : "bg-[#0C655C] text-white shadow-sm rounded-tr-sm"
              }`}
              lang={msg.lang || undefined}
            >
              {msg.text}
            </div>
          </div>
        ))}

        {/* Live Listening Transcript */}
        {liveTranscript && status !== "processing" && (
          <div className="flex justify-end">
            <div className="max-w-[85%] px-4 py-2 rounded-2xl text-sm bg-[#E3F2EF] text-[#0B4A43] border border-[#C9E5DF] italic flex items-center gap-2" lang={language}>
              <Mic size={13} className="text-[#0C655C] animate-pulse flex-shrink-0" aria-hidden="true" />
              <span>"{liveTranscript}"</span>
              {liveConfidence !== null && liveConfidence < 0.45 && (
                <span className="text-[10px] font-semibold text-[#92600C] bg-[#FBF3E4] border border-[#EAD3A2] rounded px-1.5 py-0.5">
                  low confidence — please confirm
                </span>
              )}
            </div>
          </div>
        )}

        {status === "processing" && (
          <div className="flex justify-start">
            <div className="bg-white border border-[#E4E8E4] px-4 py-2 rounded-2xl text-xs text-[#5C6B78] flex items-center gap-2">
              <RefreshCw size={13} className="animate-spin text-[#0C655C]" aria-hidden="true" />
              <span>{statusLabel.processing}</span>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
        </div>
      </div>

      {/* Captured Slot Summary — accessible chips (no emoji, tabular figures) */}
      {capturedKeys.length > 0 && (
        <div className="px-4 py-2.5 bg-[#F0F2EF] border-t border-[#E4E8E4] text-xs flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-[#23313C]">
              {language === "hi-IN" ? "दर्ज मान:" : language === "mr-IN" ? "नोंदवलेली माहिती:" : "Captured values:"}
            </span>
            {capturedKeys.map((key) => {
              const label = (slotChipLabels[key] || {})[language] || key.replace(/_/g, " ");
              let value: string = String(filledSlots[key]);
              if (["monthly_income", "existing_emis", "requested_amount"].includes(key)) {
                value = "₹" + Number(filledSlots[key]).toLocaleString("en-IN");
              } else if (["employment_duration_months", "tenure_months"].includes(key)) {
                const months = Number(filledSlots[key]);
                value = months % 12 === 0 && months >= 12
                  ? `${months / 12} ` + (language === "hi-IN" ? "साल" : language === "mr-IN" ? "वर्षे" : "yrs")
                  : `${months} ` + (language === "hi-IN" ? "महीने" : language === "mr-IN" ? "महिने" : "mo");
              } else if (valueLabels[value]) {
                value = valueLabels[value][language] || valueLabels[value]["en-IN"];
              }
              return (
                <span key={key} className={"bg-white px-2 py-0.5 rounded-md border border-[#E4E8E4] text-[#23313C] " + (key.includes("amount") || key === "monthly_income" ? "font-semibold text-[#0C655C] tabular" : "tabular")}>
                  <span className="text-[#5C6B78] font-medium">{label}:</span> {value}
                </span>
              );
            })}
          </div>

          <button
            onClick={handleApplyToForm}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#0C655C] hover:bg-[#0B5A52] text-white font-semibold rounded-lg text-xs shadow-sm transition"
          >
            <CheckCircle size={13} aria-hidden="true" />
            {isComplete
              ? (language === "hi-IN" ? "आवेदन समीक्षा करें" : language === "mr-IN" ? "अर्ज तपासा" : "Review Application")
              : (language === "hi-IN" ? "फॉर्म में संपादित करें" : language === "mr-IN" ? "फॉर्ममध्ये संपादा" : "Edit in Typed Form")}
          </button>
        </div>
      )}

      {/* Input Controls */}
      <div className="p-3.5 bg-white border-t border-[#E4E8E4] space-y-2">
        <div className="flex items-center gap-2">
          {/* Microphone capture button */}
          <button
            onClick={handleMicClick}
            disabled={status === "processing"}
            className={`p-3 rounded-full flex items-center justify-center transition shadow flex-shrink-0 ${
              isRecording
                ? "bg-[#B23A3A] text-white animate-pulse ring-4 ring-red-100"
                : handsFree
                  ? "bg-[#148A7F] hover:bg-[#0E766B] text-white"
                  : "bg-[#0C655C] hover:bg-[#0B5A52] text-white"
            } disabled:opacity-50`}
            title={isRecording ? (handsFree ? "Hands-Free is on — tap to stop" : "Tap to stop") : "Tap to speak your answer"}
            aria-label={isRecording ? "Stop microphone" : "Start microphone"}
          >
            {isRecording ? <MicOff size={20} /> : <Mic size={20} />}
          </button>

          {/* Hands-Free toggle (continuous conversation mode) */}
          <button
            onClick={() => {
              const next = !handsFree;
              setHandsFree(next);
              handsFreeRef.current = next;
              if (!next && isRecording) {
                stopListening();
                setStatus("idle");
              } else if (next && micConsent && status === "idle") {
                startListeningSafely();
              }
            }}
            className={`flex flex-col items-center justify-center px-3 py-1.5 rounded-xl border text-[10px] font-semibold transition flex-shrink-0 ${
              handsFree
                ? "bg-[#E3F2EF] border-[#0C655C] text-[#0C655C]"
                : "border-[#E4E8E4] text-[#5C6B78] hover:bg-[#F6F7F4]"
            }`}
            title="Hands-Free mode: continuous listening with automatic turn-taking after each spoken answer"
            aria-pressed={handsFree}
          >
            <InfinityIcon size={15} aria-hidden="true" />
            <span>{language === "hi-IN" ? "हैंड्स-फ्री" : language === "mr-IN" ? "हॅन्ड्स-फ्री" : "Hands-Free"}</span>
          </button>

          {/* Fallback typed input field */}
          <input
            type="text"
            value={typedInput}
            onChange={(e) => setTypedInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleTurn(typedInput)}
            placeholder={
              status === "listening"
                ? (language === "hi-IN" ? "सुन रहा हूँ… अब बोलिए…" : language === "mr-IN" ? "ऐकत आहे… आता बोला…" : "Listening… speak your answer now…")
                : language === "hi-IN"
                  ? "माइक दबाकर बोलें, या यहाँ लिखें (जैसे 'साठ हजार', 'पाँच लाख')…"
                  : language === "mr-IN"
                    ? "माइक दाबून बोला, किंवा येथे लिहा (उदा. 'साठ हजार', 'पाच लाख')…"
                    : "Speak by clicking the mic, or type here (e.g. '5 lakh', 'साठ हजार', '₹45,382')…"
            }
            disabled={isRecording || status === "processing"}
            className="flex-1 border border-[#E4E8E4] rounded-xl px-4 py-2.5 text-sm font-sans focus:outline-none focus:ring-2 focus:ring-[#148A7F] disabled:bg-[#F6F7F4] min-w-0"
            lang={language.startsWith("en") ? undefined : language}
          />

          <button
            onClick={() => handleTurn(typedInput)}
            disabled={!typedInput.trim() || status === "processing"}
            className="p-2.5 bg-[#0F2231] hover:bg-[#173247] text-white rounded-xl transition disabled:opacity-40 flex-shrink-0"
            aria-label="Send answer"
          >
            <Send size={18} />
          </button>
        </div>

        <div className="text-[11px] text-[#8B98A4] text-center flex items-center justify-center gap-2.5 flex-wrap">
          <span>
            {language === "hi-IN" ? "स्वाभाविक हिन्दी में बोला जा सकता है — 'साठ हजार', 'पाँच लाख'।"
            : language === "mr-IN" ? "मराठीत स्वाभाविक बोला — 'साठ हजार', 'पाच लाख'।"
            : "Accepts natural speech: " }
          </span>
          <span className="deva">{language === "en-IN" ? "\"5 lakh\", \"45 thousand\", \"45k\", \"₹45,382\"" : ""}</span>
          <span className="text-[#0C655C] font-medium">
            {language === "hi-IN" ? "हर मान बोलकर पुष्टि किया जाता है" : language === "mr-IN" ? "प्रत्येक मूल्य तोंडाने तपासलं जातं" : "Always confirmed verbally before saving"}
          </span>
        </div>
      </div>
    </div>
  );
};

// internal helper ref type declared late to avoid cycles
declare global { interface Window { webkitSpeechRecognition?: any; SpeechRecognition?: any } }
