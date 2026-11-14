#!/usr/bin/env python3
"""Bad/good ablation tests for scripts/current_standard_gate.py."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "current_standard_gate.py"
ACCEPTED = Path("D:/Desktop/论文最新包/2768/qa_compare/v30_tree")


def gate(root: Path, out: Path):
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), "--root", str(root), "--out", str(out)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


class CurrentStandardGateTests(unittest.TestCase):
    def setUp(self):
        if not ACCEPTED.is_dir():
            self.skipTest(f"accepted v30 tree not available: {ACCEPTED}")
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.root = self.base / "pkg"
        shutil.copytree(ACCEPTED, self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, mutate=None):
        out = self.base / "gate.json"
        if mutate:
            mutate(self.root)
        proc = gate(self.root, out)
        payload = json.loads(out.read_text(encoding="utf-8"))
        return proc.returncode, payload

    def replace(self, rel: str, old: str, new: str):
        def mutate(root: Path):
            p = root / rel
            t = p.read_text(encoding="utf-8")
            self.assertIn(old, t)
            p.write_text(t.replace(old, new, 1), encoding="utf-8")
        return mutate

    def write(self, rel: str, content: str):
        def mutate(root: Path):
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        return mutate

    def assert_rule(self, payload, rule, status="fail"):
        hits = [f for f in payload["findings"] if f["rule"] == rule]
        self.assertTrue(hits, rule)
        self.assertEqual(hits[0]["status"], status, (rule, hits[0]))

    def test_good_v30_tree_passes(self):
        rc, payload = self.check()
        self.assertEqual(rc, 0)
        self.assertEqual(payload["decision"], "PASS")
        self.assertTrue(payload["final_decision_is_binary"])

    def test_bad_hard_gate_minus_one_fails(self):
        rc, payload = self.check(self.replace(
            "workspace/harbor_task/tests/grader.py", "HARD_GATE = -10.0", "HARD_GATE = -1.0"))
        self.assertEqual(payload["decision"], "FAIL")
        self.assert_rule(payload, "hard_gate_minus_10")

    def test_bad_reward_txt_publish_fails(self):
        def mutate(root):
            p = root / "workspace/harbor_task/tests/grader.py"
            t = p.read_text(encoding="utf-8")
            t += "\n\ndef publish_old_reward():\n    _atomic_write(os.path.join(REWARD_DIR, 'reward.txt'), '0')\n"
            p.write_text(t, encoding="utf-8")
        rc, payload = self.check(mutate)
        self.assertEqual(payload["decision"], "FAIL")
        self.assert_rule(payload, "no_reward_txt_publish")

    def test_bad_docker_image_fails(self):
        rc, payload = self.check(self.replace(
            "workspace/harbor_task/task.toml", "schema_version = \"1.4\"",
            "schema_version = \"1.4\"\ndocker_image = \"hub.byted.org/legacy/task:tag\""))
        self.assertEqual(payload["decision"], "FAIL")
        self.assert_rule(payload, "no_expert_docker_image")

    def test_bad_nonlocal_disclosure_removed_fails(self):
        def mutate(root):
            p = root / "workspace/harbor_task/instruction.md"
            t = p.read_text(encoding="utf-8")
            p.write_text(t.replace("nonlocal", "local-nested-scope") +
                         "\n\n<!-- disclosure removed by ablation -->\n", encoding="utf-8")
        rc, payload = self.check(mutate)
        self.assertEqual(payload["decision"], "FAIL")
        self.assert_rule(payload, "public_contract_nonlocal")

    def test_bad_staged_whitelist_widened_fails(self):
        def mutate(root):
            p = root / "workspace/harbor_task/environment/public_eval/protocol.json"
            d = json.loads(p.read_text(encoding="utf-8"))
            d["implementation_boundary"]["staged_import_whitelist"]["allowed_import_modules"] = ["torch", "numpy", "math"]
            p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        rc, payload = self.check(mutate)
        self.assertEqual(payload["decision"], "FAIL")
        self.assert_rule(payload, "public_contract_staged_import")

    def test_bad_oracle_source_handoff_removed_fails(self):
        rc, payload = self.check(self.replace(
            "workspace/harbor_task/solution/solve.sh", "assemble_dream_solution.sh", "missing_assembler.sh"))
        self.assertEqual(payload["decision"], "FAIL")
        self.assert_rule(payload, "oracle_handoff_source_before_training")

    def test_bad_best_method_adapter_fails(self):
        def mutate(root):
            bad = Path("D:/Desktop/论文最新包/2768/qa_compare/v29_tree/expert_evidence/best_method/data.py")
            p = root / "expert_evidence/best_method/data.py"
            p.write_bytes(bad.read_bytes())
        rc, payload = self.check(mutate)
        self.assertEqual(payload["decision"], "FAIL")
        self.assert_rule(payload, "best_method_restored_starter_adapter")
        self.assert_rule(payload, "best_method_allowed_frozen_ast")

    def test_bad_source_binding_hash_fails(self):
        def mutate(root):
            p = root / "expert_evidence/best_method_selection.json"
            d = json.loads(p.read_text(encoding="utf-8"))
            d["method_sha256"]["data.py"] = "0" * 64
            p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        rc, payload = self.check(mutate)
        self.assertEqual(payload["decision"], "FAIL")
        self.assert_rule(payload, "best_method_source_binding_synced")

    def test_bad_provenance_blanket_claim_fails(self):
        def mutate(root):
            p = root / "optimization_evidence/EVIDENCE_PROVENANCE.md"
            t = p.read_text(encoding="utf-8")
            t += "\n- 旧声明：同一 train.py 与 starter/solution 逐字节一致；`data.py` 差异不影响。\n"
            p.write_text(t, encoding="utf-8")
        rc, payload = self.check(mutate)
        self.assertEqual(payload["decision"], "FAIL")
        self.assert_rule(payload, "g03_role_source_binding")


if __name__ == "__main__":
    unittest.main()
