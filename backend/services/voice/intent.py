"""
Multilingual financial utterance parsing for the LoanLens voice pipeline.
Supported: English (en-IN), Hindi (hi-IN), Marathi (mr-IN).

Handles:
- ASCII and Devanagari numerals (०-९)
- Spoken Indian currency words in romanised and Devanagari script:
  hazaar/hazar/hजार (thousand), lakh/lac/लाख, crore/karod/koti/करोड़/कोटी
- Number words: English, Hindi and Marathi, 0-100 + multipliers
- Confirmation intents across three languages
- Categorical slot phrases (employment / purpose / residence)
"""
import re
from typing import Optional, Dict, List

# ---------------------------------------------------------------------------
# Language registry
# ---------------------------------------------------------------------------
SUPPORTED_LANGUAGES = ("en-IN", "hi-IN", "mr-IN")
DEFAULT_LANGUAGE = "en-IN"

# faster-whisper / web speech ISO-639-1 codes
WHISPER_LANGUAGE_CODES = {"en-IN": "en", "hi-IN": "hi", "mr-IN": "mr"}

_LANGUAGE_ALIASES = {
    "en": "en-IN", "en-in": "en-IN", "english": "en-IN",
    "hi": "hi-IN", "hi-in": "hi-IN", "hindi": "hi-IN", "हिंदी": "hi-IN", "हिन्दी": "hi-IN",
    "mr": "mr-IN", "mr-in": "mr-IN", "marathi": "mr-IN", "मराठी": "mr-IN",
}


def normalise_language(language: Optional[str]) -> str:
    """Maps any alias/partial tag onto a supported voice language."""
    if not language:
        return DEFAULT_LANGUAGE
    key = str(language).strip().lower()
    if key in _LANGUAGE_ALIASES:
        return _LANGUAGE_ALIASES[key]
    if key in SUPPORTED_LANGUAGES:
        return key
    # fall back on the 2-letter base code ("en-us" -> "en-IN" voice persona)
    base = key.split("-")[0]
    if base in _LANGUAGE_ALIASES:
        return _LANGUAGE_ALIASES[base]
    return DEFAULT_LANGUAGE


# ---------------------------------------------------------------------------
# Text normalisation: Devanagari digits, danda, punctuation
# ---------------------------------------------------------------------------
_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

def normalize_text(text: str) -> str:
    if not text:
        return ""
    # Remove digit-group commas ("45,000" -> "45000") and the rupee sign,
    # but keep the decimal point intact ("4.5 lakh" must survive).
    t = text.lower().strip().replace(",", "").replace("₹", "")
    t = t.translate(_DEV_DIGITS)
    for d in ("।", "॥", "!", "?", ";", ":"):
        t = t.replace(d, " ")
    return re.sub(r"\s+", " ", t).strip()


# ---------------------------------------------------------------------------
# Number-word dictionary (romanised + Devanagari, Hindi + Marathi variants)
# ---------------------------------------------------------------------------
WORD_NUMBERS: Dict[str, float] = {
    # English
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90,
    # Multipliers share the same table
    "hundred": 100, "thousand": 1000, "lakh": 100000, "lac": 100000,
    "lacs": 100000, "crore": 10000000,
    # Romanised Hindi
    "shunya": 0, "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4,
    "paanch": 5, "panch": 5, "chhah": 6, "chhe": 6, "che": 6, "saat": 7, "sat": 7,
    "aath": 8, "nau": 9, "das": 10, "daha": 10, "gyarah": 11, "baarah": 12,
    "barah": 12, "terah": 13, "chaudah": 14, "pandrah": 15, "solah": 16,
    "satrah": 17, "athaarah": 18, "unnees": 19, "bees": 20, "tees": 30,
    "chaalees": 40, "chalis": 40, "pachaas": 50, "saath": 60, "sattar": 70,
    "assi": 80, "nabbe": 90, "sau": 100, "hazaar": 1000, "hazar": 1000,
    "haajar": 1000, "laakh": 100000, "karod": 10000000,
    "savva": 1.25, "dedh": 1.5, "dhai": 2.5,
    # Romanised Marathi
    "don": 2, "paach": 5, "saha": 6, "hne": 9, "daha": 10, "baraa": 12,
    "chooda": 14, "ponadra": 15, "sola": 16, "es": 80, "shambhar": 100,
    "shembhar": 100, "hajar": 1000, "kotee": 10000000,
    # Devanagari — shared Hindi/Marathi
    "शून्य": 0, "शुन्य": 0,
    "एक": 1, "दो": 2, "दोन": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5, "पाच": 5,
    "छह": 6, "छः": 6, "सहा": 6, "सात": 7, "आठ": 8, "नौ": 9, "नऊ": 9,
    "दस": 10, "दहा": 10, "ग्यारह": 11, "बारह": 12, "बारा": 12, "तेरह": 13,
    "चौदह": 14, "पंद्रह": 15, "पंधरा": 15, "सोलह": 16, "सोळा": 16,
    "सत्रह": 17, "सतरा": 17, "अठारह": 18, "अठरा": 18, "उन्नीस": 19, "एकोणीस": 19,
    "बीस": 20, "वीस": 20, "तीस": 30, "चालीस": 40, "चाळीस": 40,
    "पचास": 50, "पन्नास": 50, "साठ": 60, "सत्तर": 70, "अस्सी": 80,
    "नब्बे": 90, "सौ": 100, "शंभर": 100,
    "हज़ार": 1000, "हजार": 1000, "हजारा": 1000,
    "लाख": 100000, "लक्ष": 100000, "करोड़": 10000000, "कोटी": 10000000,
}

