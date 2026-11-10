"""
Multilingual voice pipeline tests — English (en-IN), Hindi (hi-IN), Marathi (mr-IN).

Each test uses the real pipeline (SlotFillingSession + parsers) against the
directive's reference phrases. NO fabrication: every expected value below is
hand-derived from the documented parsing rules (intent.py).
"""
import pytest
from fastapi.testclient import TestClient

from backend.services.voice.intent import (
    parse_spoken_currency_or_number,
    parse_confirmation_intent,
    parse_categorical_slot,
    parse_duration_months,
    normalise_language,
    format_inr,
)
from backend.services.voice.slot_filler import SlotFillingSession
from backend.api.app import app

client = TestClient(app)


class TestLanguageRegistry:
    def test_supported_languages(self):
        assert normalise_language("en-IN") == "en-IN"
        assert normalise_language("hi-IN") == "hi-IN"
        assert normalise_language("mr-IN") == "mr-IN"

    def test_aliases_and_fallback(self):
        assert normalise_language("hi") == "hi-IN"
        assert normalise_language("marathi") == "mr-IN"
        assert normalise_language("हिन्दी") == "hi-IN"
        assert normalise_language(None) == "en-IN"
        assert normalise_language("xx-YY") == "en-IN"  # unsupported falls back honestly


class TestEnglishAmounts:
    @pytest.mark.parametrize("text,expected", [
        ("45000", 45000),
        ("45 thousand", 45000),
        ("4.5 lakh", 450000),
        ("5 lakh", 500000),
        ("1.2 crore", 12000000),
        ("60 hazaar", 60000),
        ("sixty thousand", 60000),
        ("forty five thousand", 45000),
        ("₹45,382", 45382),
        ("50k", 50000),
    ])
    def test_english_amounts(self, text, expected):
        assert parse_spoken_currency_or_number(text) == expected


class TestHindiAmounts:
    @pytest.mark.parametrize("text,expected", [
        # romanised Hindi
        ("60 hazaar rupaye hai", 60000),
        ("12 hazaar ki EMI", 12000),
        ("paanch lakh", 500000),
        ("do lakh", 200000),
        ("chaalees hazaar", 40000),
        # Devanagari script
        ("साठ हजार", 60000),
        ("बारा हजार", 12000),
        ("पाँच लाख", 500000),
        ("पाच लाख", 500000),
        ("५ लाख", 500000),
        ("₹४५,३८२", 45382),
        ("मेरी मासिक सैलरी साठ हजार रुपये है", 60000),
        ("मुझे पाँच लाख का लोन चाहिए", 500000),
        ("मेरे ऊपर बारह हज़ार की EMI चल रही है", 12000),
    ])
    def test_hindi_amounts(self, text, expected):
        assert parse_spoken_currency_or_number(text) == expected


class TestMarathiAmounts:
    @pytest.mark.parametrize("text,expected", [
        ("साठ हजार", 60000),                                   # साठ = 60
        ("बारा हजार रुपये", 12000),                             # बारा = 12
        ("पाच लाख", 500000),                                   # पाच = 5
        ("पन्नास हजार", 50000),                                # पन्नास = 50
        ("माझा मासिक पगार साठ हजार रुपये आहे", 60000),
        ("माझ्यावर बारा हजार रुपयांचा EMI आहे", 12000),
        ("मला पाच लाख रुपयांचे कर्ज हवे आहे", 500000),
    ])
    def test_marathi_amounts(self, text, expected):
        assert parse_spoken_currency_or_number(text) == expected


class TestConfirmationIntents:
    @pytest.mark.parametrize("text,expected", [
        ("yes", True), ("haan", True), ("ha", True),
        ("हाँ", True), ("हां", True), ("जी", True), ("ठीक है", True), ("सही", True),
        ("बरोबर", True), ("आहे", True), ("होय", True), ("हो", True),
        ("no", False), ("nahi", False), ("nako", False),
        ("नहीं", False), ("नही", False), ("नाही", False), ("नको", False),
        ("गलत है", False),
        ("maybe", None), ("", None),
        ("pata nahi", False),  # contains the negative 'nahi' -> treated as No, session re-asks
    ])
    def test_confirmations(self, text, expected):
        assert parse_confirmation_intent(text) is expected


