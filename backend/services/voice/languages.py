"""
Voice assistant language resources: question sets and message templates for
English (India), Hindi (India) and Marathi (India).

These strings are spoken aloud by TTS: keep them natural, financial-literate
and free of technical jargon. Every value repeated to the applicant is
verified with a yes/no confirmation before being stored.
"""
from typing import Dict

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
    "residence_type",
]

SLOT_QUESTIONS: Dict[str, Dict[str, str]] = {
    "en-IN": {
        "applicant_name": "Hello! I am your LoanLens voice assistant. May I please have your full name?",
        "age": "Thank you! What is your age in years?",
        "employment_type": "What is your primary employment type? For example: Salaried, Self-Employed, or Business?",
        "employment_duration_months": "How long have you been in your current job or business? For example: 2 years or 24 months.",
        "monthly_income": "What is your average monthly take-home income?",
        "existing_emis": "Do you have any existing monthly loan payments or EMIs? If yes, how much per month? If none, say zero.",
        "requested_amount": "How much loan amount are you applying to borrow?",
        "tenure_months": "Over how many months or years would you like to repay this loan?",
        "loan_purpose": "What is the purpose of this loan? For example: Home, Education, Personal, Business, or Vehicle?",
        "residence_type": "Do you live in an Owned home, Rented accommodation, or Family residence?",
    },
    "hi-IN": {
        "applicant_name": "नमस्ते! मैं आपका लोन लेंस वॉइस असिस्टेंट हूँ। कृपया अपना पूरा नाम बताइए।",
        "age": "धन्यवाद! आपकी उम्र कितनी है?",
        "employment_type": "आपकी मुख्य रोज़गार कैटेगरी क्या है? जैसे: नौकरी या सैलरीड, व्यापार, या स्वयं रोज़गार?",
        "employment_duration_months": "आप अपनी मौजूदा नौकरी या व्यापार में कितने समय से हैं? जैसे: दो साल या चौबीस महीने।",
        "monthly_income": "आपकी मासिक औसत टेक-होम सैलरी या आमदनी कितनी है?",
        "existing_emis": "क्या आपकी कोई मौजूदा मासिक EMI या किस्त चल रही है? अगर हाँ, तो महीने की कितनी? अगर नहीं, तो शून्य या नहीं कहें।",
        "requested_amount": "आप कितनी राशि का लोन चाहते हैं? जैसे: पाँच लाख या दो लाख।",
        "tenure_months": "आप यह लोन कितने महीनों या सालों में चुकाना चाहेंगे?",
        "loan_purpose": "इस लोन का उद्देश्य क्या है? जैसे: घर, पढ़ाई, पर्सनल, व्यापार, या वाहन?",
        "residence_type": "आप अपने घर में कैसे रहते हैं — अपना, किराए का, या पारिवारिक?",
    },
    "mr-IN": {
        "applicant_name": "नमस्कार! मी तुमचा लोन लेन्स व्हॉइस असिस्टंट आहे. कृपया तुमचे पूर्ण नाव सांगा.",
        "age": "धन्यवाद! तुमचे वय किती आहे?",
        "employment_type": "तुमचा मुख्य व्यवसायाचा प्रकार काय आहे? उदा: नोकरी किंवा सैलरीड, व्यवसाय, किंवा स्वयंरोजगार?",
        "employment_duration_months": "तुम्ही तुमच्या सध्याच्या नोकरीत किंवा व्यवसायात किती वर्षे आहात? उदा: दोन वर्षे किंवा चोवीस महिने.",
        "monthly_income": "तुमचा मासिक सरासरी हातात येणारा पगार किंवा उत्पन्न किती आहे?",
        "existing_emis": "तुमच्यावर सध्या कोणती मासिक EMI किंवा किस्त चालू आहे का? असल्यास महिन्याला किती? नसल्यास शून्य किंवा नाही असे म्हणा.",
        "requested_amount": "तुम्हाला किती रक्कम कर्ज हवे आहे? उदा: पाच लाख किंवा दोन लाख.",
        "tenure_months": "तुम्ही हे कर्ज किती महिन्यांत किंवा वर्षांत फेडाल?",
        "loan_purpose": "या कर्जाचा उद्देश्य काय आहे? उदा: घर, शिक्षण, वैयक्तिक, व्यवसाय, किंवा वाहन?",
        "residence_type": "तुम्ही तुमच्या घरात कसे राहता — स्वतःचे, भाड्याने, किंवा कौटुंबिक?",
    },
}

MESSAGES: Dict[str, Dict[str, str]] = {
    "en-IN": {
        "confirm_value": "I heard {value}. Is that correct?",
        "confirm_clarify": "Please confirm with Yes or No: I recorded {value}. Is that correct?",
        "not_understood": "I didn't quite catch that. ",
        "retry": "Let's try that again. ",
        "complete": "Thank you! All details have been captured. Please review your entries on the screen before confirming submission.",
        "already_complete": "Your application details are already complete. Please verify them on screen and click submit.",
        "language_switched": "Switched to {language}. Everything captured so far is still saved. ",
    },
    "hi-IN": {
        "confirm_value": "मैंने {value} सुना। क्या यह सही है?",
        "confirm_clarify": "कृपया 'हाँ' या 'नहीं' से पुष्टि करें: मैंने {value} दर्ज किया है। क्या यह सही है?",
        "not_understood": "मुझे ठीक से समझ नहीं आया। ",
        "retry": "चलिए दोबारा कोशिश करते हैं। ",
        "complete": "धन्यवाद! सभी जानकारी दर्ज कर ली गई है। कृपया स्क्रीन पर अपनी जानकारी जाँच कर सबमिट करें।",
        "already_complete": "आपकी जानकारी पहले ही पूरी दर्ज हो चुकी है। कृपया स्क्रीन पर जाँच कर सबमिट बटन दबाएँ।",
        "language_switched": "अब हम {language} में बात करेंगे। अब तक दर्ज की गई जानकारी सुरक्षित है। ",
    },
    "mr-IN": {
        "confirm_value": "मला {value} ऐकलं. हे बरोबर आहे का?",
        "confirm_clarify": "कृपया 'हो' किंवा 'नाही' म्हणून खात्री द्या: मी {value} नोंदवलं आहे. हे बरोबर आहे का?",
        "not_understood": "मला नीट ऐकू आलं नाही. ",
        "retry": "चला पुन्हा प्रयत्न करूया. ",
        "complete": "धन्यवाद! सर्व माहिती नोंदवली गई आहे. कृपया स्क्रीनवर तुमची माहिती तपासून सबमिट करा.",
        "already_complete": "तुमची माहिती आधीच पूर्ण नोंदवली गई आहे. कृपया स्क्रीनवर तपासून सबमिट बटण दाबा.",
        "language_switched": "आता आपण {language} मध्ये बोलू. आत्तापर्यंत नोंदवलेली माहिती सुरक्षित आहे. ",
    },
}
