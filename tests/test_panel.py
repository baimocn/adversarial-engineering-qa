#!/usr/bin/env python3
"""Tests for the 2+1 subjective judgment panel (scripts/judge_panel.py)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "judge_panel.py"


def run_panel(root: Path, a: dict, b: dict, adj: dict | None = None):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)
        a_p = tmp_p / "a.json"
        b_p = tmp_p / "b.json"
        out = tmp_p / "panel.json"
        a_p.write_text(json.dumps(a), encoding="utf-8")
        b_p.write_text(json.dumps(b), encoding="utf-8")
        args = [sys.executable, str(SCRIPT), "compare", "--root", str(root),
                "--judgment-a", str(a_p), "--judgment-b", str(b_p), "--out", str(out)]
        if adj is not None:
            adj_p = tmp_p / "adj.json"
            adj_p.write_text(json.dumps(adj), encoding="utf-8")
            args += ["--adjudication", str(adj_p)]
        proc = subprocess.run(args, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        payload = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {}
        return proc.returncode, payload


def judgment(verdict: str, model: str = "model-a", line: int = 3,
             quote: str = "metric is accuracy") -> dict:
    return {
        "schema": "judgment/1",
        "item_id": "clarity",
        "model": model,
        "verdict": verdict,
        "confidence": 80,
        "evidence": [{"path": "instruction.md", "line": line, "quote": quote}],
        "rationale": "evidence-backed",
    }


class PanelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "instruction.md").write_text(
            "# Task\n\nThe metric is accuracy.\nThe reward is (x-B)/(U-B).\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_agreement_is_judged_agree(self):
        rc, payload = run_panel(self.root, judgment("pass"), judgment("pass", "model-b"))
        self.assertEqual(rc, 0)
        self.assertEqual(payload["category"], "judged_agree")
        self.assertEqual(payload["verdict"], "pass")

    def test_disagreement_without_adjudication_is_human_required(self):
        rc, payload = run_panel(self.root, judgment("pass"), judgment("fail", "model-b"))
        self.assertEqual(rc, 2)
        self.assertEqual(payload["category"], "human_required")

    def test_adjudication_resolves_disagreement(self):
        adj = {
            "schema": "adjudication/1",
            "item_id": "clarity",
            "model": "model-c",
            "winner": "A",
            "verdict": "pass",
            "evidence": [{"path": "instruction.md", "line": 4, "quote": "(x-B)/(U-B)"}],
            "reason": "A's citation matches the reward line.",
        }
        rc, payload = run_panel(self.root, judgment("pass"), judgment("fail", "model-b"), adj)
        self.assertEqual(rc, 0)
        self.assertEqual(payload["category"], "judged_adjudicated")
        self.assertEqual(payload["verdict"], "pass")

    def test_invalid_quote_blocks_agreement(self):
        bad = judgment("pass", "model-b", line=3, quote="not on this line")
        rc, payload = run_panel(self.root, judgment("pass"), bad)
        self.assertEqual(rc, 2)
        self.assertEqual(payload["category"], "human_required")

    def test_adjudicator_verdict_must_match_winner(self):
        adj = {
            "schema": "adjudication/1",
            "item_id": "clarity",
            "model": "model-c",
            "winner": "A",
            "verdict": "fail",
            "evidence": [{"path": "instruction.md", "line": 4, "quote": "(x-B)/(U-B)"}],
            "reason": "mismatch should be rejected",
        }
        rc, payload = run_panel(self.root, judgment("pass"), judgment("fail", "model-b"), adj)
        self.assertEqual(rc, 2)
        self.assertEqual(payload["category"], "human_required")


if __name__ == "__main__":
    unittest.main()
