"""
Conversational slot-filling session with full English / Hindi / Marathi support.
Language is carried in the persisted session state, so a mid-conversation switch
updates prompts, spoken confirmations and TTS locales WITHOUT losing captured slots.
"""
from typing import Dict, Any, Tuple, Optional
from backend.services.voice.intent import (
    parse_spoken_currency_or_number,
    parse_duration_months,
    parse_confirmation_intent,
    parse_categorical_slot,
    normalise_language,
    SUPPORTED_LANGUAGES,
    format_inr,
)
from backend.services.voice.languages import SLOT_FLOW, SLOT_QUESTIONS, MESSAGES

# Spoken labels for categorical slot values, per conversation language.
CATEGORY_LABELS = {
    "salaried":       {"en-IN": "Salaried",      "hi-IN": "नौकरी",         "mr-IN": "नोकरी"},
    "business":       {"en-IN": "Business",      "hi-IN": "व्यापार",       "mr-IN": "व्यवसाय"},
    "self_employed":  {"en-IN": "Self-Employed", "hi-IN": "स्वयं रोज़गार",  "mr-IN": "स्वयंरोजगार"},
    "gig_contract":   {"en-IN": "Gig / Contract","hi-IN": "ठेका / गिग",     "mr-IN": "कंत्राटी काम"},
    "home":           {"en-IN": "Home",          "hi-IN": "घर",            "mr-IN": "घर"},
    "education":      {"en-IN": "Education",     "hi-IN": "पढ़ाई",          "mr-IN": "शिक्षण"},
    "personal":       {"en-IN": "Personal",      "hi-IN": "पर्सनल",         "mr-IN": "वैयक्तिक"},
    "vehicle":        {"en-IN": "Vehicle",       "hi-IN": "वाहन",          "mr-IN": "वाहन"},
    "medical":        {"en-IN": "Medical",       "hi-IN": "इलाज",          "mr-IN": "उपचार"},
    "owned":          {"en-IN": "Owned",         "hi-IN": "अपना",          "mr-IN": "स्वतःचे"},
    "rented":         {"en-IN": "Rented",        "hi-IN": "किराए का",      "mr-IN": "भाड्याने"},
    "ancestral":      {"en-IN": "Family",        "hi-IN": "पारिवारिक",     "mr-IN": "कौटुंबिक"},
}


