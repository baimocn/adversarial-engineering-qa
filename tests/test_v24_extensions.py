"""v2.4 扩展自测：Gate C 执行环境类新规则 + review schema 1.1 + worklist 风险打分。

新规则的用例形态取自平台 1074 题复盘（rev 1145）与 2026-11-03 返修指南的
八类已确认运行缺陷，不是假设攻防。
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
EX_SCRIPT = SCRIPTS / "check_execution_path.py"
TEMPLATE = SKILL_ROOT / "assets" / "review_template.json"

LANDLOCK_RAW = "import landlock\n\ndef main():\n    landlock.deny_write('/data')\n"
LANDLOCK_GUARDED = (
    "try:\n    import landlock\nexcept ImportError:\n    landlock = None\n\n"
    "def main():\n    return 0\n")
DOCKERFILE_USER = "FROM python:3.11-slim\nRUN useradd -m app\nUSER app\nCOPY code /opt/code\n"
DOCKERFILE_NOROOT = "FROM python:3.11-slim\nCOPY code /opt/code\n"
HOME_BAD = 'import os\nos.makedirs("/root/cache", exist_ok=True)\n'
TASK_TOML = 'artifacts = ["/workspace/solution"]\n\n[verifier]\nenvironment_mode = "separate"\n'
INSTR_MISMATCH = "# 题面\n最终提交写入 /workspace/outputs/final。\n"
REPLACE_RACE = (
    "import os\n\n\ndef publish(tmp, dst):\n    os.replace(tmp, dst)\n\n\n"
    "def verify(dst):\n    return os.stat(dst).st_nlink == 1\n")


class ExecutionPathV24Test(unittest.TestCase):
    def _run(self, files, instruction=None):
        tmp = Path(tempfile.mkdtemp(prefix="exq24_"))
        root = tmp / "task"
        for rel, txt in files.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(txt, encoding="utf-8")
        if instruction:
            (root / "instruction.md").write_text(instruction, encoding="utf-8")
        out = tmp / "out.json"
        r = subprocess.run([sys.executable, "-B", str(EX_SCRIPT), "--root", str(root),
                            "--out", str(out)],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        self.assertTrue(out.is_file(), r.stdout + r.stderr)
        rep = json.loads(out.read_text(encoding="utf-8"))
        return r.returncode, rep

    def _rules(self, rep, rule):
        return [f for f in rep["findings"] if f["rule"] == rule]

    def test_landlock_unconditional_is_blocking(self):
        rc, rep = self._run({"tests/entry.py": LANDLOCK_RAW})
        self.assertEqual(rc, 1, "无条件 import landlock 应为 blocking")
        self.assertTrue(all(f["severity"] == "blocking"
                            for f in self._rules(rep, "landlock_dependency")))

    def test_landlock_guarded_is_informational_only(self):
        rc, rep = self._run({"tests/entry.py": LANDLOCK_GUARDED})
        self.assertEqual(rc, 0, "有 ImportError 守护不应 blocking")
        hits = self._rules(rep, "landlock_dependency")
        self.assertTrue(hits and all(f["severity"] == "informational" for f in hits))

    def test_home_writability_blocking_with_non_root_user(self):
        rc, rep = self._run({"tests/main.py": HOME_BAD,
                             "environment/Dockerfile": DOCKERFILE_USER})
        self.assertEqual(rc, 1)
        hits = self._rules(rep, "home_writability")
        self.assertTrue(hits and hits[0]["severity"] == "blocking")
        self.assertIn("/root/cache", hits[0]["detail"])

    def test_home_writability_needs_manual_without_user_directive(self):
        rc, rep = self._run({"tests/main.py": HOME_BAD,
                             "environment/Dockerfile": DOCKERFILE_NOROOT})
        self.assertEqual(rc, 0, "UID 未知时不得判 blocking")
        hits = self._rules(rep, "home_writability")
        self.assertTrue(hits and hits[0]["severity"] == "needs_manual")

    def test_artifacts_handoff_outside_mention_is_needs_manual(self):
        """抽检修正回归：题面行级提及的 artifacts 外路径默认 needs_manual。"""
        rc, rep = self._run({"task.toml": TASK_TOML,
                             "tests/grader.py": "candidate = '/workspace/solution'\n"},
                            instruction=INSTR_MISMATCH)
        self.assertEqual(rc, 0, "仅题面提及（无 tests 引用）不得判 blocking")
        hits = self._rules(rep, "artifacts_handoff_mismatch")
        self.assertTrue(hits and all(f["severity"] == "needs_manual" for f in hits))

    def test_artifacts_handoff_tests_referenced_is_blocking(self):
        """确定性移交缺口：tests/ 代码字面读写 artifacts 之外的路径 ⇒ blocking。"""
        rc, rep = self._run(
            {"task.toml": TASK_TOML,
             "tests/grader.py":
                 "candidate = '/workspace/solution'\n"
                 "result = open('/workspace/outputs/final/result.json')\n"},
            instruction=INSTR_MISMATCH)
        self.assertEqual(rc, 1)
        hits = self._rules(rep, "artifacts_handoff_mismatch")
        self.assertTrue(any(f["severity"] == "blocking" for f in hits),
                         "tests 字面引用 artifacts 外路径应为 blocking")

    def test_artifacts_mount_stem_ignored(self):
        """抽检修正回归：/workspace/dataset、/workspace/starter 等挂载不算冲突。"""
        rc, rep = self._run(
            {"task.toml": TASK_TOML,
             "tests/grader.py": "candidate = '/workspace/solution'\n"},
            instruction="# 题面\n数据集挂载于 /workspace/dataset/APAVA；"
                        "starter 见 /workspace/starter/。\n提交到 /workspace/solution。\n")
        conflicts = [f for f in self._rules(rep, "artifacts_handoff_mismatch")
                     if f["severity"] == "blocking"]
        self.assertEqual(conflicts, [], "挂载类路径不应判 blocking")

    def test_artifacts_unreferenced_is_needs_manual(self):
        rc, rep = self._run({"task.toml": TASK_TOML,
                             "tests/grader.py": "print('nothing here')\n"})
        self.assertEqual(rc, 0)
        hits = self._rules(rep, "artifacts_handoff_mismatch")
        self.assertTrue(hits and all(f["severity"] == "needs_manual" for f in hits))

    def test_artifacts_subpath_no_false_positive(self):
        """抽检修正回归（0340 误报）：artifacts 目录内部子路径不算冲突。"""
        rc, rep = self._run(
            {"task.toml": TASK_TOML,
             "tests/grader.py": "candidate = '/workspace/solution'\n"},
            instruction="# 题面\n提交路径统一为 /workspace/solution，平台整体移交该目录。\n"
                        "> cd /workspace/solution/tdmpc2\n"
                        "/workspace/solution/\n└── submission.json\n")
        self.assertEqual(rc, 0, "artifacts 内部子路径不应判 blocking")
        conflicts = [f for f in self._rules(rep, "artifacts_handoff_mismatch")
                     if f["severity"] == "blocking"]
        self.assertEqual(conflicts, [])

    def test_submission_pollution_blocking(self):
        rc, rep = self._run({
            "task.toml": TASK_TOML,
            "environment/public_eval/eval.py":
                "with open('/workspace/solution/debug.log', 'w') as f:\n    f.write('x')\n"})
        self.assertEqual(rc, 1)
        hits = self._rules(rep, "submission_dir_pollution")
        self.assertTrue(hits and hits[0]["severity"] == "blocking")

    def test_atomic_replace_race_needs_manual(self):
        rc, rep = self._run({"tests/publish.py": REPLACE_RACE})
        self.assertEqual(rc, 0, "竞态判定需人工读码，不判 blocking")
        hits = self._rules(rep, "atomic_replace_race")
        self.assertTrue(hits and hits[0]["severity"] == "needs_manual")

    def test_entrypoint_only_init_informational(self):
        rc, rep = self._run({"environment/Dockerfile":
                             "FROM python:3.11-slim\n"
                             "ENTRYPOINT [\"python\", \"-m\", \"server.serve\"]\n"})
        self.assertEqual(rc, 0)
        hits = self._rules(rep, "entrypoint_only_init")
        self.assertTrue(hits and hits[0]["severity"] == "informational")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WorklistRiskPatternTest(unittest.TestCase):
    def test_author_calibration_declaration_flagged(self):
        brw = _load("build_review_worklist")
        score, hits = brw.score_decl("Solver 必须达到作者校准的 3σ 提升才算完成，否则继续运行")
        self.assertGreaterEqual(score, 3)
        self.assertTrue(any("作者校准" in h for h in hits))

    def test_algorithm_sigma_not_mislabeled(self):
        brw = _load("build_review_worklist")
        # 题目算法自身使用 3σ（异常检测）不应带作者校准标签
        _, hits = brw.score_decl("使用 3σ 规则对梯度做异常值检测")
        self.assertFalse(any("作者校准" in h for h in hits))


class ReviewSchemaV11Test(unittest.TestCase):
    def _validate(self, review_obj, tmp):
        p = Path(tmp) / "review.json"
        p.write_text(json.dumps(review_obj, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run([sys.executable, "-B", str(SCRIPTS / "validate_review.py"),
                            "--review", str(p)],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        return r.returncode, json.loads(r.stdout)

    def test_template_with_v11_fields_valid(self):
        review = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual(review["schema_version"], "1.1")
        rc, result = self._validate(review, tempfile.mkdtemp(prefix="rv11_"))
        self.assertEqual(rc, 0, result["errors"])

    def test_platform_fail_requires_finding(self):
        review = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        review["platform_checks"] = [
            {"id": "PC1", "rule": "B-C02", "status": "fail",
             "evidence": ["task.toml:4"], "evidence_state": "verified",
             "note": "docker_image 配置了本地镜像"}]
        rc, result = self._validate(review, tempfile.mkdtemp(prefix="rv12_"))
        self.assertEqual(rc, 1)
        self.assertTrue(any("no finding in findings" in e for e in result["errors"]),
                         "fail 的平台规则必须落锤到 findings（E7）")

    def test_responsible_action_contradiction_rejected(self):
        review = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        review["findings"] = [{
            "id": "F1", "summary": "x", "severity": "major", "status": "confirmed",
            "evidence": ["a:1"], "affected_claim_ids": [], "affected_gates": [],
            "waiver_eligible": False,
            "responsible": "platform", "action": "author_fix"}]
        rc, result = self._validate(review, tempfile.mkdtemp(prefix="rv13_"))
        self.assertEqual(rc, 1)
        self.assertTrue(any("contradicts" in e for e in result["errors"]))

    def test_responsible_action_consistent_accepted(self):
        review = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        review["findings"] = [{
            "id": "F1", "summary": "x", "severity": "major", "status": "unresolved",
            "evidence": ["a:1"], "affected_claim_ids": [], "affected_gates": [],
            "waiver_eligible": False,
            "responsible": "platform", "action": "platform_fix"}]
        rc, result = self._validate(review, tempfile.mkdtemp(prefix="rv14_"))
        self.assertEqual(rc, 0, result["errors"])


if __name__ == "__main__":
    unittest.main()
