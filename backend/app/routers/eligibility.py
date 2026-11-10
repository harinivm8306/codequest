"""Eligibility results, scheme catalogue and cited Q&A."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import EligibilityRun, User, get_db
from app.deps import ApiError, current_user, lang_or_default, owned_profile, rate_limited
from app.fields import PRIORITY
from app.services import conversation, qa, rules
from app.services.doc_doctor import DOC_TYPES
from app.services.housekeeping import profile_hash

router = APIRouter()


@router.get("/profiles/{profile_id}/eligibility")
def eligibility(profile_id: str, lang: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = owned_profile(profile_id, user, db)
    lang = lang_or_default(lang, p.language)
    out = rules.grouped(p.data, lang)
    db.add(
        EligibilityRun(
            profile_hash=profile_hash(p.data),
            rules_version=out["rules_version"],
            results={
                "eligible": [s["id"] for s in out["eligible"]],
                "needs_info": [s["id"] for s in out["needs_info"]],
                "not_eligible": [s["id"] for s in out["not_eligible"]],
            },
        )
    )
    db.commit()
    for group in ("eligible", "needs_info", "almost", "not_eligible"):
        for s in out[group]:
            s["documents"] = [{"id": d, "label": DOC_TYPES[d]["label"][lang]} for d in s["required_documents"]]
    return out


@router.get("/schemes")
def list_schemes(lang: str = "en"):
    lang = lang_or_default(lang)
    return {
        "rules_version": rules.rules_version(),
        "schemes": [
            {
                "id": s["id"],
                "name": s["name"][lang],
                "level": s["level"],
                "state": s["state"],
                "category": s["category"],
                "benefit": s["benefit"][lang],
                "source_url": s["source_url"],
                "verified_on": s["verified_on"],
            }
            for s in rules.load_schemes().values()
        ],
    }


@router.get("/schemes/{scheme_id}")
def get_scheme(scheme_id: str, lang: str = "en"):
    s = rules.load_schemes().get(scheme_id)
    if s is None:
        raise ApiError(404, "scheme_not_found", "No such scheme.")
    lang = lang_or_default(lang)
    return {
        "id": s["id"],
        "name": s["name"][lang],
        "benefit": s["benefit"][lang],
        "apply_at": s["apply_at"][lang],
        "level": s["level"],
        "state": s["state"],
        "category": s["category"],
        "source_url": s["source_url"],
        "verified_on": s["verified_on"],
        "version": s["version"],
        "clauses": [{"id": c["id"], "text": c["text"][lang], "source": c["source"], "rule": c["rule"]} for c in s["clauses"]],
        "office_checks": [o[lang] for o in s.get("office_checks", [])],
        "required_documents": [{"id": d, "label": DOC_TYPES[d]["label"][lang]} for d in s["required_documents"]],
    }


@router.get("/fields")
def list_fields(lang: str = "en"):
    """Every askable fact with its question and chips, for the 'My answers' editor and Sahayak quick entry."""
    lang = lang_or_default(lang)
    out = []
    for key in PRIORITY:
        q = conversation.question_payload(key, lang)
        if q:
            out.append(q)
    return {"fields": out}


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=400)
    language: str = "en"


@router.post("/schemes/{scheme_id}/ask")
def ask(scheme_id: str, body: AskIn, user: User = Depends(current_user)):
    rate_limited(user, "ask")
    if scheme_id not in rules.load_schemes():
        raise ApiError(404, "scheme_not_found", "No such scheme.")
    return qa.answer(body.question, scheme_id, lang_or_default(body.language))