class SlotFillingSession:
    def __init__(self, session_data: Optional[Dict[str, Any]] = None):
        data = session_data or {}
        self.current_slot_idx: int = data.get("current_slot_idx", 0)
        self.awaiting_confirmation: bool = data.get("awaiting_confirmation", False)
        self.pending_value: Any = data.get("pending_value", None)
        self.filled_slots: Dict[str, Any] = data.get("filled_slots", {})
        self.transcript: list = data.get("transcript", [])
        self.is_complete: bool = data.get("is_complete", False)
        self.language: str = normalise_language(data.get("language"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_slot_idx": self.current_slot_idx,
            "awaiting_confirmation": self.awaiting_confirmation,
            "pending_value": self.pending_value,
            "filled_slots": self.filled_slots,
            "transcript": self.transcript,
            "is_complete": self.is_complete,
            "language": self.language,
        }

    # ------------------------------------------------------------------
    def _t(self, key: str, **kw) -> str:
        lang = self.language if self.language in SLOT_QUESTIONS else "en-IN"
        return MESSAGES[lang][key].format(**kw)

    def _question(self, slot: str) -> str:
        lang = self.language if self.language in SLOT_QUESTIONS else "en-IN"
        return SLOT_QUESTIONS[lang][slot]

    def process_turn(self, user_utterance: str, language: Optional[str] = None) -> Tuple[str, bool]:
        """
        Advances the conversation turn based on applicant speech/input.
        Returns: (assistant_response_text, is_intake_complete)
        """
        switch_announcement = ""
        if language:
            new_lang = normalise_language(language)
            if new_lang != self.language:
                self.language = new_lang
                # Confirm the switch explicitly — and never lose captured context
                switch_announcement = self._t("language_switched", language=self._lang_display_name())

        self.transcript.append({"role": "user", "text": user_utterance})

        if self.is_complete:
            msg = switch_announcement + self._t("already_complete")
            self.transcript.append({"role": "assistant", "text": msg})
            return msg, True

        current_slot = SLOT_FLOW[self.current_slot_idx]

        # 0. Pure language switch (no speech/typed input): re-ask the current
        #    slot — or re-confirm the pending value — in the new language without
        #    the "I didn't catch that" noise, since nothing was actually missed.
        if not user_utterance.strip():
            if self.awaiting_confirmation and self.pending_value is not None:
                msg = switch_announcement + self._t(
                    "confirm_value",
                    value=self._format_value_for_speech(current_slot, self.pending_value),
                )
            else:
                msg = switch_announcement + self._question(current_slot)
            self.transcript.append({"role": "assistant", "text": msg})
            return msg, False

        # 1. If currently awaiting confirmation of a captured value
        if self.awaiting_confirmation:
            confirmed = parse_confirmation_intent(user_utterance)
            if confirmed is True:
                # Value accepted! Store and advance
                self.filled_slots[current_slot] = self.pending_value
                self.awaiting_confirmation = False
                self.pending_value = None
                self.current_slot_idx += 1

                if self.current_slot_idx >= len(SLOT_FLOW):
                    self.is_complete = True
                    msg = (switch_announcement or "") + self._t("complete")
                    self.transcript.append({"role": "assistant", "text": msg})
                    return msg, True

                next_slot = SLOT_FLOW[self.current_slot_idx]
                next_q = (switch_announcement or "") + self._question(next_slot)
                self.transcript.append({"role": "assistant", "text": next_q})
                return next_q, False

            elif confirmed is False:
                # Value rejected by user
                self.awaiting_confirmation = False
                self.pending_value = None
                repeat_q = self._t("retry") + self._question(current_slot)
                if switch_announcement and switch_announcement not in repeat_q:
                    repeat_q = switch_announcement + repeat_q
                self.transcript.append({"role": "assistant", "text": repeat_q})
                return repeat_q, False
            else:
                # Unclear answer, re-prompt confirmation
                clarify = self._t("confirm_clarify",
                                  value=self._format_value_for_speech(current_slot, self.pending_value))
                if switch_announcement:
                    clarify = switch_announcement + clarify
                self.transcript.append({"role": "assistant", "text": clarify})
                return clarify, False

        # 2. Extract value for current slot
        extracted_val = self._extract_slot_value(current_slot, user_utterance)
        if extracted_val is not None:
            self.pending_value = extracted_val
            self.awaiting_confirmation = True
            speech_val = self._format_value_for_speech(current_slot, extracted_val)
            confirm_q = self._t("confirm_value", value=speech_val)
            if switch_announcement:
                confirm_q = switch_announcement + confirm_q
            self.transcript.append({"role": "assistant", "text": confirm_q})
            return confirm_q, False
        else:
            # Could not parse slot value — never guess silently
            retry_q = self._t("not_understood") + self._question(current_slot)
            if switch_announcement and switch_announcement not in retry_q:
                retry_q = switch_announcement + retry_q
            self.transcript.append({"role": "assistant", "text": retry_q})
            return retry_q, False

    # ------------------------------------------------------------------
    def _lang_display_name(self) -> str:
        return {"en-IN": "English", "hi-IN": "हिन्दी", "mr-IN": "मराठी"}.get(self.language, "English")

    def _extract_slot_value(self, slot: str, text: str) -> Any:
        if slot == "applicant_name":
            raw = text.strip()
            # Strip multilingual greetings / polite prefixes
            lowered = raw.lower()
            for prefix in ["my name is", "i am", "this is", "name is", "myself",
                           "mera naam", "mera naam hai", "mara naam", "majhe naav", "majha naav",
                           "मेरा नाम", "मेरा नाम है", "माझं नाव", "माझे नाव", "मी"]:
                if lowered.startswith(prefix.lower()):
                    raw = raw[len(prefix):].strip()
            cleaned = raw.strip(" ,।.?!")
            # Strip sentence-final copulas ("राहुल शर्मा है" / "मोहिनी देशमुख आहे")
            lowered_clean = cleaned.lower()
            for suffix in [" आहे", " है", " hai", " ahe", " aahe", " ji", " जी"]:
                if lowered_clean.endswith(suffix):
                    cleaned = cleaned[: len(cleaned) - len(suffix)].strip()
            cleaned = cleaned.strip(" ,।.?!")
            return cleaned.title() if len(cleaned) >= 2 else None

        elif slot == "age":
            num = parse_spoken_currency_or_number(text)
            if num is not None and 18 <= int(num) <= 100:
                return int(num)
            return None

        elif slot in ("monthly_income", "existing_emis", "requested_amount"):
            num = parse_spoken_currency_or_number(text)
            return float(num) if num is not None else None

        elif slot in ("employment_duration_months", "tenure_months"):
            return parse_duration_months(text)

        elif slot in ("employment_type", "loan_purpose", "residence_type"):
            return parse_categorical_slot(slot, text)

        return None

    def _format_value_for_speech(self, slot: str, val: Any) -> str:
        """Speak-back rendering, localised per active language."""
        lang = self.language if self.language in SLOT_QUESTIONS else "en-IN"
        if slot in ("monthly_income", "existing_emis", "requested_amount"):
            amount = format_inr(float(val))
            return {
                "en-IN": f"₹{amount} rupees",
                "hi-IN": f"₹{amount} रुपये",
                "mr-IN": f"₹{amount} रुपये",
            }[lang]
        elif slot in ("employment_duration_months", "tenure_months"):
            months = int(val)
            if months % 12 == 0 and months >= 12:
                years = months // 12
                return {
                    "en-IN": f"{years} year" + ("s" if years != 1 else ""),
                    "hi-IN": f"{years} साल",
                    "mr-IN": f"{years} वर्ष" + ("े" if years != 1 else ""),
                }[lang]
            return {
                "en-IN": f"{months} months",
                "hi-IN": f"{months} महीने",
                "mr-IN": f"{months} महिने",
            }[lang]
        elif slot == "age":
            return {
                "en-IN": f"{int(val)} years old",
                "hi-IN": f"{int(val)} साल",
                "mr-IN": f"{int(val)} वर्षे",
            }[lang]
        elif slot in ("employment_type", "loan_purpose", "residence_type"):
            # Speak the category in the conversation language — never echo the
            # internal English enum value ("salaried") inside a Hindi sentence.
            labels = CATEGORY_LABELS.get(str(val), {})
            return labels.get(lang) or labels.get("en-IN") or str(val).replace("_", " ")
        return str(val)
