from typing import Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
from backend.services.voice.stt import transcribe_audio_bytes
from backend.services.voice.languages import SLOT_QUESTIONS, SLOT_FLOW
from backend.services.voice.intent import normalise_language, WHISPER_LANGUAGE_CODES
from backend.services.voice.slot_filler import SlotFillingSession

router = APIRouter(prefix="/voice", tags=["Voice Assistant"])


class InitRequest(BaseModel):
    language: Optional[str] = None


class TurnRequest(BaseModel):
    user_utterance: str
    session_state: Optional[Dict[str, Any]] = None
    language: Optional[str] = None


class TurnResponse(BaseModel):
    assistant_message: str
    is_complete: bool
    session_state: Dict[str, Any]
    filled_slots: Dict[str, Any]
    language: str


@router.post("/init")
def initialize_voice_session(req: Optional[InitRequest] = None):
    """Starts a new conversational slot-filling session in the requested language."""
    language = normalise_language(req.language if req else None)
    session = SlotFillingSession()
    session.language = language
    initial_prompt = SLOT_QUESTIONS[language][SLOT_FLOW[0]]
    session.transcript.append({"role": "assistant", "text": initial_prompt})
    return {
        "assistant_message": initial_prompt,
        "is_complete": False,
        "language": language,
        "session_state": session.to_dict(),
        "filled_slots": {},
    }


@router.post("/turn", response_model=TurnResponse)
def handle_conversation_turn(req: TurnRequest):
    """
    Processes a user utterance (from speech or typed input) in the slot-filling flow.
    `language` is optional; when provided it switches the response language while
    preserving every already-captured slot and the conversation context.
    """
    session = SlotFillingSession(req.session_state)
    assistant_msg, is_complete = session.process_turn(req.user_utterance, req.language)
    return TurnResponse(
        assistant_message=assistant_msg,
        is_complete=is_complete,
        session_state=session.to_dict(),
        filled_slots=session.filled_slots,
        language=session.language,
    )


@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...), language: Optional[str] = Form(None)):
    """
    Transcribes browser microphone audio using local faster-whisper.
    `language` (en-IN / hi-IN / mr-IN) is applied as a recognition hint
    (selected-language enforcement); empty falls back to auto-detection.
    """
    contents = await audio.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty audio recording.")
    lang_code = WHISPER_LANGUAGE_CODES.get(normalise_language(language)) if language else None
    result = transcribe_audio_bytes(contents, filename=audio.filename or "recording.wav", language_hint=lang_code)
    return result
