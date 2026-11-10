"""Measure fact-extraction accuracy on the 30-utterance test set (10 per language).

    ANTHROPIC_API_KEY=... python scripts/eval_extractor.py      # Claude (+ keyword gap-filling)
    python scripts/eval_extractor.py                             # keyword extractor only

Prints accuracy per language and any invented sensitive facts. Report the
numbers in the README (section "Testing and results").
"""

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services import extractor  # noqa: E402
from tests.test_extractor import CASES, SENSITIVE  # noqa: E402


def main() -> int:
    per = defaultdict(lambda: [0, 0])
    invented = []
    used = set()
    for lang, pending, text, expected in CASES:
        facts, name = extractor.extract(text, lang, pending)
        used.add(name)
        for k, v in expected.items():
            per[lang][1] += 1
            if facts.get(k) == v:
                per[lang][0] += 1
            else:
                print(f"  miss [{lang}] {text!r}: {k} expected {v!r}, got {facts.get(k)!r}")
        invented += [(text, k) for k in facts if k in SENSITIVE and k not in expected and k != pending]
    total = [sum(x[0] for x in per.values()), sum(x[1] for x in per.values())]
    print(f"\nextractor: {', '.join(sorted(used))}")
    for lang, (c, n) in per.items():
        print(f"  {lang}: {c}/{n} = {c / n:.0%}")
    print(f"  all: {total[0]}/{total[1]} = {total[0] / total[1]:.0%}")
    print(f"  invented sensitive facts: {len(invented)} {invented if invented else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
