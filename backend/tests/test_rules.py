"""Rule tests, parametrised from the `examples` block of every scheme file.

A wrong eligibility answer is the worst failure this product can have, so every
scheme ships with at least one qualifying profile and one failing profile.
"""

import time

import pytest

from app.fields import FIELD_BY_NAME, coerce
from app.services import jsonlogic, rules

SCHEMES = rules.load_schemes()
CASES = [(sid, ex) for sid, s in SCHEMES.items() for ex in s["examples"]]


@pytest.mark.parametrize("sid,example", CASES, ids=[f"{s}:{e['name']}" for s, e in CASES])
def test_scheme_examples(sid, example):
    r = rules.evaluate(SCHEMES[sid], example["profile"])
    assert r["status"] == example["expect"], r
    if "failed" in example:
        assert set(example["failed"]) <= set(r["failed"]), r
    if "missing" in example:
        assert r["missing"] == example["missing"], r


@pytest.mark.parametrize("sid", list(SCHEMES))
def test_scheme_file_is_well_formed(sid):
    s = SCHEMES[sid]
    assert s["examples"], "every scheme needs examples"
    assert any(e["expect"] == "eligible" for e in s["examples"])
    assert any(e["expect"] == "not_eligible" for e in s["examples"])
    assert s["source_url"].startswith("https://")
    for lang in ("en", "ta", "hi"):
        assert s["name"][lang] and s["benefit"][lang] and s["apply_at"][lang]
    ids = [c["id"] for c in s["clauses"]]
    assert len(ids) == len(set(ids))
    for c in s["clauses"]:
        assert c["source"]["url"].startswith("https://"), f"{sid}.{c['id']} lacks a source"
        assert c["source"]["quality"] in ("official", "secondary")
        for lang in ("en", "ta", "hi"):
            assert c["text"][lang]
        for v in jsonlogic.variables(c["rule"]):
            assert v in FIELD_BY_NAME, f"{sid}.{c['id']} uses unknown field {v}"
    for e in s["examples"]:
        for k, v in e["profile"].items():
            coerce(FIELD_BY_NAME[k], v)  # example values must be valid field values


def test_every_clause_can_fail():
    """Every clause has at least one example profile that fails exactly because of it."""
    failed_somewhere = {(sid, f) for sid, s in SCHEMES.items() for e in s["examples"] for f in e.get("failed", [])}
    untested = [(sid, c["id"]) for sid, s in SCHEMES.items() for c in s["clauses"] if (sid, c["id"]) not in failed_somewhere]
    assert not untested, untested


def test_same_profile_same_result():
    p = {"age": 62, "gender": "female", "marital_status": "widowed", "bpl_card": True, "state": "Tamil Nadu"}
    assert rules.evaluate_all(p) == rules.evaluate_all(dict(p))


def test_evaluation_under_300ms():
    p = {"age": 30, "gender": "female", "state": "Tamil Nadu"}
    t = time.perf_counter()
    for _ in range(10):
        rules.evaluate_all(p)
    assert (time.perf_counter() - t) / 10 < 0.3


def test_next_question_prefers_most_unlocking_field():
    results = rules.evaluate_all({})
    assert rules.next_question(results) == "age"


def test_lakshmi_full_profile():
    lakshmi = {
        "age": 62,
        "gender": "female",
        "state": "Tamil Nadu",
        "district": "Madurai",
        "marital_status": "widowed",
        "bpl_card": True,
        "has_bank_account": True,
        "has_lpg_connection": True,
        "annual_family_income": 60000,
        "occupation": "homemaker",
        "caste_category": "MBC",
        "land_acres": 0,
        "disability_percent": 0,
        "girl_children_under_10": 0,
        "family_pays_income_tax": False,
        "family_govt_job": False,
        "family_govt_pension": "none",
        "receives_social_pension": False,
        "owns_four_wheeler": False,
        "family_elected_rep": False,
        "family_registered_professional": False,
    }
    g = rules.grouped(lakshmi, "en")
    ids = [s["id"] for s in g["eligible"]]
    assert set(ids) == {"ignoaps", "ignwps", "pmsby", "cmchis", "kmut"}
    assert g["needs_info"] == []
    assert g["next_question"] is None
    # widow pension and KMUT exclude each other: the app must say so
    assert any(set(c["schemes"]) == {"kmut", "ignwps"} for c in g["conflicts"])
    # turning 70 unlocks Vay Vandana; 71 drops PMSBY eligibility is not "upcoming"
    assert any(u["id"] == "ab_pmjay_vay_vandana" for u in rules.upcoming(dict(lakshmi, age=66), "en"))


def test_kleene_logic():
    assert jsonlogic.evaluate({"and": [{"==": [{"var": "a"}, 1]}, {"==": [{"var": "b"}, 1]}]}, {"a": 2}) is False
    assert jsonlogic.evaluate({"and": [{"==": [{"var": "a"}, 1]}, {"==": [{"var": "b"}, 1]}]}, {"a": 1}) is None
    assert jsonlogic.evaluate({"or": [{"==": [{"var": "a"}, 1]}, {"==": [{"var": "b"}, 1]}]}, {"a": 1}) is True
    assert jsonlogic.missing_for({"or": [{"==": [{"var": "a"}, 1]}, {"==": [{"var": "b"}, 1]}]}, {"a": 2}) == ["b"]
    assert jsonlogic.evaluate({"between": [{"var": "x"}, 18, 40]}, {"x": 40}) is True
    with pytest.raises(jsonlogic.RuleError):
        jsonlogic.evaluate({"nope": [1]}, {})