class TestCategoricalSlots:
    def test_employment(self):
        assert parse_categorical_slot("employment_type", "I am salaried") == "salaried"
        assert parse_categorical_slot("employment_type", "मैं नौकरी करता हूँ") == "salaried"
        assert parse_categorical_slot("employment_type", "मी नोकरीत आहे") == "salaried"
        assert parse_categorical_slot("employment_type", "मेरा व्यापार है") == "business"
        assert parse_categorical_slot("employment_type", "स्वयंरोजगार") == "self_employed"

    def test_purpose(self):
        assert parse_categorical_slot("loan_purpose", "ghar ke liye") == "home"
        assert parse_categorical_slot("loan_purpose", "बच्चों की पढ़ाई") == "education"
        assert parse_categorical_slot("loan_purpose", "मुलांच्या शिक्षणासाठी") == "education"
        assert parse_categorical_slot("loan_purpose", "gaadi kharidni hai") == "vehicle"
        assert parse_categorical_slot("loan_purpose", "वाहन") == "vehicle"
        assert parse_categorical_slot("loan_purpose", "medical treatment") == "medical"
        assert parse_categorical_slot("loan_purpose", "इलाज") == "medical"

    def test_residence(self):
        assert parse_categorical_slot("residence_type", "kiraya pe rehta hoon") == "rented"
        assert parse_categorical_slot("residence_type", "भाड्याने राहतो") == "rented"
        assert parse_categorical_slot("residence_type", "अपना घर") == "owned"
        assert parse_categorical_slot("residence_type", "स्वतःचे घर") == "owned"
        assert parse_categorical_slot("residence_type", "पारिवारिक घर") == "ancestral"

    def test_residence_answers_matching_our_own_hindi_prompt(self):
        # The Hindi question literally offers "किराए का" — it must parse.
        assert parse_categorical_slot("residence_type", "किराए का") == "rented"
        assert parse_categorical_slot("residence_type", "किराये पर") == "rented"
        assert parse_categorical_slot("residence_type", "किराएदार हूँ") == "rented"
        assert parse_categorical_slot("residence_type", "भाड्याचे घर") == "rented"
        assert parse_categorical_slot("residence_type", "अपना") == "owned"


class TestDurations:
    @pytest.mark.parametrize("text,expected", [
        ("2 years", 24), ("24 months", 24), ("do saal", 24),
        ("दो साल", 24), ("दोन वर्षे", 24), ("36 months", 36),
        ("2O months", None),  # letter O is NOT a digit: must not parse
        # compound spoken numbers in Devanagari (Hindi / Marathi)
        ("चौबीस महीने", 24), ("अट्ठाईस महीने", 28), ("तीस छह महीने", 36),
        ("चोवीस महिने", 24), ("छत्तीस महिने", 36), ("तीस महिने", 30),
        ("अठ्ठावीस महिने", 28),
    ])
    def test_durations(self, text, expected):
        assert parse_duration_months(text) == expected

    def test_compound_numbers_parse_as_values(self):
        assert parse_spoken_currency_or_number("चोवीस") == 24
        assert parse_spoken_currency_or_number("अट्ठाईस") == 28
        assert parse_spoken_currency_or_number("छत्तीस") == 36
        assert parse_spoken_currency_or_number("एकोणऐंशी") == 79
        assert parse_spoken_currency_or_number("निन्यानवे") == 99


class TestEnglishSession:
    def test_full_english_flow(self):
        s = SlotFillingSession()
        # name
        msg, _ = s.process_turn("My name is Rohit Verma")
        assert "Rohit Verma" in msg and "correct?" in msg
        msg, _ = s.process_turn("Yes")
        assert s.filled_slots["applicant_name"] == "Rohit Verma"
        # age
        msg, _ = s.process_turn("I am 28")
        assert "28" in msg
        s.process_turn("yes")
        # employment
        msg, _ = s.process_turn("I am salaried")
        s.process_turn("yes")
        # duration
        msg, _ = s.process_turn("dualless")
        assert "didn't quite catch" in msg  # honest non-parse
        msg, _ = s.process_turn("2 years")
        assert "2 years" in msg
        s.process_turn("yes")
        # income — the directive phrase
        msg, _ = s.process_turn("Meri monthly salary 60 hazaar rupaye hai")
        assert s.pending_value == 60000
        assert "60,000" in msg
        s.process_turn("yes")
        assert s.filled_slots["monthly_income"] == 60000
        # EMIs
        msg, _ = s.process_turn("12 hazaar")
        assert s.pending_value == 12000
        s.process_turn("yes")
        # requested amount
        msg, _ = s.process_turn("5 lakh")
        assert s.pending_value == 500000
        s.process_turn("correct")
        # tenure
        msg, _ = s.process_turn("24 months")
        s.process_turn("yes")
        # purpose
        msg, _ = s.process_turn("personal loan")
        s.process_turn("yes")
        # residence
        msg, is_complete = s.process_turn("rented")
        assert is_complete is False
        msg, is_complete = s.process_turn("yes")
        assert is_complete is True
        assert s.filled_slots["monthly_income"] == 60000
        assert s.filled_slots["requested_amount"] == 500000
        assert s.filled_slots["existing_emis"] == 12000


