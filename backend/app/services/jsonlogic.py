"""A small, deterministic JSON-Logic evaluator with three-valued (Kleene) logic.

Why our own instead of a pip package?
  * Eligibility needs a third answer: "unknown". If the citizen has not told us
    their income yet, `income <= 250000` is neither true nor false. Kleene logic
    lets a scheme be ruled out early (one clause is definitely false) while still
    reporting exactly which facts are missing for the rest.
  * The operator set we need is tiny, so the whole engine fits on one screen and
    is easy for judges and reviewers to audit.

Values: True, False, or UNKNOWN (None is treated as unknown in comparisons).

Supported operators: var, ==, !=, <, <=, >, >=, and, or, !, in, between.
"""

from __future__ import annotations

from typing import Any

UNKNOWN = None  # sentinel for the third truth value


class RuleError(ValueError):
    """Raised for malformed rules (caught by tests, never at runtime for valid files)."""


def _is_rule(x: Any) -> bool:
    return isinstance(x, dict) and len(x) == 1


def variables(rule: Any) -> set[str]:
    """All profile fields a rule reads."""
    out: set[str] = set()
    if _is_rule(rule):
        op, args = next(iter(rule.items()))
        if op == "var":
            out.add(args if isinstance(args, str) else args[0])
            return out
        for a in args if isinstance(args, list) else [args]:
            out |= variables(a)
    elif isinstance(rule, list):
        for a in rule:
            out |= variables(a)
    return out


def _compare(op: str, a: Any, b: Any):
    if a is None or b is None:
        return UNKNOWN
    try:
        if op == "==":
            return a == b
        if op == "!=":
            return a != b
        if op == "<":
            return a < b
        if op == "<=":
            return a <= b
        if op == ">":
            return a > b
        if op == ">=":
            return a >= b
    except TypeError as exc:  # comparing str with int etc.
        raise RuleError(f"cannot compare {a!r} {op} {b!r}") from exc
    raise RuleError(op)


def evaluate(rule: Any, data: dict) -> Any:
    """Evaluate `rule` against `data`. Returns True, False, UNKNOWN or a plain value."""
    if not _is_rule(rule):
        if isinstance(rule, list):
            return [evaluate(r, data) for r in rule]
        return rule  # literal

    op, args = next(iter(rule.items()))
    if not isinstance(args, list):
        args = [args]

    if op == "var":
        return data.get(args[0])

    if op in ("==", "!=", "<", "<=", ">", ">="):
        if len(args) != 2:
            raise RuleError(f"{op} takes 2 args")
        return _compare(op, evaluate(args[0], data), evaluate(args[1], data))

    if op == "between":  # inclusive: lo <= x <= hi
        x, lo, hi = (evaluate(a, data) for a in args)
        if x is None:
            return UNKNOWN
        return lo <= x <= hi

    if op == "in":
        needle, hay = evaluate(args[0], data), evaluate(args[1], data)
        if needle is None:
            return UNKNOWN
        return needle in hay

    if op == "!":
        v = evaluate(args[0], data)
        return UNKNOWN if v is None else not bool(v)

    if op == "and":
        seen_unknown = False
        for a in args:
            v = evaluate(a, data)
            if v is None:
                seen_unknown = True
            elif not v:
                return False
        return UNKNOWN if seen_unknown else True

    if op == "or":
        seen_unknown = False
        for a in args:
            v = evaluate(a, data)
            if v is None:
                seen_unknown = True
            elif v:
                return True
        return UNKNOWN if seen_unknown else False

    raise RuleError(f"unsupported operator {op!r}")


def missing_for(rule: Any, data: dict) -> list[str]:
    """Fields that, if known, could change an UNKNOWN result.

    For an `or` that is unknown, only the branches that are themselves unknown
    matter; for an `and`, only the unknown children (a false child would have
    made the whole thing false already).
    """
    if evaluate(rule, data) is not None or not _is_rule(rule):
        return []
    op, args = next(iter(rule.items()))
    if not isinstance(args, list):
        args = [args]
    if op == "var":
        return [args[0]] if data.get(args[0]) is None else []
    if op in ("and", "or"):
        out: list[str] = []
        for a in args:
            for f in missing_for(a, data):
                if f not in out:
                    out.append(f)
        return out
    # leaf comparison: every unset variable it reads
    return [v for v in sorted(variables(rule)) if data.get(v) is None]
