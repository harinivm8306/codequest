"""Conversation turns by text (also the fallback path) and by voice."""

from __future__ import annotations

import base64
import binascii
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import Conversation, User, get_db, utcnow
from app.deps import ApiError, current_user, lang_or_default, owned_profile, rate_limited
from app.services import bhashini, conversation

router = APIRouter()
MAX_TURNS_KEPT = 200


class Answer(BaseModel):
    field: str
    value: Any = None


class ChatIn(BaseModel):
    profile_id: str
    text: str | None = Field(default=None, max_length=1000)
    answers: list[Answer] | None = None
    language: str | None = None


def _run_turn(
    db: Session, user: User, profile_id: str, lang: str | None, text: str | None, answers: list[dict] | None, transcript_source: str = "text"
) -> dict:
    p = owned_profile(profile_id, user, db)
    if not p.consent_given:
        raise ApiError(403, "consent_required", "Please agree to the consent screen first.")
    lang = lang_or_default(lang, p.language)
    p.language = lang
    conv = p.conversation or Conversation(profile_id=p.id, language=lang)
    p.conversation = conv
    out = conversation.turn(p.data, conv.state, lang, text=text, answers=answers)
    p.data = out["profile"]
    conv.state = out["state"]
    shown = text if text is not None else ", ".join(str(a.get("label") or a.get("value")) for a in (answers or [])) or "—"
    turns = list(conv.turns or [])
    turns.append({"role": "user", "text": shown, "via": transcript_source, "at": utcnow().isoformat() + "Z"})
    turns.append({"role": "assistant", "text": out["response"]["reply_text"], "at": utcnow().isoformat() + "Z"})
    conv.turns = turns[-MAX_TURNS_KEPT:]
    p.updated_at = utcnow()
    db.commit()
    return {**out["response"], "transcript": text, "facts": p.data}


@router.get("/profiles/{profile_id}/conversation")
def get_conversation(profile_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = owned_profile(profile_id, user, db)
    conv = p.conversation
    state = (conv.state if conv else {}) or {}
    pending = state.get("pending")
    q = conversation.question_payload(pending, p.language) if pending else None
    g = conversation.greeting(p.data, p.language)
    return {"turns": (conv.turns if conv else []) or [], "greeting": g["reply_text"], "question": q or g["question"], "language": p.language}


@router.post("/chat/turn")
def chat_turn(body: ChatIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    rate_limited(user, "turn")
    if body.text is None and body.answers is None:
        raise ApiError(422, "empty_turn", "Send text or answers.")
    answers = [a.model_dump() for a in body.answers] if body.answers is not None else None
    try:
        return _run_turn(db, user, body.profile_id, body.language, body.text, answers)
    except ValueError as exc:
        raise ApiError(422, "invalid_answer", str(exc)) from exc


class VoiceIn(BaseModel):
    profile_id: str
    language: str = "en"
    audio_base64: str = Field(max_length=4_000_000)  # ~30 s of 16 kHz mono WAV
    mime: str = "audio/wav"
    sample_rate: int = 16000
    speak: bool = True


@router.post("/voice/turn")
def voice_turn(body: VoiceIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Audio in -> Bhashini ASR -> conversation turn -> Bhashini TTS.

    If Bhashini is not configured or fails, responds 503 with fallback "browser"
    so the app switches to on-device speech recognition and typing.
    """
    rate_limited(user, "turn")
    lang = lang_or_default(body.language)
    try:
        base64.b64decode(body.audio_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ApiError(422, "bad_audio", "audio_base64 is not valid base64") from exc
    fmt = "wav" if "wav" in body.mime else body.mime.split("/")[-1].split(";")[0]
    try:
        text = bhashini.asr(body.audio_base64, lang, fmt, body.sample_rate)
    except bhashini.BhashiniUnavailable as exc:
        raise ApiError(503, "asr_unavailable", f"Speech recognition unavailable: {exc}", fallback="browser") from exc
    if not text:
        raise ApiError(422, "no_speech", "I could not hear anything. Please try again.", fallback="text")
    out = _run_turn(db, user, body.profile_id, lang, text, None, transcript_source="voice")
    out["reply_audio_base64"] = None
    if body.speak:
        try:
            out["reply_audio_base64"] = bhashini.tts(out["reply_text"], lang)
        except bhashini.BhashiniUnavailable:
            pass  # the browser reads the text aloud
    return out


class TtsIn(BaseModel):
    text: str = Field(max_length=600)
    language: str = "en"


@router.post("/voice/tts")
def tts(body: TtsIn, user: User = Depends(current_user)):
    rate_limited(user, "tts")
    try:
        return {"audio_base64": bhashini.tts(body.text, lang_or_default(body.language)), "format": "wav"}
    except bhashini.BhashiniUnavailable as exc:
        raise ApiError(503, "tts_unavailable", str(exc), fallback="browser") from exc
