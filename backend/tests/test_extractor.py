"""Extraction tests: 30 sample utterances (10 per language) with expected facts.

These run against the deterministic keyword extractor in CI. To measure Claude,
run `python scripts/eval_extractor.py` with ANTHROPIC_API_KEY set.
The bar: 90%+ of expected fields correct, and zero invented sensitive facts.
"""

import pytest

from app.services import extractor

SENSITIVE = {"caste_category", "annual_family_income", "disability_percent", "bpl_card"}

# (language, pending question, utterance, expected facts)
CASES = [
    # English
    (
        "en",
        None,
        "My husband died last year, I am 62 and I live in Madurai",
        {"marital_status": "widowed", "age": 62, "gender": "female", "district": "Madurai"},
    ),
    ("en", None, "I'm 19, a first year B.Sc student in Salem", {"age": 19, "occupation": "student", "course_level": "ug", "district": "Salem"}),
    ("en", None, "I am a farmer with 2 acres", {"occupation": "farmer"}),
    ("en", "annual_family_income", "about 8 thousand a month", {"annual_family_income": 96000}),
    ("en", "annual_family_income", "1.5 lakh", {"annual_family_income": 150000}),
    ("en", "have", "I have a bank account and a ration card but no gas", {"has_bank_account": True, "bpl_card": True, "has_lpg_connection": False}),
    ("en", "family", "my son has a government job", {"family_govt_job": True}),
    ("en", "gender", "woman", {"gender": "female"}),
    ("en", "pregnant", "no", {"pregnant": False}),
    ("en", None, "I studied in a government school and now do a diploma", {"studied_govt_school": True, "course_level": "diploma"}),
    # Tamil
    ("ta", None, "என் கணவர் இறந்துவிட்டார், எனக்கு 62 வயது", {"marital_status": "widowed", "age": 62, "gender": "female"}),
    ("ta", None, "நான் சேலத்தில் கல்லூரியில் படிக்கிறேன்", {"occupation": "student", "district": "Salem"}),
    ("ta", None, "நான் விவசாயி", {"occupation": "farmer"}),
    ("ta", "annual_family_income", "மாதம் 5 ஆயிரம்", {"annual_family_income": 60000}),
    ("ta", "state", "ஆம்", {"state": "Tamil Nadu"}),
    ("ta", "land_acres", "நிலம் இல்லை", {"land_acres": 0}),
    ("ta", "have", "வங்கிக் கணக்கு இருக்கு, எரிவாயு இல்லை", {"has_bank_account": True, "has_lpg_connection": False}),
    ("ta", "family", "இவை எதுவும் இல்லை", {extractor.NONE_KEY: True}),
    ("ta", "marital_status", "திருமணமானவர்", {"marital_status": "married"}),
    ("ta", "age", "45", {"age": 45}),
    # Hindi
    ("hi", None, "मेरे पति की मृत्यु हो गई है, मेरी उम्र 58 साल है", {"marital_status": "widowed", "gender": "female", "age": 58}),
    ("hi", None, "मैं किसान हूँ", {"occupation": "farmer"}),
    ("hi", None, "मैं कॉलेज में पढ़ रहा हूँ", {"occupation": "student"}),
    ("hi", "annual_family_income", "2 लाख", {"annual_family_income": 200000}),
    ("hi", "gender", "महिला", {"gender": "female"}),
    ("hi", "pregnant", "हाँ", {"pregnant": True}),
    ("hi", "have", "बैंक खाता है और गैस कनेक्शन नहीं है", {"has_bank_account": True, "has_lpg_connection": False}),
    ("hi", "family", "कोई नहीं", {extractor.NONE_KEY: True}),
    ("hi", "state", "नहीं, दूसरा राज्य", {"state": "Other"}),
    ("hi", "girl_children_under_10", "2", {"girl_children_under_10": 2}),
]


@pytest.fixture(scope="module")
def results():
    out = []
    for lang, pending, text, expected in CASES:
        facts = extractor._validate(extractor.KeywordExtractor().extract(text, lang, pending), text, pending)
        out.append((lang, pending, text, expected, facts))
    return out


def test_accuracy_at_least_90_percent(results):
    total = correct = 0
    misses = []
    for _lang, _pending, text, expected, facts in results:
        for k, v in expected.items():
            total += 1
            if facts.get(k) == v:
                correct += 1
            else:
                misses.append((text, k, v, facts.get(k)))
    acc = correct / total
    print(f"\nkeyword extractor accuracy: {correct}/{total} = {acc:.0%}")
    assert acc >= 0.9, misses


def test_never_invents_sensitive_facts(results):
    for _lang, pending, text, expected, facts in results:
        invented = {k for k in facts if k in SENSITIVE and k not in expected and k != pending}
        assert not invented, (text, invented)


def test_unrelated_text_gives_nothing():
    assert extractor.KeywordExtractor().extract("hmm okay", "en", None) == {}
