"""Deterministic eligibility engine. The only component allowed to decide eligibility.

A scheme file lists clauses; the scheme's rule is the AND of its clauses. Each
clause is evaluated on its own with three-valued logic, so for every scheme we
can say exactly which clause passed, which failed, and which facts are missing.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from functools import lru_cache
from pathlib import Path

from app.config import settings
from app.fields import FIELD_BY_NAME, GROUPS, PRIORITY, normalise
from app.services import jsonlogic

ELIGIBLE, NOT_ELIGIBLE, NEEDS_INFO = "eligible", "not_eligible", "needs_info"


@lru_cache
def load_schemes() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for path in sorted(Path(settings.schemes_dir).glob("*/*.json")):
        s = json.loads(path.read_text(encoding="utf-8"))
        out[s["id"]] = s
    return out


@lru_cache
def rules_version() -> str:
    """Content hash of every scheme file, so an audit row pins the exact rules used."""
    h = hashlib.sha256()
    for sid, s in sorted(load_schemes().items()):
        h.update(sid.encode())
        h.update(json.dumps([c["rule"] for c in s["clauses"]], sort_keys=True).encode())
        h.update(str(s.get("version", 1)).encode())
    return h.hexdigest()[:12]


def evaluate(scheme: dict, profile: dict) -> dict:
    p = normalise(profile)
    passed, failed, missing = [], [], []
    for c in scheme["clauses"]:
        v = jsonlogic.evaluate(c["rule"], p)
        if v is True:
            passed.append(c["id"])
        elif v is False:
            failed.append(c["id"])
        else:
            for f in jsonlogic.missing_for(c["rule"], p):
                if f not in missing:
                    missing.append(f)
    if failed:
        status = NOT_ELIGIBLE
    elif missing:
        status = NEEDS_INFO
    else:
        status = ELIGIBLE
    return {"id": scheme["id"], "status": status, "passed": passed, "failed": failed, "missing": missing}


def evaluate_all(profile: dict) -> list[dict]:
    return [evaluate(s, profile) for s in load_schemes().values()]


def question_key(field_name: str) -> str:
    f = FIELD_BY_NAME[field_name]
    return f.group or f.name


def next_question(results: list[dict]) -> str | None:
    """The question (field name or group id) that unlocks the most undecided schemes."""
    counts: Counter[str] = Counter()
    for r in results:
        if r["status"] == NEEDS_INFO:
            for key in {question_key(f) for f in r["missing"]}:
                counts[key] += 1
    if not counts:
        return None
    order = {k: i for i, k in enumerate(PRIORITY)}
    return sorted(counts, key=lambda k: (-counts[k], order.get(k, 999)))[0]


def fields_for_question(key: str) -> list[str]:
    if key in GROUPS:
        return [f.name for f in FIELD_BY_NAME.values() if f.group == key]
    return [key]


def _localise(d: dict | None, lang: str) -> str:
    if not d:
        return ""
    return d.get(lang) or d.get("en", "")


def explain(result: dict, lang: str) -> dict:
    """Turn a raw result into what the citizen sees: reason, clauses with sources."""
    s = load_schemes()[result["id"]]
    clauses = {c["id"]: c for c in s["clauses"]}

    def view(cid: str) -> dict:
        c = clauses[cid]
        return {"id": cid, "text": _localise(c["text"], lang), "source": c["source"]}

    out = {
        "id": s["id"],
        "status": result["status"],
        "name": _localise(s["name"], lang),
        "level": s["level"],
        "category": s["category"],
        "benefit": _localise(s["benefit"], lang),
        "apply_at": _localise(s["apply_at"], lang),
        "source_url": s["source_url"],
        "verified_on": s["verified_on"],
        "passed": [view(c) for c in result["passed"]],
        "failed": [view(c) for c in result["failed"]],
        "missing": result["missing"],
        "office_checks": [_localise(o, lang) for o in s.get("office_checks", [])],
        "required_documents": s["required_documents"],
        "benefit_weight": s.get("benefit_weight", 0),
    }
    out["reason"] = (
        "; ".join(c["text"] for c in out["passed"])
        if result["status"] == ELIGIBLE
        else ("; ".join(c["text"] for c in out["failed"]) if result["status"] == NOT_ELIGIBLE else "")
    )
    return out


def conflicts(eligible_ids: set[str], lang: str) -> list[dict]:
    out = []
    for sid in eligible_ids:
        for c in load_schemes()[sid].get("conflicts_with", []):
            if c["scheme"] in eligible_ids:
                out.append({"schemes": [sid, c["scheme"]], "note": _localise(c["note"], lang)})
    return out


def upcoming(profile: dict, lang: str, horizon_years: int = 10) -> list[dict]:
    """Life-event reminders: schemes that become available as the person ages."""
    p = normalise(profile)
    if p.get("age") is None:
        return []
    now = {r["id"]: r["status"] for r in evaluate_all(p)}
    out = []
    for years in range(1, horizon_years + 1):
        future = dict(p, age=p["age"] + years)
        for r in evaluate_all(future):
            if now[r["id"]] != ELIGIBLE and r["status"] == ELIGIBLE and not any(u["id"] == r["id"] for u in out):
                s = load_schemes()[r["id"]]
                out.append({"id": r["id"], "name": _localise(s["name"], lang), "in_years": years, "at_age": p["age"] + years})
    return out


def grouped(profile: dict, lang: str) -> dict:
    results = evaluate_all(profile)
    views = [explain(r, lang) for r in results]
    eligible = sorted([v for v in views if v["status"] == ELIGIBLE], key=lambda v: -v["benefit_weight"])
    eligible_ids = {v["id"] for v in eligible}
    return {
        "rules_version": rules_version(),
        "eligible": eligible,
        "needs_info": [v for v in views if v["status"] == NEEDS_INFO],
        # "almost": failed exactly one clause
        "almost": [v for v in views if v["status"] == NOT_ELIGIBLE and len(v["failed"]) == 1],
        "not_eligible": [v for v in views if v["status"] == NOT_ELIGIBLE],
        "conflicts": conflicts(eligible_ids, lang),
        "upcoming": upcoming(profile, lang),
        "next_question": next_question(results),
        "disclaimer": {
            "en": "This is guidance only. The final decision is made by the department.",
            "ta": "இது வழிகாட்டுதல் மட்டுமே. இறுதி முடிவை அரசுத் துறையே எடுக்கும்.",
            "hi": "यह केवल मार्गदर्शन है। अंतिम निर्णय विभाग करेगा।",
        }[lang],
    }
