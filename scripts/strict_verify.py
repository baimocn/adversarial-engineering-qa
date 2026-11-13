#!/usr/bin/env python3
"""End-to-end deterministic pipeline for one package.

This is the single command the orchestrator (or a workflow) calls after the
model-produced inputs exist:

  run-config.json       human-selected model roles
  decomposition.json    model-proposed checks (validated here)
  judgments/<id>/       optional 2+1 judgments

Steps: validate roles -> validate decomposition -> run CPU checks -> compare
panel (if present) -> merge -> deterministic verdict.

Usage:
  python scripts/strict_verify.py --repo-root . --task-root <task> --work-dir <ws>
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(script: str, args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-I", str(HERE / script), *args],
        shell=False, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Strict deterministic pipeline")
    parser.add_argument("--repo-root", default=str(HERE.parent))
    parser.add_argument("--task-root", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--package-zip", default=None,
                        help="submission zip; enables the official 0.3.10 and 0.5.0 layers")
    args = parser.parse_args()

    task = Path(args.task_root).resolve()
    work = Path(args.work_dir).resolve()
    work.mkdir(parents=True, exist_ok=True)
    steps = []

    config = work / "run-config.json"
    if not config.is_file():
        print(f"FATAL: missing {config}")
        return 2
    rc, out = run("validate_run_config.py",
                  ["--config", str(config), "--out", str(work / "config-validation.json")])
    steps.append({"step": "config", "rc": rc, "tail": out[-500:]})
    if rc != 0:
        return 2

    spec = work / "decomposition.json"
    if not spec.is_file():
        print(f"FATAL: missing {spec}")
        return 2
    rc, out = run("validate_decomposition.py",
                  ["--spec", str(spec), "--root", str(task), "--out", str(work / "validation.json")])
    steps.append({"step": "decomposition", "rc": rc, "tail": out[-500:]})
    if rc != 0:
        return 2

    rc, out = run("run_decomposition_checks.py",
                  ["--spec", str(spec), "--root", str(task), "--out", str(work / "check-results.json")])
    steps.append({"step": "checks", "rc": rc, "tail": out[-500:]})
    # rc 1 = a mechanical check failed; rc 2 = manual items remain. Both go to verdict.

    results = work / "check-results.json"

    official = []
    if args.package_zip:
        package_zip = str(Path(args.package_zip).resolve())

        # Official 0.3.10 layer: run the auditor and the 21-item prefill.
        # The prefill is an advisory artifact; only the official auditor's
        # aggregate decision feeds the verdict.
        rc, out = run("qa_official.py",
                      ["run", "--workspace", str(work), "--zip", package_zip])
        steps.append({"step": "official-0.3.10-run", "rc": rc, "tail": out[-500:]})
        rc, out = run("qa_official.py",
                      ["review", "--workspace", str(work), "--task-dir", str(task)])
        steps.append({"step": "official-0.3.10-review", "rc": rc, "tail": out[-500:]})
        filled_standard = work / "official" / "review.json"
        if filled_standard.is_file():
            # The official auditor refuses internal worksheets inside the out-dir.
            external_review = work / "standard_review_input.json"
            external_review.write_bytes(filled_standard.read_bytes())
            rc, out = run("qa_official.py",
                          ["run", "--workspace", str(work), "--zip", package_zip,
                           "--standard-review", str(external_review)])
            steps.append({"step": "official-0.3.10-final", "rc": rc, "tail": out[-500:]})
        audit_report = work / "official" / "report.json"
        decision_03, code_03 = "UNKNOWN", ""
        if audit_report.is_file():
            audit = json.loads(audit_report.read_text(encoding="utf-8"))
            decision_03 = str(audit.get("decision") or "UNKNOWN")
            code_03 = str(audit.get("code") or "")
        if decision_03 == "PASS":
            category, verdict = "verified", "pass"
        elif decision_03 == "FAIL":
            category, verdict = "verified", "fail"
        else:
            category, verdict = "human_required", "unknown"
        official.append({
            "check_id": "official-0.3.10:auditor",
            "category": category,
            "verdict": verdict,
            "evidence": {"decision": decision_03, "code": code_03,
                         "prefill_review": str(work / "official" / "review.json")},
        })

        # Official unified-qa 0.5.0 layer: prepare the 90-item template; run the
        # final review only if official-0.5.0/review.json was filled.
        rc, out = run("qa_unified.py",
                      ["prepare", "--workspace", str(work), "--zip", package_zip])
        steps.append({"step": "official-0.5.0-prepare", "rc": rc, "tail": out[-500:]})
        rc, out = run("qa_unified.py", ["review", "--workspace", str(work)])
        steps.append({"step": "official-0.5.0-review", "rc": rc, "tail": out[-500:]})
        summary_path = work / "official-0.5.0" / "summary.json"
        decision_05, code_05 = "UNKNOWN", ""
        if summary_path.is_file():
            summary_0 = json.loads(summary_path.read_text(encoding="utf-8"))
            decision_05 = str(summary_0.get("decision") or "UNKNOWN")
            code_05 = str(summary_0.get("code") or "")
        if decision_05 == "PASS":
            category, verdict = "verified", "pass"
        elif decision_05 == "FAIL":
            category, verdict = "verified", "fail"
        else:
            category, verdict = "human_required", "unknown"
        official.append({
            "check_id": "official-0.5.0:auditor",
            "category": category,
            "verdict": verdict,
            "evidence": {"decision": decision_05, "code": code_05,
                         "review_template": str(work / "official-0.5.0" / "inspection" / "review_template.json")},
        })
    else:
        steps.append({"step": "official", "rc": 0, "tail": "no --package-zip; skipped"})

    panel_dir = work / "judgments"
    if panel_dir.is_dir() and any(p.is_dir() for p in panel_dir.iterdir()):
        rc, out = run("compare_judgments.py",
                      ["--root", str(task), "--dir", str(panel_dir), "--out", str(work / "panel.json")])
        steps.append({"step": "panel", "rc": rc, "tail": out[-500:]})
        if (work / "panel.json").is_file():
            rc, out = run("merge_check_results.py",
                          ["--checks", str(results), "--panel", str(work / "panel.json"),
                           "--out", str(work / "check-results-all.json")])
            steps.append({"step": "merge", "rc": rc, "tail": out[-500:]})
            if rc == 0:
                results = work / "check-results-all.json"
    else:
        steps.append({"step": "panel", "rc": 0, "tail": "no judgments/; skipped"})

    if official:
        data = json.loads(results.read_text(encoding="utf-8"))
        data.setdefault("items", []).extend(official)
        final_results = work / "check-results-final.json"
        final_results.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        results = final_results
        steps.append({"step": "official-merge", "rc": 0,
                      "tail": "%d official checks" % len(official)})

    rc, out = run("verdict.py", ["--results", str(results), "--out", str(work / "verdict.json")])
    steps.append({"step": "verdict", "rc": rc, "tail": out[-500:]})
    verdict = {}
    if (work / "verdict.json").is_file():
        verdict = json.loads((work / "verdict.json").read_text(encoding="utf-8"))

    summary = {
        "schema": "strict-verify/1",
        "task_root": str(task),
        "work_dir": str(work),
        "decision": verdict.get("decision"),
        "verdict": verdict,
        "steps": steps,
    }
    (work / "strict_verify.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": summary["decision"],
                      "counts": verdict.get("counts"),
                      "open_ids": verdict.get("open_ids"),
                      "fail_ids": verdict.get("fail_ids")}, ensure_ascii=False, indent=2))
    print("written:", work / "strict_verify.json", file=sys.stderr)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
