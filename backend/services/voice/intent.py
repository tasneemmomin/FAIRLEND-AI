import re
from typing import Optional, Tuple, Any

WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90, "hundred": 100, "thousand": 1000,
    "lakh": 100000, "lac": 100000, "lacs": 100000, "crore": 10000000,
    # Common Hindi/Marathi words
    "shunya": 0, "ek": 1, "don": 2, "do": 2, "teen": 3, "char": 4, "paanch": 5,
    "daha": 10, "das": 10, "hazaar": 1000, "hazar": 1000, "sawwa": 1.25, "dedh": 1.5, "dhai": 2.5
}

def parse_spoken_currency_or_number(text: str) -> Optional[float]:
    """
    Parses natural language currency expressions common in India:
    e.g. '4.5 lakh', '45 thousand', '50k', '45000', '1.2 crore', 'sixty thousand'.
    """
    if not text:
        return None
    raw = text.lower().strip().replace(",", "")

    if raw in ("no", "none", "zero", "nil", "na", "nothing"):
        return 0.0

    # 1. Regex for 'X.Y crore'
    m_crore = re.search(r"([\d\.]+)\s*(?:cr|crore|crores)\b", raw)
    if m_crore:
        try:
            return round(float(m_crore.group(1)) * 10000000, 2)
        except ValueError:
            pass

    # 2. Regex for 'X.Y lakh' or 'X L'
    m_lakh = re.search(r"([\d\.]+)\s*(?:lakh|lakhs|lac|lacs|l)\b", raw)
    if m_lakh:
        try:
            return round(float(m_lakh.group(1)) * 100000, 2)
        except ValueError:
            pass

    # 3. Regex for 'X thousand' or 'X k'
    m_k = re.search(r"([\d\.]+)\s*(?:k|thousand|thousands|hazar|hazaar)\b", raw)
    if m_k:
        try:
            return round(float(m_k.group(1)) * 1000, 2)
        except ValueError:
            pass

    # 4. Direct numerical match
    m_num = re.search(r"\b\d+(?:\.\d+)?\b", raw)
    if m_num:
        try:
            return float(m_num.group(0))
        except ValueError:
            pass

    # 5. Spoken word combinations: e.g. "forty five thousand"
    words = raw.split()
    total = 0.0
    current = 0.0
    found_word = False
    for w in words:
        if w in WORD_NUMBERS:
            found_word = True
            val = WORD_NUMBERS[w]
            if val in (100, 1000, 100000, 10000000):
                current = max(1, current) * val
                total += current
                current = 0
            else:
                current += val
    total += current
    if found_word and total > 0:
        return float(total)

    return None

def parse_duration_months(text: str) -> Optional[int]:
    """Parses loan or employment duration, normalizing years to months."""
    if not text:
        return None
    raw = text.lower().strip()

    # Match 'X years' or 'X.Y years'
    m_yr = re.search(r"([\d\.]+)\s*(?:year|years|saal|varsh)", raw)
    if m_yr:
        try:
            return int(round(float(m_yr.group(1)) * 12))
        except ValueError:
            pass

    # Match 'X months'
    m_mo = re.search(r"(\d+)\s*(?:month|months|mahine)", raw)
    if m_mo:
        try:
            return int(m_mo.group(1))
        except ValueError:
            pass

    # Fallback to direct number
    num = parse_spoken_currency_or_number(raw)
    if num is not None:
        val = int(num)
        # If user says e.g. '3', assume years if <= 5, else months
        if val <= 7:
            return val * 12
        return val

    return None

def parse_confirmation_intent(text: str) -> Optional[bool]:
    """Classifies affirmative vs negative answers."""
    raw = text.lower().strip()
    affirmative = {"yes", "yeah", "yep", "correct", "right", "sure", "ok", "okay", "ha", "haan", "ho", "barobar"}
    negative = {"no", "nope", "wrong", "incorrect", "change", "nahi", "nako"}

    words = set(re.findall(r"\w+", raw))
    if words.intersection(affirmative):
        return True
    if words.intersection(negative):
        return False
    return None

def parse_categorical_slot(slot: str, text: str) -> Optional[str]:
    raw = text.lower().strip()
    if slot == "employment_type":
        if any(w in raw for w in ["salary", "salaried", "job", "private", "govt", "employee", "service"]):
            return "salaried"
        if any(w in raw for w in ["business", "shop", "enterprise", "dhandha", "vyapar"]):
            return "business"
        if any(w in raw for w in ["self", "freelance", "independent", "consultant"]):
            return "self_employed"
        if any(w in raw for w in ["gig", "contract", "driver", "delivery"]):
            return "gig_contract"

    elif slot == "loan_purpose":
        if any(w in raw for w in ["home", "house", "flat", "apartment", "renovat", "ghar"]):
            return "home"
        if any(w in raw for w in ["education", "study", "college", "school", "degree"]):
            return "education"
        if any(w in raw for w in ["business", "expand", "stock", "working capital"]):
            return "business"
        if any(w in raw for w in ["vehicle", "car", "bike", "scooter", "auto"]):
            return "vehicle"
        if any(w in raw for w in ["medical", "health", "hospital", "treatment"]):
            return "medical"
        return "personal"

    elif slot == "residence_type":
        if any(w in raw for w in ["own", "owned", "khudka"]):
            return "owned"
        if any(w in raw for w in ["rent", "rented", "kiraya"]):
            return "rented"
        if any(w in raw for w in ["family", "parent", "ancestral", "paternal"]):
            return "ancestral"

    return None
