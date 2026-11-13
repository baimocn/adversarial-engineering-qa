#!/usr/bin/env python3
"""Validate a model-proposed decomposition before any check is executed.

Four hard rules:
  1. finite answer space (must include "unknown")
  2. executable verifier (command / file_contains / json_value / regex / hash_equal)
  3. traceability (every check points to an existing requirement)
  4. coverage (every requirement has at least one check)

A check that cannot be executed is not accepted; a requirement with no check is
reported as uncovered, not silently passed.

Usage:
  python scripts/validate_decomposition.py --spec decomposition.json \
    --root <task-root> --out validation.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SUPPORTED = {"command", "file_contains", "json_value", "regex", "hash_equal", "manual"}
SHELL_CHARS = set("|&;<>`$")
ALLOWED_COMMANDS = {"python", "python3", "pytest"}
MAX_TEXT_BYTES = 8_000_000


def safe_path(root: Path, rel: str) -> Path | None:
    if not isinstance(rel, str) or not rel.strip():
        return None
    candidate = (root / rel).resolve()
    root_resolved = root.resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        return None
    return candidate


def command_args_problem(root: Path, exe: str, argv_args: list[str]) -> str | None:
    if exe not in ALLOWED_COMMANDS:
        return f"command not allowed: {exe}"
    if exe in ("python", "python3"):
        if not argv_args:
            return "python command needs a script path under the task root"
        first = argv_args[0]
        if first.startswith("-"):
            return "python -c/-m/stdin is not allowed; pass a script under the task root"
        script = safe_path(root, first)
        if script is None or not script.is_file() or script.suffix != ".py":
            return f"python script must be a .py file under the task root: {first}"
        return None
    if exe == "pytest":
        for arg in argv_args:
            if arg.startswith("-"):
                continue
            if safe_path(root, arg) is None:
                return f"pytest arg escapes the task root: {arg}"
        return None
    return None


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a decomposition spec")
    parser.add_argument("--spec", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    try:
        spec = load(Path(args.spec))
    except (OSError, ValueError) as exc:
        print(f"FATAL: cannot read spec: {exc}")
        return 2

    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(spec, dict):
        errors.append("spec is not an object")
        spec = {}
    if spec.get("schema") != "decomposition/1":
        errors.append("schema must be 'decomposition/1'")
    if not isinstance(spec.get("task_family"), str) or not spec.get("task_family"):
        errors.append("task_family missing")

    requirements = spec.get("requirements") or []
    checks = spec.get("checks") or []
    if not isinstance(requirements, list) or not requirements:
        errors.append("requirements must be a non-empty list")
        requirements = []
    if not isinstance(checks, list) or not checks:
        errors.append("checks must be a non-empty list")
        checks = []

    req_ids = set()
    for index, req in enumerate(requirements):
        label = f"requirements[{index}]"
        if not isinstance(req, dict):
            errors.append(f"{label}: not an object")
            continue
        rid = req.get("id")
        if not isinstance(rid, str) or not rid:
            errors.append(f"{label}: id missing")
            continue
        if rid in req_ids:
            errors.append(f"{label}: duplicate id {rid}")
        req_ids.add(rid)
        if not isinstance(req.get("text"), str) or not req.get("text").strip():
            errors.append(f"{label} ({rid}): text missing")
        if not isinstance(req.get("source"), str) or not req.get("source").strip():
            errors.append(f"{label} ({rid}): source missing")

    check_ids = set()
    covered = set()
    manual_checks = 0
    for index, check in enumerate(checks):
        label = f"checks[{index}]"
        if not isinstance(check, dict):
            errors.append(f"{label}: not an object")
            continue
        cid = check.get("id")
        if not isinstance(cid, str) or not cid:
            errors.append(f"{label}: id missing")
            continue
        if cid in check_ids:
            errors.append(f"{label}: duplicate id {cid}")
        check_ids.add(cid)
        rid = check.get("requirement_id")
        if rid not in req_ids:
            errors.append(f"{label} ({cid}): requirement_id {rid!r} not found")
        else:
            covered.add(rid)
        if not isinstance(check.get("question"), str) or not check.get("question").strip():
            errors.append(f"{label} ({cid}): question missing")

        answer_space = check.get("answer_space")
        if not isinstance(answer_space, list) or not (2 <= len(answer_space) <= 6):
            errors.append(f"{label} ({cid}): answer_space must be a list of 2-6 options")
        elif "unknown" not in answer_space:
            errors.append(f"{label} ({cid}): answer_space must include 'unknown'")
        elif len(set(answer_space)) != len(answer_space):
            errors.append(f"{label} ({cid}): answer_space has duplicates")

        verifier = check.get("verifier")
        if not isinstance(verifier, dict):
            errors.append(f"{label} ({cid}): verifier missing")
            continue
        kind = verifier.get("kind")
        if kind not in SUPPORTED:
            errors.append(f"{label} ({cid}): unsupported verifier kind {kind!r}")
            continue
        if kind == "manual":
            if not check.get("human_required"):
                errors.append(f"{label} ({cid}): manual verifier requires human_required=true")
            else:
                manual_checks += 1
        elif kind == "command":
            command = verifier.get("command")
            argv = verifier.get("args")
            assertion = verifier.get("assert")
            if not isinstance(command, str) or not command:
                errors.append(f"{label} ({cid}): command verifier needs command")
            elif any(ch in SHELL_CHARS for ch in command):
                warnings.append(f"{label} ({cid}): command contains shell metacharacters; use argv")
            if not isinstance(argv, list) or any(not isinstance(x, str) for x in argv):
                errors.append(f"{label} ({cid}): command verifier args must be a string list")
                argv = []
            if isinstance(command, str) and command:
                problem = command_args_problem(root, Path(command).name, argv)
                if problem:
                    errors.append(f"{label} ({cid}): {problem}")
            if not isinstance(assertion, dict) or not any(
                    key in assertion for key in ("exit_code", "stdout_contains", "stderr_contains")):
                errors.append(f"{label} ({cid}): command verifier assert needs exit_code/stdout_contains/stderr_contains")
        elif kind == "file_contains":
            if not isinstance(verifier.get("path"), str) or not isinstance(verifier.get("needle"), str):
                errors.append(f"{label} ({cid}): file_contains needs path and needle")
            else:
                p = (root / verifier["path"]).resolve()
                if root not in p.parents and p != root:
                    errors.append(f"{label} ({cid}): path escapes task root")
                elif not p.is_file():
                    errors.append(f"{label} ({cid}): file not found: {verifier['path']}")
                elif p.stat().st_size > MAX_TEXT_BYTES:
                    errors.append(f"{label} ({cid}): file too large for static check (> {MAX_TEXT_BYTES} bytes)")
        elif kind == "json_value":
            if not all(isinstance(verifier.get(k), str) for k in ("path", "pointer")):
                errors.append(f"{label} ({cid}): json_value needs path and pointer")
            elif "equals" not in verifier:
                errors.append(f"{label} ({cid}): json_value needs equals")
            else:
                p = safe_path(root, verifier["path"])
                if p is None:
                    errors.append(f"{label} ({cid}): path escapes task root")
                elif not p.is_file():
                    errors.append(f"{label} ({cid}): file not found: {verifier['path']}")
                elif p.stat().st_size > MAX_TEXT_BYTES:
                    errors.append(f"{label} ({cid}): file too large for static check (> {MAX_TEXT_BYTES} bytes)")
        elif kind == "regex":
            if not isinstance(verifier.get("path"), str) or not isinstance(verifier.get("pattern"), str):
                errors.append(f"{label} ({cid}): regex needs path and pattern")
            else:
                try:
                    re.compile(verifier["pattern"])
                except re.error as exc:
                    errors.append(f"{label} ({cid}): invalid regex ({exc})")
                p = safe_path(root, verifier["path"])
                if p is None:
                    errors.append(f"{label} ({cid}): path escapes task root")
                elif not p.is_file():
                    errors.append(f"{label} ({cid}): file not found: {verifier['path']}")
                elif p.stat().st_size > MAX_TEXT_BYTES:
                    errors.append(f"{label} ({cid}): file too large for static check (> {MAX_TEXT_BYTES} bytes)")
        elif kind == "hash_equal":
            digest = verifier.get("sha256")
            if not isinstance(verifier.get("path"), str):
                errors.append(f"{label} ({cid}): hash_equal needs path")
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
                errors.append(f"{label} ({cid}): hash_equal needs a 64-hex sha256")

    uncovered = sorted(req_ids - covered)
    if uncovered:
        errors.append("uncovered requirements: " + ", ".join(uncovered))

    payload = {
        "schema": "decomposition-validation/1",
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "coverage": {
            "requirements": len(req_ids),
            "checks": len(check_ids),
            "covered": len(covered),
            "uncovered": uncovered,
            "manual_checks": manual_checks,
        },
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": payload["valid"], "coverage": payload["coverage"]}, ensure_ascii=False))
    for error in errors:
        print("  ERROR:", error)
    for warning in warnings:
        print("  WARN:", warning)
    print("written:", out)
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
