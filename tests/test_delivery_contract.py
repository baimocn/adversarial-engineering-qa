"""交付契约机械检查（D-C01/D-C02，v2.4.1）自测。

D-C01 来源：1074 题复盘评分阶段 72 题 RewardFileNotFoundError（声明落点从未被写入）；
D-C02 来源：评分资产/锚点不一致 2 题 + 1841 实测指纹合同失效（5/26 失配）。
"""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "check_delivery_contract.py"

TASK_TOML_REWARD_OK = 'reward_file = "/logs/verifier/reward.txt"\n'
TASK_TOML_REWARD_BAD = 'reward_file = "/logs/verifier/reward.txt"\n'
TASK_TOML_NO_REWARD = '[verifier]\nenvironment_mode = "separate"\n'

TEST_SH_OK = '#!/bin/bash\nREWARD_DIR="${REWARD_DIR:-/logs/verifier}"\necho 1 > "$REWARD_DIR/reward.txt"\n'
TEST_SH_BAD = '#!/bin/bash\nOUT_DIR="/workspace/.verifier"\necho 1 > "$OUT_DIR/reward.txt"\n'


def make_pkg(tmp: Path, toml_text: str, test_sh: str | None = None,
             extra_files: dict | None = None):
    root = Path(tmp) / "pkg"
    base = root / "workspace" / "harbor_task"
    (base / "tests").mkdir(parents=True)
    (base / "solution").mkdir(parents=True)
    (base / "solution" / "solve.sh").write_text(
        "#!/bin/bash\ncp method.py /workspace/solution/\n", encoding="utf-8")
    (base / "solution" / "method.py").write_text("# reference\n", encoding="utf-8")
    (base / "task.toml").write_text(toml_text, encoding="utf-8")
    (base / "instruction.md").write_text("# task\n", encoding="utf-8")
    if test_sh is not None:
        (base / "tests" / "test.sh").write_text(test_sh, encoding="utf-8")
    for rel, txt in (extra_files or {}).items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(txt, (bytes, bytearray)):
            p.write_bytes(txt)
        else:
            p.write_text(txt, encoding="utf-8")
    return root


