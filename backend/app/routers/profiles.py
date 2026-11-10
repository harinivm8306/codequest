"""Sessions and profiles (including Sahayak multi-family mode and delete-my-data)."""

from __future__ import annotations

import secrets
from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import Conversation, Profile, User, get_db
from app.deps import ApiError, current_user, lang_or_default, owned_profile
from app.fields import FIELD_BY_NAME, coerce, normalise
from app.services.housekeeping import hash_secret

router = APIRouter()
MAX_SAHAYAK_PROFILES = 50


class SessionIn(BaseModel):
    role: Literal["citizen", "sahayak"] = "citizen"


@router.post("/session")
def start_session(body: SessionIn | None = None, db: Session = Depends(get_db)):
    """Anonymous session. The token is shown once and stored only as a hash."""
    token = secrets.token_urlsafe(24)
    user = User(token_hash=hash_secret(token), role=(body or SessionIn()).role)
    db.add(user)
    db.commit()
    return {"token": token, "user_id": user.id, "role": user.role}


@router.post("/session/role")
def set_role(body: SessionIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.role = body.role
    db.commit()
    return {"role": user.role}


@router.delete("/session")
def delete_everything(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Delete the session and every profile, conversation and document under it."""
    n = len(user.profiles)
    db.delete(user)
    db.commit()
    return {"deleted": True, "profiles_deleted": n}


class ProfileIn(BaseModel):
    label: str = Field(default="", max_length=80)
    language: str = "en"


def profile_view(p: Profile) -> dict:
    return {
        "id": p.id,
        "label": p.label,
        "language": p.language,
        "consent_given": p.consent_given,
        "facts": p.data,
        "derived": normalise(p.data),
        "updated_at": p.updated_at.isoformat() + "Z",
        "documents": len(p.documents),
    }


@router.post("/profiles")
def create_profile(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role == "citizen" and user.profiles:
        return profile_view(user.profiles[0])  # a citizen has one profile
    if len(user.profiles) >= MAX_SAHAYAK_PROFILES:
        raise ApiError(400, "too_many_profiles", f"A helper can keep up to {MAX_SAHAYAK_PROFILES} families.")
    p = Profile(owner_user_id=user.id, label=body.label.strip(), language=lang_or_default(body.language))
    p.conversation = Conversation(language=p.language)
    db.add(p)
    db.commit()
    return profile_view(p)


@router.get("/profiles")
def list_profiles(user: User = Depends(current_user)):
    return {"role": user.role, "profiles": [profile_view(p) for p in sorted(user.profiles, key=lambda p: p.updated_at, reverse=True)]}


@router.get("/profiles/{profile_id}")
def get_profile(profile_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return profile_view(owned_profile(profile_id, user, db))


class ProfilePatch(BaseModel):
    facts: dict[str, Any] | None = None
    language: str | None = None
    label: str | None = Field(default=None, max_length=80)
    consent_given: bool | None = None


@router.patch("/profiles/{profile_id}")
def patch_profile(profile_id: str, body: ProfilePatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Direct edits: quick entry by a helper, or the citizen correcting an answer. null clears a fact."""
    p = owned_profile(profile_id, user, db)
    if body.facts:
        data = dict(p.data or {})
        for k, v in body.facts.items():
            f = FIELD_BY_NAME.get(k)
            if f is None:
                raise ApiError(422, "unknown_field", f"Unknown field {k}")
            try:
                val = coerce(f, v)
            except (ValueError, TypeError) as exc:
                raise ApiError(422, "invalid_value", str(exc)) from exc
            if val is None:
                data.pop(k, None)
            else:
                data[k] = val
        p.data = data
    if body.language:
        p.language = lang_or_default(body.language)
    if body.label is not None:
        p.label = body.label.strip()
    if body.consent_given is not None:
        p.consent_given = body.consent_given
    db.commit()
    return profile_view(p)


@router.delete("/profiles/{profile_id}")
def delete_profile(profile_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = owned_profile(profile_id, user, db)
    db.delete(p)
    db.commit()
    return {"deleted": True}
