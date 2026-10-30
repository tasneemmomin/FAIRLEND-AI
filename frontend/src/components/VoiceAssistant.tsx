import React, { useState, useEffect, useRef } from "react";
import { Mic, MicOff, Send, Volume2, VolumeX, CheckCircle, RefreshCw, Languages, Radio } from "lucide-react";
import { initVoice, processVoiceTurn, transcribeAudioBlob } from "../api";
import { ApplicantIntakeForm } from "../types";

interface VoiceAssistantProps {
  onFormReady: (data: Partial<ApplicantIntakeForm>, transcript: string) => void;
}

export const VoiceAssistant: React.FC<VoiceAssistantProps> = ({ onFormReady }) => {
  const [sessionState, setSessionState] = useState<any>(null);
  const [messages, setMessages] = useState<{ role: "assistant" | "user"; text: string }[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const [typedInput, setTypedInput] = useState("");
  const [filledSlots, setFilledSlots] = useState<Record<string, any>>({});
  const [isComplete, setIsComplete] = useState(false);
  const [micConsent, setMicConsent] = useState(false);
  const [speechLanguage, setSpeechLanguage] = useState<"en-IN" | "hi-IN" | "mr-IN">("en-IN");
  const [liveTranscript, setLiveTranscript] = useState<string>("");

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const recognitionRef = useRef<any>(null);

  // Initialize voice session on mount
  useEffect(() => {
    initVoice().then((res) => {
      setSessionState(res.session_state);
      setMessages([{ role: "assistant", text: res.assistant_message }]);
      speak(res.assistant_message);
    }).catch(console.error);
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, liveTranscript]);

  const speak = (text: string) => {
    if (!ttsEnabled || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.lang = speechLanguage;
    window.speechSynthesis.speak(utterance);
  };

  const handleTurn = async (userText: string) => {
    if (!userText.trim()) return;
    setIsProcessing(true);
    setLiveTranscript("");
    setMessages((prev) => [...prev, { role: "user", text: userText }]);
    setTypedInput("");

    try {
      const res = await processVoiceTurn(userText, sessionState);
      setSessionState(res.session_state);
      setFilledSlots(res.filled_slots);
      setMessages((prev) => [...prev, { role: "assistant", text: res.assistant_message }]);
      speak(res.assistant_message);

      if (res.is_complete) {
        setIsComplete(true);
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "I encountered an error processing that. Please try typing your answer." }
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  const startListening = async () => {
    if (!micConsent) {
      alert("Please check the microphone consent box before enabling audio capture.");
      return;
    }

    // Check if Web Speech API is supported (Chrome, Edge, Android, Safari)
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      try {
        if (recognitionRef.current) {
          recognitionRef.current.abort();
        }
        const recognition = new SpeechRecognition();
        recognitionRef.current = recognition;
        recognition.lang = speechLanguage;
        recognition.interimResults = true;
        recognition.continuous = false;
        recognition.maxAlternatives = 1;

        recognition.onstart = () => {
          setIsRecording(true);
          setLiveTranscript("Listening to your voice...");
        };

        recognition.onresult = (event: any) => {
          let interim = "";
          let final = "";
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              final += event.results[i][0].transcript;
            } else {
              interim += event.results[i][0].transcript;
            }
          }
          if (interim) {
            setLiveTranscript(interim);
          }
          if (final && final.trim()) {
            setIsRecording(false);
            setLiveTranscript("");
            handleTurn(final.trim());
          }
        };

        recognition.onerror = (event: any) => {
          console.warn("Web Speech API event:", event.error);
          setIsRecording(false);
          setLiveTranscript("");
          // Fall back to MediaRecorder
          startMediaRecorderFallback();
        };

        recognition.onend = () => {
          setIsRecording(false);
          setLiveTranscript("");
        };

        recognition.start();
        return;
      } catch (err) {
        console.warn("SpeechRecognition init error, falling back to MediaRecorder:", err);
      }
    }

    // Fallback: Use MediaRecorder + Backend faster-whisper
    startMediaRecorderFallback();
  };

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
        setIsProcessing(true);
        try {
          const sttRes = await transcribeAudioBlob(audioBlob);
          if (sttRes.text && sttRes.text.trim()) {
            await handleTurn(sttRes.text);
          } else {
            setMessages((prev) => [
              ...prev,
              { role: "assistant", text: "I could not hear any speech clearly. You can try speaking again or type your answer below." }
            ]);
          }
        } catch (e: any) {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", text: "Speech transcription was offline or interrupted. Please type your response below." }
          ]);
        } finally {
          setIsProcessing(false);
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
      setLiveTranscript("Recording audio (fallback mode)...");
    } catch (err) {
      alert("Microphone access was denied or is not supported. Please use the typed input box below.");
    }
  };

  const stopListening = () => {
    if (recognitionRef.current && isRecording) {
      try {
        recognitionRef.current.stop();
      } catch (e) {
        // ignore
      }
    }
    if (mediaRecorderRef.current && isRecording) {
      try {
        mediaRecorderRef.current.stop();
      } catch (e) {
        // ignore
      }
    }
    setIsRecording(false);
    setLiveTranscript("");
  };

  const handleApplyToForm = () => {
    const transcriptText = messages.map((m) => `${m.role.toUpperCase()}: ${m.text}`).join("\n");
    onFormReady(filledSlots, transcriptText);
  };

  return (
    <div className="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden flex flex-col h-[640px]">
      {/* Header */}
      <div className="bg-slate-900 text-white px-5 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-3 h-3 rounded-full bg-emerald-400 animate-pulse" />
          <div>
            <h3 className="font-semibold text-sm">FairLendAI Voice Assistant</h3>
            <span className="text-[10px] text-slate-400">Conversational Slot Filling • Real-Time Voice</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Language Selector */}
          <div className="flex items-center gap-1 bg-slate-800 px-2 py-1 rounded-lg text-xs">
            <Languages size={13} className="text-teal-400" />
            <select
              value={speechLanguage}
              onChange={(e) => setSpeechLanguage(e.target.value as any)}
              className="bg-transparent text-slate-200 text-xs focus:outline-none"
            >
              <option value="en-IN" className="bg-slate-800 text-white">English (India)</option>
              <option value="hi-IN" className="bg-slate-800 text-white">Hindi (हिन्दी)</option>
              <option value="mr-IN" className="bg-slate-800 text-white">Marathi (मराठी)</option>
            </select>
          </div>

          <button
            onClick={() => setTtsEnabled(!ttsEnabled)}
            className="p-1.5 hover:bg-slate-800 rounded-lg text-slate-300 transition"
            title={ttsEnabled ? "Mute Voice Reading" : "Enable Voice Reading"}
          >
            {ttsEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
          </button>
        </div>
      </div>

      {/* DPDP Consent Banner */}
      <div className="bg-teal-50 px-4 py-2 border-b border-teal-100 flex items-center justify-between text-xs text-teal-900">
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={micConsent}
            onChange={(e) => setMicConsent(e.target.checked)}
            className="rounded text-teal-600 focus:ring-teal-500 w-4 h-4 cursor-pointer"
          />
          <span className="font-medium">
            I consent to microphone capture for loan intake (Zero raw audio stored; DPDP Act compliant).
          </span>
        </label>
        <span className="text-[10px] text-teal-700 bg-teal-100 px-2 py-0.5 rounded-full font-semibold">
          DPDP 2023
        </span>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-50/50">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === "assistant" ? "justify-start" : "justify-end"}`}
          >
            <div
              className={`max-w-[82%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                msg.role === "assistant"
                  ? "bg-white text-slate-800 border border-slate-200 shadow-sm rounded-tl-sm"
                  : "bg-teal-600 text-white shadow-sm rounded-tr-sm"
              }`}
            >
              {msg.text}
            </div>
          </div>
        ))}

        {/* Live Listening Transcript */}
        {liveTranscript && (
          <div className="flex justify-end">
            <div className="max-w-[82%] px-4 py-2 rounded-2xl text-sm bg-teal-500/20 text-teal-900 border border-teal-300 animate-pulse italic flex items-center gap-2">
              <Radio size={14} className="text-teal-600 animate-spin" />
              <span>"{liveTranscript}"</span>
            </div>
          </div>
        )}

        {isProcessing && (
          <div className="flex justify-start">
            <div className="bg-white border border-slate-200 px-4 py-2 rounded-2xl text-xs text-slate-500 flex items-center gap-2">
              <RefreshCw size={14} className="animate-spin text-teal-600" />
              <span>Understanding your response...</span>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Captured Slot Summary Card */}
      {Object.keys(filledSlots).length > 0 && (
        <div className="px-4 py-2.5 bg-slate-100/90 border-t border-slate-200 text-xs flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-slate-700">Captured Values:</span>
            {filledSlots.applicant_name && (
              <span className="bg-white px-2 py-0.5 rounded border border-slate-300 text-slate-800">
                👤 {filledSlots.applicant_name}
              </span>
            )}
            {filledSlots.monthly_income && (
              <span className="bg-white px-2 py-0.5 rounded border border-slate-300 text-slate-800 font-semibold text-teal-700">
                💰 ₹{Number(filledSlots.monthly_income).toLocaleString("en-IN")}
              </span>
            )}
            {filledSlots.requested_amount && (
              <span className="bg-white px-2 py-0.5 rounded border border-slate-300 text-slate-800 font-semibold text-teal-700">
                🏷️ ₹{Number(filledSlots.requested_amount).toLocaleString("en-IN")}
              </span>
            )}
            {filledSlots.tenure_months && (
              <span className="bg-white px-2 py-0.5 rounded border border-slate-300 text-slate-800">
                ⏱️ {filledSlots.tenure_months} Mo
              </span>
            )}
          </div>

          <button
            onClick={handleApplyToForm}
            className="flex items-center gap-1.5 px-3 py-1 bg-teal-600 hover:bg-teal-700 text-white font-semibold rounded-lg text-xs shadow-sm transition"
          >
            <CheckCircle size={13} />
            {isComplete ? "Review Application" : "Edit in Typed Form"}
          </button>
        </div>
      )}

      {/* Input Controls */}
      <div className="p-3.5 bg-white border-t border-slate-200 space-y-2">
        <div className="flex items-center gap-2">
          {/* Microphone capture button */}
          <button
            onClick={isRecording ? stopListening : startListening}
            disabled={isProcessing}
            className={`p-3 rounded-full flex items-center justify-center transition shadow ${
              isRecording
                ? "bg-rose-600 text-white animate-pulse ring-4 ring-rose-200"
                : "bg-teal-600 hover:bg-teal-700 text-white"
            } disabled:opacity-50`}
            title={isRecording ? "Click to stop listening" : "Click to speak your response"}
          >
            {isRecording ? <MicOff size={20} /> : <Mic size={20} />}
          </button>

          {/* Fallback typed input field */}
          <input
            type="text"
            value={typedInput}
            onChange={(e) => setTypedInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleTurn(typedInput)}
            placeholder={
              isRecording
                ? "Listening... Speak your answer now..."
                : "Speak by clicking the mic or type here (e.g., '5 lakh', '45 thousand')..."
            }
            disabled={isRecording || isProcessing}
            className="flex-1 border border-slate-300 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:bg-slate-100"
          />

          <button
            onClick={() => handleTurn(typedInput)}
            disabled={!typedInput.trim() || isProcessing}
            className="p-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl transition disabled:opacity-40"
          >
            <Send size={18} />
          </button>
        </div>

        <div className="text-[11px] text-slate-400 text-center flex items-center justify-center gap-3">
          <span>💡 Accepts natural speech in Lakhs & Thousands (e.g. <em>"5 lakh"</em>, <em>"50 thousand"</em>, <em>"45k"</em>)</span>
          <span>•</span>
          <span className="text-teal-700 font-medium">Always confirmed verbally before saving</span>
        </div>
      </div>
    </div>
  );
};
