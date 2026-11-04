"""平台源包硬规则（B-C01–B-C04，v2.4）自测。

案例边界直接取自 supplement platform-audit 的 PLATFORM_EVAL_CASES：
  · 注释/说明文字出现字段名不算配置（B-C02）
  · 仅 README 里的 URL 不算实际生效的包源（B-C03）
  · .npmrc 写 bnpm 但 npm install --registry=... 覆盖 ⇒ 不符合（B-C04）
  · 未用 npm 的题目 B-C04 不适用
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "check_platform_rules.py"

TASK_TOML_CLEAN = '[verifier]\nenvironment_mode = "separate"\nartifacts = ["/workspace/solution"]\n'
TASK_TOML_IMAGE = TASK_TOML_CLEAN + 'docker_image = "task-agent:v1"\n'
TASK_TOML_COMMENT = ("[verifier]\nenvironment_mode = \"separate\"\n"
                     "# docker_image 由平台构建，无需填写\n")
DOCKERFILE_CLEAN = "FROM python:3.11-slim\nRUN pip install numpy\nCOPY starter /opt/starter\n"
DOCKERFILE_TUNA = ("FROM python:3.11-slim\n"
                   "RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple numpy\n")


def make_pkg(tmp: Path, toml_text=TASK_TOML_CLEAN, dockerfile_text=DOCKERFILE_CLEAN,
             extra_files=None, layout="package"):
    """layout=package: workspace/harbor_task/…；layout=taskdir: 根即任务目录。"""
    root = Path(tmp) / "pkg"
    base = root / "workspace" / "harbor_task" if layout == "package" else root
    (base / "environment" / "starter").mkdir(parents=True)  # COPY starter 的真实来源
    (base / "environment" / "starter" / "main.py").write_text("# starter\n", encoding="utf-8")
    if toml_text is not None:
        (base / "task.toml").write_text(toml_text, encoding="utf-8")
    (base / "instruction.md").write_text("# task\n提交到 /workspace/solution\n", encoding="utf-8")
    if dockerfile_text is not None:
        (base / "environment" / "Dockerfile").write_text(dockerfile_text, encoding="utf-8")
    for rel, txt in (extra_files or {}).items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8")
    return root


class PlatformRulesTest(unittest.TestCase):
    def _run(self, root):
        out = Path(root).parent / "platform-rules.json"
        r = subprocess.run([sys.executable, "-B", str(SCRIPT), "--root", str(root),
                            "--out", str(out)],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        self.assertTrue(out.is_file(), r.stdout + r.stderr)
        return r.returncode, json.loads(out.read_text(encoding="utf-8"))

    def _check(self, rep, cid):
        return next(c for c in rep["checks"] if c["id"] == cid)

    # ── B-C01 ──
    def test_c01_pass_canonical_layout(self):
        rc, rep = self._run(make_pkg(tempfile.mkdtemp(prefix="pr1_")))
        self.assertEqual(rc, 0)
        self.assertEqual(self._check(rep, "B-C01")["status"], "pass")

    def test_c01_fail_multiple_task_toml(self):
        rc, rep = self._run(make_pkg(
            tempfile.mkdtemp(prefix="pr2_"),
            extra_files={"backup/task.toml": TASK_TOML_CLEAN}))
        self.assertEqual(rc, 1)
        self.assertEqual(self._check(rep, "B-C01")["status"], "fail")
        detail = self._check(rep, "B-C01")["findings"][0]["detail"]
        self.assertIn("2 份 task.toml", detail)

    def test_c01_fail_missing(self):
        root = make_pkg(tempfile.mkdtemp(prefix="pr3_"))
        (root / "workspace" / "harbor_task" / "task.toml").unlink()
        rc, rep = self._run(root)
        self.assertEqual(rc, 1)
        self.assertEqual(self._check(rep, "B-C01")["status"], "fail")

    # ── B-C02 ──
    def test_c02_fail_docker_image_configured(self):
        rc, rep = self._run(make_pkg(tempfile.mkdtemp(prefix="pr4_"),
                                     toml_text=TASK_TOML_IMAGE))
        self.assertEqual(rc, 1)
        c02 = self._check(rep, "B-C02")
        self.assertEqual(c02["status"], "fail")
        self.assertTrue(any("docker_image" in f["detail"] and f["severity"] == "blocking"
                            for f in c02["findings"]))

    def test_c02_pass_comment_only_mention(self):
        rc, rep = self._run(make_pkg(tempfile.mkdtemp(prefix="pr5_"),
                                     toml_text=TASK_TOML_COMMENT))
        c02 = self._check(rep, "B-C02")
        self.assertEqual(c02["status"], "pass",
                         "注释中出现 docker_image 不算配置，不应判 fail")

    def test_c02_fail_missing_dockerfile(self):
        rc, rep = self._run(make_pkg(tempfile.mkdtemp(prefix="pr6_"),
                                     dockerfile_text=None))
        c02 = self._check(rep, "B-C02")
        self.assertEqual(c02["status"], "fail")
        self.assertTrue(any("Dockerfile" in f["detail"] for f in c02["findings"]))

    def test_c02_fail_copy_source_missing(self):
        rc, rep = self._run(make_pkg(tempfile.mkdtemp(prefix="pr7_"),
                                     dockerfile_text="FROM python:3.11-slim\n"
                                                     "COPY assets/gone.bin /opt/\n"))
        c02 = self._check(rep, "B-C02")
        self.assertEqual(c02["status"], "fail")
        self.assertTrue(any("COPY/ADD" in f["detail"] for f in c02["findings"]))

    # ── B-C03 ──
    def test_c03_fail_tsinghua_index_in_dockerfile(self):
        rc, rep = self._run(make_pkg(tempfile.mkdtemp(prefix="pr8_"),
                                     dockerfile_text=DOCKERFILE_TUNA))
        self.assertEqual(rc, 1)
        c03 = self._check(rep, "B-C03")
        self.assertEqual(c03["status"], "fail")
        self.assertTrue(any("pypi.tuna.tsinghua.edu.cn" in f["detail"]
                            for f in c03["findings"]))

    def test_c03_readme_only_mention_not_violation(self):
        rc, rep = self._run(make_pkg(
            tempfile.mkdtemp(prefix="pr9_"),
            extra_files={"workspace/harbor_task/README.md":
                         "备用源：https://pypi.tuna.tsinghua.edu.cn/simple（未使用）"}))
        self.assertEqual(self._check(rep, "B-C03")["status"], "pass",
                         "说明文档里的 URL 不判违规（说明 ≠ 生效）")

    # ── B-C04 ──
    def test_c04_fail_registry_override(self):
        rc, rep = self._run(make_pkg(
            tempfile.mkdtemp(prefix="pr10_"),
            extra_files={
                "workspace/harbor_task/environment/.npmrc": "registry=https://bnpm.byted.org\n",
                "workspace/harbor_task/environment/Dockerfile":
                    "FROM node:20\nRUN npm config set registry https://bnpm.byted.org\n"
                    "RUN npm install --registry=https://registry.npmjs.org\n"
                    "COPY web /opt/web\n",
            }))
        c04 = self._check(rep, "B-C04")
        self.assertEqual(c04["status"], "fail",
                         "命令行 --registry 覆盖 .npmrc ⇒ 不符合")
        self.assertTrue(any("覆盖" in f["detail"] for f in c04["findings"]))

    def test_c04_pass_bnpm_config(self):
        rc, rep = self._run(make_pkg(
            tempfile.mkdtemp(prefix="pr11_"),
            extra_files={
                "workspace/harbor_task/environment/Dockerfile":
                    "FROM node:20\nRUN npm config set registry https://bnpm.byted.org\n"
                    "RUN npm install\nCOPY web /opt/web\n",
            }))
        self.assertEqual(self._check(rep, "B-C04")["status"], "pass")

    def test_c04_not_applicable_without_npm(self):
        rc, rep = self._run(make_pkg(tempfile.mkdtemp(prefix="pr12_")))
        self.assertEqual(self._check(rep, "B-C04")["status"], "not_applicable")

    def test_c04_needs_manual_npm_without_config(self):
        rc, rep = self._run(make_pkg(
            tempfile.mkdtemp(prefix="pr13_"),
            extra_files={"workspace/harbor_task/environment/Dockerfile":
                         "FROM node:20\nRUN npm install\nCOPY web /opt/web\n"}))
        self.assertEqual(self._check(rep, "B-C04")["status"], "needs_manual")


if __name__ == "__main__":
    unittest.main()
