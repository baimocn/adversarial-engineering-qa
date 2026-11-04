"""核对清单与覆盖率闸门的自测。

要防的两类假绿：
  · 清单生成了但没人填，仍被当成「读过」
  · 单元自报 PASS，但覆盖率只有 60%
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
BUILD = SKILL_ROOT / "scripts" / "build_review_worklist.py"
VALIDATE = SKILL_ROOT / "scripts" / "validate_coverage.py"
PLAN = SKILL_ROOT / "scripts" / "plan_gate_dispatch.py"
MERGE = SKILL_ROOT / "scripts" / "merge_gate_results.py"

DECLS = [
    {"path": "tests/evaluate.py", "line": 10,
     "text": "# 超时一律不计候选，必须单独报告"},
    {"path": "tests/evaluate.py", "line": 20,
     "text": "# 这里是普通说明，没有约束力"},
]

MANIFEST = {
    "source_digest": "x", "files_total": 3, "python_files_indexed": 2,
    "shards": [{"id": "shard-0001", "group": "tests", "file_count": 3,
                "path": "shards/shard-0001.json"}],
}

SHARD = {
    "id": "shard-0001", "group": "tests",
    "files": [
        {"path": "tests/evaluate.py", "size_bytes": 100, "declarations": DECLS},
        {"path": "tests/config.yaml", "size_bytes": 50},
        {"path": "tests/Dockerfile", "size_bytes": 30},
    ],
}

SYMBOLS = [
    {"kind": "function", "line": 5, "path": "tests/evaluate.py", "qualname": "evaluate"},
    {"kind": "function", "line": 15, "path": "tests/evaluate.py", "qualname": "helper"},
    {"kind": "class", "line": 30, "path": "tests/evaluate.py", "qualname": "TensorWrapper"},
]


def run(args):
    return subprocess.run([sys.executable, "-B"] + [str(a) for a in args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")


def setup():
    tmp = Path(tempfile.mkdtemp(prefix="cov_"))
    ev = tmp / "ev"
    (ev / "shards").mkdir(parents=True)
    (ev / "manifest.json").write_text(json.dumps(MANIFEST), encoding="utf-8")
    (ev / "shards" / "shard-0001.json").write_text(json.dumps(SHARD), encoding="utf-8")
    (ev / "symbols.json").write_text(json.dumps(SYMBOLS), encoding="utf-8")
    return tmp, ev


def build(tmp, ev):
    out = tmp / "wl.json"
    r = run([BUILD, "--evidence-dir", ev, "--shard", "shard-0001", "--out", out])
    return r, out, json.loads(out.read_text(encoding="utf-8"))


class WorklistBuildTest(unittest.TestCase):
    def test_slots_created(self):
        tmp, ev = setup()
        r, out, w = build(tmp, ev)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(w["files"]), 3)
        self.assertTrue(all(f["disposition"] is None for f in w["files"]))
        # 高风险声明必须被标 must_bind，普通说明不必须
        by_line = {d["line"]: d for d in w["declarations"]}
        self.assertTrue(by_line[10]["must_bind"], "绝对声明应强制绑定")
        self.assertFalse(by_line[20]["must_bind"], "无约束力的说明不该强制")
        # 热点：evaluate / TensorWrapper 命中，helper 不命中
        names = [h["qualname"] for h in w["hotspots"]]
        self.assertIn("evaluate", names)
        self.assertIn("TensorWrapper", names)
        self.assertNotIn("helper", names)
        self.assertTrue(w["blindspot_checklist"], "必须有盲区清单")


class CoverageValidateTest(unittest.TestCase):
    def _fill(self, w, disp="read", bind=True, answers=True):
        for f in w["files"]:
            f["disposition"] = disp
            if disp in ("skim", "skip"):
                f["reason"] = "测试用"
        for d in w["declarations"]:
            if d["must_bind"]:
                d["bound_to"] = "tests/evaluate.py:99" if bind else None
                d["verdict"] = "holds" if bind else None
        for h in w["hotspots"]:
            h["answers"] = (["答" for _ in h["questions"]]
                            if answers else [])
        return w

    def _validate(self, tmp, w, result=None):
        wl = tmp / "filled.json"
        wl.write_text(json.dumps(w, ensure_ascii=False), encoding="utf-8")
        args = [VALIDATE, "--worklist", wl, "--out", tmp / "cov.json"]
        if result is not None:
            rp = tmp / "res.json"
            rp.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
            args += ["--result", rp]
        r = run(args)
        return r.returncode, json.loads((tmp / "cov.json").read_text(encoding="utf-8"))

    def test_complete_passes(self):
        tmp, ev = setup()
        _, _, w = build(tmp, ev)
        rc, rep = self._validate(tmp, self._fill(w))
        self.assertEqual(rc, 0, rep["errors"])
        self.assertEqual(rep["coverage_pct"], 100.0)

    def test_empty_disposition_fails(self):
        tmp, ev = setup()
        _, _, w = build(tmp, ev)
        w = self._fill(w)
        w["files"][0]["disposition"] = None
        rc, rep = self._validate(tmp, w)
        self.assertEqual(rc, 1)
        self.assertTrue(any("未处置" in e for e in rep["errors"]))

    def test_must_bind_unfilled_fails(self):
        tmp, ev = setup()
        _, _, w = build(tmp, ev)
        rc, rep = self._validate(tmp, self._fill(w, bind=False))
        self.assertEqual(rc, 1)
        self.assertTrue(any("bound_to 为空" in e for e in rep["errors"]))

    def test_hotspot_answers_wrong_length_fails(self):
        tmp, ev = setup()
        _, _, w = build(tmp, ev)
        rc, rep = self._validate(tmp, self._fill(w, answers=False))
        self.assertEqual(rc, 1)
        self.assertTrue(any("answers 条数" in e for e in rep["errors"]))

    def test_finding_without_snippet_fails(self):
        tmp, ev = setup()
        _, _, w = build(tmp, ev)
        res = {"findings": [{"severity": "blocking", "summary": "x",
                             "evidence": "tests/evaluate.py:12"}]}
        rc, rep = self._validate(tmp, self._fill(w), result=res)
        self.assertEqual(rc, 1)
        self.assertTrue(any("snippet" in e for e in rep["errors"]))


class MergeCoverageTest(unittest.TestCase):
    def test_pass_with_low_coverage_becomes_incomplete(self):
        tmp, ev = setup()
        plan_p = tmp / "plan.json"
        run([PLAN, "--task-dir", tmp, "--evidence-dir", ev, "--out", plan_p])
        plan = json.loads(plan_p.read_text(encoding="utf-8"))
        for u in plan["units"]:
            if u["id"] == "MERGE":
                continue
            p = tmp / u["output"]
            p.parent.mkdir(parents=True, exist_ok=True)
            rec = {"unit_id": u["id"], "gate": u["gate"], "status": "PASS",
                   "findings": [], "reason": "ok"}
            if u["kind"] == "code_review":
                rec["coverage"] = {"coverage_pct": 60.0, "complete": False}
            p.write_text(json.dumps(rec), encoding="utf-8")
        r = run([MERGE, "--plan", plan_p, "--results-dir", tmp,
                 "--out", tmp / "gates" / "merged.json"])
        m = json.loads((tmp / "gates" / "merged.json").read_text(encoding="utf-8"))
        self.assertEqual(r.returncode, 2, "覆盖率不足不得判 PASS")
        self.assertEqual(m["decision"], "INCOMPLETE")
        self.assertTrue(any("覆盖率不足" in e for e in m["errors"]))


class MirrorAndIntensityTest(unittest.TestCase):
    """同源副本差异必须被强制说明——0340 QA05 的唯一发现路径。"""

    def _two_shard_ev(self, same=False):
        tmp = Path(tempfile.mkdtemp(prefix="mir_"))
        ev = tmp / "ev"
        (ev / "shards").mkdir(parents=True)
        man = {
            "source_digest": "x", "files_total": 2, "python_files_indexed": 0,
            "shards": [
                {"id": "shard-0001", "group": "environment", "file_count": 1,
                 "path": "shards/shard-0001.json"},
                {"id": "shard-0002", "group": "solution", "file_count": 1,
                 "path": "shards/shard-0002.json"},
            ],
            "files": [
                {"path": "environment/starter/tdmpc2/tdmpc2.py",
                 "sha256": "aaa", "size_bytes": 10},
                {"path": "solution/tdmpc2/tdmpc2.py",
                 "sha256": "aaa" if same else "bbb", "size_bytes": 10},
            ],
        }
        (ev / "manifest.json").write_text(json.dumps(man), encoding="utf-8")
        (ev / "shards" / "shard-0001.json").write_text(json.dumps({
            "id": "shard-0001", "group": "environment",
            "files": [{"path": "environment/starter/tdmpc2/tdmpc2.py",
                       "size_bytes": 10}]}), encoding="utf-8")
        (ev / "shards" / "shard-0002.json").write_text(json.dumps({
            "id": "shard-0002", "group": "solution",
            "files": [{"path": "solution/tdmpc2/tdmpc2.py",
                       "size_bytes": 10}]}), encoding="utf-8")
        return tmp, ev

    def test_diff_creates_must_explain(self):
        tmp, ev = self._two_shard_ev(same=False)
        out = tmp / "wl"
        run([BUILD, "--evidence-dir", ev, "--all", "--outdir", out])
        w = json.loads((out / "shard-0001.json").read_text(encoding="utf-8"))
        self.assertEqual(len(w["mirror_sets"]), 1)
        self.assertTrue(w["mirror_sets"][0]["must_explain"])
        self.assertIn("tdmpc2/tdmpc2.py", w["mirror_notes"])
        self.assertIsNone(w["mirror_notes"]["tdmpc2/tdmpc2.py"])

    def test_identical_needs_no_note(self):
        tmp, ev = self._two_shard_ev(same=True)
        out = tmp / "wl"
        run([BUILD, "--evidence-dir", ev, "--all", "--outdir", out])
        w = json.loads((out / "shard-0001.json").read_text(encoding="utf-8"))
        self.assertEqual(len(w["mirror_sets"]), 1)
        self.assertFalse(w["mirror_sets"][0]["must_explain"])
        self.assertEqual(w["mirror_notes"], {})

    def test_unfilled_mirror_note_fails_validation(self):
        tmp, ev = self._two_shard_ev(same=False)
        out = tmp / "wl"
        run([BUILD, "--evidence-dir", ev, "--all", "--outdir", out])
        w = json.loads((out / "shard-0001.json").read_text(encoding="utf-8"))
        for f in w["files"]:
            f["disposition"] = "read"
            f["reason"] = ""
        wl = tmp / "filled.json"
        wl.write_text(json.dumps(w, ensure_ascii=False), encoding="utf-8")
        r = run([VALIDATE, "--worklist", wl, "--out", tmp / "cov.json"])
        self.assertEqual(r.returncode, 1)
        rep = json.loads((tmp / "cov.json").read_text(encoding="utf-8"))
        self.assertTrue(any("mirror_notes" in e for e in rep["errors"]))

    def test_intensity_reduces_hotspots(self):
        tmp, ev = setup()
        n = {}
        for mode in ("light", "strict"):
            o = tmp / ("wl_" + mode)
            run([BUILD, "--evidence-dir", ev, "--shard", "shard-0001",
                 "--out", o / "w.json", "--intensity", mode])
            w = json.loads((o / "w.json").read_text(encoding="utf-8"))
            n[mode] = sum(len(h["questions"]) for h in w["hotspots"])
        self.assertLess(n["light"], n["strict"], "light 档问题数应少于 strict")


if __name__ == "__main__":
    unittest.main()
