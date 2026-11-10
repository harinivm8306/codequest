"""Document Doctor: read a photo of a certificate, extract key fields, find problems.

Privacy: the image is processed in memory and never written to disk or the
database. Any 12-digit Aadhaar number is masked to its last 4 digits before
anything is stored or returned.

OCR uses Tesseract (eng + tam + hin language packs where installed). PaddleOCR
can be plugged in later via the `ocr_image` function; Tesseract was chosen for
the prototype because it fits in a free-tier container's memory.
"""

from __future__ import annotations

import io
import re
from datetime import date, datetime

from rapidfuzz import fuzz

DOC_TYPES: dict[str, dict] = {
    "aadhaar": {
        "label": {"en": "Aadhaar card", "ta": "ஆதார் அட்டை", "hi": "आधार कार्ड"},
        "ocr": True,
        "keywords": ["aadhaar", "aadhar", "unique identification", "uidai", "ஆதார்", "आधार", "mera aadhaar"],
    },
    "income_certificate": {
        "label": {"en": "Income certificate", "ta": "வருமானச் சான்றிதழ்", "hi": "आय प्रमाणपत्र"},
        "ocr": True,
        "max_age_months": 12,
        "keywords": ["income certificate", "annual income", "வருமானச் சான்றிதழ்", "வருமான சான்றிதழ்", "ஆண்டு வருமானம்", "आय प्रमाण", "वार्षिक आय"],
    },
    "community_certificate": {
        "label": {"en": "Community (caste) certificate", "ta": "சாதிச் சான்றிதழ்", "hi": "जाति प्रमाणपत्र"},
        "ocr": True,
        "keywords": ["community certificate", "caste certificate", "belongs to", "சாதிச் சான்றிதழ்", "சாதி சான்றிதழ்", "சமூகச் சான்றிதழ்", "जाति प्रमाण"],
    },
    "residence_certificate": {
        "label": {"en": "Residence / nativity certificate", "ta": "இருப்பிடச் சான்றிதழ்", "hi": "निवास प्रमाणपत्र"},
        "ocr": True,
        "keywords": [
            "nativity",
            "residence certificate",
            "residential certificate",
            "domicile",
            "இருப்பிடச் சான்றிதழ்",
            "இருப்பிட சான்றிதழ்",
            "निवास प्रमाण",
            "मूल निवास",
        ],
    },
    "bank_passbook": {
        "label": {"en": "Bank passbook", "ta": "வங்கிக் கணக்குப் புத்தகம்", "hi": "बैंक पासबुक"},
        "ocr": True,
        "keywords": ["passbook", "ifsc", "savings bank", "account no", "a/c no", "customer id", "கணக்கு எண்", "खाता संख्या", "पासबुक"],
    },
    # recognised only by manual choice (shown in checklists)
    "ration_card": {"label": {"en": "Ration (family) card", "ta": "குடும்ப அட்டை", "hi": "राशन कार्ड"}, "ocr": False},
    "age_proof": {
        "label": {
            "en": "Age proof (birth / school certificate or voter ID)",
            "ta": "வயதுச் சான்று (பிறப்பு / பள்ளிச் சான்றிதழ் அல்லது வாக்காளர் அட்டை)",
            "hi": "आयु प्रमाण (जन्म / स्कूल प्रमाणपत्र या वोटर ID)",
        },
        "ocr": False,
    },
    "death_certificate_spouse": {"label": {"en": "Husband's death certificate", "ta": "கணவரின் இறப்புச் சான்றிதழ்", "hi": "पति का मृत्यु प्रमाणपत्र"}, "ocr": False},
    "disability_certificate": {
        "label": {"en": "Disability certificate / UDID card", "ta": "மாற்றுத்திறனாளி சான்றிதழ் / UDID அட்டை", "hi": "विकलांगता प्रमाणपत्र / UDID कार्ड"},
        "ocr": False,
    },
    "land_record": {"label": {"en": "Land record (patta / chitta)", "ta": "நில ஆவணம் (பட்டா / சிட்டா)", "hi": "भूमि अभिलेख"}, "ocr": False},
    "school_certificate": {
        "label": {"en": "School certificate (Class 6–12, government school)", "ta": "பள்ளிச் சான்றிதழ் (6–12, அரசுப் பள்ளி)", "hi": "स्कूल प्रमाणपत्र (कक्षा 6–12)"},
        "ocr": False,
    },
    "admission_proof": {
        "label": {"en": "College admission / bonafide certificate", "ta": "கல்லூரி சேர்க்கை / உண்மைச் சான்றிதழ்", "hi": "कॉलेज प्रवेश / बोनाफाइड प्रमाणपत्र"},
        "ocr": False,
    },
    "birth_certificate_child": {"label": {"en": "Daughter's birth certificate", "ta": "மகளின் பிறப்புச் சான்றிதழ்", "hi": "बेटी का जन्म प्रमाणपत्र"}, "ocr": False},
    "mcp_card": {"label": {"en": "Mother and Child Protection (MCP) card", "ta": "தாய் சேய் பாதுகாப்பு அட்டை", "hi": "मातृ एवं शिशु सुरक्षा कार्ड"}, "ocr": False},
}

