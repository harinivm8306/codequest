"""Document Doctor: classification, extraction and validators on synthetic documents.

All samples are synthetic, generated here. Never test with real people's IDs.
"""

from datetime import date
from io import BytesIO

import pytest
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.services import doc_doctor as dd

TODAY = date(2026, 11, 10)

SAMPLES = {
    "aadhaar": "Government of India\nLakshmi Murugan\nDOB: 12/03/1964\nFemale\n1234 5678 9012\nMera Aadhaar, Meri Pehchaan",
    "income_certificate": "GOVERNMENT OF TAMIL NADU\nINCOME CERTIFICATE\nCertificate No: TN-INC-2026-0042\nThis is to certify that Tmt. Lakshmi Murugan, W/o Murugan\nannual income Rs. 60,000\nDate of issue: 01/04/2026\nValid up to: 31/03/2027",
    "community_certificate": "COMMUNITY CERTIFICATE\nThis is to certify that Selvi Priya R, D/o Raman belongs to the MBC community\nDate: 05/06/2019",
    "residence_certificate": "NATIVITY CERTIFICATE\nName: Arun Kumar\nresident of Salem district\nDate of issue: 10/01/2026",
    "bank_passbook": "STATE BANK OF INDIA\nSavings Bank Passbook\nName: LAKSHMI MURUGAN\nA/C No: 3021XXXX4512\nIFSC: SBIN0001234",
}


@pytest.mark.parametrize("doc_type,text", SAMPLES.items())
def test_classifies_each_type(doc_type, text):
    assert dd.classify(text) == doc_type


def test_extracts_fields():
    f = dd.extract_fields(SAMPLES["income_certificate"], "income_certificate")
    assert f["name"] == "Lakshmi Murugan" and f["valid_until"] == "31/03/2027" and f["annual_income"] == 60000
    assert f["certificate_no"] == "TN-INC-2026-0042"
    a = dd.extract_fields(SAMPLES["aadhaar"], "aadhaar")
    assert a["name"] == "Lakshmi Murugan" and a["dob"] == "12/03/1964" and a["aadhaar_last4"] == "9012"
    assert dd.extract_fields(SAMPLES["community_certificate"], "community_certificate")["name"] == "Priya R"
    assert dd.extract_fields(SAMPLES["bank_passbook"], "bank_passbook")["ifsc"] == "SBIN0001234"


def test_aadhaar_is_masked_everywhere():
    r = dd.analyse_text(SAMPLES["aadhaar"], "en", None, "profile")
    assert "1234 5678" not in r["preview"] and "XXXX XXXX 9012" in r["preview"]
    assert "1234 5678" not in str(r["extracted"])


def test_name_mismatch_and_spelling_tolerance():
    issues = dd.validate("income_certificate", {"name": "Laxmi Venkatesan"}, "en", "Lakshmi Murugan", "aadhaar", today=TODAY)
    assert [i["code"] for i in issues] == ["name_mismatch"] and "Aadhaar" in issues[0]["message"]
    assert dd.validate("income_certificate", {"name": "LAKSHMI MURUGAN"}, "en", "Lakshmi Murugan", "aadhaar", today=TODAY) == []
    assert dd.validate("income_certificate", {"name": "Murugan Lakshmi"}, "en", "Lakshmi Murugan", "aadhaar", today=TODAY) == []
    assert dd.name_score("Tmt. Lakshmi Murugan", "Lakshmi Murugan") >= 85


def test_cross_script_names_are_flagged_not_failed():
    issues = dd.validate("income_certificate", {"name": "லட்சுமி முருகன்"}, "ta", "Lakshmi Murugan", "aadhaar", today=TODAY)
    assert [i["code"] for i in issues] == ["name_other_script"] and issues[0]["severity"] == "warning"


def test_expiry_and_age():
    exp = dd.validate("income_certificate", {"name": "A B", "valid_until": "31/10/2026"}, "en", None, "profile", today=TODAY)
    assert [i["code"] for i in exp] == ["expired"] and exp[0]["severity"] == "blocking"
    old = dd.validate("income_certificate", {"name": "A B", "issue_date": "01/01/2025"}, "ta", None, "profile", today=TODAY)
    assert [i["code"] for i in old] == ["old"] and "மாதங்களுக்கு" in old[0]["message"]
    # community certificates do not expire
    assert dd.validate("community_certificate", {"name": "A B", "issue_date": "01/01/2010"}, "en", None, "profile", today=TODAY) == []


def test_blur_is_blocking():
    issues = dd.validate("aadhaar", {"name": "A B"}, "hi", None, "profile", quality={"confidence": 30, "sharpness": 500})
    assert issues[0]["code"] == "blurry" and issues[0]["severity"] == "blocking"


def test_checklist_statuses():
    docs = [{"doc_type": "aadhaar", "issues": []}, {"doc_type": "income_certificate", "issues": [{"code": "expired", "severity": "blocking", "message": "x"}]}]
    cl = dd.checklist(["aadhaar", "income_certificate", "bank_passbook"], docs, "en")
    assert [c["status"] for c in cl] == ["ok", "problem", "missing"]


def render_certificate(lines: list[str], blur: float = 0) -> bytes:
    img = Image.new("RGB", (1400, 140 + 90 * len(lines)), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 46)
    except OSError:
        font = ImageFont.load_default(size=46)
    for i, ln in enumerate(lines):
        d.text((60, 60 + 90 * i), ln, fill="black", font=font)
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    buf = BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def test_real_ocr_on_rendered_image():
    png = render_certificate(["INCOME CERTIFICATE", "Name: Lakshmi Murugan", "Annual income Rs. 60,000", "Valid up to: 31/03/2027"])
    text, q = dd.ocr_image(png)
    r = dd.analyse_text(text, "en", "Lakshmi Murugan", "aadhaar", quality=q, today=TODAY)
    assert r["doc_type"] == "income_certificate"
    assert r["extracted"]["name"].lower() == "lakshmi murugan"
    assert r["issues"] == []


def test_blurry_photo_detected():
    png = render_certificate(["INCOME CERTIFICATE", "Name: Lakshmi Murugan"], blur=6)
    text, q = dd.ocr_image(png)
    r = dd.analyse_text(text, "en", None, "profile", doc_type_hint="income_certificate", quality=q, today=TODAY)
    assert "blurry" in [i["code"] for i in r["issues"]]
