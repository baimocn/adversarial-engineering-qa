#!/usr/bin/env python3
"""Validate the human-selected model roles for the 2+1 protocol.

Rules:
  - decomposer: one model
  - judges: exactly two distinct models from different families
  - adjudicator: one model from a third family (not the judges' families)
  - executor: optional

Model strings are "provider/model" or "provider/model$level"; the family is the
model name before the first '-' (deepseek-v4.1-flash -> deepseek, glm-5.3-flash
-> glm, mimo-v2.6-pro -> mimo).

Usage:
  python scripts/validate_run_config.py --config run-config.json --out validation.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def family(model: str) -> str:
    name = str(model).split("$", 1)[0].rsplit("/", 1)[-1].strip()
    return name.split("-", 1)[0].lower()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate model roles")
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    try:
        cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"FATAL: cannot read config: {exc}")
        return 1

    errors: list[str] = []
    decomposer = cfg.get("decomposer")
    judges = cfg.get("judges")
    adjudicator = cfg.get("adjudicator")
    executor = cfg.get("executor")

    if not isinstance(decomposer, str) or not decomposer.strip():
        errors.append("decomposer must be one non-empty model string")
    if not isinstance(judges, list) or len(judges) != 2:
        errors.append("judges must be a list of exactly two models")
        judges = []
    elif any(not isinstance(j, str) or not j.strip() for j in judges):
        errors.append("judges contains an empty/invalid model")
    elif judges[0] == judges[1]:
        errors.append("judges must be two distinct models, not the same model twice")
    elif family(judges[0]) == family(judges[1]):
        errors.append(f"judges must be different families; both are {family(judges[0])}")
    if not isinstance(adjudicator, str) or not adjudicator.strip():
        errors.append("adjudicator must be one non-empty model string")
    elif len(judges) == 2 and all(isinstance(j, str) for j in judges):
        judge_families = {family(j) for j in judges}
        if family(adjudicator) in judge_families:
            errors.append(
                f"adjudicator family {family(adjudicator)} is the same as a judge; use a third family"
            )
    if executor is not None and (not isinstance(executor, str) or not executor.strip()):
        errors.append("executor must be a non-empty model string when provided")

    payload = {
        "schema": "model-roles-validation/1",
        "valid": not errors,
        "errors": errors,
        "families": {
            "decomposer": family(decomposer) if isinstance(decomposer, str) and decomposer else None,
            "judges": [family(j) for j in judges if isinstance(j, str) and j],
            "adjudicator": family(adjudicator) if isinstance(adjudicator, str) and adjudicator else None,
        },
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("written:", out)
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