MSG = {
    "name_mismatch": {
        "en": "The name on this document ({doc}) differs from {ref} ({other}). Ask the issuing office to correct it.",
        "ta": "இந்த ஆவணத்தில் உள்ள பெயர் ({doc}) {ref} பெயரிலிருந்து ({other}) வேறுபடுகிறது. வழங்கிய அலுவலகத்தில் திருத்தம் கேளுங்கள்.",
        "hi": "इस दस्तावेज़ पर नाम ({doc}) {ref} ({other}) से अलग है। जारी करने वाले कार्यालय से सुधार करवाएँ।",
    },
    "expired": {
        "en": "This certificate expired on {d}. Renew it at an e-Sevai centre.",
        "ta": "இந்தச் சான்றிதழ் {d} அன்று காலாவதியானது. இ-சேவை மையத்தில் புதுப்பிக்கவும்.",
        "hi": "यह प्रमाणपत्र {d} को समाप्त हो गया। ई-सेवा केंद्र पर नवीनीकरण कराएँ।",
    },
    "old": {
        "en": "Issued on {d}, more than {m} months ago. Offices often ask for a recent one.",
        "ta": "{d} அன்று வழங்கப்பட்டது, {m} மாதங்களுக்கு மேல் ஆகிறது. அலுவலகங்கள் புதியதைக் கேட்கலாம்.",
        "hi": "{d} को जारी, {m} महीने से पुराना। कार्यालय अक्सर नया माँगते हैं।",
    },
    "blurry": {
        "en": "The photo is blurry or dark. Retake it in good light, holding the phone steady.",
        "ta": "புகைப்படம் தெளிவாக இல்லை. நல்ல வெளிச்சத்தில் கைபேசியை அசைக்காமல் மீண்டும் எடுக்கவும்.",
        "hi": "फ़ोटो धुंधली है। अच्छी रोशनी में फ़ोन स्थिर रखकर दोबारा लें।",
    },
    "unknown_type": {
        "en": "I could not tell which document this is. Please choose the type.",
        "ta": "இது எந்த ஆவணம் என்று தெரியவில்லை. வகையைத் தேர்ந்தெடுக்கவும்.",
        "hi": "यह कौन सा दस्तावेज़ है, पता नहीं चला। कृपया प्रकार चुनें।",
    },
    "no_name": {
        "en": "I could not read a name on this document. Check it by eye before you go.",
        "ta": "இந்த ஆவணத்தில் பெயரைப் படிக்க முடியவில்லை. செல்வதற்கு முன் சரிபார்க்கவும்.",
        "hi": "इस दस्तावेज़ पर नाम नहीं पढ़ पाया। जाने से पहले देख लें।",
    },
    "name_other_script": {
        "en": "The names are in different scripts, so I could not compare them. Check by eye that they match.",
        "ta": "பெயர்கள் வெவ்வேறு எழுத்துகளில் உள்ளதால் ஒப்பிட முடியவில்லை. பொருந்துகிறதா என நீங்களே சரிபார்க்கவும்.",
        "hi": "नाम अलग लिपियों में हैं, इसलिए तुलना नहीं हो सकी। खुद मिलान कर लें।",
    },
}
REF = {"aadhaar": {"en": "your Aadhaar", "ta": "உங்கள் ஆதார்", "hi": "आपके आधार"}, "profile": {"en": "the name you gave", "ta": "நீங்கள் சொன்ன", "hi": "आपके बताए नाम"}}

