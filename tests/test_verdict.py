#!/usr/bin/env python3
"""Tests for the binary current-standard scripts/verdict.py."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verdict.py"


def run(items, legacy=False, non_strict=False):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)
        results_p = tmp_p / "results.json"
        out = tmp_p / "verdict.json"
        results_p.write_text(json.dumps({"schema": "check-results/1", "items": items}), encoding="utf-8")
        args = [sys.executable, str(SCRIPT), "--results", str(results_p), "--out", str(out)]
        if legacy:
            args.append("--legacy-incomplete")
        if non_strict:
            args.append("--non-strict")
        proc = subprocess.run(args, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        payload = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {}
        return proc.returncode, payload


def item(cid, category, verdict):
    return {"check_id": cid, "category": category, "verdict": verdict}


class CurrentStandardVerdictTests(unittest.TestCase):
    def test_all_verified_pass(self):
        rc, payload = run([item("C1", "verified", "pass")])
        self.assertEqual(rc, 0)
        self.assertEqual(payload["decision"], "PASS")
        self.assertTrue(payload["binary_external_decision"])

    def test_verified_fail(self):
        rc, payload = run([item("C1", "verified", "fail")])
        self.assertEqual(rc, 1)
        self.assertEqual(payload["decision"], "FAIL")

    def test_human_required_is_qa_not_finished_fail(self):
        rc, payload = run([item("C1", "verified", "pass"), item("C2", "human_required", "unknown")])
        self.assertEqual(rc, 1)
        self.assertEqual(payload["decision"], "FAIL")
        self.assertEqual(payload["completion_status"], "QA_NOT_FINISHED")
        self.assertIn("C2", payload["open_ids"])

    def test_legacy_compat_can_expose_incomplete(self):
        rc, payload = run([item("C1", "verified", "pass"), item("C2", "human_required", "unknown")], legacy=True)
        self.assertEqual(rc, 1)
        self.assertEqual(payload["decision"], "FAIL")
        self.assertEqual(payload["legacy_orchestration_decision"], "INCOMPLETE")

    def test_non_strict_compat_can_expose_pass_with_open(self):
        rc, payload = run([item("C1", "verified", "pass"), item("C2", "human_required", "unknown")], non_strict=True)
        self.assertEqual(rc, 1)
        self.assertEqual(payload["decision"], "FAIL")
        self.assertEqual(payload["legacy_orchestration_decision"], "PASS_WITH_OPEN")

    def test_empty_is_qa_not_finished(self):
        rc, payload = run([])
        self.assertEqual(rc, 1)
        self.assertEqual(payload["decision"], "FAIL")
        self.assertEqual(payload["completion_status"], "QA_NOT_FINISHED")

    def test_judged_agree_pass(self):
        rc, payload = run([item("C1", "judged_agree", "pass")])
        self.assertEqual(rc, 0)
        self.assertEqual(payload["decision"], "PASS")

    def test_judged_adjudicated_fail(self):
        rc, payload = run([item("C1", "judged_adjudicated", "fail")])
        self.assertEqual(rc, 1)
        self.assertEqual(payload["decision"], "FAIL")


if __name__ == "__main__":
    unittest.main()
