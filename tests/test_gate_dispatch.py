"""并行分派与合并的自测。

覆盖两个最容易出错的地方：
  · 分派计划漏了某个 gate（子代理根本不会被派到）
  · 合并时把「缺单元」当成「通过」（最危险的假绿）
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
PLAN = SKILL_ROOT / "scripts" / "plan_gate_dispatch.py"
MERGE = SKILL_ROOT / "scripts" / "merge_gate_results.py"

MANIFEST = {
    "schema_version": "1",
    "source_digest": "deadbeef",
    "files_total": 5,
    "python_files_indexed": 3,
    "shards": [
        {"id": "shard-0001", "group": "environment", "file_count": 3,
         "path": "shards/shard-0001.json"},
        {"id": "shard-0002", "group": "tests", "file_count": 2,
         "path": "shards/shard-0002.json"},
    ],
}


def mk_task():
    tmp = Path(tempfile.mkdtemp(prefix="disp_"))
    task = tmp / "task"
    (task / "tests").mkdir(parents=True)
    (task / "tests" / "x.py").write_text("x = 1\n", encoding="utf-8")
    ev = tmp / "ev"
    (ev / "shards").mkdir(parents=True)
    (ev / "manifest.json").write_text(json.dumps(MANIFEST), encoding="utf-8")
    return tmp, task, ev


def run(args):
    return subprocess.run([sys.executable, "-B"] + args, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


class DispatchPlanTest(unittest.TestCase):
    def test_plan_covers_all_gates(self):
        tmp, task, ev = mk_task()
        out = tmp / "plan.json"
        r = run([str(PLAN), "--task-dir", str(task), "--evidence-dir", str(ev),
                 "--out", str(out)])
        self.assertEqual(r.returncode, 0, r.stderr)
        plan = json.loads(out.read_text(encoding="utf-8"))
        ids = [u["id"] for u in plan["units"]]
        for need in ("A.regression", "B.shard-0001", "B.shard-0002",
                     "C1.static", "C2.honest", "MERGE"):
            self.assertIn(need, ids, "计划漏了 %s" % need)
        # MERGE 必须依赖所有其他单元
        merge = [u for u in plan["units"] if u["id"] == "MERGE"][0]
        self.assertEqual(set(merge["depends_on"]), set(ids) - {"MERGE"})

    def test_no_baseline_marks_not_applicable(self):
        tmp, task, ev = mk_task()
        out = tmp / "plan.json"
        run([str(PLAN), "--task-dir", str(task), "--evidence-dir", str(ev),
             "--out", str(out)])
        plan = json.loads(out.read_text(encoding="utf-8"))
        a = [u for u in plan["units"] if u["id"] == "A.regression"][0]
        self.assertEqual(a["status_if_no_baseline"], "not_applicable")


class MergeTest(unittest.TestCase):
    def _setup(self):
        tmp, task, ev = mk_task()
        plan_p = tmp / "plan.json"
        run([str(PLAN), "--task-dir", str(task), "--evidence-dir", str(ev),
             "--out", str(plan_p)])
        plan = json.loads(plan_p.read_text(encoding="utf-8"))
        res = tmp
        return tmp, plan, res

    def _write(self, res, plan, uid, status, findings=None, reason=""):
        u = [x for x in plan["units"] if x["id"] == uid][0]
        p = res / u["output"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"unit_id": uid, "gate": u["gate"], "status": status,
                                 "findings": findings or [], "reason": reason},
                                ensure_ascii=False), encoding="utf-8")

    def _merge(self, res, plan):
        out = res / "gates" / "merged.json"
        r = run([str(MERGE), "--plan", str(res / "plan.json"),
                 "--results-dir", str(res), "--out", str(out)])
        return r.returncode, json.loads(out.read_text(encoding="utf-8"))

    def _fill_all_pass(self, res, plan):
        for u in plan["units"]:
            if u["id"] == "MERGE":
                continue
            st = "not_applicable" if u["id"] == "A.regression" else "PASS"
            self._write(res, plan, u["id"], st,
                        reason="无基线" if st == "not_applicable" else "")

    def test_all_pass(self):
        tmp, plan, res = self._setup()
        for u in plan["units"]:
            if u["id"] == "MERGE" or u["id"] == "A.regression":
                continue
            self._write(res, plan, u["id"], "PASS")
        self._write(res, plan, "A.regression", "PASS", reason="有基线")
        rc, m = self._merge(res, plan)
        self.assertEqual(rc, 0)
        self.assertEqual(m["decision"], "PASS")

    def test_missing_unit_is_incomplete_not_pass(self):
        tmp, plan, res = self._setup()
        self._fill_all_pass(res, plan)
        # 故意不写 B.shard-0002
        (res / "gates" / "B.shard-0002.json").unlink()
        rc, m = self._merge(res, plan)
        self.assertEqual(rc, 2, "缺单元必须 INCOMPLETE")
        self.assertEqual(m["decision"], "INCOMPLETE")
        self.assertIn("B.shard-0002", m["missing"])

    def test_one_fail_makes_fail(self):
        tmp, plan, res = self._setup()
        self._fill_all_pass(res, plan)
        self._write(res, plan, "B.shard-0001", "FAIL",
                    findings=[{"severity": "major", "summary": "x"}])
        rc, m = self._merge(res, plan)
        self.assertEqual(rc, 1)
        self.assertEqual(m["decision"], "FAIL")

    def test_blocking_with_pass_is_contradiction(self):
        tmp, plan, res = self._setup()
        self._fill_all_pass(res, plan)
        self._write(res, plan, "C1.static", "PASS",
                    findings=[{"severity": "blocking", "summary": "numpy 喂给 tensor"}])
        rc, m = self._merge(res, plan)
        self.assertEqual(rc, 1)
        self.assertTrue(any("自相矛盾" in e for e in m["errors"]))

    def test_not_applicable_without_reason_downgraded(self):
        tmp, plan, res = self._setup()
        self._fill_all_pass(res, plan)
        self._write(res, plan, "B.shard-0001", "not_applicable", reason="")
        rc, m = self._merge(res, plan)
        self.assertEqual(rc, 2)
        self.assertTrue(any("not_applicable" in e for e in m["errors"]))


if __name__ == "__main__":
    unittest.main()
