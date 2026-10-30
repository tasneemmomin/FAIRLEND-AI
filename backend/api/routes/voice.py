from typing import Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from backend.services.voice.stt import transcribe_audio_bytes
from backend.services.voice.slot_filler import SlotFillingSession, SLOT_QUESTIONS, SLOT_FLOW

router = APIRouter(prefix="/voice", tags=["Voice Assistant"])

class TurnRequest(BaseModel):
    user_utterance: str
    session_state: Optional[Dict[str, Any]] = None

class TurnResponse(BaseModel):
    assistant_message: str
    is_complete: bool
    session_state: Dict[str, Any]
    filled_slots: Dict[str, Any]

@router.post("/init")
def initialize_voice_session():
    """Starts a new conversational slot-filling session."""
    session = SlotFillingSession()
    initial_prompt = SLOT_QUESTIONS[SLOT_FLOW[0]]
    session.transcript.append({"role": "assistant", "text": initial_prompt})
    return {
        "assistant_message": initial_prompt,
        "is_complete": False,
        "session_state": session.to_dict(),
        "filled_slots": {}
    }

@router.post("/turn", response_model=TurnResponse)
def handle_conversation_turn(req: TurnRequest):
    """Processes a user utterance (from speech or typed input) in the slot-filling flow."""
    session = SlotFillingSession(req.session_state)
    assistant_msg, is_complete = session.process_turn(req.user_utterance)
    return TurnResponse(
        assistant_message=assistant_msg,
        is_complete=is_complete,
        session_state=session.to_dict(),
        filled_slots=session.filled_slots
    )

@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """Transcribes browser microphone audio recording using local faster-whisper."""
    contents = await audio.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty audio recording.")
    result = transcribe_audio_bytes(contents, filename=audio.filename or "recording.wav")
    return result
