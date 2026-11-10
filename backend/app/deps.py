"""Shared request helpers: auth, profile ownership, errors, rate limits."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db import Profile, User, get_db
from app.services.housekeeping import hash_secret, limiter

LANGS = ("en", "ta", "hi")


class ApiError(HTTPException):
    def __init__(self, status: int, code: str, message: str, fallback: str | None = None):
        detail = {"code": code, "message": message}
        if fallback:
            detail["fallback"] = fallback
        super().__init__(status_code=status, detail=detail)


def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise ApiError(401, "no_session", "Start a session first (POST /api/v1/session).")
    user = db.query(User).filter(User.token_hash == hash_secret(token)).first()
    if user is None:
        raise ApiError(401, "bad_session", "Session not found or deleted.")
    return user


def owned_profile(profile_id: str, user: User, db: Session) -> Profile:
    p = db.get(Profile, profile_id)
    if p is None or p.owner_user_id != user.id:  # same error either way: don't leak existence
        raise ApiError(404, "profile_not_found", "No such profile for this session.")
    return p


def rate_limited(user: User, bucket: str) -> None:
    if not limiter.allow(f"{bucket}:{user.id}"):
        raise ApiError(429, "rate_limited", "Too many requests. Please wait a minute.")


def lang_or_default(lang: str | None, default: str = "en") -> str:
    return lang if lang in LANGS else default
