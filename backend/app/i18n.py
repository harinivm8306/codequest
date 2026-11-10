"""Fixed sentences the assistant says. Short on purpose: they are read aloud."""

from __future__ import annotations

MESSAGES: dict[str, dict[str, str]] = {
    "greeting": {
        "en": "Vanakkam! I am Sathi. Tell me a little about yourself — your age, where you live and your family.",
        "ta": "வணக்கம்! நான் சாதி. உங்களைப் பற்றி கொஞ்சம் சொல்லுங்கள் — உங்கள் வயது, ஊர், குடும்பம்.",
        "hi": "नमस्ते! मैं साथी हूँ। अपने बारे में थोड़ा बताइए — आपकी उम्र, आप कहाँ रहते हैं और आपका परिवार।",
    },
    "noted": {"en": "Noted.", "ta": "சரி, குறித்துக்கொண்டேன்.", "hi": "ठीक है, नोट कर लिया।"},
    "not_understood": {"en": "Sorry, I didn't catch that.", "ta": "மன்னிக்கவும், எனக்குப் புரியவில்லை.", "hi": "माफ़ कीजिए, मैं समझ नहीं पाया।"},
    "confirm_change": {
        "en": "Earlier you said {old}. Now you said {new}. Should I change it?",
        "ta": "முன்பு நீங்கள் {old} என்று சொன்னீர்கள். இப்போது {new} என்கிறீர்கள். மாற்றட்டுமா?",
        "hi": "पहले आपने {old} कहा था। अब आप {new} कह रहे हैं। क्या मैं बदल दूँ?",
    },
    "changed": {"en": "Updated.", "ta": "மாற்றிவிட்டேன்.", "hi": "बदल दिया।"},
    "kept": {"en": "OK, I kept your earlier answer.", "ta": "சரி, முந்தைய பதிலையே வைத்துக்கொண்டேன்.", "hi": "ठीक है, पहला जवाब ही रखा।"},
    "done": {
        "en": "Thank you. You may qualify for {n} schemes. Tap 'See my schemes'.",
        "ta": "நன்றி. நீங்கள் {n} திட்டங்களுக்குத் தகுதி பெறலாம். 'என் திட்டங்கள்' என்பதைத் தொடவும்.",
        "hi": "धन्यवाद। आप {n} योजनाओं के लिए पात्र हो सकते हैं। 'मेरी योजनाएँ' दबाएँ।",
    },
    "done_none": {
        "en": "Thank you. I could not find a scheme that fits yet. Tap 'See my schemes' to see what is close.",
        "ta": "நன்றி. இப்போது பொருந்தும் திட்டம் கிடைக்கவில்லை. நெருக்கமானவற்றைக் காண 'என் திட்டங்கள்' தொடவும்.",
        "hi": "धन्यवाद। अभी कोई उपयुक्त योजना नहीं मिली। करीबी योजनाएँ देखने के लिए 'मेरी योजनाएँ' दबाएँ।",
    },
    "yes": {"en": "Yes", "ta": "ஆம்", "hi": "हाँ"},
    "no": {"en": "No", "ta": "இல்லை", "hi": "नहीं"},
}


def t(key: str, lang: str, **kw) -> str:
    s = MESSAGES[key].get(lang) or MESSAGES[key]["en"]
    return s.format(**kw) if kw else s
