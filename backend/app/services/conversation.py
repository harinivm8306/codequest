"""Conversation manager: a small state machine, not a free chatbot.

Each turn: extract facts -> merge (confirming changes) -> run the rules engine ->
ask the one question that unlocks the most schemes, or finish.
"""

from __future__ import annotations

from typing import Any

from app.fields import FIELD_BY_NAME, FIELDS, GROUPS, NONE_OF_THESE, coerce, default_for_group_item, label, normalise
from app.i18n import t
from app.services import extractor, rules


def question_payload(key: str | None, lang: str) -> dict | None:
    """The question plus quick-reply chips for the frontend."""
    if key is None:
        return None
    if key in GROUPS:
        items = []
        for f in FIELDS:
            if f.group == key:
                for opt in f.options:
                    items.append({"field": f.name, "value": opt.value, "label": label(opt, lang)})
        return {"key": key, "text": GROUPS[key]["question"][lang], "multi": True, "options": items, "none_label": NONE_OF_THESE[lang]}
    f = FIELD_BY_NAME[key]
    return {
        "key": key,
        "text": (f.question or {}).get(lang, key),
        "multi": False,
        "input": f.type,
        "options": [{"field": f.name, "value": o.value, "label": label(o, lang)} for o in f.options],
    }


def _display(field: str, value: Any, lang: str) -> str:
    f = FIELD_BY_NAME[field]
    for o in f.options:
        if o.value == value:
            return label(o, lang)
    if isinstance(value, bool):
        return t("yes" if value else "no", lang)
    return str(value)


def _apply_group_defaults(group: str, facts: dict) -> dict:
    """In a tap-all-that-apply answer, unticked items are recorded as 'no'."""
    out = dict(facts)
    for f in FIELDS:
        if f.group == group and f.name not in out:
            out[f.name] = default_for_group_item(f)
    return out


def answers_to_facts(answers: list[dict], pending: str | None) -> dict:
    """Structured chip answers: [{"field": ..., "value": ...}] or [] for 'none of these'."""
    facts: dict[str, Any] = {}
    for a in answers:
        f = FIELD_BY_NAME.get(a.get("field", ""))
        if f is None:
            continue
        facts[f.name] = coerce(f, a.get("value"))
    if pending in GROUPS:
        facts = _apply_group_defaults(pending, facts)
    return facts


def turn(profile_data: dict, state: dict, lang: str, text: str | None = None, answers: list[dict] | None = None) -> dict:
    """Run one turn. Returns the response and the new (profile_data, state)."""
    state = dict(state or {})
    data = dict(profile_data or {})
    pending = state.get("pending")
    facts: dict[str, Any] = {}
    prefix: list[str] = []
    used = "chips"

    # 1. a pending "should I change it?" question
    confirm = state.pop("confirm", None)
    if confirm and answers and answers[0].get("field") == "__confirm__":
        text, answers = ("yes" if answers[0].get("value") else "no"), None
    if confirm and text is not None and not answers:
        yn = extractor._yes_no(text)  # noqa: SLF001 — shared helper
        if yn is True:
            data[confirm["field"]] = confirm["value"]
            prefix.append(t("changed", lang))
        else:
            prefix.append(t("kept", lang))
        text = None

    # 2. new facts
    if answers is not None:
        facts = answers_to_facts(answers, pending)
    elif text:
        facts, used = extractor.extract(text, lang, pending)
        if facts.pop(extractor.NONE_KEY, False) and pending in GROUPS:
            facts = _apply_group_defaults(pending, {})
        elif pending in GROUPS and any(FIELD_BY_NAME[k].group == pending for k in facts):
            facts = _apply_group_defaults(pending, facts)

    # 3. merge, asking before overwriting an earlier answer
    added: dict[str, Any] = {}
    asked_now = set(rules.fields_for_question(pending)) if pending else set()
    for k, v in facts.items():
        old = data.get(k)
        if old is not None and old != v and k not in asked_now and "confirm" not in state:
            state["confirm"] = {"field": k, "value": v}
            continue
        if old != v:
            data[k] = v
            added[k] = v

    # 4. decide what to say next
    results = rules.evaluate_all(data)
    nxt = rules.next_question(results)
    eligible = [r for r in results if r["status"] == rules.ELIGIBLE]
    question = None
    if "confirm" in state:
        c = state["confirm"]
        reply = t("confirm_change", lang, old=_display(c["field"], data.get(c["field"]), lang), new=_display(c["field"], c["value"], lang))
        question = {
            "key": "__confirm__",
            "text": reply,
            "multi": False,
            "input": "bool",
            "options": [{"field": "__confirm__", "value": True, "label": t("yes", lang)}, {"field": "__confirm__", "value": False, "label": t("no", lang)}],
        }
        state["pending"] = pending
    elif nxt is None:
        reply = t("done", lang, n=len(eligible)) if eligible else t("done_none", lang)
        state["pending"] = None
    else:
        question = question_payload(nxt, lang)
        lead = []
        if text is not None or answers is not None:
            if added:
                lead.append(t("noted", lang))
            elif nxt == pending and not prefix:
                lead.append(t("not_understood", lang))
        reply = " ".join(prefix + lead + [question["text"]])
        state["pending"] = nxt
    if prefix and question is None:
        reply = " ".join(prefix + [reply])

    return {
        "profile": data,
        "state": state,
        "response": {
            "facts_added": added,
            "reply_text": reply,
            "question": question,
            "next_field": state.get("pending"),
            "done": nxt is None and "confirm" not in state,
            "eligible_count": len(eligible),
            "extractor": used,
        },
    }


def greeting(profile_data: dict, lang: str) -> dict:
    data = normalise(profile_data or {})
    results = rules.evaluate_all(data)
    nxt = rules.next_question(results)
    q = question_payload(nxt, lang) if data else None
    return {"reply_text": t("greeting", lang), "question": q, "next_field": nxt if data else None}
