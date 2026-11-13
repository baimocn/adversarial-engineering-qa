#!/usr/bin/env python3
"""Compare two independent subjective judgments and apply the 2+1 rule.

Two different-family judges answer the same item in isolation. Agreement with
verifiable evidence is a pass; disagreement goes to an adjudicator; an
adjudicator that cannot cite evidence (or is itself invalid) goes to a human.

Usage:
  python scripts/judge_panel.py compare --root <task-root> \
    --judgment-a <a.json> --judgment-b <b.json> \
    [--adjudication <adj.json>] --out <panel.json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import panel_lib  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="2+1 subjective judgment panel")
    sub = parser.add_subparsers(dest="cmd", required=True)
    cmp_p = sub.add_parser("compare")
    cmp_p.add_argument("--root", required=True)
    cmp_p.add_argument("--judgment-a", required=True)
    cmp_p.add_argument("--judgment-b", required=True)
    cmp_p.add_argument("--adjudication", default=None)
    cmp_p.add_argument("--out", required=True)

    args = parser.parse_args()
    if args.cmd != "compare":
        return 2

    root = Path(args.root).resolve()
    try:
        a = panel_lib.load_json(Path(args.judgment_a))
        b = panel_lib.load_json(Path(args.judgment_b))
        adj = panel_lib.load_json(Path(args.adjudication)) if args.adjudication else None
    except (OSError, ValueError) as exc:
        print(f"FATAL: cannot read judgment: {exc}")
        return 1

    result = panel_lib.decide_panel(root, a, b, adj)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "item_id": result["item_id"],
        "category": result["category"],
        "verdict": result["verdict"],
        "A": result["judges"]["A"],
        "B": result["judges"]["B"],
        "adjudication": result["adjudication"],
    }, ensure_ascii=False, indent=2))
    print("written:", out)
    if result["category"] == "human_required":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
