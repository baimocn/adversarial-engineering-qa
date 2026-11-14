#!/usr/bin/env python3
"""Binary current-standard verdict from check results.

The 0.5.0/0.5.6 effective profile exposes only PASS or FAIL to authors.
Internal coverage gaps are retained as `completion_status=QA_NOT_FINISHED`,
but they are not an author-facing PASS and never become PASS_WITH_WAIVERS.
Legacy scripts can still pass `--legacy-incomplete` to preserve their old
orchestration semantics; the current-standard gate does not use that mode.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

CATEGORIES = {"verified", "judged_agree", "judged_adjudicated", "human_required", "unknown"}
VERDICTS = {"pass", "fail", "unknown"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Current-standard binary QA verdict")
    parser.add_argument("--results", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--legacy-incomplete", action="store_true",
                        help="compatibility only: expose INCOMPLETE/PASS_WITH_OPEN as orchestration status")
    parser.add_argument("--non-strict", action="store_true",
                        help="deprecated compatibility alias for --legacy-incomplete")
    args = parser.parse_args()
    legacy_mode = args.legacy_incomplete or args.non_strict

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

    if errors or fail_ids:
        decision = "FAIL"
        completion = "QA_NOT_FINISHED" if errors and not fail_ids else "COMPLETE"
    elif open_ids or not items:
        decision = "FAIL"
        completion = "QA_NOT_FINISHED"
    else:
        decision = "PASS"
        completion = "COMPLETE"

    legacy_decision = decision
    if legacy_mode and open_ids and not fail_ids:
        legacy_decision = "PASS_WITH_OPEN" if args.non_strict else "INCOMPLETE"
    elif legacy_mode and completion == "QA_NOT_FINISHED" and not fail_ids:
        legacy_decision = "INCOMPLETE"

    payload = {
        "schema": "current-standard-verdict/1",
        "profile": "current-20261114",
        "decision": decision,
        "binary_external_decision": True,
        "completion_status": completion,
        "legacy_orchestration_decision": legacy_decision if legacy_mode else None,
        "counts": dict(sorted(counts.items())),
        "fail_ids": fail_ids,
        "open_ids": open_ids,
        "errors": errors,
        "note": "human_required/unknown/empty results are QA_NOT_FINISHED and never external PASS/PASS_WITH_WAIVERS.",
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("written:", out)
    return 0 if decision == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
