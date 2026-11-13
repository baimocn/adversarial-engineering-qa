#!/usr/bin/env python3
"""Merge mechanical check results with 2+1 panel decisions.

The decomposition runner emits human_required placeholders for subjective checks.
The panel emits judged_agree / judged_adjudicated / human_required decisions.
This script replaces each placeholder with the matching panel decision and keeps
unmatched panel items as additional rows.

Usage:
  python scripts/merge_check_results.py --checks check-results.json \
    --panel panel.json --out check-results-all.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge checks and panel results")
    parser.add_argument("--checks", required=True)
    parser.add_argument("--panel", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    try:
        checks = load(Path(args.checks)).get("items") or []
        panel = load(Path(args.panel)).get("items") or []
    except (OSError, ValueError) as exc:
        print(f"FATAL: cannot read inputs: {exc}")
        return 2

    by_item = {item.get("item_id"): item for item in panel if item.get("item_id")}
    used = set()
    merged = []
    for item in checks:
        cid = item.get("check_id")
        decision = by_item.get(cid)
        if item.get("category") == "human_required" and decision is not None:
            used.add(cid)
            merged.append({
                "check_id": cid,
                "category": decision.get("category", "human_required"),
                "verdict": decision.get("verdict", "unknown"),
                "evidence": {"panel": decision},
            })
        else:
            merged.append(item)

    for item in panel:
        if item.get("item_id") not in used:
            merged.append({
                "check_id": item.get("item_id"),
                "category": item.get("category", "human_required"),
                "verdict": item.get("verdict", "unknown"),
                "evidence": {"panel": item},
            })

    payload = {"schema": "check-results/1", "items": merged}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("items:", len(merged), "panel_used:", len(used))
    print("written:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