class DeliveryContractTest(unittest.TestCase):
    def _run(self, root):
        out = Path(root).parent / "delivery.json"
        r = subprocess.run([sys.executable, "-B", str(SCRIPT), "--root", str(root),
                            "--out", str(out)],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        self.assertTrue(out.is_file(), r.stdout + r.stderr)
        return r.returncode, json.loads(out.read_text(encoding="utf-8"))

    def _check(self, rep, cid):
        return next(c for c in rep["checks"] if c["id"] == cid)

    # ── D-C01 ──
    def test_d01_pass_declared_path_written(self):
        rc, rep = self._run(make_pkg(tempfile.mkdtemp(prefix="dc1_"),
                                     TASK_TOML_REWARD_OK, TEST_SH_OK))
        self.assertEqual(rc, 0)
        self.assertEqual(self._check(rep, "D-C01")["status"], "pass")

    def test_d01_fail_declared_path_never_written(self):
        rc, rep = self._run(make_pkg(tempfile.mkdtemp(prefix="dc2_"),
                                     TASK_TOML_REWARD_BAD, TEST_SH_BAD))
        self.assertEqual(rc, 1)
        c = self._check(rep, "D-C01")
        self.assertEqual(c["status"], "fail")
        self.assertTrue(any("/logs/verifier/reward.txt" in f["detail"]
                            for f in c["findings"]))
        self.assertTrue(any(".verifier" in f["detail"] for f in c["findings"]))

    def test_d01_not_applicable_without_declaration(self):
        rc, rep = self._run(make_pkg(tempfile.mkdtemp(prefix="dc3_"),
                                     TASK_TOML_NO_REWARD, TEST_SH_OK))
        self.assertEqual(self._check(rep, "D-C01")["status"], "not_applicable")

    # ── D-C02 ──
    def _manifest_pkg(self, prefix, sha_override=None, declare_missing=False):
        tmp = Path(tempfile.mkdtemp(prefix=prefix))
        payload = b"payload-bytes"
        real_sha = hashlib.sha256(payload).hexdigest()
        sha = sha_override or real_sha
        manifest = {"files": {"data.bin": {"size": len(payload), "sha256": sha}}}
        extra = {"workspace/harbor_task/frozen_manifest.json": json.dumps(manifest)}
        if not declare_missing:
            extra["workspace/harbor_task/data.bin"] = payload
        return make_pkg(tmp, TASK_TOML_NO_REWARD, TEST_SH_OK, extra), real_sha

    def test_d02_pass_hashes_match(self):
        root, _ = self._manifest_pkg("dc4_")
        rc, rep = self._run(root)
        self.assertEqual(rc, 0)
        self.assertEqual(self._check(rep, "D-C02")["status"], "pass")

    def test_d02_fail_hash_mismatch(self):
        root, _ = self._manifest_pkg("dc5_", sha_override="0" * 64)
        rc, rep = self._run(root)
        self.assertEqual(rc, 1)
        c = self._check(rep, "D-C02")
        self.assertEqual(c["status"], "fail")
        self.assertTrue(any("清单声明与实物不符" in f["detail"] for f in c["findings"]))

    def test_d02_missing_file_needs_manual(self):
        root, _ = self._manifest_pkg("dc6_", declare_missing=True)
        rc, rep = self._run(root)
        self.assertEqual(rc, 0)
        self.assertEqual(self._check(rep, "D-C02")["status"], "needs_manual")

    def test_d02_evidence_scope_mismatch_needs_manual(self):
        """专家证据清单（expert_evidence/）不一致不阻断提交，记 needs_manual。"""
        tmp = Path(tempfile.mkdtemp(prefix="dc8_"))
        payload = b"payload-bytes"
        manifest = {"files": {"data.bin": {"size": len(payload), "sha256": "0" * 64}}}
        root = make_pkg(tmp, TASK_TOML_NO_REWARD, TEST_SH_OK, {
            "expert_evidence/provenance/hashes.json": json.dumps(manifest),
            "expert_evidence/provenance/data.bin": payload,
        })
        rc, rep = self._run(root)
        self.assertEqual(rc, 0, "证据侧不一致不应判 fail")
        self.assertEqual(self._check(rep, "D-C02")["status"], "needs_manual")

    def test_d02_revision_log_history_not_current_declaration(self):
        """qa_batch_v2 交叉审计修正：清单 revision_log 的旧哈希是实名刷新记录，
        不是当前声明——不得产生假失配。"""
        tmp = Path(tempfile.mkdtemp(prefix="dc15_"))
        payload = b"payload-bytes"
        real_sha = hashlib.sha256(payload).hexdigest()
        manifest = {
            "package": {"files": {"data.bin": {"size": len(payload), "sha256": real_sha}}},
            "revision_log": [{"old_declared": {"data.bin": {"size": 1, "sha256": "0" * 64}},
                              "old_actual_v1": {"data.bin": {"size": 2, "sha256": "1" * 64}},
                              "v2_current": {"data.bin": {"size": len(payload), "sha256": real_sha}}}],
        }
        root = make_pkg(tmp, TASK_TOML_NO_REWARD, TEST_SH_OK, {
            "workspace/harbor_task/frozen_manifest.json": json.dumps(manifest),
            "workspace/harbor_task/data.bin": payload,
        })
        rc, rep = self._run(root)
        self.assertEqual(rc, 0, "revision_log 旧哈希不得计为当前声明")
        self.assertEqual(self._check(rep, "D-C02")["status"], "pass")

    def test_d02_not_applicable_without_manifest(self):
        rc, rep = self._run(make_pkg(tempfile.mkdtemp(prefix="dc7_"),
                                     TASK_TOML_NO_REWARD, TEST_SH_OK))
        self.assertEqual(self._check(rep, "D-C02")["status"], "not_applicable")

    # ── D-C03：reward 二选一 ──
    def test_d03_fail_dual_reward_files(self):
        root = make_pkg(tempfile.mkdtemp(prefix="dc9_"), TASK_TOML_NO_REWARD,
                        '#!/bin/bash\nOUT=/logs/verifier\necho 1 > "$OUT/reward.json"\necho 1 > "$OUT/reward.txt"\n')
        rc, rep = self._run(root)
        self.assertEqual(rc, 1)
        c = self._check(rep, "D-C03")
        self.assertEqual(c["status"], "fail")
        self.assertTrue(any("二选一" in f["detail"] for f in c["findings"]))

    def test_d03_pass_single_reward(self):
        root = make_pkg(tempfile.mkdtemp(prefix="dc10_"), TASK_TOML_NO_REWARD,
                        '#!/bin/bash\nOUT=/logs/verifier\necho 1 > "$OUT/reward.json"\n')
        rc, rep = self._run(root)
        self.assertEqual(self._check(rep, "D-C03")["status"], "pass")

    def test_d03_diagnostics_not_counted(self):
        root = make_pkg(tempfile.mkdtemp(prefix="dc11_"), TASK_TOML_NO_REWARD,
                        '#!/bin/bash\nOUT=/logs/verifier\necho 1 > "$OUT/reward.json"\n'
                        'echo detail > "$OUT/reward_detail.json"\necho r > "$OUT/result.json"\n')
        rc, rep = self._run(root)
        self.assertEqual(self._check(rep, "D-C03")["status"], "pass",
                         "reward_detail/result 属诊断文件，不算第二种正式 reward")

    def test_d03_variable_indirect_dual_write_needs_manual(self):
        """2604 r2 交叉审计：变量赋值 + 循环镜像的间接双写，行级扫描抓不到 →
        文件级双字面量共存 + 写调用 ⇒ needs_manual（人工确认落点）。"""
        script = (
            '#!/bin/bash\n'
            'OUT=/workspace/.verifier\n'
            'REWARD_TXT="$OUT_DIR/reward.txt"\n'
            'REWARD_JSON="$OUT_DIR/reward.json"\n'
            'publish_reward() { for name in reward.txt reward.json; do '
            'atomic_write "$OUT_DIR/$name"; done }\n'
            'grader --out "$REWARD_JSON"\n')
        root = make_pkg(tempfile.mkdtemp(prefix="dc16_"), TASK_TOML_NO_REWARD, script)
        rc, rep = self._run(root)
        c = self._check(rep, "D-C03")
        self.assertEqual(c["status"], "needs_manual",
                         "变量间接双写应触发 needs_manual 而非 pass")

    # ── D-C04：Oracle 入口 ──
    def test_d04_fail_missing_oracle_entry(self):
        root = make_pkg(tempfile.mkdtemp(prefix="dc12_"),
                        TASK_TOML_NO_REWARD, TEST_SH_OK)
        (root / "workspace" / "harbor_task" / "solution" / "solve.sh").unlink()
        rc, rep = self._run(root)
        self.assertEqual(rc, 1)
        c = self._check(rep, "D-C04")
        self.assertEqual(c["status"], "fail")
        self.assertTrue(any("solution/solve.sh" in f["detail"] for f in c["findings"]))

    def test_d04_pass_oracle_entry_present(self):
        root = make_pkg(tempfile.mkdtemp(prefix="dc13_"), TASK_TOML_NO_REWARD, TEST_SH_OK,
                        {"workspace/harbor_task/solution/solve.sh": "#!/bin/bash\ncp method.py /workspace/solution/\n",
                         "workspace/harbor_task/solution/method.py": "# reference\n"})
        rc, rep = self._run(root)
        self.assertEqual(self._check(rep, "D-C04")["status"], "pass")

    def test_d04_fail_oracle_leaked_to_agent_image(self):
        root = make_pkg(tempfile.mkdtemp(prefix="dc14_"), TASK_TOML_NO_REWARD, TEST_SH_OK,
                        {"workspace/harbor_task/solution/solve.sh": "#!/bin/bash\ntrue\n",
                         "workspace/harbor_task/environment/Dockerfile":
                             "FROM python:3.11\nCOPY solution/ /workspace/solution/\n"})
        rc, rep = self._run(root)
        self.assertEqual(rc, 1)
        c = self._check(rep, "D-C04")
        self.assertEqual(c["status"], "fail")
        self.assertTrue(any("Oracle 私有参考解暴露" in f["detail"] for f in c["findings"]))


if __name__ == "__main__":
    unittest.main()