AADHAAR_RE = re.compile(r"(?<!\d)(\d{4})[ \-]?(\d{4})[ \-]?(\d{4})(?!\d)")
DATE_RE = re.compile(r"(?<!\d)(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4}|\d{2})(?!\d)")
NAME_PATTERNS = [
    re.compile(r"(?:^|\n)\s*(?:name|பெயர்|नाम)\s*[:\-]?\s*([^\n:]{3,60})", re.I),
    re.compile(
        r"certify that\s+(?:thiru|tmt|selvi|shri|smt|sri|kumari|mr|mrs|ms)?\.?\s*([A-Za-z][A-Za-z .]{2,50}?)(?:\s*,|\s+(?:s/o|d/o|w/o|son|daughter|wife)\b)",
        re.I,
    ),
]
DOB_RE = re.compile(r"(?:dob|date of birth|year of birth|பிறந்த\s*தேதி|जन्म\s*तिथि)\s*[:/\-]?\s*([0-9/\-.]{6,10})", re.I)
VALID_RE = re.compile(r"(?:valid\s*(?:up\s*to|upto|till|until)|validity|செல்லுபடி[^\n\d]*|वैधता[^\n\d]*|वैध[^\n\d]*)\s*[:\-]?\s*([0-9/\-.]{6,10})", re.I)
ISSUE_RE = re.compile(r"(?:date of issue|issued on|issue date|date|நாள்|தேதி|दिनांक|जारी करने की तिथि)\s*[:\-]?\s*([0-9/\-.]{6,10})", re.I)
CERT_NO_RE = re.compile(r"(?:certificate\s*(?:no|number)|cert\.?\s*no|சான்றிதழ்\s*எண்|प्रमाणपत्र\s*संख्या)\s*[:.\-]?\s*([A-Z0-9/\-]{6,30})", re.I)
INCOME_RE = re.compile(r"(?:rs\.?|₹|rupees)\s*([\d,]{4,10})", re.I)
IFSC_RE = re.compile(r"\b([A-Z]{4}0[A-Z0-9]{6})\b")


def mask_aadhaar(text: str) -> str:
    return AADHAAR_RE.sub(lambda m: f"XXXX XXXX {m.group(3)}", text)


def parse_date(s: str | None) -> date | None:
    if not s:
        return None
    m = DATE_RE.search(s)
    if not m:
        return None
    d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if y < 100:
        y += 2000 if y < 50 else 1900
    try:
        return date(y, mth, d)
    except ValueError:
        return None


def classify(text: str) -> str | None:
    t = text.lower()
    best, score = None, 0
    for dt, meta in DOC_TYPES.items():
        n = sum(1 for k in meta.get("keywords", []) if k in t)
        if dt == "aadhaar" and AADHAAR_RE.search(text):
            n += 1
        if dt == "bank_passbook" and IFSC_RE.search(text):
            n += 1
        if n > score:
            best, score = dt, n
    return best


def extract_fields(text: str, doc_type: str | None) -> dict:
    out: dict = {}
    for pat in NAME_PATTERNS:
        m = pat.search(text)
        if m:
            out["name"] = re.sub(r"\s+", " ", m.group(1)).strip(" .,")
            break
    if "name" not in out and doc_type == "aadhaar":
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for i, ln in enumerate(lines):
            if DOB_RE.search(ln) and i > 0:
                cand = lines[i - 1]
                if re.search(r"[A-Za-z஀-௿ऀ-ॿ]{3}", cand) and not re.search(r"government|india|भारत|இந்திய", cand, re.I):
                    out["name"] = cand
                break
    if m := DOB_RE.search(text):
        out["dob"] = m.group(1)
    if m := VALID_RE.search(text):
        out["valid_until"] = m.group(1)
    if m := ISSUE_RE.search(text):
        out["issue_date"] = m.group(1)
    if m := CERT_NO_RE.search(text):
        out["certificate_no"] = m.group(1)
    if doc_type == "income_certificate" and (m := INCOME_RE.search(text)):
        out["annual_income"] = int(m.group(1).replace(",", ""))
    if doc_type == "bank_passbook" and (m := IFSC_RE.search(text)):
        out["ifsc"] = m.group(1)
    if doc_type == "aadhaar" and (m := AADHAAR_RE.search(text)):
        out["aadhaar_last4"] = m.group(3)
    return {k: mask_aadhaar(v) if isinstance(v, str) else v for k, v in out.items()}


def _script(s: str) -> str:
    if re.search(r"[஀-௿]", s):
        return "ta"
    if re.search(r"[ऀ-ॿ]", s):
        return "hi"
    return "latin"


def _clean_name(s: str) -> str:
    s = re.sub(r"\b(thiru|tmt|selvi|shri|smt|sri|kumari|mr|mrs|ms|dr)\b\.?", " ", s, flags=re.I)
    return re.sub(r"[^\w\s]", " ", s).strip().lower()


