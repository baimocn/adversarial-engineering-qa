#!/usr/bin/env python3
"""Run the vendored official unified-qa 0.5.0 layer.

prepare: generate the 90-check review template from the package zip.
review:  if official-0.5.0/review.json exists, run the official final review.

The official skill is read-only; this wrapper only invokes its trusted script.

Usage:
  python scripts/qa_unified.py prepare --workspace <ws> --zip <package.zip>
  python scripts/qa_unified.py review  --workspace <ws>
  python scripts/qa_unified.py summary --workspace <ws>
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OFFICIAL = HERE.parent / "official" / "autoresearch-unified-qa"
AUDIT = OFFICIAL / "scripts" / "audit_current.py"
PY = sys.executable


def run_official(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PY, "-I", str(AUDIT), *args], shell=False, capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )


def out_dir(ws: Path) -> Path:
    return ws / "official-0.5.0"


def cmd_prepare(a) -> int:
    if not AUDIT.is_file():
        print(f"FATAL: official 0.5.0 audit_current.py not found: {AUDIT}")
        return 2
    ws = Path(a.workspace).resolve()
    out = out_dir(ws)
    out.mkdir(parents=True, exist_ok=True)
    proc = run_official([str(Path(a.zip).resolve()), "--out-dir", str(out), "--prepare-only"])
    (out / "prepare.json").write_text(
        json.dumps({"returncode": proc.returncode, "stdout": proc.stdout,
                    "stderr": proc.stderr[-2000:]}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(proc.stdout.strip()[-1000:])
    if proc.returncode != 0:
        print(proc.stderr[-1000:], file=sys.stderr)
    return proc.returncode


def cmd_review(a) -> int:
    ws = Path(a.workspace).resolve()
    out = out_dir(ws)
    prep_path = out / "prepare.json"
    if not prep_path.is_file():
        print("FATAL: run `qa_unified.py prepare` first")
        return 2
    prep = json.loads(prep_path.read_text(encoding="utf-8"))
    try:
        prepared = json.loads(prep.get("stdout") or "{}")
    except ValueError:
        prepared = {}
    source_root = prepared.get("source_root")
    review = out / "review.json"
    summary = {
        "schema": "official-0.5.0-summary/1",
        "review_template": str(out / "inspection" / "review_template.json"),
        "review": str(review),
        "decision": "INCOMPLETE",
        "code": "REVIEW_NOT_FILLED",
    }
    if not isinstance(source_root, str) or not Path(source_root).is_dir():
        summary.update({"code": "SOURCE_ROOT_MISSING", "source_root": source_root})
    elif not review.is_file():
        summary["code"] = "REVIEW_NOT_FILLED"
    else:
        final = out / "final"
        final.mkdir(parents=True, exist_ok=True)
        proc = run_official([source_root, "--review", str(review), "--out-dir", str(final)])
        report = {}
        if (final / "report.json").is_file():
            report = json.loads((final / "report.json").read_text(encoding="utf-8"))
        summary = {
            "schema": "official-0.5.0-summary/1",
            "review_template": str(out / "inspection" / "review_template.json"),
            "review": str(review),
            "final_dir": str(final),
            "decision": report.get("decision", "INCOMPLETE"),
            "returncode": proc.returncode,
            "checks": report.get("checks") or [],
            "stderr": proc.stderr[-2000:],
        }
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": summary.get("decision"), "code": summary.get("code"),
                      "review_template": summary.get("review_template")}, ensure_ascii=False))
    return 0 if summary.get("decision") in ("PASS", "FAIL") else 2


def cmd_summary(a) -> int:
    ws = Path(a.workspace).resolve()
    p = out_dir(ws) / "summary.json"
    if not p.is_file():
        print("FATAL: no summary; run prepare/review first")
        return 2
    print(p.read_text(encoding="utf-8"))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Official unified-qa 0.5.0 wrapper")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare"); p.add_argument("--workspace", required=True)
    p.add_argument("--zip", required=True); p.set_defaults(fn=cmd_prepare)
    p = sub.add_parser("review"); p.add_argument("--workspace", required=True)
    p.set_defaults(fn=cmd_review)
    p = sub.add_parser("summary"); p.add_argument("--workspace", required=True)
    p.set_defaults(fn=cmd_summary)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
