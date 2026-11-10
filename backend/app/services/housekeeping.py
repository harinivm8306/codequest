"""Rate limiting, retention clean-up and audit hashing."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import defaultdict, deque
from datetime import timedelta

from app.config import settings
from app.db import Document, Profile, SessionLocal, utcnow


class RateLimiter:
    """Sliding one-minute window per key. In-memory: fine for a single instance."""

    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self.hits: dict[str, deque] = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self.lock:
            q = self.hits[key]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= self.per_minute:
                return False
            q.append(now)
            return True


limiter = RateLimiter(settings.rate_limit_per_minute)


def profile_hash(data: dict) -> str:
    """Hash of eligibility inputs only — no name or district — for the audit log."""
    facts = {k: v for k, v in sorted(data.items()) if k not in ("name", "district")}
    return hashlib.sha256((settings.hash_salt + json.dumps(facts, sort_keys=True, default=str)).encode()).hexdigest()


def hash_secret(s: str) -> str:
    return hashlib.sha256((settings.hash_salt + s).encode()).hexdigest()


def cleanup() -> dict:
    """Delete expired document records and profiles inactive past the retention window."""
    now = utcnow()
    with SessionLocal() as db:
        docs = db.query(Document).filter(Document.saved.is_(False), Document.expires_at.is_not(None), Document.expires_at < now).delete()
        old = db.query(Profile).filter(Profile.updated_at < now - timedelta(days=settings.profile_inactive_days)).all()
        for p in old:
            db.delete(p)
        db.commit()
    return {"documents_deleted": docs, "profiles_deleted": len(old)}
