#!/usr/bin/env python3
"""Execute the mechanical checks in a validated decomposition on the CPU.

Only command / file_contains / json_value / regex / hash_equal run here.
Manual checks are returned as human_required placeholders for the 2+1 panel.

Command safety: argv list, shell=False, cwd fixed to the task root, timeout,
and an executable allowlist. The decomposition is model-proposed; it is not
trusted to run arbitrary binaries.

Usage:
  python scripts/run_decomposition_checks.py --spec decomposition.json \
    --root <task-root> --out check-results.json [--timeout 600]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

ALLOWED_COMMANDS = {"python", "python3", "pytest"}
DEFAULT_TIMEOUT = 600
MAX_TEXT_BYTES = 8_000_000


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def safe_path(root: Path, rel: str) -> Path | None:
    if not isinstance(rel, str) or not rel.strip():
        return None
    candidate = (root / rel).resolve()
    root_resolved = root.resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        return None
    return candidate


def command_args_problem(root: Path, exe: str, argv_args: list[str]) -> str | None:
    """Reject commands that can execute arbitrary code outside the task root.

    python/python3: the first arg must be a .py file under the root; no -c/-m/stdin.
    pytest: non-flag args must stay under the root.
    Anything else is rejected.
    """
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
    return f"command not allowed: {exe}"


def resolve_pointer(data, pointer: str):
    if pointer in ("", "/"):
        return data, True
    if not pointer.startswith("/"):
        return None, False
    cur = data
    for raw in pointer[1:].split("/"):
        key = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, list):
            try:
                cur = cur[int(key)]
            except (ValueError, IndexError):
                return None, False
        elif isinstance(cur, dict):
            if key not in cur:
                return None, False
            cur = cur[key]
        else:
            return None, False
    return cur, True


def run_mechanical(check: dict, root: Path, timeout: int) -> dict:
    verifier = check.get("verifier") or {}
    kind = verifier.get("kind")
    cid = check.get("id")

    if kind == "manual":
        return {
            "check_id": cid,
            "category": "human_required",
            "verdict": "unknown",
            "evidence": {"kind": "manual", "reason": "subjective item; needs the 2+1 panel"},
        }

    if kind == "command":
        command = verifier.get("command")
        if not isinstance(command, str) or not command:
            return {"check_id": cid, "category": "verified", "verdict": "fail",
                    "evidence": {"kind": "command", "error": "missing command"}}
        exe = Path(command).name
        if exe not in ALLOWED_COMMANDS:
            return {"check_id": cid, "category": "verified", "verdict": "fail",
                    "evidence": {"kind": "command", "error": f"command not allowed: {exe}"}}
        raw_args = [str(x) for x in (verifier.get("args") or [])]
        problem = command_args_problem(root, exe, raw_args)
        if problem:
            return {"check_id": cid, "category": "verified", "verdict": "fail",
                    "evidence": {"kind": "command", "error": problem}}
        argv = [command] + raw_args
        try:
            proc = subprocess.run(
                argv, cwd=root, shell=False, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"check_id": cid, "category": "verified", "verdict": "fail",
                    "evidence": {"kind": "command", "error": str(exc), "argv": argv}}
        assertion = verifier.get("assert") or {}
        ok = True
        if "exit_code" in assertion:
            ok = ok and proc.returncode == assertion["exit_code"]
        if "stdout_contains" in assertion:
            ok = ok and assertion["stdout_contains"] in proc.stdout
        if "stderr_contains" in assertion:
            ok = ok and assertion["stderr_contains"] in proc.stderr
        return {
            "check_id": cid,
            "category": "verified",
            "verdict": "pass" if ok else "fail",
            "evidence": {
                "kind": "command", "argv": argv, "exit_code": proc.returncode,
                "stdout_tail": proc.stdout[-1000:], "stderr_tail": proc.stderr[-1000:],
            },
        }

    path = safe_path(root, verifier.get("path"))
    if path is None or not path.is_file():
        return {"check_id": cid, "category": "verified", "verdict": "fail",
                "evidence": {"kind": kind, "error": "path missing or escapes root"}}
    if kind in ("file_contains", "json_value", "regex") and path.stat().st_size > MAX_TEXT_BYTES:
        return {"check_id": cid, "category": "verified", "verdict": "fail",
                "evidence": {"kind": kind,
                             "error": f"file too large for static check (> {MAX_TEXT_BYTES} bytes)"}}

    if kind == "file_contains":
        needle = verifier.get("needle")
        if not isinstance(needle, str):
            return {"check_id": cid, "category": "verified", "verdict": "fail",
                    "evidence": {"kind": kind, "error": "missing needle"}}
        text = path.read_text(encoding="utf-8", errors="replace")
        ok = needle in text
        return {"check_id": cid, "category": "verified", "verdict": "pass" if ok else "fail",
                "evidence": {"kind": kind, "path": verifier["path"], "needle": needle}}

    if kind == "json_value":
        pointer = verifier.get("pointer")
        try:
            value, ok = resolve_pointer(load(path), pointer)
        except (OSError, ValueError) as exc:
            return {"check_id": cid, "category": "verified", "verdict": "fail",
                    "evidence": {"kind": kind, "error": str(exc)}}
        passed = ok and value == verifier.get("equals")
        return {"check_id": cid, "category": "verified", "verdict": "pass" if passed else "fail",
                "evidence": {"kind": kind, "path": verifier["path"], "pointer": pointer,
                             "observed": value if ok else None}}

    if kind == "regex":
        try:
            pattern = re.compile(verifier["pattern"])
        except re.error as exc:
            return {"check_id": cid, "category": "verified", "verdict": "fail",
                    "evidence": {"kind": kind, "error": f"invalid regex: {exc}"}}
        text = path.read_text(encoding="utf-8", errors="replace")
        matched = bool(pattern.search(text))
        expect_match = verifier.get("must_match", True)
        passed = matched == expect_match
        return {"check_id": cid, "category": "verified", "verdict": "pass" if passed else "fail",
                "evidence": {"kind": kind, "path": verifier["path"],
                             "matched": matched, "must_match": expect_match}}

    if kind == "hash_equal":
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        expected = str(verifier.get("sha256", "")).lower()
        return {"check_id": cid, "category": "verified",
                "verdict": "pass" if digest == expected else "fail",
                "evidence": {"kind": kind, "path": verifier["path"],
                             "observed": digest, "expected": expected}}

    return {"check_id": cid, "category": "verified", "verdict": "fail",
            "evidence": {"kind": kind, "error": "unsupported verifier"}}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run decomposition checks")
    parser.add_argument("--spec", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    try:
        spec = load(Path(args.spec))
    except (OSError, ValueError) as exc:
        print(f"FATAL: cannot read spec: {exc}")
        return 2

    items = [run_mechanical(check, root, args.timeout)
             for check in (spec.get("checks") or [])]
    payload = {"schema": "check-results/1", "items": items}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    fails = [x for x in items if x["category"] == "verified" and x["verdict"] == "fail"]
    manual = [x for x in items if x["category"] == "human_required"]
    print(f"checks={len(items)} fail={len(fails)} manual={len(manual)}")
    for item in fails:
        print(f"  FAIL {item['check_id']}: {item['evidence']}")
    print("written:", out)
    if fails:
        return 1
    return 2 if manual else 0


if __name__ == "__main__":
    raise SystemExit(main())
