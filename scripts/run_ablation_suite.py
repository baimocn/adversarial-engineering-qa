#!/usr/bin/env python3
"""Run the configured bad/good ablation suite against current_standard_gate.py."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "current_standard_gate.py"


def jload(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def jwrite(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def set_pointer(obj, pointer: str, value) -> None:
    parts = [p.replace("~1", "/").replace("~0", "~") for p in pointer.lstrip("/").split("/")]
    cur = obj
    for part in parts[:-1]:
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    key = int(parts[-1]) if isinstance(cur, list) else parts[-1]
    cur[key] = value


def apply_case(root: Path, case: dict) -> None:
    op = case["op"]
    if op == "copy_file":
        target = root / case["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(Path(case["src"]).read_bytes())
        return
    if op == "delete":
        target = root / case["path"]
        if target.is_file():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)
        else:
            raise ValueError(f"{case['id']}: delete target missing: {case['path']}")
        return
    target = root / case["path"]
    if op in ("replace", "replace_all_append"):
        raw = target.read_text(encoding="utf-8")
        if case["old"] not in raw:
            raise ValueError(f"{case['id']}: target text not found: {case['old']!r}")
        replaced = raw.replace(case["old"], case["new"]) if op == "replace_all_append" else raw.replace(case["old"], case["new"], 1)
        if op == "replace_all_append":
            replaced += case.get("append", "")
        target.write_text(replaced, encoding="utf-8")
        return
    if op == "append":
        with target.open("a", encoding="utf-8") as stream:
            stream.write(case["text"])
        return
    if op == "json_set":
        data = jload(target)
        set_pointer(data, case["pointer"], case["value"])
        jwrite(target, data)
        return
    raise ValueError(f"unsupported op: {op}")


def run_gate(root: Path, out: Path, profile: str) -> dict:
    proc = subprocess.run(
        [sys.executable, "-I", str(GATE), "--root", str(root), "--profile", profile, "--out", str(out)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    payload = jload(out) if out.is_file() else {}
    payload["returncode"] = proc.returncode
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description="Run current-standard ablation suite")
    ap.add_argument("--catalog", default=str(ROOT / "config/ablation_cases.json"))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    catalog = jload(Path(args.catalog))
    good_root = Path(os.environ.get("CURRENT_STANDARD_GOOD_ROOT") or catalog["good_root"])
    profile = catalog["good_profile"]
    if not good_root.is_dir():
        # CI will not have the local accepted v30 tree. Skip with an explicit
        # status instead of pretending the ablation suite ran.
        report = {
            "schema": "current-standard-ablation-suite/1",
            "ok": True,
            "skipped": True,
            "reason": f"good_root missing: {good_root}",
            "results": [],
        }
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        jwrite(out, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    results = []
    with tempfile.TemporaryDirectory(prefix="current-standard-ablation-") as tmp:
        base = Path(tmp)
        good_out = base / "good.json"
        good = run_gate(good_root, good_out, profile)
        results.append({"case": "good", "expected": "PASS", "decision": good.get("decision"), "ok": good.get("decision") == "PASS"})
        for case in catalog["cases"]:
            root = base / case["id"]
            shutil.copytree(good_root, root)
            apply_case(root, case)
            out = base / f"{case['id']}.json"
            payload = run_gate(root, out, profile)
            failed_rules = {f["rule"] for f in payload.get("findings", []) if f.get("status") == "fail"}
            ok = payload.get("decision") == "FAIL" and case["rule"] in failed_rules
            results.append({
                "case": case["id"], "rule": case["rule"], "expected": "FAIL",
                "decision": payload.get("decision"), "failed_rules": sorted(failed_rules), "ok": ok,
            })

    ok = all(r["ok"] for r in results)
    report = {"schema": "current-standard-ablation-suite/1", "ok": ok, "results": results}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    jwrite(out, report)
    print(json.dumps({"ok": ok, "good": results[0], "cases": len(results) - 1}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
