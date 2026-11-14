#!/usr/bin/env python3
"""Tests for the versioned current-standard catalog and ablation tooling."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATE = ROOT / "scripts" / "validate_rule_catalog.py"
ABLATION = ROOT / "scripts" / "run_ablation_suite.py"


class RuleCatalogTests(unittest.TestCase):
    def test_catalog_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "catalog.json"
            proc = subprocess.run(
                [sys.executable, "-I", str(VALIDATE), "--out", str(out)],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(payload["ok"])
            self.assertGreaterEqual(payload["current_rules"], 10)
            self.assertGreaterEqual(payload["ablation_cases"], 10)

    def test_ablation_suite_with_missing_good_root_is_explicitly_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            catalog = root / "ablation.json"
            catalog.write_text(json.dumps({
                "schema": "ablation-case-catalog/1",
                "good_root": str(root / "missing_tree"),
                "good_profile": "auto2768-v30",
                "cases": [],
            }), encoding="utf-8")
            out = root / "suite.json"
            proc = subprocess.run(
                [sys.executable, "-I", str(ABLATION), "--catalog", str(catalog), "--out", str(out)],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(payload["ok"])
            self.assertTrue(payload["skipped"])
            self.assertIn("good_root missing", payload["reason"])


if __name__ == "__main__":
    unittest.main()
