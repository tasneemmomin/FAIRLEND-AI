import io
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from backend.core.config import settings

_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            settings.MODEL_DIR.mkdir(parents=True, exist_ok=True)
            _whisper_model = WhisperModel(
                settings.WHISPER_MODEL_SIZE,
                device=settings.WHISPER_DEVICE,
                compute_type=settings.WHISPER_COMPUTE_TYPE,
                download_root=str(settings.MODEL_DIR)
            )
        except Exception as e:
            # Fallback when faster-whisper runtime is unavailable
            _whisper_model = False
    return _whisper_model

def transcribe_audio_bytes(audio_bytes: bytes, filename: str = "audio.wav", language_hint: Optional[str] = None) -> Dict[str, Any]:
    """Transcribes audio bytes locally using faster-whisper.

    `language_hint` is an ISO-639-1 code (en/hi/mr). When provided, the model is
    forced to that language (selected-language enforcement); when None it
    auto-detects. Reported `language` in the response always reflects what the
    model actually used, so the UI can surface any mismatch honestly."""
    model = get_whisper_model()
    if not model:
        return {
            "text": "",
            "language": language_hint or "en",
            "confidence": 0.0,
            "error": "Local speech recognition model not initialized. Please use typed input fallback."
        }

    # Save to temp file for faster-whisper ingestion
    suffix = Path(filename).suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        segments, info = model.transcribe(
            tmp_path,
            beam_size=3,
            language=language_hint,  # explicit selection when enforced, auto-detect otherwise
            task="transcribe"
        )
        full_text = " ".join([segment.text.strip() for segment in segments]).strip()

        # Configurable retention: delete raw audio immediately by default
        if not settings.STORE_RAW_AUDIO:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

        return {
            "text": full_text,
            "language": info.language,
            "confidence": round(info.language_probability, 2)
        }
    except Exception as e:
        if not settings.STORE_RAW_AUDIO and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return {
            "text": "",
            "language": "en",
            "confidence": 0.0,
            "error": str(e)
        }
