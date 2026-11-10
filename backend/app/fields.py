"""Every fact SchemeSathi may ask about, in one place.

This registry drives four things, so they can never drift apart:
  1. the Profile model (types and allowed values),
  2. the LLM extraction schema,
  3. the follow-up questions and their quick-reply chips (in ta / hi / en),
  4. the rule files, which may only reference fields defined here (tested).

Some yes/no facts are asked together as one multi-select "group" question
("Which of these apply to your family?") so a citizen answers 7 exclusion
checks with one tap. Unticked items are recorded as False, never guessed.

Translations: Tamil and Hindi strings were written for the prototype and
should be reviewed by a native speaker before a field pilot.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

L = dict[str, str]  # {"en": ..., "ta": ..., "hi": ...}


@dataclass(frozen=True)
class Option:
    value: Any
    label: L


@dataclass(frozen=True)
class Field:
    name: str
    type: str  # "int" | "bool" | "enum" | "str"
    question: L | None = None
    options: tuple[Option, ...] = ()
    group: str | None = None  # asked inside a multi-select group question
    sensitive: bool = False  # never inferred by the extractor
    description: str = ""  # for the LLM schema
    enum: tuple[str, ...] = ()


YES = Option(True, {"en": "Yes", "ta": "ஆம்", "hi": "हाँ"})
NO = Option(False, {"en": "No", "ta": "இல்லை", "hi": "नहीं"})

TRADES = (
    "carpenter",
    "boat_maker",
    "armourer",
    "blacksmith",
    "hammer_toolkit_maker",
    "locksmith",
    "goldsmith",
    "potter",
    "sculptor_stone_carver",
    "cobbler",
    "mason",
    "basket_mat_broom_coir_maker",
    "doll_toy_maker",
    "barber",
    "garland_maker",
    "washerman",
    "tailor",
    "fishing_net_maker",
)
TRADE_LABELS: dict[str, L] = {
    "carpenter": {"en": "Carpenter", "ta": "தச்சர்", "hi": "बढ़ई"},
    "boat_maker": {"en": "Boat maker", "ta": "படகு செய்பவர்", "hi": "नाव बनाने वाले"},
    "armourer": {"en": "Armourer", "ta": "ஆயுதம் செய்பவர்", "hi": "अस्त्रकार"},
    "blacksmith": {"en": "Blacksmith", "ta": "கொல்லர்", "hi": "लोहार"},
    "hammer_toolkit_maker": {"en": "Hammer & tool kit maker", "ta": "சுத்தி / கருவி செய்பவர்", "hi": "हथौड़ा और टूलकिट निर्माता"},
    "locksmith": {"en": "Locksmith", "ta": "பூட்டு செய்பவர்", "hi": "ताला बनाने वाले"},
    "goldsmith": {"en": "Goldsmith", "ta": "பொற்கொல்லர்", "hi": "सुनार"},
    "potter": {"en": "Potter", "ta": "குயவர்", "hi": "कुम्हार"},
    "sculptor_stone_carver": {"en": "Sculptor / stone carver", "ta": "சிற்பி / கல் தச்சர்", "hi": "मूर्तिकार / पत्थर तराश"},
    "cobbler": {"en": "Cobbler / footwear maker", "ta": "செருப்பு தைப்பவர்", "hi": "मोची"},
    "mason": {"en": "Mason", "ta": "கொத்தனார்", "hi": "राजमिस्त्री"},
    "basket_mat_broom_coir_maker": {
        "en": "Basket / mat / broom / coir maker",
        "ta": "கூடை / பாய் / துடைப்பம் / கயிறு செய்பவர்",
        "hi": "टोकरी / चटाई / झाड़ू / कॉयर बुनकर",
    },
    "doll_toy_maker": {"en": "Traditional doll & toy maker", "ta": "பொம்மை செய்பவர்", "hi": "पारंपरिक गुड़िया-खिलौना निर्माता"},
    "barber": {"en": "Barber", "ta": "நாவிதர்", "hi": "नाई"},
    "garland_maker": {"en": "Garland maker", "ta": "மாலை கட்டுபவர்", "hi": "माला बनाने वाले"},
    "washerman": {"en": "Washerman", "ta": "சலவைத் தொழிலாளி", "hi": "धोबी"},
    "tailor": {"en": "Tailor", "ta": "தையல்காரர்", "hi": "दर्जी"},
    "fishing_net_maker": {"en": "Fishing net maker", "ta": "மீன்வலை செய்பவர்", "hi": "मछली जाल निर्माता"},
}

FIELDS: list[Field] = [
    Field("name", "str", description="Applicant's full name exactly as on documents"),
    Field("district", "str", description="District of residence, e.g. Madurai"),
    Field(
        "age",
        "int",
        description="Age in completed years",
        question={"en": "How old are you?", "ta": "உங்கள் வயது என்ன?", "hi": "आपकी उम्र कितनी है?"},
    ),
    Field(
        "gender",
        "enum",
        enum=("female", "male", "other"),
        description="Gender of the applicant",
        question={"en": "Are you a woman, a man, or other?", "ta": "நீங்கள் பெண்ணா, ஆணா, அல்லது மற்றவரா?", "hi": "आप महिला हैं, पुरुष हैं, या अन्य?"},
        options=(
            Option("female", {"en": "Woman", "ta": "பெண்", "hi": "महिला"}),
            Option("male", {"en": "Man", "ta": "ஆண்", "hi": "पुरुष"}),
            Option("other", {"en": "Other / transgender", "ta": "மூன்றாம் பாலினம்", "hi": "अन्य / ट्रांसजेंडर"}),
        ),
    ),
    Field(
        "state",
        "enum",
        enum=("Tamil Nadu", "Other"),
        description="'Tamil Nadu' if the applicant lives in Tamil Nadu, otherwise 'Other'",
        question={"en": "Do you live in Tamil Nadu?", "ta": "நீங்கள் தமிழ்நாட்டில் வசிக்கிறீர்களா?", "hi": "क्या आप तमिलनाडु में रहते हैं?"},
        options=(
            Option("Tamil Nadu", {"en": "Yes, Tamil Nadu", "ta": "ஆம், தமிழ்நாடு", "hi": "हाँ, तमिलनाडु"}),
            Option("Other", {"en": "Another state", "ta": "வேறு மாநிலம்", "hi": "दूसरा राज्य"}),
        ),
    ),
    Field(
        "marital_status",
        "enum",
        enum=("single", "married", "widowed", "divorced"),
        description="Marital status. 'widowed' if their spouse has died.",
        question={
            "en": "Are you married, single, widowed or divorced?",
            "ta": "நீங்கள் திருமணமானவரா, திருமணமாகாதவரா, கணவர்/மனைவியை இழந்தவரா, அல்லது விவாகரத்தானவரா?",
            "hi": "आप विवाहित हैं, अविवाहित, विधवा/विधुर या तलाकशुदा?",
        },
        options=(
            Option("married", {"en": "Married", "ta": "திருமணமானவர்", "hi": "विवाहित"}),
            Option("single", {"en": "Single", "ta": "திருமணமாகாதவர்", "hi": "अविवाहित"}),
            Option("widowed", {"en": "Widowed", "ta": "துணையை இழந்தவர்", "hi": "विधवा / विधुर"}),
            Option("divorced", {"en": "Divorced / separated", "ta": "விவாகரத்து / பிரிந்தவர்", "hi": "तलाकशुदा / अलग"}),
        ),
    ),
    Field(
        "annual_family_income",
        "int",
        sensitive=True,
        description="Total yearly income of the whole family in rupees. Only if the user states it.",
        question={
            "en": "Roughly how much does your whole family earn in a year?",
            "ta": "உங்கள் குடும்பத்தின் மொத்த ஆண்டு வருமானம் சுமார் எவ்வளவு?",
            "hi": "आपके पूरे परिवार की सालाना आमदनी लगभग कितनी है?",
        },
        options=(
            Option(100000, {"en": "Below ₹1.2 lakh", "ta": "₹1.2 லட்சத்திற்கு கீழ்", "hi": "₹1.2 लाख से कम"}),
            Option(200000, {"en": "₹1.2 – 2.5 lakh", "ta": "₹1.2 – 2.5 லட்சம்", "hi": "₹1.2 – 2.5 लाख"}),
            Option(500000, {"en": "₹2.5 – 8 lakh", "ta": "₹2.5 – 8 லட்சம்", "hi": "₹2.5 – 8 लाख"}),
            Option(900000, {"en": "Above ₹8 lakh", "ta": "₹8 லட்சத்திற்கு மேல்", "hi": "₹8 लाख से अधिक"}),
        ),
    ),
    Field(
        "caste_category",
        "enum",
        enum=("GEN", "OBC", "BC", "MBC", "SC", "ST"),
        sensitive=True,
        description="Community category as on the community certificate. Only if stated.",
        question={
            "en": "Which community category is on your certificate?",
            "ta": "உங்கள் சாதிச் சான்றிதழில் உள்ள பிரிவு எது?",
            "hi": "आपके जाति प्रमाणपत्र पर कौन सी श्रेणी है?",
        },
        options=(
            Option("SC", {"en": "SC", "ta": "SC (ஆதிதிராவிடர்)", "hi": "SC (अनुसूचित जाति)"}),
            Option("ST", {"en": "ST", "ta": "ST (பழங்குடியினர்)", "hi": "ST (अनुसूचित जनजाति)"}),
            Option("MBC", {"en": "MBC", "ta": "MBC", "hi": "MBC"}),
            Option("BC", {"en": "BC", "ta": "BC", "hi": "BC"}),
            Option("OBC", {"en": "OBC", "ta": "OBC", "hi": "OBC"}),
            Option("GEN", {"en": "General", "ta": "பொது (OC)", "hi": "सामान्य"}),
        ),
    ),
    Field(
        "occupation",
        "enum",
        enum=("farmer", "artisan", "daily_wage", "homemaker", "student", "salaried", "business", "unemployed", "retired", "other"),
        description="Main occupation. 'artisan' for traditional crafts (tailor, potter, carpenter...). 'student' if studying.",
        question={"en": "What do you do for a living?", "ta": "நீங்கள் என்ன வேலை செய்கிறீர்கள்?", "hi": "आप क्या काम करते हैं?"},
        options=(
            Option("farmer", {"en": "Farming", "ta": "விவசாயம்", "hi": "खेती"}),
            Option("artisan", {"en": "Craft / artisan work", "ta": "கைவினைத் தொழில்", "hi": "कारीगरी"}),
            Option("daily_wage", {"en": "Daily wage work", "ta": "தினக்கூலி", "hi": "दिहाड़ी मज़दूरी"}),
            Option("homemaker", {"en": "Home maker", "ta": "இல்லத்தரசி", "hi": "गृहिणी"}),
            Option("student", {"en": "Student", "ta": "மாணவர்", "hi": "छात्र"}),
            Option("salaried", {"en": "Salaried job", "ta": "சம்பள வேலை", "hi": "नौकरी"}),
            Option("business", {"en": "Own business", "ta": "சொந்தத் தொழில்", "hi": "अपना व्यापार"}),
            Option("unemployed", {"en": "No work now", "ta": "தற்போது வேலை இல்லை", "hi": "अभी काम नहीं"}),
            Option("retired", {"en": "Retired", "ta": "ஓய்வு பெற்றவர்", "hi": "सेवानिवृत्त"}),
        ),
    ),
    Field(
        "traditional_trade",
        "enum",
        enum=TRADES + ("none",),
        description="Which of the 18 PM Vishwakarma traditional trades, if any",
        question={"en": "Which craft do you work in?", "ta": "நீங்கள் எந்தக் கைவினைத் தொழில் செய்கிறீர்கள்?", "hi": "आप कौन सी कारीगरी करते हैं?"},
        options=tuple(Option(t, TRADE_LABELS[t]) for t in TRADES) + (Option("none", {"en": "Something else", "ta": "வேறு தொழில்", "hi": "कुछ और"}),),
    ),
    Field(
        "course_level",
        "enum",
        enum=("school", "class_11_12", "iti", "diploma", "ug", "pg", "none"),
        description="Current course: school (up to class 10), class_11_12, iti, diploma, ug (degree), pg",
        question={"en": "What are you studying now?", "ta": "நீங்கள் இப்போது என்ன படிக்கிறீர்கள்?", "hi": "आप अभी क्या पढ़ रहे हैं?"},
        options=(
            Option("school", {"en": "School (up to 10th)", "ta": "பள்ளி (10ஆம் வகுப்பு வரை)", "hi": "स्कूल (10वीं तक)"}),
            Option("class_11_12", {"en": "11th / 12th", "ta": "11 / 12ஆம் வகுப்பு", "hi": "11वीं / 12वीं"}),
            Option("iti", {"en": "ITI", "ta": "ஐடிஐ", "hi": "आईटीआई"}),
            Option("diploma", {"en": "Diploma", "ta": "பட்டயப் படிப்பு", "hi": "डिप्लोमा"}),
            Option("ug", {"en": "Degree (UG)", "ta": "இளநிலைப் பட்டம்", "hi": "स्नातक"}),
            Option("pg", {"en": "Post-graduate", "ta": "முதுநிலைப் பட்டம்", "hi": "स्नातकोत्तर"}),
        ),
    ),
    Field(
        "studied_govt_school",
        "bool",
        description="Studied classes 6 to 12 in a Tamil Nadu government school (or government-aided Tamil-medium school)",
        question={
            "en": "Did you study from 6th to 12th in a government school (or a government-aided Tamil-medium school)?",
            "ta": "நீங்கள் 6 முதல் 12ஆம் வகுப்பு வரை அரசுப் பள்ளியில் (அல்லது அரசு உதவி பெறும் தமிழ்வழிப் பள்ளியில்) படித்தீர்களா?",
            "hi": "क्या आपने 6वीं से 12वीं तक सरकारी स्कूल (या सरकारी सहायता प्राप्त तमिल माध्यम स्कूल) में पढ़ाई की?",
        },
        options=(YES, NO),
    ),
    Field(
        "land_acres",
        "int",
        description="Acres of farm land the family owns (0 if none). Round to nearest whole acre.",
        question={
            "en": "Does your family own farm land? If yes, how many acres?",
            "ta": "உங்கள் குடும்பத்திற்கு விவசாய நிலம் உள்ளதா? இருந்தால் எத்தனை ஏக்கர்?",
            "hi": "क्या आपके परिवार के पास खेती की ज़मीन है? हो तो कितने एकड़?",
        },
        options=(
            Option(0, {"en": "No land", "ta": "நிலம் இல்லை", "hi": "ज़मीन नहीं"}),
            Option(2, {"en": "Up to 2 acres", "ta": "2 ஏக்கர் வரை", "hi": "2 एकड़ तक"}),
            Option(5, {"en": "2 – 5 acres", "ta": "2 – 5 ஏக்கர்", "hi": "2 – 5 एकड़"}),
            Option(10, {"en": "5 – 10 acres", "ta": "5 – 10 ஏக்கர்", "hi": "5 – 10 एकड़"}),
            Option(11, {"en": "More than 10 acres", "ta": "10 ஏக்கருக்கு மேல்", "hi": "10 एकड़ से अधिक"}),
        ),
    ),
    Field(
        "land_irrigated",
        "bool",
        description="True if the land is wet/irrigated (nanjai), False if dry (punjai)",
        question={"en": "Is the land wet (irrigated) land?", "ta": "அது நஞ்சை (பாசன) நிலமா?", "hi": "क्या वह सिंचित (गीली) ज़मीन है?"},
        options=(
            Option(True, {"en": "Wet / irrigated", "ta": "நஞ்சை", "hi": "सिंचित"}),
            Option(False, {"en": "Dry land", "ta": "புஞ்சை", "hi": "असिंचित"}),
        ),
    ),
    Field(
        "disability_percent",
        "int",
        sensitive=True,
        description="Disability percentage on the disability certificate, 0 if none. Only if stated.",
        question={
            "en": "Do you have a disability certificate? What percentage?",
            "ta": "உங்களிடம் மாற்றுத்திறனாளி சான்றிதழ் உள்ளதா? எத்தனை சதவீதம்?",
            "hi": "क्या आपके पास विकलांगता प्रमाणपत्र है? कितने प्रतिशत?",
        },
        options=(
            Option(0, {"en": "No disability", "ta": "இல்லை", "hi": "नहीं"}),
            Option(20, {"en": "Below 40%", "ta": "40%க்கு கீழ்", "hi": "40% से कम"}),
            Option(40, {"en": "40% – 79%", "ta": "40% – 79%", "hi": "40% – 79%"}),
            Option(80, {"en": "80% or more", "ta": "80% அல்லது அதிகம்", "hi": "80% या अधिक"}),
        ),
    ),
    Field(
        "girl_children_under_10",
        "int",
        description="Number of daughters under 10 years old the applicant is parent or legal guardian of",
        question={
            "en": "How many daughters under 10 years old do you have?",
            "ta": "உங்களுக்கு 10 வயதுக்குட்பட்ட எத்தனை மகள்கள் உள்ளனர்?",
            "hi": "आपकी 10 साल से कम उम्र की कितनी बेटियाँ हैं?",
        },
        options=(
            Option(0, {"en": "None", "ta": "இல்லை", "hi": "कोई नहीं"}),
            Option(1, {"en": "1", "ta": "1", "hi": "1"}),
            Option(2, {"en": "2 or more", "ta": "2 அல்லது அதிகம்", "hi": "2 या अधिक"}),
        ),
    ),
    Field(
        "pregnant",
        "bool",
        description="True if the applicant is currently pregnant",
        question={"en": "Are you pregnant now?", "ta": "நீங்கள் இப்போது கர்ப்பமாக இருக்கிறீர்களா?", "hi": "क्या आप अभी गर्भवती हैं?"},
        options=(YES, NO),
    ),
    # -- "Which of these do you have?" group ---------------------------------
    Field(
        "has_bank_account",
        "bool",
        group="have",
        description="Has a savings bank or post office account",
        options=(Option(True, {"en": "Bank or post office account", "ta": "வங்கி / அஞ்சலகக் கணக்கு", "hi": "बैंक या डाकघर खाता"}),),
    ),
    Field(
        "bpl_card",
        "bool",
        group="have",
        sensitive=True,
        description="Has a BPL / priority household (PHH) or Antyodaya (AAY) ration card. Only if stated.",
        options=(Option(True, {"en": "PHH / AAY (BPL) ration card", "ta": "PHH / AAY (வறுமைக் கோட்டுக்குக் கீழ்) குடும்ப அட்டை", "hi": "BPL / अंत्योदय राशन कार्ड"}),),
    ),
    Field(
        "has_lpg_connection",
        "bool",
        group="have",
        description="Household already has an LPG gas connection",
        options=(Option(True, {"en": "LPG gas connection at home", "ta": "வீட்டில் எரிவாயு இணைப்பு", "hi": "घर में LPG गैस कनेक्शन"}),),
    ),
    # -- "Does any of this apply to your family?" group ----------------------
    Field(
        "family_pays_income_tax",
        "bool",
        group="family",
        description="Anyone in the family paid income tax in the last assessment year",
        options=(Option(True, {"en": "Someone pays income tax", "ta": "யாரேனும் வருமான வரி செலுத்துகிறார்கள்", "hi": "कोई आयकर भरता है"}),),
    ),
    Field(
        "family_govt_job",
        "bool",
        group="family",
        description="Anyone in the family has a central/state government, PSU, bank or local-body job",
        options=(Option(True, {"en": "Someone has a government job", "ta": "யாரேனும் அரசு வேலையில் உள்ளனர்", "hi": "किसी की सरकारी नौकरी है"}),),
    ),
    Field(
        "family_govt_pension",
        "enum",
        group="family",
        enum=("none", "below_10k", "10k_plus"),
        description="Government (service) pension in the family: none, below_10k or 10k_plus per month",
        options=(
            Option("below_10k", {"en": "Government pension below ₹10,000/month", "ta": "அரசு ஓய்வூதியம் ₹10,000க்கு கீழ்", "hi": "₹10,000 से कम सरकारी पेंशन"}),
            Option("10k_plus", {"en": "Government pension ₹10,000+/month", "ta": "அரசு ஓய்வூதியம் ₹10,000 அல்லது அதிகம்", "hi": "₹10,000 या अधिक सरकारी पेंशन"}),
        ),
    ),
    Field(
        "receives_social_pension",
        "bool",
        group="family",
        description="Applicant already receives an old-age, widow, disability or welfare-board pension",
        options=(
            Option(
                True,
                {
                    "en": "I already get an old-age / widow / disability pension",
                    "ta": "நான் ஏற்கனவே முதியோர் / விதவை / மாற்றுத்திறனாளி ஓய்வூதியம் பெறுகிறேன்",
                    "hi": "मुझे पहले से वृद्धा / विधवा / विकलांग पेंशन मिलती है",
                },
            ),
        ),
    ),
    Field(
        "owns_four_wheeler",
        "bool",
        group="family",
        description="Family owns a car, jeep, tractor or other four-wheeler",
        options=(Option(True, {"en": "We own a car / jeep / tractor", "ta": "எங்களிடம் கார் / ஜீப் / டிராக்டர் உள்ளது", "hi": "हमारे पास कार / जीप / ट्रैक्टर है"}),),
    ),
    Field(
        "family_elected_rep",
        "bool",
        group="family",
        description="Anyone in the family is or was an MP, MLA, minister, mayor or local body head/member",
        options=(
            Option(
                True, {"en": "Someone is an MP / MLA / elected member", "ta": "யாரேனும் MP / MLA / உள்ளாட்சி உறுப்பினர்", "hi": "कोई सांसद / विधायक / निर्वाचित सदस्य है"}
            ),
        ),
    ),
    Field(
        "family_registered_professional",
        "bool",
        group="family",
        description="Anyone in the family is a registered doctor, engineer, lawyer, chartered accountant or architect",
        options=(
            Option(
                True,
                {
                    "en": "Someone is a doctor / engineer / lawyer / CA",
                    "ta": "யாரேனும் மருத்துவர் / பொறியாளர் / வழக்கறிஞர் / CA",
                    "hi": "कोई डॉक्टर / इंजीनियर / वकील / CA है",
                },
            ),
        ),
    ),
    # -- self versions, asked only when the family answer was "yes" ----------
    Field(
        "pays_income_tax",
        "bool",
        description="The applicant personally has paid income tax",
        question={"en": "Do you yourself pay income tax?", "ta": "நீங்களே வருமான வரி செலுத்துகிறீர்களா?", "hi": "क्या आप स्वयं आयकर भरते हैं?"},
        options=(YES, NO),
    ),
    Field(
        "govt_job",
        "bool",
        description="The applicant personally has a government or PSU job",
        question={
            "en": "Do you yourself have a government or PSU job?",
            "ta": "நீங்களே அரசு அல்லது பொதுத்துறை வேலையில் உள்ளீர்களா?",
            "hi": "क्या आपकी स्वयं सरकारी या PSU नौकरी है?",
        },
        options=(YES, NO),
    ),
]

FIELD_BY_NAME: dict[str, Field] = {f.name: f for f in FIELDS}

GROUPS: dict[str, dict] = {
    "have": {
        "question": {
            "en": "Which of these do you have? Tap all that apply.",
            "ta": "இவற்றில் உங்களிடம் எவை உள்ளன? பொருந்தும் அனைத்தையும் தொடவும்.",
            "hi": "इनमें से आपके पास क्या है? जो लागू हों सब चुनें।",
        },
        "none_value": False,
    },
    "family": {
        "question": {
            "en": "Does any of this apply to you or your family? Tap all that apply.",
            "ta": "இவற்றில் ஏதேனும் உங்களுக்கோ உங்கள் குடும்பத்திற்கோ பொருந்துமா? பொருந்தும் அனைத்தையும் தொடவும்.",
            "hi": "क्या इनमें से कुछ आप पर या आपके परिवार पर लागू होता है? सब चुनें।",
        },
        "none_value": False,
    },
}
NONE_OF_THESE: L = {"en": "None of these", "ta": "இவை எதுவும் இல்லை", "hi": "इनमें से कोई नहीं"}

# Tie-break order when two questions unlock the same number of schemes.
PRIORITY = [
    "age",
    "gender",
    "state",
    "marital_status",
    "have",
    "annual_family_income",
    "occupation",
    "caste_category",
    "course_level",
    "studied_govt_school",
    "land_acres",
    "land_irrigated",
    "disability_percent",
    "girl_children_under_10",
    "pregnant",
    "traditional_trade",
    "family",
    "pays_income_tax",
    "govt_job",
]

TN_DISTRICTS = {
    "ariyalur",
    "chengalpattu",
    "chennai",
    "coimbatore",
    "cuddalore",
    "dharmapuri",
    "dindigul",
    "erode",
    "kallakurichi",
    "kanchipuram",
    "kanyakumari",
    "karur",
    "krishnagiri",
    "madurai",
    "mayiladuthurai",
    "nagapattinam",
    "namakkal",
    "nilgiris",
    "perambalur",
    "pudukkottai",
    "ramanathapuram",
    "ranipet",
    "salem",
    "sivaganga",
    "tenkasi",
    "thanjavur",
    "theni",
    "thoothukudi",
    "tiruchirappalli",
    "tirunelveli",
    "tirupathur",
    "tiruppur",
    "tiruvallur",
    "tiruvannamalai",
    "tiruvarur",
    "vellore",
    "viluppuram",
    "virudhunagar",
}


def default_for_group_item(f: Field) -> Any:
    """Value recorded for an item the citizen did NOT tick in a group question."""
    if f.name == "family_govt_pension":
        return "none"
    return False


def coerce(f: Field, value: Any) -> Any:
    """Validate and normalise a value for a field. Raises ValueError if invalid."""
    if value is None:
        return None
    if f.type == "int":
        if isinstance(value, bool):
            raise ValueError(f"{f.name}: bool is not int")
        v = int(round(float(value)))
        if v < 0 or (f.name == "age" and v > 120) or (f.name == "disability_percent" and v > 100):
            raise ValueError(f"{f.name}: out of range")
        return v
    if f.type == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in ("true", "yes"):
            return True
        if isinstance(value, str) and value.lower() in ("false", "no"):
            return False
        raise ValueError(f"{f.name}: not a bool")
    if f.type == "enum":
        if value not in f.enum:
            raise ValueError(f"{f.name}: {value!r} not in {f.enum}")
        return value
    return str(value).strip()[:120]


def normalise(profile: dict) -> dict:
    """Apply safe, logically certain derivations. Never guesses sensitive facts."""
    p = dict(profile)
    # self <-> family consistency
    for self_f, fam_f in (("pays_income_tax", "family_pays_income_tax"), ("govt_job", "family_govt_job")):
        if p.get(self_f) is True:
            p[fam_f] = True
        if p.get(fam_f) is False:
            p[self_f] = False
    # a district in Tamil Nadu implies the state
    d = (p.get("district") or "").lower().replace(" district", "").strip()
    if p.get("state") is None and d in TN_DISTRICTS:
        p["state"] = "Tamil Nadu"
    # only women can be pregnant; pregnancy after 55 is treated as not applicable
    if p.get("gender") == "male" or (p.get("age") is not None and p["age"] >= 55):
        if p.get("pregnant") is None:
            p["pregnant"] = False
    # no land -> irrigation question does not apply
    if p.get("land_acres") == 0 and p.get("land_irrigated") is None:
        p["land_irrigated"] = False
    # not an artisan -> trade question does not apply
    if p.get("occupation") not in (None, "artisan") and p.get("traditional_trade") is None:
        p["traditional_trade"] = "none"
    # not a student -> course question does not apply
    if p.get("occupation") not in (None, "student") and p.get("course_level") is None:
        p["course_level"] = "none"
    return p


def label(opt_or_l: Option | L, lang: str) -> str:
    lab = opt_or_l.label if isinstance(opt_or_l, Option) else opt_or_l
    return lab.get(lang) or lab["en"]
