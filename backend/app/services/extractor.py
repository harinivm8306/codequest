"""Turn what the citizen said into profile facts. Never decides eligibility.

Two extractors share one contract `extract(text, lang, pending) -> dict`:

* ClaudeExtractor — Claude with a forced tool call whose input schema is built
  from the field registry, so output is always structured. Used when
  ANTHROPIC_API_KEY is set.
* KeywordExtractor — deterministic patterns in Tamil, Hindi and English. Used
  when no key is set, when the LLM times out, and to fill gaps.

Both refuse to infer sensitive facts (caste, income, disability, BPL): those are
only recorded when the person states them, or answers the question about them.
Every value is validated against the field registry before it is returned.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.config import settings
from app.fields import FIELD_BY_NAME, FIELDS, GROUPS, TN_DISTRICTS, TRADE_LABELS, coerce

log = logging.getLogger(__name__)

NONE_KEY = "__none_of_these__"

YES_WORDS = {"yes", "yeah", "yep", "haan", "han", "ha", "ஆம்", "ஆமா", "ஆமாம்", "உண்டு", "இருக்கு", "இருக்கிறது", "உள்ளது", "हाँ", "हां", "जी", "true"}
NO_WORDS = {"no", "nope", "nahi", "nahin", "illa", "இல்லை", "இல்ல", "கிடையாது", "नहीं", "नही", "ना", "false", "none", "zero", "0"}
NONE_PHRASES = ["none of these", "none", "nothing", "no", "எதுவும் இல்லை", "ஒன்றும் இல்லை", "இல்லை", "कोई नहीं", "कुछ नहीं", "नहीं"]

# keyword -> (field, value). Matched as substrings on lowercased text.
KEYWORDS: list[tuple[str, str, Any]] = [
    # widowhood (also implies the speaker is a woman when phrased about a husband)
    ("widow", "marital_status", "widowed"),
    ("विधवा", "marital_status", "widowed"),
    ("விதவை", "marital_status", "widowed"),
    ("husband died", "marital_status", "widowed"),
    ("husband passed", "marital_status", "widowed"),
    ("husband is no more", "marital_status", "widowed"),
    ("கணவர் இறந்து", "marital_status", "widowed"),
    ("கணவர் இறந்த", "marital_status", "widowed"),
    ("கணவர் இல்லை", "marital_status", "widowed"),
    ("पति की मृत्यु", "marital_status", "widowed"),
    ("पति नहीं रहे", "marital_status", "widowed"),
    ("पति का देहांत", "marital_status", "widowed"),
    ("unmarried", "marital_status", "single"),
    ("not married", "marital_status", "single"),
    ("திருமணமாகாத", "marital_status", "single"),
    ("अविवाहित", "marital_status", "single"),
    ("divorced", "marital_status", "divorced"),
    ("விவாகரத்து", "marital_status", "divorced"),
    ("तलाक", "marital_status", "divorced"),
    ("married", "marital_status", "married"),
    ("திருமணமான", "marital_status", "married"),
    ("शादीशुदा", "marital_status", "married"),
    ("विवाहित", "marital_status", "married"),
    # gender
    ("i am a woman", "gender", "female"),
    ("i'm a woman", "gender", "female"),
    ("female", "gender", "female"),
    ("பெண்", "gender", "female"),
    ("महिला", "gender", "female"),
    ("औरत", "gender", "female"),
    ("my husband", "gender", "female"),
    ("என் கணவர்", "gender", "female"),
    ("கணவர்", "gender", "female"),
    ("मेरे पति", "gender", "female"),
    ("पति", "gender", "female"),
    ("i am a man", "gender", "male"),
    ("i'm a man", "gender", "male"),
    ("male", "gender", "male"),
    ("ஆண்", "gender", "male"),
    ("पुरुष", "gender", "male"),
    ("my wife", "gender", "male"),
    ("என் மனைவி", "gender", "male"),
    ("मेरी पत्नी", "gender", "male"),
    ("transgender", "gender", "other"),
    ("திருநங்கை", "gender", "other"),
    ("மூன்றாம் பாலின", "gender", "other"),
    ("ट्रांसजेंडर", "gender", "other"),
    ("किन्नर", "gender", "other"),
    # state
    ("tamil nadu", "state", "Tamil Nadu"),
    ("tamilnadu", "state", "Tamil Nadu"),
    ("தமிழ்நாடு", "state", "Tamil Nadu"),
    ("தமிழகம்", "state", "Tamil Nadu"),
    ("तमिलनाडु", "state", "Tamil Nadu"),
    ("another state", "state", "Other"),
    ("other state", "state", "Other"),
    ("வேறு மாநில", "state", "Other"),
    ("दूसरा राज्य", "state", "Other"),
    ("दूसरे राज्य", "state", "Other"),
    # occupation
    ("farmer", "occupation", "farmer"),
    ("farming", "occupation", "farmer"),
    ("விவசாய", "occupation", "farmer"),
    ("किसान", "occupation", "farmer"),
    ("खेती", "occupation", "farmer"),
    ("student", "occupation", "student"),
    ("studying", "occupation", "student"),
    ("college", "occupation", "student"),
    ("மாணவ", "occupation", "student"),
    ("படிக்கிறேன்", "occupation", "student"),
    ("கல்லூரி", "occupation", "student"),
    ("छात्र", "occupation", "student"),
    ("पढ़ रहा", "occupation", "student"),
    ("पढ़ रही", "occupation", "student"),
    ("कॉलेज", "occupation", "student"),
    ("daily wage", "occupation", "daily_wage"),
    ("coolie", "occupation", "daily_wage"),
    ("labour", "occupation", "daily_wage"),
    ("கூலி", "occupation", "daily_wage"),
    ("मज़दूर", "occupation", "daily_wage"),
    ("मजदूर", "occupation", "daily_wage"),
    ("दिहाड़ी", "occupation", "daily_wage"),
    ("homemaker", "occupation", "homemaker"),
    ("housewife", "occupation", "homemaker"),
    ("இல்லத்தரசி", "occupation", "homemaker"),
    ("गृहिणी", "occupation", "homemaker"),
    ("retired", "occupation", "retired"),
    ("ஓய்வு பெற்ற", "occupation", "retired"),
    ("सेवानिवृत्त", "occupation", "retired"),
    ("रिटायर", "occupation", "retired"),
    ("no work", "occupation", "unemployed"),
    ("unemployed", "occupation", "unemployed"),
    ("வேலை இல்லை", "occupation", "unemployed"),
    ("बेरोजगार", "occupation", "unemployed"),
    ("काम नहीं", "occupation", "unemployed"),
    ("own business", "occupation", "business"),
    ("shop", "occupation", "business"),
    ("சொந்தத் தொழில்", "occupation", "business"),
    ("कारोबार", "occupation", "business"),
    ("व्यापार", "occupation", "business"),
    ("दुकान", "occupation", "business"),
    ("salaried", "occupation", "salaried"),
    ("company job", "occupation", "salaried"),
    ("சம்பள", "occupation", "salaried"),
    ("नौकरी करता", "occupation", "salaried"),
    ("नौकरी करती", "occupation", "salaried"),
    ("artisan", "occupation", "artisan"),
    ("craft", "occupation", "artisan"),
    ("கைவினை", "occupation", "artisan"),
    ("कारीगर", "occupation", "artisan"),
    # course
    ("iti", "course_level", "iti"),
    ("ஐடிஐ", "course_level", "iti"),
    ("आईटीआई", "course_level", "iti"),
    ("diploma", "course_level", "diploma"),
    ("polytechnic", "course_level", "diploma"),
    ("பட்டய", "course_level", "diploma"),
    ("டிப்ளமோ", "course_level", "diploma"),
    ("डिप्लोमा", "course_level", "diploma"),
    ("b.a", "course_level", "ug"),
    ("b.sc", "course_level", "ug"),
    ("b.com", "course_level", "ug"),
    ("b.e", "course_level", "ug"),
    ("b.tech", "course_level", "ug"),
    ("degree", "course_level", "ug"),
    ("first year", "course_level", "ug"),
    ("பட்டப்படிப்பு", "course_level", "ug"),
    ("இளநிலை", "course_level", "ug"),
    ("स्नातक", "course_level", "ug"),
    ("m.a", "course_level", "pg"),
    ("m.sc", "course_level", "pg"),
    ("post graduate", "course_level", "pg"),
    ("முதுநிலை", "course_level", "pg"),
    ("स्नातकोत्तर", "course_level", "pg"),
    ("12th", "course_level", "class_11_12"),
    ("11th", "course_level", "class_11_12"),
    ("plus two", "course_level", "class_11_12"),
    ("பிளஸ் டூ", "course_level", "class_11_12"),
    ("12वीं", "course_level", "class_11_12"),
    ("11वीं", "course_level", "class_11_12"),
    ("government school", "studied_govt_school", True),
    ("govt school", "studied_govt_school", True),
    ("அரசுப் பள்ளி", "studied_govt_school", True),
    ("அரசு பள்ளி", "studied_govt_school", True),
    ("सरकारी स्कूल", "studied_govt_school", True),
    ("private school", "studied_govt_school", False),
    ("தனியார் பள்ளி", "studied_govt_school", False),
    ("प्राइवेट स्कूल", "studied_govt_school", False),
    ("निजी स्कूल", "studied_govt_school", False),
    # pregnancy
    ("pregnant", "pregnant", True),
    ("கர்ப்ப", "pregnant", True),
    ("गर्भवती", "pregnant", True),
    ("प्रेग्नेंट", "pregnant", True),
    # explicit sensitive statements (stated, never inferred)
    ("bpl", "bpl_card", True),
    ("antyodaya", "bpl_card", True),
    ("aay card", "bpl_card", True),
    ("phh", "bpl_card", True),
    ("बीपीएल", "bpl_card", True),
    ("अंत्योदय", "bpl_card", True),
    ("வறுமைக் கோட்டுக்குக் கீழ்", "bpl_card", True),
    ("bank account", "has_bank_account", True),
    ("வங்கிக் கணக்கு", "has_bank_account", True),
    ("வங்கி கணக்கு", "has_bank_account", True),
    ("बैंक खाता", "has_bank_account", True),
    ("बैंक में खाता", "has_bank_account", True),
    ("no gas", "has_lpg_connection", False),
    ("எரிவாயு இல்லை", "has_lpg_connection", False),
    ("गैस नहीं", "has_lpg_connection", False),
    ("gas connection", "has_lpg_connection", True),
    ("எரிவாயு இணைப்பு", "has_lpg_connection", True),
    ("गैस कनेक्शन", "has_lpg_connection", True),
    ("old age pension", "receives_social_pension", True),
    ("widow pension", "receives_social_pension", True),
    ("முதியோர் ஓய்வூதியம் பெறுகிறேன்", "receives_social_pension", True),
    ("no land", "land_acres", 0),
    ("நிலம் இல்லை", "land_acres", 0),
    ("ज़मीन नहीं", "land_acres", 0),
    ("जमीन नहीं", "land_acres", 0),
]
# words for "tap all that apply" items, used only while that group question is pending
GROUP_KEYWORDS: list[tuple[str, str, Any]] = [
    ("bank", "has_bank_account", True),
    ("post office", "has_bank_account", True),
    ("வங்கி", "has_bank_account", True),
    ("அஞ்சலக", "has_bank_account", True),
    ("बैंक", "has_bank_account", True),
    ("डाकघर", "has_bank_account", True),
    ("ration", "bpl_card", True),
    ("bpl", "bpl_card", True),
    ("phh", "bpl_card", True),
    ("aay", "bpl_card", True),
    ("குடும்ப அட்டை", "bpl_card", True),
    ("ரேஷன்", "bpl_card", True),
    ("राशन", "bpl_card", True),
    ("बीपीएल", "bpl_card", True),
    ("gas", "has_lpg_connection", True),
    ("lpg", "has_lpg_connection", True),
    ("cylinder", "has_lpg_connection", True),
    ("எரிவாயு", "has_lpg_connection", True),
    ("சிலிண்டர்", "has_lpg_connection", True),
    ("கேஸ்", "has_lpg_connection", True),
    ("गैस", "has_lpg_connection", True),
    ("सिलेंडर", "has_lpg_connection", True),
    ("income tax", "family_pays_income_tax", True),
    ("tax", "family_pays_income_tax", True),
    ("வருமான வரி", "family_pays_income_tax", True),
    ("आयकर", "family_pays_income_tax", True),
    ("इनकम टैक्स", "family_pays_income_tax", True),
    ("government job", "family_govt_job", True),
    ("govt job", "family_govt_job", True),
    ("அரசு வேலை", "family_govt_job", True),
    ("அரசுப் பணி", "family_govt_job", True),
    ("सरकारी नौकरी", "family_govt_job", True),
    ("car", "owns_four_wheeler", True),
    ("jeep", "owns_four_wheeler", True),
    ("tractor", "owns_four_wheeler", True),
    ("கார்", "owns_four_wheeler", True),
    ("ஜீப்", "owns_four_wheeler", True),
    ("டிராக்டர்", "owns_four_wheeler", True),
    ("कार", "owns_four_wheeler", True),
    ("ट्रैक्टर", "owns_four_wheeler", True),
    ("जीप", "owns_four_wheeler", True),
    ("mla", "family_elected_rep", True),
    ("mp", "family_elected_rep", True),
    ("councillor", "family_elected_rep", True),
    ("panchayat president", "family_elected_rep", True),
    ("கவுன்சிலர்", "family_elected_rep", True),
    ("ஊராட்சித் தலைவர்", "family_elected_rep", True),
    ("विधायक", "family_elected_rep", True),
    ("सांसद", "family_elected_rep", True),
    ("सरपंच", "family_elected_rep", True),
    ("doctor", "family_registered_professional", True),
    ("lawyer", "family_registered_professional", True),
    ("engineer", "family_registered_professional", True),
    ("chartered accountant", "family_registered_professional", True),
    ("மருத்துவர்", "family_registered_professional", True),
    ("டாக்டர்", "family_registered_professional", True),
    ("வழக்கறிஞர்", "family_registered_professional", True),
    ("பொறியாளர்", "family_registered_professional", True),
    ("डॉक्टर", "family_registered_professional", True),
    ("वकील", "family_registered_professional", True),
    ("इंजीनियर", "family_registered_professional", True),
    ("old age pension", "receives_social_pension", True),
    ("widow pension", "receives_social_pension", True),
    ("முதியோர் ஓய்வூதியம்", "receives_social_pension", True),
    ("விதவை ஓய்வூதியம்", "receives_social_pension", True),
    ("वृद्धा पेंशन", "receives_social_pension", True),
    ("विधवा पेंशन", "receives_social_pension", True),
]

NEGATORS_BEFORE = ("no ", "not ", "don't ", "dont ", "do not ", "never ", "without ", "नहीं ", "ना ")
NEGATORS_AFTER = ("இல்லை", "இல்ல", "கிடையாது", "नहीं", "नही", " no", " not")


def _polarity(word: str, t: str) -> bool | None:
    """True if `word` is mentioned affirmatively, False if negated, None if absent."""
    w = word.lower()
    m = None
    if re.fullmatch(r"[a-z0-9.'\s]+", w) and len(w) <= 4:
        m = re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", t)
    else:
        i = t.find(w)
        m = (i, i + len(w)) if i >= 0 else None
    if m is None:
        return None
    start, end = (m.start(), m.end()) if hasattr(m, "start") else m
    before, after = t[max(0, start - 12) : start], t[end : end + 14]
    if any(n in before for n in NEGATORS_BEFORE) or any(n in after for n in NEGATORS_AFTER):
        return False
    return True


# extra words that identify an option inside a specific question
OPTION_WORDS: dict[str, dict[Any, list[str]]] = {
    "gender": {
        "female": ["woman", "female", "பெண்", "महिला"],
        "male": ["man", "male", "ஆண்", "पुरुष"],
        "other": ["other", "trans", "மூன்றாம்", "திருநங்கை", "अन्य", "ट्रांस"],
    },
    "state": {
        "Tamil Nadu": ["yes", "ஆம்", "ஆமா", "हाँ", "हां", "tamil", "தமிழ்", "तमिल"],
        "Other": ["no", "இல்லை", "नहीं", "other", "another", "வேறு", "दूसरा", "दूसरे"],
    },
    "marital_status": {
        "married": ["married", "திருமணமான", "विवाहित", "शादीशुदा"],
        "single": ["single", "unmarried", "திருமணமாகாத", "अविवाहित"],
        "widowed": ["widow", "துணையை இழந்த", "விதவை", "கணவர் இல்லை", "विधवा", "विधुर"],
        "divorced": ["divorc", "separat", "விவாகரத்து", "பிரிந்த", "तलाक", "अलग"],
    },
    "land_irrigated": {True: ["wet", "irrigat", "நஞ்சை", "பாசன", "सिंचित", "गीली"], False: ["dry", "புஞ்சை", "असिंचित", "सूखी"]},
    "caste_category": {
        "SC": ["sc", "ஆதிதிராவிட", "अनुसूचित जाति", "दलित"],
        "ST": ["st", "பழங்குடி", "जनजाति", "आदिवासी"],
        "MBC": ["mbc", "மிகவும் பிற்படுத்த"],
        "BC": ["bc", "பிற்படுத்த"],
        "OBC": ["obc", "ओबीसी", "पिछड़ा"],
        "GEN": ["general", "gen", "oc", "பொது", "सामान्य"],
    },
}

AMOUNT_UNITS = [
    ("lakh", 100000),
    ("lakhs", 100000),
    ("lac", 100000),
    ("லட்சம்", 100000),
    ("லட்ச", 100000),
    ("लाख", 100000),
    ("thousand", 1000),
    ("ஆயிரம்", 1000),
    ("हज़ार", 1000),
    ("हजार", 1000),
    ("k", 1000),
]
PER_MONTH = ["per month", "a month", "monthly", "மாதம்", "மாதத்திற்கு", "महीना", "महीने", "मासिक"]


def _num_tokens(text: str) -> list[float]:
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text.replace(",", ""))]


def parse_amount(text: str) -> int | None:
    t = text.lower().replace(",", "")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(lakhs?|lac|லட்சம்|லட்ச|लाख|thousand|ஆயிரம்|हज़ार|हजार|k\b)?", t)
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2)
    if unit:
        value *= dict(AMOUNT_UNITS).get(unit, dict(AMOUNT_UNITS).get(unit.rstrip("s"), 1))
    if any(w in t for w in PER_MONTH):
        value *= 12
    return int(value)


def _yes_no(text: str) -> bool | None:
    words = set(re.findall(r"[\w஀-௿ऀ-ॿ']+", text.lower()))
    t = text.lower()
    has_no = bool(words & NO_WORDS) or any(p in t for p in ("இல்லை", "नहीं", "கிடையாது"))
    has_yes = bool(words & YES_WORDS) or any(p in t for p in ("ஆம்", "हाँ", "हां"))
    if has_no and not has_yes:
        return False
    if has_yes and not has_no:
        return True
    return None


class KeywordExtractor:
    name = "keywords"

    def extract(self, text: str, lang: str, pending: str | None) -> dict:
        t = " " + text.lower().strip() + " "
        facts: dict[str, Any] = {}

        # 1. answer to the pending question
        if pending in GROUPS:
            items = {f.name for f in FIELDS if f.group == pending}
            for f in FIELDS:
                if f.name not in items:
                    continue
                for opt in f.options:
                    if any(_loose_in(w.lower(), t) for w in opt.label.values()):
                        facts[f.name] = opt.value
            for kw, fld, val in GROUP_KEYWORDS:
                if fld in items and fld not in facts:
                    pol = _polarity(kw, t)
                    if pol is not None:
                        facts[fld] = val if pol else False
            if "pension" in t and "family_govt_pension" in items and "family_govt_pension" not in facts and "receives_social_pension" not in facts:
                amt = parse_amount(t)
                if amt:
                    facts["family_govt_pension"] = "10k_plus" if amt >= 10000 * (12 if any(w in t for w in PER_MONTH) else 1) else "below_10k"
            if not any(v is not False for v in facts.values()) and any(_loose_in(p, t) for p in NONE_PHRASES):
                facts[NONE_KEY] = True
        elif pending:
            f = FIELD_BY_NAME[pending]
            if f.type == "int":
                if pending == "annual_family_income":
                    v = parse_amount(t)
                    if v is not None:
                        facts[pending] = v
                else:
                    nums = _num_tokens(t)
                    if nums:
                        facts[pending] = int(nums[0])
                    elif _yes_no(t) is False:
                        facts[pending] = 0  # "no land", "no disability", "no daughters"
            elif f.type == "bool":
                v = _yes_no(t)
                if v is not None:
                    facts[pending] = v
            elif f.type == "enum":
                facts.update(self._match_enum(f.name, t))

        # 2. anything else the person volunteered
        for kw, fld, val in KEYWORDS:
            if fld in facts:
                continue
            if isinstance(val, bool):
                pol = _polarity(kw, t)
                if pol is not None:
                    facts[fld] = val if pol else (not val)
            elif _loose_in(kw, t):
                facts[fld] = val
        if "age" not in facts:
            m = re.search(r"(?:i am|i'm|age|aged|வயது|उम्र|आयु)\D{0,6}(\d{1,3})|(\d{1,3})\s*(?:years? old|yrs|வயது|வயசு|साल|वर्ष)", t)
            if m:
                facts["age"] = int(m.group(1) or m.group(2))
        if "district" not in facts:
            for d in TN_DISTRICTS:
                if d in t:
                    facts["district"] = d.title()
                    break
            for ta, d in TAMIL_DISTRICTS.items():
                if ta in t:
                    facts["district"] = d
        if "traditional_trade" not in facts:
            for trade, lab in TRADE_LABELS.items():
                if any(_loose_in(w.lower(), t) for w in lab.values()):
                    facts["traditional_trade"] = trade
                    facts.setdefault("occupation", "artisan")
                    break
        if "annual_family_income" not in facts and any(w in t for w in ("income", "earn", "வருமானம்", "சம்பாதி", "आय", "कमाई", "कमाते")):
            v = parse_amount(t)
            if v is not None and v >= 1000:
                facts["annual_family_income"] = v
        return facts

    def _match_enum(self, name: str, t: str) -> dict:
        f = FIELD_BY_NAME[name]
        words = OPTION_WORDS.get(name, {})
        best = None
        for opt in f.options:
            cands = [w.lower() for w in opt.label.values()] + [str(opt.value).lower()] + words.get(opt.value, [])
            if any(_loose_in(c, t) for c in cands):
                best = opt.value
                if name != "gender":  # "woman" contains "man": keep looking only for gender
                    break
                break
        if best is None and name == "occupation":
            for kw, fld, val in KEYWORDS:
                if fld == "occupation" and _loose_in(kw, t):
                    best = val
                    break
        return {name: best} if best is not None else {}


TAMIL_DISTRICTS = {
    "மதுரை": "Madurai",
    "சென்னை": "Chennai",
    "கோயம்புத்தூர்": "Coimbatore",
    "சேலம்": "Salem",
    "திருச்சி": "Tiruchirappalli",
    "திருவள்ளூர்": "Tiruvallur",
    "திருநெல்வேலி": "Tirunelveli",
    "தஞ்சாவூர்": "Thanjavur",
    "வேலூர்": "Vellore",
    "ஈரோடு": "Erode",
    "கன்னியாகுமரி": "Kanyakumari",
    "தூத்துக்குடி": "Thoothukudi",
    "திண்டுக்கல்": "Dindigul",
    "விழுப்புரம்": "Viluppuram",
}


def _loose_in(word: str, t: str) -> bool:
    """Word match: whole-word for short Latin tokens, substring for others."""
    w = word.lower().strip()
    if not w:
        return False
    if re.fullmatch(r"[a-z0-9.'\s]+", w) and len(w) <= 4:
        return re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", t) is not None
    return w in t


# --------------------------------------------------------------------------- Claude
SYSTEM_PROMPT = """You extract facts for an Indian welfare-scheme eligibility form.
The user may speak Tamil, Hindi, English or a mix. Call record_facts exactly once.
Rules:
- Record only facts the user actually stated in this message. Use null for anything not said.
- Never guess caste_category, annual_family_income, disability_percent or bpl_card. Record them only if the user states them or directly answers a question about them.
- annual_family_income is in rupees per YEAR for the whole family. Convert "10 thousand a month" to 120000.
- If the question was a 'tap all that apply' list and the user says none apply, set none_of_these to true.
- A short reply like "yes", "62" or "ஆம்" answers the pending question.
"""


def _tool_schema() -> dict:
    props: dict[str, Any] = {}
    for f in FIELDS:
        if f.type == "int":
            t: dict[str, Any] = {"type": ["integer", "null"]}
        elif f.type == "bool":
            t = {"type": ["boolean", "null"]}
        elif f.type == "enum":
            t = {"type": ["string", "null"], "enum": list(f.enum) + [None]}
        else:
            t = {"type": ["string", "null"]}
        t["description"] = f.description
        props[f.name] = t
    props["none_of_these"] = {"type": "boolean", "description": "User said none of the listed items apply"}
    return {"type": "object", "properties": props}


class ClaudeExtractor:
    name = "claude"

    def __init__(self) -> None:
        import anthropic

        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=settings.llm_timeout_s, max_retries=1)

    def extract(self, text: str, lang: str, pending: str | None) -> dict:
        q = ""
        if pending in GROUPS:
            items = ", ".join(f.name for f in FIELDS if f.group == pending)
            q = f"Pending question (tap all that apply): {GROUPS[pending]['question']['en']} Items: {items}."
        elif pending:
            f = FIELD_BY_NAME[pending]
            q = f"Pending question: {(f.question or {}).get('en', pending)} (field: {pending})."
        msg = self.client.messages.create(
            model=settings.anthropic_model,
            max_tokens=600,
            system=SYSTEM_PROMPT,
            tools=[{"name": "record_facts", "description": "Record facts the user stated.", "input_schema": _tool_schema()}],
            tool_choice={"type": "tool", "name": "record_facts"},
            messages=[{"role": "user", "content": f"{q}\nUser said ({lang}): {text}"}],
        )
        raw = next((b.input for b in msg.content if getattr(b, "type", "") == "tool_use"), {}) or {}
        out = {k: v for k, v in raw.items() if v is not None and k != "none_of_these"}
        if raw.get("none_of_these"):
            out[NONE_KEY] = True
        return out


def _validate(facts: dict, text: str, pending: str | None) -> dict:
    clean: dict[str, Any] = {}
    for k, v in facts.items():
        if k == NONE_KEY:
            clean[k] = True
            continue
        f = FIELD_BY_NAME.get(k)
        if f is None:
            continue
        try:
            clean[k] = coerce(f, v)
        except (ValueError, TypeError):
            log.info("dropped invalid %s=%r", k, v)
    return clean


_keyword = KeywordExtractor()
_claude: ClaudeExtractor | None = None


def extract(text: str, lang: str, pending: str | None) -> tuple[dict, str]:
    """Returns (facts, extractor_name). Claude first if configured; keywords fill gaps."""
    global _claude
    base = _validate(_keyword.extract(text, lang, pending), text, pending)
    if not settings.llm_enabled:
        return base, "keywords"
    try:
        if _claude is None:
            _claude = ClaudeExtractor()
        llm = _validate(_claude.extract(text, lang, pending), text, pending)
        merged = {**base, **llm}
        return merged, "claude"
    except Exception as exc:  # network, timeout, quota: never break the conversation
        log.warning("LLM extraction failed, using keywords: %s", exc)
        return base, "keywords"


def tool_schema_json() -> str:
    return json.dumps(_tool_schema(), ensure_ascii=False)
