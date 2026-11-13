#!/usr/bin/env python3
"""Tests for scripts/validate_decomposition.py."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_decomposition.py"


def base_spec() -> dict:
    return {
        "schema": "decomposition/1",
        "task_family": "harbor",
        "requirements": [
            {"id": "R1", "text": "reject NPZ predictions", "source": "instruction.md:42"},
        ],
        "checks": [
            {
                "id": "C1",
                "requirement_id": "R1",
                "question": "Does the grader reject an NPZ container?",
                "answer_space": ["pass", "fail", "unknown"],
                "verifier": {
                    "kind": "command",
                    "command": "python",
                    "args": ["-I", "probes/npz_candidate/probe.py"],
                    "assert": {"exit_code": 0},
                },
            }
        ],
    }


def run(spec: dict):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)
        spec_p = tmp_p / "spec.json"
        out = tmp_p / "validation.json"
        spec_p.write_text(json.dumps(spec), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--spec", str(spec_p), "--root", str(ROOT), "--out", str(out)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        payload = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {}
        return proc.returncode, payload


class DecompositionTests(unittest.TestCase):
    def test_valid_spec(self):
        rc, payload = run(base_spec())
        self.assertEqual(rc, 0, payload)
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["coverage"]["uncovered"], [])

    def test_uncovered_requirement_is_invalid(self):
        spec = base_spec()
        spec["requirements"].append({"id": "R2", "text": "disclose limits", "source": "protocol.json"})
        rc, payload = run(spec)
        self.assertEqual(rc, 1)
        self.assertEqual(payload["coverage"]["uncovered"], ["R2"])

    def test_manual_requires_human_required(self):
        spec = base_spec()
        spec["checks"][0]["verifier"] = {"kind": "manual"}
        rc, payload = run(spec)
        self.assertEqual(rc, 1)
        self.assertTrue(any("human_required" in e for e in payload["errors"]))

    def test_unsupported_verifier_is_invalid(self):
        spec = base_spec()
        spec["checks"][0]["verifier"] = {"kind": "vibes"}
        rc, payload = run(spec)
        self.assertEqual(rc, 1)
        self.assertTrue(any("unsupported verifier" in e for e in payload["errors"]))

    def test_answer_space_needs_unknown(self):
        spec = base_spec()
        spec["checks"][0]["answer_space"] = ["pass", "fail"]
        rc, payload = run(spec)
        self.assertEqual(rc, 1)
        self.assertTrue(any("unknown" in e for e in payload["errors"]))


if __name__ == "__main__":
    unittest.main()
