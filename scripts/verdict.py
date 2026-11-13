#!/usr/bin/env python3
"""Deterministic verdict from check results.

Categories:
  verified            — script/CPU check
  judged_agree        — two different-family judges agree with valid evidence
  judged_adjudicated  — an adjudicator resolved a disagreement with valid evidence
  human_required      — disagreement/unknown that no model could settle
  unknown             — no executable check

Rules (strict is the default):
  any fail (verified or judged)          -> FAIL
  any human_required / unknown / unknown  -> INCOMPLETE
  all pass                                -> PASS
  empty results                           -> INCOMPLETE

Usage:
  python scripts/verdict.py --results check-results.json --out verdict.json [--non-strict]
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

CATEGORIES = {"verified", "judged_agree", "judged_adjudicated", "human_required", "unknown"}
VERDICTS = {"pass", "fail", "unknown"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic QA verdict")
    parser.add_argument("--results", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--non-strict", action="store_true")
    args = parser.parse_args()

    try:
        data = json.loads(Path(args.results).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"FATAL: cannot read results: {exc}")
        return 2

    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        print("FATAL: results must contain an items list")
        return 2

    errors: list[str] = []
    counts = Counter()
    fail_ids: list[str] = []
    open_ids: list[str] = []
    for index, item in enumerate(items):
        label = f"items[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: not an object")
            continue
        cid = item.get("check_id")
        category = item.get("category")
        verdict = item.get("verdict")
        if not isinstance(cid, str) or not cid:
            errors.append(f"{label}: check_id missing")
            cid = label
        if category not in CATEGORIES:
            errors.append(f"{cid}: category {category!r} invalid")
            category = "unknown"
        if verdict not in VERDICTS:
            errors.append(f"{cid}: verdict {verdict!r} invalid")
            verdict = "unknown"
        counts[category] += 1
        if verdict == "fail" and category in ("verified", "judged_agree", "judged_adjudicated"):
            fail_ids.append(cid)
        if category in ("human_required", "unknown") or verdict == "unknown":
            open_ids.append(cid)

    strict = not args.non_strict
    if errors:
        decision = "INCOMPLETE"
    elif fail_ids:
        decision = "FAIL"
    elif open_ids:
        decision = "INCOMPLETE" if strict else "PASS_WITH_OPEN"
    elif items:
        decision = "PASS"
    else:
        decision = "INCOMPLETE"

    payload = {
        "schema": "verdict/1",
        "strict": strict,
        "decision": decision,
        "counts": dict(sorted(counts.items())),
        "fail_ids": fail_ids,
        "open_ids": open_ids,
        "errors": errors,
        "note": "human_required/unknown are never auto-passed in strict mode.",
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("written:", out)
    return {"PASS": 0, "PASS_WITH_OPEN": 0, "FAIL": 1}.get(decision, 2)


if __name__ == "__main__":
    raise SystemExit(main())
