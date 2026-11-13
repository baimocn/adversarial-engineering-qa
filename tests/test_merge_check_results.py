#!/usr/bin/env python3
"""Tests for scripts/merge_check_results.py."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "merge_check_results.py"


def run(checks, panel):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)
        checks_p = tmp_p / "checks.json"
        panel_p = tmp_p / "panel.json"
        out = tmp_p / "merged.json"
        checks_p.write_text(json.dumps({"schema": "check-results/1", "items": checks}), encoding="utf-8")
        panel_p.write_text(json.dumps({"schema": "panel/1", "items": panel}), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--checks", str(checks_p),
             "--panel", str(panel_p), "--out", str(out)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        payload = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {}
        return proc.returncode, payload


class MergeTests(unittest.TestCase):
    def test_panel_replaces_manual_placeholder(self):
        checks = [
            {"check_id": "C1", "category": "verified", "verdict": "pass"},
            {"check_id": "C2", "category": "human_required", "verdict": "unknown"},
        ]
        panel = [{"item_id": "C2", "category": "judged_agree", "verdict": "pass"}]
        rc, payload = run(checks, panel)
        self.assertEqual(rc, 0)
        by_id = {x["check_id"]: x for x in payload["items"]}
        self.assertEqual(by_id["C1"]["category"], "verified")
        self.assertEqual(by_id["C2"]["category"], "judged_agree")
        self.assertEqual(by_id["C2"]["verdict"], "pass")

    def test_panel_without_check_is_added(self):
        checks = [{"check_id": "C1", "category": "verified", "verdict": "pass"}]
        panel = [{"item_id": "S1", "category": "judged_adjudicated", "verdict": "fail"}]
        rc, payload = run(checks, panel)
        self.assertEqual(rc, 0)
        by_id = {x["check_id"]: x for x in payload["items"]}
        self.assertEqual(by_id["S1"]["category"], "judged_adjudicated")
        self.assertEqual(by_id["S1"]["verdict"], "fail")

    def test_manual_without_panel_stays_open(self):
        checks = [{"check_id": "C1", "category": "human_required", "verdict": "unknown"}]
        rc, payload = run(checks, [])
        self.assertEqual(rc, 0)
        self.assertEqual(payload["items"][0]["category"], "human_required")


if __name__ == "__main__":
    unittest.main()
