"""API tests: every endpoint's happy path and the shared error shape, plus the full Lakshmi journey."""

from datetime import date, timedelta
from io import BytesIO

API = "/api/v1"


def new_profile(client, h, lang="ta", consent=True):
    p = client.post(f"{API}/profiles", json={"language": lang}, headers=h).json()
    if consent:
        client.patch(f"{API}/profiles/{p['id']}", json={"consent_given": True}, headers=h)
    return p["id"]


def say(client, h, pid, text=None, answers=None, lang="ta"):
    body = {"profile_id": pid, "language": lang}
    if text is not None:
        body["text"] = text
    if answers is not None:
        body["answers"] = answers
    r = client.post(f"{API}/chat/turn", json=body, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def test_health(client):
    j = client.get(f"{API}/health").json()
    assert j["status"] == "ok" and j["db"] == "ok" and j["schemes"] == 17
    assert j["bhashini"] == "not_configured" and j["llm"] == "keywords"


def test_error_shape(client):
    r = client.get(f"{API}/profiles")
    assert r.status_code == 401
    assert r.json() == {"error": {"code": "no_session", "message": "Start a session first (POST /api/v1/session)."}}
    r = client.post(f"{API}/chat/turn", json={}, headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "bad_session"


def test_consent_required(client, session):
    pid = new_profile(client, session, consent=False)
    r = client.post(f"{API}/chat/turn", json={"profile_id": pid, "text": "hello"}, headers=session)
    assert r.status_code == 403 and r.json()["error"]["code"] == "consent_required"


def test_lakshmi_journey_in_tamil(client, session):
    """Lakshmi, 62, widow, Madurai: speaks Tamil, answers follow-ups, sees schemes, uploads, downloads."""
    h = session
    pid = new_profile(client, h, "ta")
    conv = client.get(f"{API}/profiles/{pid}/conversation", headers=h).json()
    assert conv["greeting"].startswith("வணக்கம்")

    r = say(client, h, pid, "என் கணவர் இறந்துவிட்டார். எனக்கு 62 வயது. நான் மதுரையில் இருக்கிறேன்.")
    assert r["facts_added"]["marital_status"] == "widowed"
    assert r["facts_added"]["age"] == 62
    assert r["facts_added"]["gender"] == "female"
    assert r["facts_added"]["district"] == "Madurai"
    assert not r["done"]

    # answer every follow-up the way Lakshmi would, by voice-style text where natural, chips otherwise
    replies = {
        "have": [{"field": "has_bank_account", "value": True}, {"field": "bpl_card", "value": True}, {"field": "has_lpg_connection", "value": True}],
        "annual_family_income": "வருமானம் மாதம் 5 ஆயிரம்",
        "occupation": [{"field": "occupation", "value": "homemaker"}],
        "land_acres": "நிலம் இல்லை",
        "disability_percent": "இல்லை",
        "girl_children_under_10": "இல்லை",
        "family": "இவை எதுவும் இல்லை",
        "caste_category": [{"field": "caste_category", "value": "MBC"}],
    }
    asked = []
    for _ in range(25):
        key = r["next_field"]
        if r["done"]:
            break
        asked.append(key)
        reply = replies[key]
        r = say(client, h, pid, text=reply) if isinstance(reply, str) else say(client, h, pid, answers=reply)
    assert r["done"], asked
    print("lakshmi asked:", len(asked), asked)
    assert len(asked) <= 10, asked

    facts = client.get(f"{API}/profiles/{pid}", headers=h).json()["facts"]
    assert facts["annual_family_income"] == 60000
    assert facts["family_govt_pension"] == "none" and facts["owns_four_wheeler"] is False

    e = client.get(f"{API}/profiles/{pid}/eligibility?lang=ta", headers=h).json()
    ids = {s["id"] for s in e["eligible"]}
    assert ids == {"ignoaps", "ignwps", "pmsby", "cmchis", "kmut"}
    widow = next(s for s in e["eligible"] if s["id"] == "ignwps")
    assert widow["passed"][0]["source"]["url"].startswith("https://")
    assert "விதவை" in widow["reason"]
    assert e["conflicts"] and e["disclaimer"].startswith("இது")
    assert any(u["id"] == "ab_pmjay_vay_vandana" and u["at_age"] == 70 for u in e["upcoming"])

    # reproducible: same profile, same answer
    assert client.get(f"{API}/profiles/{pid}/eligibility?lang=ta", headers=h).json()["eligible"] == e["eligible"]

    # Document Doctor via manual entry (OCR tested separately): an expired income certificate
    old = (date.today() - timedelta(days=30)).strftime("%d/%m/%Y")
    client.patch(f"{API}/profiles/{pid}", json={"facts": {"name": "Lakshmi Murugan"}}, headers=h)
    up = client.post(
        f"{API}/profiles/{pid}/documents",
        data={"consent": "true", "doc_type": "income_certificate", "manual_fields": f'{{"name": "Lakshmi Murugan", "valid_until": "{old}"}}'},
        headers=h,
    ).json()
    assert [i["code"] for i in up["issues"]] == ["expired"]

    ck = client.get(f"{API}/profiles/{pid}/checklist/cmchis", headers=h).json()["checklist"]
    status = {c["doc_type"]: c["status"] for c in ck}
    assert status == {"income_certificate": "problem", "ration_card": "missing", "aadhaar": "missing"}

    # packet: signed URL, PDF bytes
    link = client.post(f"{API}/profiles/{pid}/packets/ignwps", headers=h).json()["url"]
    pdf = client.get(link)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF") and len(pdf.content) > 2000
    assert client.get(link.replace("sig=", "sig=x")).status_code == 403

    # delete my data
    assert client.delete(f"{API}/profiles/{pid}", headers=h).json()["deleted"]
    assert client.get(f"{API}/profiles/{pid}", headers=h).status_code == 404


def test_confirm_before_overwriting(client, session):
    pid = new_profile(client, session, "en")
    say(client, session, pid, "I am 45 years old", lang="en")
    r = say(client, session, pid, "actually I am 47 years old", lang="en")
    assert r["question"]["key"] == "__confirm__" and "45" in r["reply_text"] and "47" in r["reply_text"]
    r = say(client, session, pid, answers=[{"field": "__confirm__", "value": True}], lang="en")
    assert client.get(f"{API}/profiles/{pid}", headers=session).json()["facts"]["age"] == 47
    assert r["reply_text"].startswith("Updated")


def test_not_understood_repeats_question(client, session):
    pid = new_profile(client, session, "hi")
    r = say(client, session, pid, "मेरी उम्र 30 साल है", lang="hi")
    assert r["facts_added"] == {"age": 30}
    r2 = say(client, session, pid, "हम्म", lang="hi")
    assert r2["reply_text"].startswith("माफ़") and r2["next_field"] == r["next_field"]


def test_sahayak_keeps_families_separate(client):
    tok = client.post(f"{API}/session", json={"role": "sahayak"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    a = client.post(f"{API}/profiles", json={"label": "Lakshmi", "language": "ta"}, headers=h).json()["id"]
    b = client.post(f"{API}/profiles", json={"label": "Arun", "language": "en"}, headers=h).json()["id"]
    assert a != b
    client.patch(f"{API}/profiles/{a}", json={"facts": {"age": 62}}, headers=h)
    client.patch(f"{API}/profiles/{b}", json={"facts": {"age": 19, "occupation": "student"}}, headers=h)
    lst = client.get(f"{API}/profiles", headers=h).json()["profiles"]
    assert {p["label"]: p["facts"].get("age") for p in lst} == {"Lakshmi": 62, "Arun": 19}
    # another session cannot see them
    other = {"Authorization": "Bearer " + client.post(f"{API}/session").json()["token"]}
    assert client.get(f"{API}/profiles/{a}", headers=other).status_code == 404
    assert client.delete(f"{API}/session", headers=h).json()["profiles_deleted"] == 2


def test_citizen_has_one_profile(client, session):
    a = client.post(f"{API}/profiles", json={}, headers=session).json()["id"]
    b = client.post(f"{API}/profiles", json={}, headers=session).json()["id"]
    assert a == b


def test_patch_validates(client, session):
    pid = new_profile(client, session)
    r = client.patch(f"{API}/profiles/{pid}", json={"facts": {"age": "abc"}}, headers=session)
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_value"
    r = client.patch(f"{API}/profiles/{pid}", json={"facts": {"caste": "SC"}}, headers=session)
    assert r.json()["error"]["code"] == "unknown_field"


def test_schemes_and_ask(client, session):
    lst = client.get(f"{API}/schemes?lang=hi").json()["schemes"]
    assert len(lst) == 17 and any(s["name"].startswith("प्रधानमंत्री") for s in lst)
    s = client.get(f"{API}/schemes/pm_kisan").json()
    assert s["clauses"][0]["source"]["url"].startswith("https://")
    a = client.post(f"{API}/schemes/pm_kisan/ask", json={"question": "How much money do I get?", "language": "en"}, headers=session).json()
    assert a["grounded"] and "6,000" in a["answer"] and a["citations"]
    a = client.post(f"{API}/schemes/pm_kisan/ask", json={"question": "எங்கே விண்ணப்பிப்பது?", "language": "ta"}, headers=session).json()
    assert a["grounded"] and "pmkisan.gov.in" in a["answer"]
    a = client.post(f"{API}/schemes/pm_kisan/ask", json={"question": "zzzz qqqq", "language": "en"}, headers=session).json()
    assert not a["grounded"]
    assert client.get(f"{API}/schemes/nope").status_code == 404


def test_voice_falls_back_without_bhashini(client, session):
    pid = new_profile(client, session)
    r = client.post(f"{API}/voice/turn", json={"profile_id": pid, "language": "ta", "audio_base64": "UklGRg=="}, headers=session)
    assert r.status_code == 503 and r.json()["error"]["fallback"] == "browser"
    r = client.post(f"{API}/voice/tts", json={"text": "வணக்கம்", "language": "ta"}, headers=session)
    assert r.status_code == 503


def test_upload_requires_consent_and_image_type(client, session):
    pid = new_profile(client, session)
    r = client.post(f"{API}/profiles/{pid}/documents", data={"doc_type": "aadhaar"}, headers=session)
    assert r.status_code == 403
    r = client.post(f"{API}/profiles/{pid}/documents", data={"consent": "true"}, files={"file": ("a.txt", BytesIO(b"hi"), "text/plain")}, headers=session)
    assert r.status_code == 415


def test_photo_upload_ocr(client, session):
    from tests.test_doc_doctor import render_certificate

    pid = new_profile(client, session, "en")
    client.patch(f"{API}/profiles/{pid}", json={"facts": {"name": "Lakshmi Murugan"}}, headers=session)
    png = render_certificate(
        [
            "GOVERNMENT OF TAMIL NADU",
            "INCOME CERTIFICATE",
            "Name: Laxmi Venkatesan",
            "Annual income Rs. 60,000",
            "Date of issue: 01/04/2026",
            "Valid up to: 31/03/2027",
        ]
    )
    r = client.post(f"{API}/profiles/{pid}/documents", data={"consent": "true"}, files={"file": ("c.png", BytesIO(png), "image/png")}, headers=session)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["document"]["doc_type"] == "income_certificate"
    assert "name_mismatch" in [i["code"] for i in j["issues"]]
    docs = client.get(f"{API}/profiles/{pid}/documents", headers=session).json()["documents"]
    assert docs[0]["expires_at"] is not None
    kept = client.post(f"{API}/profiles/{pid}/documents/{docs[0]['id']}/keep", headers=session).json()
    assert kept["expires_at"] is None
    assert client.delete(f"{API}/profiles/{pid}/documents/{docs[0]['id']}", headers=session).json()["deleted"]


def test_audit_log_has_no_personal_fields(client, session):
    from app.db import EligibilityRun, SessionLocal

    pid = new_profile(client, session)
    client.patch(f"{API}/profiles/{pid}", json={"facts": {"name": "Secret Name", "age": 30}}, headers=session)
    client.get(f"{API}/profiles/{pid}/eligibility", headers=session)
    with SessionLocal() as db:
        row = db.query(EligibilityRun).order_by(EligibilityRun.created_at.desc()).first()
        assert "Secret" not in str(row.results) and len(row.profile_hash) == 64 and row.rules_version


def test_retention_cleanup(client, session):
    from app.db import Document, SessionLocal, utcnow
    from app.services.housekeeping import cleanup

    pid = new_profile(client, session)
    client.post(f"{API}/profiles/{pid}/documents", data={"consent": "true", "doc_type": "ration_card"}, headers=session)
    with SessionLocal() as db:
        for d in db.query(Document).filter(Document.profile_id == pid):
            d.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()
    assert cleanup()["documents_deleted"] >= 1
    assert client.get(f"{API}/profiles/{pid}/documents", headers=session).json()["documents"] == []


def test_fields_for_answers_editor(client):
    f = client.get(f"{API}/fields?lang=ta").json()["fields"]
    keys = [q["key"] for q in f]
    assert keys[0] == "age" and "family" in keys and "have" in keys
    fam = next(q for q in f if q["key"] == "family")
    assert fam["multi"] and fam["none_label"] == "இவை எதுவும் இல்லை"
