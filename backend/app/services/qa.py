"""Cited Q&A about a scheme, answered only from the scheme's own encoded text.

Passages come from the scheme file (clauses, benefit, where to apply, office
checks, documents), each carrying its source link, in all three languages.
Retrieval is a small BM25 over those passages. With Claude configured, the
answer is phrased from the retrieved passages only; otherwise the best
passages are returned as the answer. If nothing relevant is found, we say so.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter

from app.config import settings
from app.services import rules
from app.services.doc_doctor import DOC_TYPES

log = logging.getLogger(__name__)
WORD = re.compile(r"[\w஀-௿ऀ-ॿ]+")
STOP = {"the", "a", "an", "is", "are", "i", "my", "to", "of", "for", "do", "what", "how", "can", "in", "this", "it", "be", "and", "or", "scheme"}

NOT_FOUND = {
    "en": "I could not find that in the official rules I have. Please ask at the office: {office}.",
    "ta": "என்னிடம் உள்ள அதிகாரப்பூர்வ விதிகளில் இது இல்லை. அலுவலகத்தில் கேளுங்கள்: {office}.",
    "hi": "मेरे पास मौजूद आधिकारिक नियमों में यह नहीं मिला। कृपया कार्यालय में पूछें: {office}.",
}


def _tokens(s: str) -> list[str]:
    return [w for w in WORD.findall(s.lower()) if w not in STOP and len(w) > 1]


def passages(scheme_id: str, lang: str) -> list[dict]:
    s = rules.load_schemes()[scheme_id]
    out = []
    for c in s["clauses"]:
        out.append({"text": c["text"][lang], "kind": "eligibility", "source": c["source"]})
    gen = {"title": "Official scheme page", "url": s["source_url"], "locator": "", "quality": "official"}
    benefit_word = {"en": "Benefit", "ta": "பயன்", "hi": "लाभ"}[lang]
    apply_word = {"en": "Where to apply", "ta": "எங்கே விண்ணப்பிப்பது", "hi": "कहाँ आवेदन करें"}[lang]
    docs_word = {"en": "Documents needed", "ta": "தேவையான ஆவணங்கள்", "hi": "आवश्यक दस्तावेज़"}[lang]
    out.append({"text": f"{benefit_word}: {s['benefit'][lang]} (money amount)", "kind": "benefit", "source": gen})
    out.append({"text": f"{apply_word}: {s['apply_at'][lang]} (apply office where)", "kind": "apply", "source": gen})
    out.append(
        {
            "text": f"{docs_word}: " + ", ".join(DOC_TYPES[d]["label"][lang] for d in s["required_documents"]) + " (documents papers certificate)",
            "kind": "documents",
            "source": gen,
        }
    )
    for o in s.get("office_checks", []):
        out.append({"text": o[lang], "kind": "office_check", "source": gen})
    return out


def retrieve(question: str, scheme_id: str, lang: str, k: int = 4) -> list[dict]:
    ps = passages(scheme_id, lang) + (passages(scheme_id, "en") if lang != "en" else [])
    docs = [_tokens(p["text"]) for p in ps]
    q = _tokens(question)
    if not q:
        return []
    n = len(docs)
    avg = sum(len(d) for d in docs) / n
    df = Counter(w for d in docs for w in set(d))
    scored = []
    for p, d in zip(ps, docs, strict=False):
        tf = Counter(d)
        score = 0.0
        for w in q:
            # prefix match helps with Tamil/Hindi inflections
            f = sum(c for t, c in tf.items() if t == w or (len(w) >= 4 and (t.startswith(w[:4]) or w.startswith(t[:4]))))
            if f:
                idf = math.log(1 + (n - df.get(w, 0) + 0.5) / (df.get(w, 0) + 0.5))
                score += idf * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * len(d) / avg))
        if score > 0:
            scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    seen, out = set(), []
    for _, p in scored:
        if p["text"] not in seen:
            seen.add(p["text"])
            out.append(p)
        if len(out) == k:
            break
    return out


def answer(question: str, scheme_id: str, lang: str) -> dict:
    s = rules.load_schemes()[scheme_id]
    hits = retrieve(question, scheme_id, lang)
    if not hits:
        return {"answer": NOT_FOUND[lang].format(office=s["apply_at"][lang]), "citations": [], "grounded": False}
    text = " ".join(h["text"] for h in hits[:2])
    if settings.llm_enabled:
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=settings.llm_timeout_s, max_retries=1)
            ctx = "\n".join(f"[{i + 1}] {h['text']}" for i, h in enumerate(hits))
            msg = client.messages.create(
                model=settings.anthropic_model,
                max_tokens=300,
                system="Answer in at most two short sentences, in the language code given, using ONLY the numbered passages. "
                "Cite like [1]. If the passages do not answer the question, reply exactly NOT_FOUND.",
                messages=[{"role": "user", "content": f"Language: {lang}\nScheme: {s['name']['en']}\nPassages:\n{ctx}\nQuestion: {question}"}],
            )
            out = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
            if out and out != "NOT_FOUND":
                text = out
            elif out == "NOT_FOUND":
                return {"answer": NOT_FOUND[lang].format(office=s["apply_at"][lang]), "citations": [], "grounded": False}
        except Exception as exc:
            log.warning("LLM answer failed, returning passages: %s", exc)
    return {"answer": text, "citations": [{"text": h["text"], "source": h["source"]} for h in hits], "grounded": True}