_MULTIPLIERS = {100.0, 1000.0, 100000.0, 10000000.0}

# Compound numbers 21-99 (Hindi + Marathi, Devanagari). Spoken ages, tenures and
# EMIs overwhelmingly use these forms, so they must not fall through to "not understood".
_COMPOUND_NUMBERS: Dict[str, float] = {
    # Hindi
    "इक्कीस": 21, "बाईस": 22, "तेईस": 23, "चौबीस": 24, "पच्चीस": 25, "छब्बीस": 26,
    "सत्ताईस": 27, "अट्ठाईस": 28, "अठ्ठाईस": 28, "उनतीस": 29,
    "इकतीस": 31, "इकत्तीस": 31, "बत्तीस": 32, "तैंतीस": 33, "चौंतीस": 34,
    "पैंतीस": 35, "छत्तीस": 36, "सैंतीस": 37, "अड़तीस": 38, "उनतालीस": 39,
    "इकतालीस": 41, "बयालीस": 42, "तैंतालीस": 43, "चवालीस": 44, "पैंतालीस": 45,
    "छियालीस": 46, "सैंतालीस": 47, "अड़तालीस": 48, "उनचास": 49,
    "इक्यावन": 51, "बावन": 52, "तिरपन": 53, "चौवन": 54, "पचपन": 55,
    "छप्पन": 56, "सत्तावन": 57, "अट्ठावन": 58, "उनसठ": 59,
    "इकसठ": 61, "बासठ": 62, "तिरसठ": 63, "चौंसठ": 64, "पैंसठ": 65,
    "छियासठ": 66, "सड़सठ": 67, "अड़सठ": 68, "उनहत्तर": 69,
    "इकहत्तर": 71, "बहत्तर": 72, "तिहत्तर": 73, "चौहत्तर": 74, "पचहत्तर": 75,
    "छिहत्तर": 76, "सतहत्तर": 77, "अठहत्तर": 78, "उनासी": 79,
    "इक्यासी": 81, "बयासी": 82, "तिरासी": 83, "चौरासी": 84, "पचासी": 85,
    "छियासी": 86, "सत्तासी": 87, "अट्ठासी": 88, "नवासी": 89,
    "इक्यानवे": 91, "बानवे": 92, "तिरानवे": 93, "चौरानवे": 94, "पचानवे": 95,
    "छियानवे": 96, "सत्तानवे": 97, "अट्ठानवे": 98, "निन्यानवे": 99,
    # Marathi
    "एकवीस": 21, "बावीस": 22, "तेवीस": 23, "चोवीस": 24, "पंचवीस": 25, "सव्वीस": 26,
    "सत्तावीस": 27, "अठ्ठावीस": 28, "एकोणतीस": 29,
    "एकतीस": 31, "तेहेतीस": 33, "चौतीस": 34, "पस्तीस": 35, "सदतीस": 37,
    "अडतीस": 38, "एकोणचाळीस": 39,
    "एक्केचाळीस": 41, "बेचाळीस": 42, "त्रेचाळीस": 43, "चव्वेचाळीस": 44,
    "पंचेचाळीस": 45, "सेहेचाळीस": 46, "सत्तेचाळीस": 47, "अठ्ठेचाळीस": 48,
    "एकोणपन्नास": 49, "एक्कावन्न": 51, "बावन्न": 52, "त्रेपन्न": 53,
    "चौपन्न": 54, "पंचावन्न": 55, "छप्पन्न": 56, "सत्तावन्न": 57, "अठ्ठावन्न": 58,
    "एकोणसाठ": 59, "एकसष्ट": 61, "बासष्ट": 62, "त्रेसष्ट": 63, "चौसष्ट": 64,
    "पासष्ट": 65, "सहासष्ट": 66, "सदुसष्ट": 67, "अडुसष्ट": 68, "एकोणसत्तर": 69,
    "एक्काहत्तर": 71, "बाहत्तर": 72, "त्र्याहत्तर": 73, "चौऱ्याहत्तर": 74,
    "पंच्याहत्तर": 75, "शहात्तर": 76, "सत्याहत्तर": 77, "अठ्ठ्याहत्तर": 78,
    "एकोणऐंशी": 79, "ऐंशी": 80, "एक्क्याऐंशी": 81, "ब्याऐंशी": 82,
    "त्र्याऐंशी": 83, "चौऱ्याऐंशी": 84, "पंच्याऐंशी": 85, "शहाऐंशी": 86,
    "सत्त्याऐंशी": 87, "अठ्ठ्याऐंशी": 88, "एकोणनव्वद": 89, "नव्वद": 90,
    "एक्क्याण्णव": 91, "ब्याण्णव": 92, "त्र्याण्णव": 93, "चौऱ्याण्णव": 94,
    "पंच्याण्णव": 95, "शहाण्णव": 96, "सत्त्याण्णव": 97, "अठ्ठ्याण्णव": 98,
    "नव्व्याण्णव": 99,
}
WORD_NUMBERS.update(_COMPOUND_NUMBERS)

