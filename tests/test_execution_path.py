"""Gate C（执行层门禁）自测：真阳性命中 + 修后不误报。

用例形态直接取自 0340 的真实故障：
  · 未修版：act = np.asarray(...) → env.step(act)，而包装器内 action.numpy()
  · 修后版：act = torch.from_numpy(...) → env.step(act)
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "check_execution_path.py"

WRAPPER = '''\
class TensorWrapper:
    def __init__(self, env):
        self.env = env

    def step(self, action):
        obs, reward, done, info = self.env.step(action.numpy())
        return obs, reward, done, info
'''

EVAL_BAD = '''\
import numpy as np


def run(env, resp):
    act = np.asarray(resp["action"], dtype=np.float64)
    obs, r, done, info = env.step(act)
    return r
'''

EVAL_GOOD = '''\
import numpy as np
import torch


def run(env, resp):
    act = np.asarray(resp["action"], dtype=np.float64)
    obs, r, done, info = env.step(torch.from_numpy(act))
    return r
'''


ARITY_BAD = '''\
def run_episode(env):
    if env.dead:
        return 0.0, 0
    return 1.0, 1


def main(env):
    total, steps = run_episode(env)
    return total
'''

ARITY_BAD_TRIPLE = '''\
def run_episode(env):
    if env.dead:
        return 3, 0.0, "timeout"
    return 1, 1.0, "ok"


def main(env):
    total, score = run_episode(env)
    return total
'''


class ExecutionPathTest(unittest.TestCase):
    def _run(self, eval_src):
        tmp = tempfile.mkdtemp(prefix="exq_")
        root = Path(tmp) / "task"
        (root / "envs" / "wrappers").mkdir(parents=True)
        (root / "envs" / "wrappers" / "tensor.py").write_text(WRAPPER, encoding="utf-8")
        (root / "evaluate.py").write_text(eval_src, encoding="utf-8")
        out = Path(tmp) / "out.json"
        r = subprocess.run([sys.executable, "-B", str(SCRIPT), "--root", str(root),
                            "--out", str(out)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        return r.returncode, json.loads(out.read_text(encoding="utf-8"))

    def test_detects_numpy_into_tensor_wrapper(self):
        rc, rep = self._run(EVAL_BAD)
        self.assertEqual(rc, 1, "未修版应报 blocking 并返回 1")
        self.assertGreaterEqual(rep["summary"]["blocking"], 1)
        rules = [f["rule"] for f in rep["findings"] if f["severity"] == "blocking"]
        self.assertIn("tensor_api_mismatch", rules)

    def test_clean_after_fix(self):
        rc, rep = self._run(EVAL_GOOD)
        self.assertEqual(rc, 0, "改用 torch.from_numpy 后不应报 blocking")
        self.assertEqual(rep["summary"]["blocking"], 0)

    def test_return_arity_mismatch(self):
        rc, rep = self._run(ARITY_BAD_TRIPLE)
        self.assertEqual(rc, 1, "3 返 2 收应报 blocking")
        rules = [f["rule"] for f in rep["findings"] if f["severity"] == "blocking"]
        self.assertIn("return_arity_mismatch", rules)

    def test_return_arity_ok_no_false_positive(self):
        rc, rep = self._run(ARITY_BAD)
        self.assertEqual(rep["summary"]["blocking"], 0, "2 返 2 收不应误报")


if __name__ == "__main__":
    unittest.main()
