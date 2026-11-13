#!/usr/bin/env python3
"""Tests for scripts/run_decomposition_checks.py and validate_run_config.py."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_decomposition_checks.py"
CONFIG = ROOT / "scripts" / "validate_run_config.py"


def run(script: Path, args: list[str]):
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out.json"
        proc = subprocess.run(
            [sys.executable, str(script), *args, "--out", str(out)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        payload = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {}
        return proc.returncode, payload


class DecompositionRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "a.txt").write_text("hello world\n", encoding="utf-8")
        (self.root / "data.json").write_text(json.dumps({"status": "ok", "n": 3}), encoding="utf-8")
        self.sha = hashlib.sha256((self.root / "a.txt").read_bytes()).hexdigest()

    def tearDown(self):
        self.tmp.cleanup()

    def spec(self, checks):
        p = self.root / "spec.json"
        p.write_text(json.dumps({"schema": "decomposition/1", "task_family": "test",
                                 "requirements": [], "checks": checks}), encoding="utf-8")
        return str(p)

    def test_file_and_json_and_hash_checks(self):
        spec = self.spec([
            {"id": "C1", "requirement_id": "R1", "answer_space": ["pass", "fail", "unknown"],
             "verifier": {"kind": "file_contains", "path": "a.txt", "needle": "hello"}},
            {"id": "C2", "requirement_id": "R1", "answer_space": ["pass", "fail", "unknown"],
             "verifier": {"kind": "json_value", "path": "data.json", "pointer": "/status", "equals": "ok"}},
            {"id": "C3", "requirement_id": "R1", "answer_space": ["pass", "fail", "unknown"],
             "verifier": {"kind": "hash_equal", "path": "a.txt", "sha256": self.sha}},
            {"id": "C4", "requirement_id": "R1", "answer_space": ["pass", "fail", "unknown"],
             "verifier": {"kind": "regex", "path": "a.txt", "pattern": "wor.d", "must_match": True}},
        ])
        rc, payload = run(RUNNER, ["--spec", spec, "--root", str(self.root)])
        self.assertEqual(rc, 0, payload)
        self.assertEqual([x["verdict"] for x in payload["items"]], ["pass", "pass", "pass", "pass"])

    def test_fail_is_reported(self):
        spec = self.spec([
            {"id": "C1", "requirement_id": "R1", "answer_space": ["pass", "fail", "unknown"],
             "verifier": {"kind": "file_contains", "path": "a.txt", "needle": "absent"}},
        ])
        rc, payload = run(RUNNER, ["--spec", spec, "--root", str(self.root)])
        self.assertEqual(rc, 1)
        self.assertEqual(payload["items"][0]["verdict"], "fail")

    def test_manual_is_human_required(self):
        spec = self.spec([
            {"id": "C1", "requirement_id": "R1", "answer_space": ["pass", "fail", "unknown"],
             "human_required": True, "verifier": {"kind": "manual"}},
        ])
        rc, payload = run(RUNNER, ["--spec", spec, "--root", str(self.root)])
        self.assertEqual(rc, 2)
        self.assertEqual(payload["items"][0]["category"], "human_required")

    def test_disallowed_command(self):
        spec = self.spec([
            {"id": "C1", "requirement_id": "R1", "answer_space": ["pass", "fail", "unknown"],
             "verifier": {"kind": "command", "command": "powershell", "args": [],
                          "assert": {"exit_code": 0}}},
        ])
        rc, payload = run(RUNNER, ["--spec", spec, "--root", str(self.root)])
        self.assertEqual(rc, 1)
        self.assertIn("not allowed", payload["items"][0]["evidence"]["error"])


class RunConfigTests(unittest.TestCase):
    def test_valid_roles(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            p.write_text(json.dumps({
                "decomposer": "p/deepseek-v4.1-flash$max",
                "judges": ["p/deepseek-v4.1-flash$max", "p/glm-5.3-flash$max"],
                "adjudicator": "p/mimo-v2.6-pro",
                "executor": "p/glm-5.3-flash$high",
            }), encoding="utf-8")
            rc, payload = run(CONFIG, ["--config", str(p)])
        self.assertEqual(rc, 0, payload)
        self.assertTrue(payload["valid"])

    def test_same_family_judges_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            p.write_text(json.dumps({
                "decomposer": "p/deepseek-v4.1-flash$max",
                "judges": ["p/deepseek-v4.1-flash$max", "q/deepseek-v4.1-flash$max"],
                "adjudicator": "p/mimo-v2.6-pro",
            }), encoding="utf-8")
            rc, payload = run(CONFIG, ["--config", str(p)])
        self.assertEqual(rc, 1)
        self.assertTrue(any("different families" in e for e in payload["errors"]))

    def test_adjudicator_must_be_third_family(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            p.write_text(json.dumps({
                "decomposer": "p/deepseek-v4.1-flash$max",
                "judges": ["p/deepseek-v4.1-flash$max", "p/glm-5.3-flash$max"],
                "adjudicator": "p/glm-5.3-flash$max",
            }), encoding="utf-8")
            rc, payload = run(CONFIG, ["--config", str(p)])
        self.assertEqual(rc, 1)
        self.assertTrue(any("third family" in e for e in payload["errors"]))


if __name__ == "__main__":
    unittest.main()
