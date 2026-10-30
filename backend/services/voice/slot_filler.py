from typing import Dict, Any, Tuple, Optional
from backend.services.voice.intent import (
    parse_spoken_currency_or_number,
    parse_duration_months,
    parse_confirmation_intent,
    parse_categorical_slot
)

SLOT_FLOW = [
    "applicant_name",
    "age",
    "employment_type",
    "employment_duration_months",
    "monthly_income",
    "existing_emis",
    "requested_amount",
    "tenure_months",
    "loan_purpose",
    "residence_type"
]

SLOT_QUESTIONS = {
    "applicant_name": "Hello! I am your LoanLens voice assistant. May I please have your full name?",
    "age": "Thank you! What is your age in years?",
    "employment_type": "What is your primary employment type? For example: Salaried, Self-Employed, or Business?",
    "employment_duration_months": "How long have you been in your current job or business? For example: 2 years or 24 months.",
    "monthly_income": "What is your average monthly take-home income?",
    "existing_emis": "Do you have any existing monthly loan payments or EMIs? If yes, how much per month? If none, say zero.",
    "requested_amount": "How much loan amount are you applying to borrow?",
    "tenure_months": "Over how many months or years would you like to repay this loan?",
    "loan_purpose": "What is the purpose of this loan? For example: Home, Education, Personal, Business, or Vehicle?",
    "residence_type": "Do you live in an Owned home, Rented accommodation, or Family residence?"
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_slot_idx": self.current_slot_idx,
            "awaiting_confirmation": self.awaiting_confirmation,
            "pending_value": self.pending_value,
            "filled_slots": self.filled_slots,
            "transcript": self.transcript,
            "is_complete": self.is_complete
        }

    def process_turn(self, user_utterance: str) -> Tuple[str, bool]:
        """
        Advances the conversation turn based on applicant speech/input.
        Returns: (assistant_response_text, is_intake_complete)
        """
        self.transcript.append({"role": "user", "text": user_utterance})

        if self.is_complete:
            msg = "Your application is complete. Please verify your details on screen and click submit."
            self.transcript.append({"role": "assistant", "text": msg})
            return msg, True

        current_slot = SLOT_FLOW[self.current_slot_idx]

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
                    msg = "Thank you! All details have been captured. Please review your entries on the screen before confirming submission."
                    self.transcript.append({"role": "assistant", "text": msg})
                    return msg, True

                next_slot = SLOT_FLOW[self.current_slot_idx]
                next_q = SLOT_QUESTIONS[next_slot]
                self.transcript.append({"role": "assistant", "text": next_q})
                return next_q, False

            elif confirmed is False:
                # Value rejected by user
                self.awaiting_confirmation = False
                self.pending_value = None
                repeat_q = f"Let's try that again. {SLOT_QUESTIONS[current_slot]}"
                self.transcript.append({"role": "assistant", "text": repeat_q})
                return repeat_q, False
            else:
                # Unclear answer, re-prompt confirmation
                clarify = f"Please confirm with Yes or No: I recorded {self._format_value_for_speech(current_slot, self.pending_value)}. Is that correct?"
                self.transcript.append({"role": "assistant", "text": clarify})
                return clarify, False

        # 2. Extract value for current slot
        extracted_val = self._extract_slot_value(current_slot, user_utterance)
        if extracted_val is not None:
            self.pending_value = extracted_val
            self.awaiting_confirmation = True
            speech_val = self._format_value_for_speech(current_slot, extracted_val)
            confirm_q = f"I heard {speech_val}. Is that correct?"
            self.transcript.append({"role": "assistant", "text": confirm_q})
            return confirm_q, False
        else:
            # Could not parse slot value
            retry_q = f"I didn't quite catch that. {SLOT_QUESTIONS[current_slot]}"
            self.transcript.append({"role": "assistant", "text": retry_q})
            return retry_q, False

    def _extract_slot_value(self, slot: str, text: str) -> Any:
        if slot == "applicant_name":
            # Strip greetings or polite prefixes
            clean = text.strip()
            for prefix in ["my name is", "i am", "this is", "name is", "myself"]:
                if clean.lower().startswith(prefix):
                    clean = clean[len(prefix):].strip()
            return clean.title() if len(clean) >= 2 else None

        elif slot == "age":
            num = parse_spoken_currency_or_number(text)
            if num and 18 <= int(num) <= 100:
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
        if slot in ("monthly_income", "existing_emis", "requested_amount"):
            return f"{float(val):,.0f} rupees"
        elif slot in ("employment_duration_months", "tenure_months"):
            return f"{int(val)} months"
        elif slot == "age":
            return f"{int(val)} years old"
        return str(val)