def name_score(a: str, b: str) -> float:
    return fuzz.token_sort_ratio(_clean_name(a), _clean_name(b))


def validate(
    doc_type: str | None, fields: dict, lang: str, reference_name: str | None, reference_kind: str, quality: dict | None = None, today: date | None = None
) -> list[dict]:
    today = today or date.today()
    issues: list[dict] = []

    def add(code: str, severity: str, **kw):
        issues.append({"code": code, "severity": severity, "message": MSG[code][lang].format(**kw)})

    if quality and (quality.get("confidence", 100) < 60 or quality.get("sharpness", 999) < 40):
        add("blurry", "blocking")
    if doc_type is None:
        add("unknown_type", "blocking")
        return issues
    name = fields.get("name")
    if reference_name and name:
        if _script(name) != _script(reference_name):
            add("name_other_script", "warning")
        elif name_score(name, reference_name) < 85:
            add("name_mismatch", "blocking", doc=name, ref=REF[reference_kind][lang], other=reference_name)
    elif DOC_TYPES[doc_type]["ocr"] and not name and doc_type != "bank_passbook":
        add("no_name", "warning")
    valid = parse_date(fields.get("valid_until"))
    if valid and valid < today:
        add("expired", "blocking", d=valid.strftime("%d/%m/%Y"))
    elif not valid and (months := DOC_TYPES[doc_type].get("max_age_months")):
        issued = parse_date(fields.get("issue_date"))
        if issued and (today - issued).days > months * 30.5:
            add("old", "warning", d=issued.strftime("%d/%m/%Y"), m=months)
    return issues


# ----------------------------------------------------------------------------- OCR
def _tesseract_langs() -> str:
    try:
        import pytesseract

        have = set(pytesseract.get_languages(config=""))
    except Exception:
        return "eng"
    return "+".join(lang for lang in ("eng", "tam", "hin") if lang in have) or "eng"


def prepare(image_bytes: bytes):
    from PIL import Image, ImageOps

    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img).convert("L")
    w, h = img.size
    scale = 1600 / max(w, h)
    if scale < 1:
        img = img.resize((int(w * scale), int(h * scale)))
    return ImageOps.autocontrast(img)


def sharpness(img) -> float:
    """Variance of a Laplacian filter: low values mean a blurry photo."""
    import numpy as np

    a = np.asarray(img, dtype=float)
    if a.shape[0] < 3 or a.shape[1] < 3:
        return 0.0
    lap = -4 * a[1:-1, 1:-1] + a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:]
    return float(lap.var())


def ocr_image(image_bytes: bytes) -> tuple[str, dict]:
    import pytesseract

    img = prepare(image_bytes)
    data = pytesseract.image_to_data(img, lang=_tesseract_langs(), output_type=pytesseract.Output.DICT)
    confs = [float(c) for c, w in zip(data["conf"], data["text"], strict=False) if w.strip() and float(c) >= 0]
    text = pytesseract.image_to_string(img, lang=_tesseract_langs())
    return text, {"confidence": sum(confs) / len(confs) if confs else 0.0, "sharpness": sharpness(img)}


def analyse_text(
    text: str,
    lang: str,
    reference_name: str | None,
    reference_kind: str,
    doc_type_hint: str | None = None,
    quality: dict | None = None,
    today: date | None = None,
) -> dict:
    doc_type = doc_type_hint or classify(text)
    fields = extract_fields(text, doc_type)
    issues = validate(doc_type, fields, lang, reference_name, reference_kind, quality, today)
    return {"doc_type": doc_type, "extracted": fields, "issues": issues, "quality": quality, "preview": mask_aadhaar(text)[:400]}


def checklist(required: list[str], docs: list[dict], lang: str) -> list[dict]:
    """Per required document: ok / problem / missing, using the newest upload of each type."""
    latest: dict[str, dict] = {}
    for d in sorted(docs, key=lambda d: d.get("created_at") or datetime.min):
        latest[d["doc_type"]] = d
    out = []
    for dt in required:
        d = latest.get(dt)
        if d is None:
            status = "missing"
        elif any(i["severity"] == "blocking" for i in d.get("issues", [])):
            status = "problem"
        else:
            status = "ok"
        out.append(
            {
                "doc_type": dt,
                "label": DOC_TYPES[dt]["label"][lang],
                "status": status,
                "issues": d.get("issues", []) if d else [],
                "ocr_supported": DOC_TYPES[dt]["ocr"],
            }
        )
    return out