ZERO_WORDS = {"no", "none", "zero", "nil", "na", "nothing", "nahi", "nahin", "नहीं", "नाही", "नको", "शून्य", "नाहीआहे"}

_TOKEN_RE = re.compile(r"\S+")


def _token_value(token: str) -> Optional[float]:
    # whitespace-split tokens keep Devanagari matras/conjuncts intact
    t = token.strip().strip(".,!?;:।")
    if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", t):
        try:
            return float(t)
        except ValueError:
            return None
    # finance-style suffix: "50k"
    m = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)k", t)
    if m:
        try:
            return float(m.group(1)) * 1000
        except ValueError:
            return None
    return WORD_NUMBERS.get(t)


def parse_spoken_currency_or_number(text: str) -> Optional[float]:
    """
    Parses natural language currency expressions common in India, across
    English / Hindi / Marathi, romanised or Devanagari script:
      '4.5 lakh', '45 thousand', '50k', '45000', '1.2 crore', 'sixty thousand',
      '60 हजार', 'साठ हजार', 'पाच लाख', '५ लाख', '₹45,382', 'meri salary 60 hazaar hai'
    Returns None when no number can be interpreted (never guesses).
    """
    if not text:
        return None
    raw = normalize_text(text)
    if not raw:
        return None

    if raw in ZERO_WORDS:
        return 0.0

    tokens = _TOKEN_RE.findall(raw)
    total = 0.0
    current = 0.0
    found = False

    for tok in tokens:
        val = _token_value(tok)
        if val is None:
            continue
        found = True
        if val in _MULTIPLIERS or val == 1000.0 or val == 100.0:
            # 'sixty hazaar' -> 60 x 1000 ; bare 'lakh'/'hazaar' -> multiplier x 1
            current = (current if current > 0 else 1.0) * val
            total += current
            current = 0.0
        else:
            # combine tens + units: 'forty five' -> 45, 'chaalees paanch' -> 45
            if current > 0 and 1 <= val <= 9 and current % 10 == 0 and current >= 20:
                current += val
            else:
                current += val

    total += current
    if found and total > 0:
        return float(round(total, 2))
    if found and total == 0:
        return 0.0
    return None


def format_inr(value: float) -> str:
    """Indian digit grouping: 500000 -> '5,00,000'."""
    s = str(int(round(abs(value))))
    if len(s) <= 3:
        sign = "-" if value < 0 else ""
        return sign + s
    head, tail = s[:-3], s[-3:]
    parts: List[str] = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    sign = "-" if value < 0 else ""
    return sign + ",".join(parts + [tail])


def parse_duration_months(text: str) -> Optional[int]:
    """
    Parses loan or employment duration, normalising years to months.
    Accepts English, Hindi ('saal', 'महीने') and Marathi ('वर्ष', 'महिने') words.
    """
    if not text:
        return None
    raw = normalize_text(text)

    m_yr = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:year|years|saal|saal|varsh|वर्ष|साल)|"
                     r"\b(?:एक|दो|तीन|चार|पांच|पाँच|पाच|दस|दहा)\b(?=\s*(?:वर्ष|साल))", raw)
    if m_yr:
        try:
            yr = m_yr.group(1)
            if yr is None:
                yr = str(int(WORD_NUMBERS.get(m_yr.group(0), 0)))
            return int(round(float(yr) * 12))
        except (ValueError, TypeError):
            pass

    m_mo = re.search(r"([0-9]+)\s*(?:month|months|mahine|mahino|महीने|महिने|महिन्यां)", raw)
    if m_mo:
        try:
            return int(m_mo.group(1))
        except ValueError:
            pass

    num = parse_spoken_currency_or_number(raw)
    if num is not None and num > 0:
        val = int(num)
        # small bare number most plausibly means years
        if val <= 7:
            return val * 12
        return val
    return None


