"""Check every scheme file before it ships: structure, fields, sources, and its own examples.

    python scripts/validate_schemes.py

Exit code 1 on any problem. Run in CI and before adding or editing a scheme.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.fields import FIELD_BY_NAME, coerce  # noqa: E402
from app.services import jsonlogic, rules  # noqa: E402
from app.services.doc_doctor import DOC_TYPES  # noqa: E402

REQUIRED = ["id", "level", "category", "name", "benefit", "clauses", "required_documents", "apply_at", "source_url", "verified_on", "version", "examples"]


def main() -> int:
    problems: list[str] = []
    schemes = rules.load_schemes()
    secondary = []
    for sid, s in schemes.items():
        for k in REQUIRED:
            if k not in s:
                problems.append(f"{sid}: missing '{k}'")
        for d in s.get("required_documents", []):
            if d not in DOC_TYPES:
                problems.append(f"{sid}: unknown document type '{d}'")
        for c in s.get("clauses", []):
            for v in jsonlogic.variables(c["rule"]):
                if v not in FIELD_BY_NAME:
                    problems.append(f"{sid}.{c['id']}: unknown field '{v}'")
            if c["source"]["quality"] == "secondary":
                secondary.append(f"{sid}.{c['id']}")
        failed_clauses = set()
        for e in s.get("examples", []):
            for k, v in e["profile"].items():
                try:
                    coerce(FIELD_BY_NAME[k], v)
                except Exception as exc:
                    problems.append(f"{sid} example '{e['name']}': {exc}")
            r = rules.evaluate(s, e["profile"])
            if r["status"] != e["expect"]:
                problems.append(f"{sid} example '{e['name']}': expected {e['expect']}, got {r['status']}")
            failed_clauses |= set(e.get("failed", []))
        for c in s.get("clauses", []):
            if c["id"] not in failed_clauses:
                problems.append(f"{sid}.{c['id']}: no example fails this clause")
    print(f"{len(schemes)} schemes, rules version {rules.rules_version()}")
    if secondary:
        print(f"{len(secondary)} clauses cite a secondary source; replace with the official guideline when available:")
        for x in sorted({s.split('.')[0] for s in secondary}):
            print(f"  - {x}")
    for p in problems:
        print("PROBLEM:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
