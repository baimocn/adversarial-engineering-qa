#!/usr/bin/env python3
"""End-to-end test for scripts/strict_verify.py."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "strict_verify.py"

CONFIG = {
    "decomposer": "p/deepseek-v4.1-flash$max",
    "judges": ["p/deepseek-v4.1-flash$max", "p/glm-5.3-flash$max"],
    "adjudicator": "p/mimo-v2.6-pro",
}


def decomposition(manual: bool = False) -> dict:
    check = {
        "id": "C1",
        "requirement_id": "R1",
        "question": "does a.txt contain hello?",
        "answer_space": ["pass", "fail", "unknown"],
        "verifier": {"kind": "file_contains", "path": "a.txt", "needle": "hello"},
    }
    if manual:
        check["verifier"] = {"kind": "manual"}
        check["human_required"] = True
    return {
        "schema": "decomposition/1",
        "task_family": "test",
        "requirements": [{"id": "R1", "text": "a.txt contains hello", "source": "a.txt"}],
        "checks": [check],
    }


def judgment(verdict: str, model: str) -> dict:
    return {
        "schema": "judgment/1", "item_id": "C1", "model": model, "verdict": verdict,
        "confidence": 80,
        "evidence": [{"path": "a.txt", "line": 1, "quote": "hello"}],
        "rationale": "demo",
    }


def run(work: Path, task: Path):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(ROOT),
         "--task-root", str(task), "--work-dir", str(work)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


class StrictVerifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.task = self.base / "task"
        self.task.mkdir()
        (self.task / "a.txt").write_text("hello world\n", encoding="utf-8")
        self.work = self.base / "work"
        self.work.mkdir()
        (self.work / "run-config.json").write_text(json.dumps(CONFIG), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def write_spec(self, manual=False):
        (self.work / "decomposition.json").write_text(
            json.dumps(decomposition(manual)), encoding="utf-8")

    def test_mechanical_pass(self):
        self.write_spec()
        proc = run(self.work, self.task)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        verdict = json.loads((self.work / "verdict.json").read_text(encoding="utf-8"))
        self.assertEqual(verdict["decision"], "PASS")

    def test_manual_without_panel_is_incomplete(self):
        self.write_spec(manual=True)
        proc = run(self.work, self.task)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        verdict = json.loads((self.work / "verdict.json").read_text(encoding="utf-8"))
        self.assertEqual(verdict["decision"], "INCOMPLETE")
        self.assertIn("C1", verdict["open_ids"])

    def test_manual_with_agreeing_panel_passes(self):
        self.write_spec(manual=True)
        jdir = self.work / "judgments" / "C1"
        jdir.mkdir(parents=True)
        (jdir / "a.json").write_text(json.dumps(judgment("pass", "model-a")), encoding="utf-8")
        (jdir / "b.json").write_text(json.dumps(judgment("pass", "model-b")), encoding="utf-8")
        proc = run(self.work, self.task)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        verdict = json.loads((self.work / "verdict.json").read_text(encoding="utf-8"))
        self.assertEqual(verdict["decision"], "PASS")
        self.assertEqual(verdict["counts"].get("judged_agree"), 1)


if __name__ == "__main__":
    unittest.main()