# ---------------------------------------------------------------------------
# Confirmation intent (three languages, romanised + Devanagari)
# ---------------------------------------------------------------------------
_AFFIRMATIVE = {
    "yes", "yeah", "yep", "correct", "right", "sure", "ok", "okay", "true",
    "ha", "haan", "han", "hoy", "ho", "barobar", "ahe", "aaho", "theek", "tik",
    "sahi", "ji", "haje", "okha",
    "हाँ", "हां", "जी", "हो", "होय", "ठीक", "सही", "बरोबर", "आहे", "आहो", "असे",
}
_NEGATIVE = {
    "no", "nope", "wrong", "incorrect", "change", "false",
    "nahi", "nahin", "nako", "galat",
    "नहीं", "नही", "नाही", "नको", "गलत", "चूक", "चुकीच", "बदल",
}

def parse_confirmation_intent(text: str) -> Optional[bool]:
    """Classifies affirmative vs negative answers in all three languages."""
    raw = normalize_text(text)
    if not raw:
        return None
    # whitespace split: \w+ cannot match Devanagari matras (Mn/Mc marks)
    words = set(raw.split())
    if words & _AFFIRMATIVE:
        return True
    if words & _NEGATIVE:
        return False
    return None


# ---------------------------------------------------------------------------
# Categorical slot matching (three languages)
# ---------------------------------------------------------------------------
_EMPLOYMENT_WORDS = {
    "salaried": ["salary", "salaried", "salarid", "job", "private", "govt", "employee", "service",
                 "naukri", "nokari", "nokri", "sarkari", "peti",
                 "नौकरी", "नोकरी", "सैलरी", "सैलरीड", "सरकारी", "पगार"],
    "business": ["business", "shop", "enterprise", "dhandha", "vyapar", "dukan",
                 "vyavasay", "vyavasai", "vyapari", "dhande",
                 "व्यापार", "व्यवसाय", "दुकान", "व्यवसायात"],
    "self_employed": ["self", "freelance", "independent", "consultant", "swayam", "svayamrojgar", "swayamrojgar",
                      "स्वयंरोजगार", "स्वयं", "स्वतंत्र", "स्वतंत्र"],
    "gig_contract": ["gig", "contract", "driver", "delivery", "theka",
                     "ड्रिवर", "डिलिव्हरी", "ठेका"],
}
_PURPOSE_WORDS = {
    "home": ["home", "house", "flat", "apartment", "renovat", "ghar",
             "घर", "घराचे", "घरासाठी", "मकान", "रुम"],
    "education": ["education", "study", "college", "school", "degree",
                  "shiksha", "shikshan", "padhai", "padhaai", "abhyas",
                  "शिक्षण", "पढ़ाई", "पढाई", "अभ्यास"],
    "business": ["business", "expand", "stock", "working", "capital",
                 "व्यापार", "व्यवसाय", "विस्तार"],
    "vehicle": ["vehicle", "car", "bike", "scooter", "auto", "gaadi", "gaari",
                "वाहन", "गाड़ी", "गाडी", "दुचाकी"],
    "medical": ["medical", "health", "hospital", "treatment",
                "ilaj", "upachar", "dawai", "आरोग्य",
                "इलाज", "उपचार", "हॉस्पिटल", "आजार"],
}
_RESIDENCE_WORDS = {
    "owned": ["own", "owned", "khudka", "swatah", "apna", "apan",
              "स्वतःचे", "स्वता", "अपना", "मालकी"],
    "rented": ["rent", "rented", "kiraya", "kiraye", "bhadne", "bhade", "bhaade",
               "किराया", "किराए", "किराये", "किराएदार", "भाडे", "भाड्याने", "भाड्यात",
               "भाड्याचे", "भाड्याच्या"],
    "ancestral": ["family", "parent", "ancestral", "paternal", "parivarik", "kautumbik",
                  "पारिवारिक", "कौटुंबिक", "वडिलधाऱ्या"],
}

def parse_categorical_slot(slot: str, text: str) -> Optional[str]:
    raw = normalize_text(text)
    if not raw or not raw.strip():
        return None
    groups = {
        "employment_type": _EMPLOYMENT_WORDS,
        "loan_purpose": _PURPOSE_WORDS,
        "residence_type": _RESIDENCE_WORDS,
    }.get(slot, {})
    for value, words in groups.items():
        if any((" " + w) in (" " + raw) for w in words):
            return value
    if slot == "loan_purpose":
        return "personal"
    return None
