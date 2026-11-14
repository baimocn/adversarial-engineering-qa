#!/usr/bin/env python3
"""Validate the current-standard rule catalog and profile references."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def jload(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate current-standard rule catalog")
    ap.add_argument("--catalog", default=str(ROOT / "config/rule_catalog.json"))
    ap.add_argument("--profiles", default=str(ROOT / "config/profiles"))
    ap.add_argument("--ablation", default=str(ROOT / "config/ablation_cases.json"))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    errors: list[str] = []
    catalog = jload(Path(args.catalog))
    ablation = jload(Path(args.ablation))
    profiles_dir = Path(args.profiles)
    profile_names = {p.stem for p in profiles_dir.glob("*.json")}
    case_ids = {c["id"] for c in ablation["cases"]}
    current_rules = [r for r in catalog["rules"] if r.get("class") in ("current_mechanical", "current_ablation_only")]

    for rule in catalog["rules"]:
        for key in ("id", "class", "source_docs", "verification"):
            if not rule.get(key):
                errors.append(f"rule missing {key}: {rule}")
        if rule.get("class") in ("current_mechanical", "current_ablation_only"):
            if not rule.get("bad_case"):
                errors.append(f"current rule has no bad_case: {rule.get('id')}")
            elif not (ROOT / rule["bad_case"]).is_file():
                bad_id = Path(rule["bad_case"]).stem
                if bad_id not in case_ids:
                    errors.append(f"bad_case not represented in ablation case catalog: {rule.get('id')} -> {rule['bad_case']}")
        if rule.get("class") == "legacy_archived" and not rule.get("superseded_by"):
            errors.append(f"legacy rule has no superseded_by: {rule.get('id')}")

    for name in ("default", ablation.get("good_profile")):
        if name and name not in profile_names:
            errors.append(f"missing profile: {name}")
    for case in ablation["cases"]:
        for key in ("id", "rule", "op", "path"):
            if not case.get(key):
                errors.append(f"ablation case missing {key}: {case}")

    result = {
        "schema": "rule-catalog-validation/1",
        "ok": not errors,
        "current_rules": len(current_rules),
        "legacy_rules": sum(r.get("class") == "legacy_archived" for r in catalog["rules"]),
        "platform_scope_rules": sum(r.get("class") == "platform_scope" for r in catalog["rules"]),
        "profiles": sorted(profile_names),
        "ablation_cases": len(ablation["cases"]),
        "errors": errors,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
