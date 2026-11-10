"""Document Doctor uploads, per-scheme checklists and PDF packets."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import timedelta

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Document, Profile, User, get_db, utcnow
from app.deps import ApiError, current_user, lang_or_default, owned_profile, rate_limited
from app.services import doc_doctor, packet, rules

router = APIRouter()
ALLOWED = {"image/jpeg", "image/png", "image/webp"}
PACKET_URL_TTL_S = 600


def _reference_name(p: Profile, exclude_id: str | None = None) -> tuple[str | None, str]:
    """Compare against the Aadhaar name if one was uploaded, else the name the person gave."""
    aad = [d for d in p.documents if d.doc_type == "aadhaar" and d.id != exclude_id and d.extracted.get("name")]
    if aad:
        return aad[-1].extracted["name"], "aadhaar"
    return (p.data or {}).get("name"), "profile"


def doc_view(d: Document, lang: str) -> dict:
    return {
        "id": d.id,
        "doc_type": d.doc_type,
        "label": doc_doctor.DOC_TYPES.get(d.doc_type, {}).get("label", {}).get(lang, d.doc_type),
        "extracted": d.extracted,
        "issues": d.issues,
        "source": d.source,
        "created_at": d.created_at.isoformat() + "Z",
        "expires_at": d.expires_at.isoformat() + "Z" if d.expires_at else None,
    }


@router.post("/profiles/{profile_id}/documents")
async def upload_document(
    profile_id: str,
    consent: bool = Form(False),
    doc_type: str | None = Form(None),
    manual_fields: str | None = Form(None, description='JSON, e.g. {"name": "...", "valid_until": "31/03/2027"}'),
    file: UploadFile | None = File(None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Upload a photo (OCR) or enter the fields by hand. The image is never stored."""
    rate_limited(user, "upload")
    p = owned_profile(profile_id, user, db)
    if not consent:
        raise ApiError(403, "consent_required", "Consent is needed before each document upload.")
    if doc_type and doc_type not in doc_doctor.DOC_TYPES:
        raise ApiError(422, "unknown_doc_type", f"Unknown document type {doc_type}")
    lang = p.language
    ref, ref_kind = _reference_name(p)

    if file is not None:
        if file.content_type not in ALLOWED:
            raise ApiError(415, "unsupported_file", "Please upload a JPEG or PNG photo.")
        data = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
        if len(data) > settings.max_upload_mb * 1024 * 1024:
            raise ApiError(413, "too_large", f"Photo is larger than {settings.max_upload_mb} MB.")
        try:
            text, quality = doc_doctor.ocr_image(data)
        except Exception as exc:  # unreadable image or OCR missing
            raise ApiError(422, "ocr_failed", f"Could not read the photo ({exc.__class__.__name__}). Enter the details by hand.", fallback="manual") from exc
        finally:
            del data  # drop the image bytes as soon as OCR is done
        result = doc_doctor.analyse_text(text, lang, ref, ref_kind, doc_type_hint=doc_type, quality=quality)
        source = "ocr"
    elif manual_fields:
        if not doc_type:
            raise ApiError(422, "doc_type_required", "Choose the document type for manual entry.")
        try:
            fields = {k: str(v)[:80] for k, v in json.loads(manual_fields).items() if k in ("name", "dob", "issue_date", "valid_until", "certificate_no")}
        except (ValueError, AttributeError) as exc:
            raise ApiError(422, "bad_manual_fields", "manual_fields must be a JSON object") from exc
        fields = {k: doc_doctor.mask_aadhaar(v) for k, v in fields.items()}
        result = {
            "doc_type": doc_type,
            "extracted": fields,
            "issues": doc_doctor.validate(doc_type, fields, lang, ref, ref_kind),
            "preview": "",
            "quality": None,
        }
        source = "manual"
    elif doc_type:  # "I have this document" with no details
        result = {"doc_type": doc_type, "extracted": {}, "issues": [], "preview": "", "quality": None}
        source = "manual"
    else:
        raise ApiError(422, "nothing_uploaded", "Send a photo, or a document type.")

    if result["doc_type"] is None:
        return {"document": None, "issues": result["issues"], "preview": result["preview"], "saved": False}
    d = Document(
        profile_id=p.id,
        doc_type=result["doc_type"],
        extracted=result["extracted"],
        issues=result["issues"],
        source=source,
        expires_at=utcnow() + timedelta(hours=settings.document_retention_hours),
    )
    db.add(d)
    p.updated_at = utcnow()
    db.commit()
    db.refresh(p)
    # a new Aadhaar can reveal name mismatches in documents uploaded earlier
    if d.doc_type == "aadhaar" and d.extracted.get("name"):
        for other in p.documents:
            if other.id != d.id and other.doc_type != "aadhaar":
                other.issues = doc_doctor.validate(other.doc_type, other.extracted, lang, d.extracted["name"], "aadhaar")
        db.commit()
    return {"document": doc_view(d, lang), "issues": d.issues, "preview": result["preview"], "saved": True}


