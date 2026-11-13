#!/usr/bin/env python3
"""Batch-compare subjective judgments for all items in a directory.

Expected layout:
  <dir>/<item_id>/a.json
  <dir>/<item_id>/b.json
  <dir>/<item_id>/adjudication.json   (optional)

Output: panel.json with one decision per item and counts by category.
Exit: 0 = no human_required, 2 = at least one human_required, 1 = read/parse error.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import panel_lib  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch 2+1 judgment panel")
    parser.add_argument("--root", required=True)
    parser.add_argument("--dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    base = Path(args.dir).resolve()
    if not base.is_dir():
        print(f"FATAL: judgment dir not found: {base}")
        return 1

    items = []
    errors = []
    for item_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        a_p = item_dir / "a.json"
        b_p = item_dir / "b.json"
        if not a_p.is_file() or not b_p.is_file():
            errors.append(f"{item_dir.name}: missing a.json or b.json")
            items.append({
                "schema": "panel-decision/1", "item_id": item_dir.name,
                "category": "human_required", "verdict": "unknown",
                "errors": ["missing a.json or b.json"],
            })
            continue
        try:
            a = panel_lib.load_json(a_p)
            b = panel_lib.load_json(b_p)
            adj_p = item_dir / "adjudication.json"
            adj = panel_lib.load_json(adj_p) if adj_p.is_file() else None
        except (OSError, ValueError) as exc:
            errors.append(f"{item_dir.name}: {exc}")
            items.append({
                "schema": "panel-decision/1", "item_id": item_dir.name,
                "category": "human_required", "verdict": "unknown",
                "errors": [str(exc)],
            })
            continue
        items.append(panel_lib.decide_panel(root, a, b, adj))

    counts = Counter(item["category"] for item in items)
    payload = {
        "schema": "panel/1",
        "items": items,
        "counts": dict(sorted(counts.items())),
        "errors": errors,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("items:", len(items), "counts:", payload["counts"])
    for item in items:
        print(f"  {item['item_id']}: {item['category']} -> {item['verdict']}")
    if errors:
        for error in errors:
            print("  ERROR:", error)
    print("written:", out)
    if errors:
        return 1
    return 2 if counts.get("human_required") else 0


if __name__ == "__main__":
    raise SystemExit(main())