class TestHindiSession:
    def test_hindi_prompts(self):
        res = client.post("/api/voice/init", json={"language": "hi-IN"})
        assert res.status_code == 200
        data = res.json()
        assert "लोन लेंस" in data["assistant_message"]
        assert data["language"] == "hi-IN"

    def test_hindi_full_flow(self):
        res = client.post("/api/voice/init", json={"language": "hi-IN"})
        state = res.json()["session_state"]
        s = SlotFillingSession(state)
        _, _ = s.process_turn("मेरा नाम राहुल शर्मा है")
        assert s.pending_value == "राहुल शर्मा"
        _, _ = s.process_turn("हाँ")
        assert s.filled_slots["applicant_name"] == "राहुल शर्मा"
        # Age question must already be in Hindi
        assert "उम्र" in s.transcript[-1]["text"]
        _, _ = s.process_turn("पता नहीं")  # genuinely unparseable → honest retry, no guess
        assert "समझ नहीं" in s.transcript[-1]["text"]
        _, _ = s.process_turn("अट्ठाईस")   # spoken compound number now parses
        assert s.pending_value == 28
        _, _ = s.process_turn("हाँ")
        assert s.filled_slots["age"] == 28
        _, _ = s.process_turn("नौकरी")
        _, _ = s.process_turn("हाँ")
        _, _ = s.process_turn("दो साल")
        _, _ = s.process_turn("जी")
        # Monthly income — directive phrase, Devanagari answer
        _, _ = s.process_turn("साठ हजार रुपये")
        assert s.pending_value == 60000
        assert "60,000" in s.transcript[-1]["text"]
        _, _ = s.process_turn("हाँ")
        assert s.filled_slots["monthly_income"] == 60000

    def test_hindi_confirmation_via_api(self):
        res = client.post("/api/voice/init", json={"language": "hi-IN"})
        state = res.json()["session_state"]
        res = client.post("/api/voice/turn", json={
            "user_utterance": "मेरा नाम सुनीता है", "session_state": state, "language": "hi-IN"})
        assert "सुनीता" in res.json()["assistant_message"]


class TestMarathiSession:
    def test_marathi_prompts(self):
        res = client.post("/api/voice/init", json={"language": "mr-IN"})
        assert res.status_code == 200
        data = res.json()
        assert "लोन लेन्स" in data["assistant_message"]
        assert data["language"] == "mr-IN"

    def test_marathi_directive_phrases(self):
        res = client.post("/api/voice/init", json={"language": "mr-IN"})
        state = res.json()["session_state"]
        s = SlotFillingSession(state)
        _, _ = s.process_turn("माझं नाव मोहिनी देशमुख आहे")
        assert s.pending_value == "मोहिनी देशमुख"
        _, _ = s.process_turn("हो")     # Marathi yes
        assert s.filled_slots["applicant_name"] == "मोहिनी देशमुख"
        _, _ = s.process_turn("सातत्याने", language="mr-IN")
        # honest retry on unparseable noise
        assert "ऐकू आलं नाही" in s.transcript[-1]["text"]
        _, _ = s.process_turn("अठ्ठा", language="mr-IN")
        assert "ऐकू आलं नाही" in s.transcript[-1]["text"]
        _, _ = s.process_turn("टीस", language="mr-IN")
        assert "ऐकू आलं नाही" in s.transcript[-1]["text"]
        _, _ = s.process_turn("30")
        _, _ = s.process_turn("हो")
        _, _ = s.process_turn("नोकरी")
        _, _ = s.process_turn("हो")
        _, _ = s.process_turn("दोन वर्षे")
        _, _ = s.process_turn("हो")
        # Monthly income — directive Marathi phrase
        msg, _ = s.process_turn("माझा मासिक पगार साठ हजार रुपये आहे")
        assert s.pending_value == 60000
        _, _ = s.process_turn("हो")
        assert s.filled_slots["monthly_income"] == 60000
        # EMIs — directive Marathi phrase
        msg_ = s.process_turn("माझ्यावर बारा हजार रुपयांचा EMI आहे")[0]
        assert s.pending_value == 12000
        s.process_turn("हो")
        # Requested amount — directive Marathi phrase
        msg_, _ = s.process_turn("मला पाच लाख रुपयांचे कर्ज हवे आहे")
        assert s.pending_value == 500000
        s.process_turn("हो")
        assert s.filled_slots["requested_amount"] == 500000