@router.get("/profiles/{profile_id}/documents")
def list_documents(profile_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = owned_profile(profile_id, user, db)
    return {
        "documents": [doc_view(d, p.language) for d in p.documents],
        "types": [{"id": k, "label": v["label"][p.language], "ocr": v["ocr"]} for k, v in doc_doctor.DOC_TYPES.items()],
    }


@router.post("/profiles/{profile_id}/documents/{doc_id}/keep")
def keep_document(profile_id: str, doc_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Opt out of 24-hour auto-deletion for this document's extracted details."""
    p = owned_profile(profile_id, user, db)
    d = next((d for d in p.documents if d.id == doc_id), None)
    if d is None:
        raise ApiError(404, "document_not_found", "No such document.")
    d.saved, d.expires_at = True, None
    db.commit()
    return doc_view(d, p.language)


@router.delete("/profiles/{profile_id}/documents/{doc_id}")
def delete_document(profile_id: str, doc_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = owned_profile(profile_id, user, db)
    d = next((d for d in p.documents if d.id == doc_id), None)
    if d is None:
        raise ApiError(404, "document_not_found", "No such document.")
    db.delete(d)
    db.commit()
    return {"deleted": True}


@router.get("/profiles/{profile_id}/checklist/{scheme_id}")
def scheme_checklist(profile_id: str, scheme_id: str, lang: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = owned_profile(profile_id, user, db)
    s = rules.load_schemes().get(scheme_id)
    if s is None:
        raise ApiError(404, "scheme_not_found", "No such scheme.")
    lang = lang_or_default(lang, p.language)
    docs = [{"doc_type": d.doc_type, "issues": d.issues, "created_at": d.created_at} for d in p.documents]
    return {"scheme": rules.explain(rules.evaluate(s, p.data), lang), "checklist": doc_doctor.checklist(s["required_documents"], docs, lang)}


def _sign(profile_id: str, scheme_id: str, exp: int) -> str:
    msg = f"{profile_id}:{scheme_id}:{exp}".encode()
    return base64.urlsafe_b64encode(hmac.new(settings.hash_salt.encode(), msg, hashlib.sha256).digest()[:18]).decode()


@router.post("/profiles/{profile_id}/packets/{scheme_id}")
def create_packet(profile_id: str, scheme_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Returns a download URL that works for 10 minutes (no token in the URL)."""
    owned_profile(profile_id, user, db)
    if scheme_id not in rules.load_schemes():
        raise ApiError(404, "scheme_not_found", "No such scheme.")
    exp = int(time.time()) + PACKET_URL_TTL_S
    return {"url": f"/api/v1/packets/{profile_id}/{scheme_id}.pdf?exp={exp}&sig={_sign(profile_id, scheme_id, exp)}", "expires_in": PACKET_URL_TTL_S}


@router.get("/packets/{profile_id}/{scheme_id}.pdf")
def download_packet(profile_id: str, scheme_id: str, exp: int, sig: str, db: Session = Depends(get_db)):
    if exp < time.time() or not hmac.compare_digest(sig, _sign(profile_id, scheme_id, exp)):
        raise ApiError(403, "link_expired", "This download link has expired. Generate the packet again.")
    p = db.get(Profile, profile_id)
    if p is None or scheme_id not in rules.load_schemes():
        raise ApiError(404, "not_found", "Not found.")
    docs = [{"doc_type": d.doc_type, "issues": d.issues, "created_at": d.created_at} for d in p.documents]
    pdf = packet.build_pdf(scheme_id, p.data, docs)
    return Response(
        pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="schemesathi-{scheme_id}.pdf"', "Cache-Control": "no-store"}
    )
