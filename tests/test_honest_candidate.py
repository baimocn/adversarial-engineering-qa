"""Gate C · 诚实候选冒烟的自测。

三种判定必须都能复现：
  · tensor_api_mismatch   → blocking（0340 QA06 形态）
  · fingerprint_false_positive → blocking（0340 QA05 形态）
  · 正常出分              → pass
加一条：崩溃文本未归类时不能静默放过（必须 blocking/unclassified_crash）。
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "check_honest_candidate.py"

ENTRY_BAD_API = '''\
import argparse, sys
p = argparse.ArgumentParser(); p.add_argument("--solution_dir"); p.add_argument("--out")
a = p.parse_args()
act = __import__("numpy").zeros(4)
act.numpy()          # tensor_api_mismatch
'''

ENTRY_TAMPERED = '''\
import argparse, sys
p = argparse.ArgumentParser(); p.add_argument("--solution_dir"); p.add_argument("--out")
a = p.parse_args()
sys.stdout.write("frozen_method_tampered: act\\n")
sys.exit(1)
'''

ENTRY_OK = '''\
import argparse, json
p = argparse.ArgumentParser(); p.add_argument("--solution_dir"); p.add_argument("--out")
a = p.parse_args()
json.dump({"episode_reward_mean": 412.5}, open(a.out, "w"))
'''

ENTRY_WEIRD = '''\
import argparse
p = argparse.ArgumentParser(); p.add_argument("--solution_dir"); p.add_argument("--out")
a = p.parse_args()
raise KeyError("something nobody classified")
'''


def build(task_src):
    tmp = Path(tempfile.mkdtemp(prefix="hc_"))
    task = tmp / "task"
    (task / "tests").mkdir(parents=True)
    (task / "tests" / "evaluate.py").write_text(task_src, encoding="utf-8")
    (task / "reference").mkdir()
    (task / "instruction.md").write_text("stub", encoding="utf-8")
    return tmp, task


class HonestCandidateTest(unittest.TestCase):
    def _run(self, src):
        tmp, task = build(src)
        out = tmp / "rep.json"
        r = subprocess.run([sys.executable, "-B", str(SCRIPT),
                            "--task-dir", str(task), "--out", str(out)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        return r.returncode, json.loads(out.read_text(encoding="utf-8"))

    def test_numpy_api_crash_is_blocking(self):
        rc, rep = self._run(ENTRY_BAD_API)
        self.assertEqual(rc, 1)
        self.assertEqual(rep["verdict"], "blocking")
        self.assertEqual(rep["crash"]["type"], "tensor_api_mismatch")

    def test_fingerprint_false_positive_is_blocking(self):
        rc, rep = self._run(ENTRY_TAMPERED)
        self.assertEqual(rc, 1)
        self.assertEqual(rep["crash"]["type"], "fingerprint_false_positive")

    def test_score_is_pass(self):
        rc, rep = self._run(ENTRY_OK)
        self.assertEqual(rc, 0)
        self.assertEqual(rep["verdict"], "pass")
        self.assertEqual(rep["score"]["value"], 412.5)

    def test_unclassified_crash_not_silently_passed(self):
        rc, rep = self._run(ENTRY_WEIRD)
        self.assertEqual(rc, 1)
        self.assertEqual(rep["crash"]["type"], "unclassified_crash")

    def test_missing_candidate_is_needs_manual(self):
        tmp, task = build(ENTRY_OK)
        for d in ("reference",):
            (task / d).rmdir()
        out = tmp / "rep.json"
        r = subprocess.run([sys.executable, "-B", str(SCRIPT),
                            "--task-dir", str(task), "--out", str(out)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        rep = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(r.returncode, 2)
        self.assertEqual(rep["verdict"], "needs_manual")


if __name__ == "__main__":
    unittest.main()