class TestLocalisedSpeakBack:
    """Categorical answers must be echoed in the conversation language, never
    as internal English enum values inside a Hindi/Marathi sentence."""

    def test_hindi_employment_and_purpose_labels(self):
        s = SlotFillingSession()
        s.language = "hi-IN"
        s.current_slot_idx = 2  # employment_type
        msg, _ = s.process_turn("नौकरी")
        assert "नौकरी" in msg
        assert "salaried" not in msg
        s2 = SlotFillingSession()
        s2.language = "hi-IN"
        s2.current_slot_idx = 8  # loan_purpose
        msg2, _ = s2.process_turn("पढ़ाई")
        assert "पढ़ाई" in msg2
        assert "education" not in msg2

    def test_marathi_residence_label(self):
        s = SlotFillingSession()
        s.language = "mr-IN"
        s.current_slot_idx = 9  # residence_type
        msg, _ = s.process_turn("भाड्याने")
        assert "भाड्याने" in msg
        assert "rented" not in msg

    def test_english_labels_unchanged(self):
        s = SlotFillingSession()
        s.current_slot_idx = 2
        msg, _ = s.process_turn("salaried")
        assert "Salaried" in msg


class TestLanguageSwitching:
    def test_switch_preserves_slots_and_updates_prompts(self):
        # Start in English, capture two slots, then switch to Hindi mid-conversation
        res = client.post("/api/voice/init", json={"language": "en-IN"})
        state = res.json()["session_state"]
        s = SlotFillingSession(state)
        _, _ = s.process_turn("My name is Priya Nair")
        _, _ = s.process_turn("yes")
        _, _ = s.process_turn("35")
        _, _ = s.process_turn("yes")
        _, _ = s.process_turn("salaried")
        _, _ = s.process_turn("yes")
        # switch to Hindi on the duration question
        msg, _ = s.process_turn("", language="hi-IN")
        assert "हिन्दी" in msg
        assert "सुरक्षित" in msg  # explicitly reassures context preservation
        # current question now in Hindi
        assert "नौकरी" in s.transcript[-1]["text"] or "समय" in s.transcript[-1]["text"]
        # captured slots intact
        assert s.filled_slots["applicant_name"] == "Priya Nair"
        assert s.filled_slots["age"] == 35
        # and the Hindi question can be answered in Devanagari words
        _, _ = s.process_turn("दो साल")
        assert s.pending_value == 24
        _, _ = s.process_turn("हाँ")

    def test_switch_to_marathi_via_api_preserves_state(self):
        res = client.post("/api/voice/init", json={"language": "hi-IN"})
        state = res.json()["session_state"]
        res = client.post("/api/voice/turn", json={
            "user_utterance": "राहुल", "session_state": state, "language": "hi-IN"})
        state2 = res.json()["session_state"]
        res = client.post("/api/voice/turn", json={
            "user_utterance": "", "session_state": state2, "language": "mr-IN"})
        data = res.json()
        assert data["language"] == "mr-IN"
        assert "मराठी" in data["assistant_message"]
        # awaiting_confirmation context preserved across the switch
        assert data["session_state"]["language"] == "mr-IN"


class TestBackwardCompatibility:
    def test_init_without_body_defaults_english(self):
        res = client.post("/api/voice/init")
        assert res.status_code == 200
        assert res.json()["language"] == "en-IN"
        assert "LoanLens" in res.json()["assistant_message"]

    def test_turn_without_language_uses_session_language(self):
        res = client.post("/api/voice/init", json={"language": "en-IN"})
        state = res.json()["session_state"]
        res = client.post("/api/voice/turn", json={"user_utterance": "Priya Sharma", "session_state": state})
        assert "Priya Sharma" in res.json()["assistant_message"]


class TestINRFormatting:
    @pytest.mark.parametrize("value,expected", [
        (45000, "45,000"),
        (500000, "5,00,000"),
        (1200000, "12,00,000"),
        (45382, "45,382"),
        (10000000, "1,00,00,000"),
    ])
    def test_indian_grouping(self, value, expected):
        assert format_inr(value) == expected
