import argparse
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReturnContractTests(unittest.TestCase):
    def test_detects_timeout_arity_mismatch_and_cli_exit(self):
        checker = load_script("check_return_contracts")
        source = '''\
def run_isolated_inference(timeout):
    if timeout:
        return {"ok": False}, None, None
    return {"ok": True}, [1.0]

def evaluate(timeout):
    status, logits = run_isolated_inference(timeout)
    return status
'''
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "src"
            root.mkdir()
            (root / "evaluate_verify.py").write_text(source, encoding="utf-8")
            result = checker.analyze(root)
            self.assertEqual(len(result["findings"]), 1)
            finding = result["findings"][0]
            self.assertEqual(finding["expected_arity"], 2)
            self.assertEqual(finding["possible_arities"], [2, 3])
            self.assertEqual(finding["confidence"], "confirmed_static")

            output = Path(temp) / "out" / "returns.json"
            process = subprocess.run([
                sys.executable, str(SCRIPTS / "check_return_contracts.py"),
                "--root", str(root), "--out", str(output), "--fail-on-findings",
            ], capture_output=True, text=True)
            self.assertEqual(process.returncode, 1, (process.stdout or "") + (process.stderr or ""))
            self.assertTrue(output.exists())


class CollectorTests(unittest.TestCase):
    def test_builds_manifest_shards_and_declaration_index(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "src"
            root.mkdir()
            (root / "task.toml").write_text('dev_score_command = "python evaluate.py"\n', encoding="utf-8")
            (root / "evaluate.py").write_text("def main():\n    return 0\n", encoding="utf-8")
            (root / ".git").mkdir()
            (root / ".git" / "ignored").write_text("not reviewed", encoding="utf-8")
            out = Path(temp) / "index"
            process = subprocess.run([
                sys.executable, str(SCRIPTS / "collect_evidence.py"),
                "--root", str(root), "--out", str(out), "--max-files-per-shard", "1",
            ], capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, (process.stdout or "") + (process.stderr or ""))
            manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["files_total"], 2)
            self.assertEqual(manifest["python_files_indexed"], 1)
            self.assertGreaterEqual(manifest["declaration_candidates"], 1)
            self.assertEqual(len(manifest["shards"]), 2)
            self.assertEqual(len(manifest["source_digest"]), 64)
            self.assertTrue((out / "symbols.json").exists())


class ReviewValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = load_script("validate_review")
        cls.schema = json.loads((SKILL_ROOT / "references" / "report-schema.json").read_text(encoding="utf-8"))
        cls.template = json.loads((SKILL_ROOT / "assets" / "review_template.json").read_text(encoding="utf-8"))

    def errors(self, review):
        return self.validator.validate_review(review, self.schema)

    def test_template_is_valid_but_incomplete(self):
        self.assertEqual(self.errors(copy.deepcopy(self.template)), [])

    def make_static_pass(self):
        review = copy.deepcopy(self.template)
        review["artifact"].update({"path": "artifact.zip", "sha256": "a" * 64, "size_bytes": 10})
        review["current_correctness"] = {
            "status": "pass",
            "checks": [{"id": "B1", "description": "Static contract checked", "status": "pass",
                        "evidence": ["returns.json"], "finding_ids": []}],
        }
        review["claims"][0].update({
            "behavior_required": False, "status": "pass", "evidence_level": "EV2",
            "coverage_refs": [],
            "implementation_evidence": [{"path": "evaluate.py", "line": 1, "kind": "code", "note": "checked"}],
        })
        review["behavior_coverage"][0]["branches"] = [
            {"name": "normal", "status": "pass", "evidence": ["static proof"]},
            {"name": "failure_or_timeout", "status": "pass", "evidence": ["static proof"]},
        ]
        review["behavior_coverage"][0]["untested_branches"] = []
        review["standard_decision"] = "PASS"
        review["coverage_statement"].update({
            "files_total": 1, "files_indexed": 1, "machine_scanned": 1,
            "human_reviewed": 1, "behavior_branches_run": 2, "unreviewed": [],
        })
        review["weakest_link"] = "Dynamic behavior was not required for this static contract"
        return review

    def test_valid_static_pass_is_accepted(self):
        self.assertEqual(self.errors(self.make_static_pass()), [])

    def test_static_behavior_pass_is_rejected(self):
        review = self.make_static_pass()
        review["claims"][0]["behavior_required"] = True
        review["claims"][0]["evidence_level"] = "EV3"
        review["claims"][0]["coverage_refs"] = ["B0"]
        errors = self.errors(review)
        self.assertTrue(any("static mode" in error for error in errors), errors)

    def test_early_crash_is_not_defense_pass(self):
        review = copy.deepcopy(self.template)
        review["mode"] = "dynamic"
        review["adversarial_cases"] = [{
            "id": "A1", "claim_id": "C0", "attack": "malformed payload",
            "authorization": "explicit sandbox authorization", "core_mechanism": True,
            "reached_target": False, "reachability_evidence": [],
            "early_exit": {"kind": "syntax_error", "message": "IndentationError"},
            "defense_observed": True, "oracle": "reward=-1",
            "control": {"expected_without_defense": "attack runs", "observed": "not run"},
            "ablation": {"performed": True, "result": "same early crash"},
            "status": "pass", "evidence": ["attack.log"],
        }]
        review["coverage_statement"]["attacks_total"] = 1
        errors = self.errors(review)
        self.assertTrue(any("reached the target" in error for error in errors), errors)
        self.assertTrue(any("early exit" in error for error in errors), errors)

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "duplicate.json"
            path.write_text('{"a": 1, "a": 2}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                self.validator.strict_json_load(path)


class AutoResearchIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.official = self.root / "autoresearch-task-qa-legacy-waiver"
        self.official.mkdir()
        self.script = SCRIPTS / "check_autoresearch_integration.py"
        manifest = json.loads((SKILL_ROOT / "references" / "autoresearch-v4-coverage.json").read_text(encoding="utf-8"))
        (self.official / "SKILL.md").write_text(
            "---\nname: autoresearch-task-qa-legacy-waiver\n---\n版本 v0.3.10-standard-waiver.5\n",
            encoding="utf-8",
        )
        (self.official / "references").mkdir()
        for name in manifest["official_references"]:
            (self.official / "references" / name).write_text(name + "\n", encoding="utf-8")
        (self.official / "scripts").mkdir()
        for name in manifest["official_scripts"]:
            (self.official / "scripts" / name).write_text("# test double\n", encoding="utf-8")
        (self.official / "scripts" / "audit_standard_with_waivers.py").write_text(
            "import argparse\n"
            "p=argparse.ArgumentParser()\n"
            "p.add_argument('source')\n"
            "p.add_argument('--standard-review')\n"
            "p.add_argument('--review')\n"
            "p.add_argument('--out-dir', required=True)\n"
            "p.parse_args()\n",
            encoding="utf-8",
        )
        baseline = self.root / "autoresearch-baseline-quality"
        (baseline / "references").mkdir(parents=True)
        (baseline / "SKILL.md").write_text("---\nname: autoresearch-baseline-quality\n---\n", encoding="utf-8")
        (baseline / "references" / "baseline-review-method.md").write_text("method\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(self.script), *args], capture_output=True, text=True)

    def test_contract_probe_and_complete_minimal_delivery(self):
        contract_path = self.root / "contract.json"
        process = self.run_cli("contract", "--official-skill", str(self.official), "--out", str(contract_path))
        self.assertEqual(process.returncode, 0, (process.stdout or "") + (process.stderr or ""))
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        self.assertTrue(contract["valid"])
        self.assertEqual(contract["references_checked"], 18)

        artifact = self.root / "artifact.zip"
        artifact.write_bytes(b"test artifact")
        import hashlib
        artifact_sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
        delivery = self.root / "delivery"
        delivery.mkdir()
        coverage_path = delivery / "autoresearch_coverage.json"
        process = self.run_cli("init-coverage", "--artifact", str(artifact), "--sha256", artifact_sha, "--out", str(coverage_path))
        self.assertEqual(process.returncode, 0, (process.stdout or "") + (process.stderr or ""))
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(coverage["requirements"]), 115)
        for row in coverage["requirements"]:
            row.update(status="pass", evidence=["current-evidence/" + row["id"]])
        coverage["official_contract"] = {
            "path": str(self.official.resolve()),
            "contract_sha256": contract["contract_sha256"],
            "status": "verified",
        }

        review = copy.deepcopy(ReviewValidationTests.template) if hasattr(ReviewValidationTests, "template") else None
        if review is None:
            ReviewValidationTests.setUpClass()
            review = copy.deepcopy(ReviewValidationTests.template)
        review["domain"] = "autoresearch_harbor"
        review["artifact"].update({"path": str(artifact), "sha256": artifact_sha, "size_bytes": artifact.stat().st_size})
        review["current_correctness"] = {
            "status": "pass",
            "checks": [{"id": "B1", "description": "Static contract checked", "status": "pass", "evidence": ["returns.json"], "finding_ids": []}],
        }
        review["claims"][0].update({
            "behavior_required": False, "status": "pass", "evidence_level": "EV2", "coverage_refs": [],
            "implementation_evidence": [{"path": "evaluate.py", "line": 1, "kind": "code", "note": "checked"}],
        })
        review["behavior_coverage"][0]["branches"] = [
            {"name": "normal", "status": "pass", "evidence": ["static proof"]},
            {"name": "failure_or_timeout", "status": "pass", "evidence": ["static proof"]},
        ]
        review["behavior_coverage"][0]["untested_branches"] = []
        review["standard_decision"] = "PASS"
        review["coverage_statement"].update({
            "files_total": 1, "files_indexed": 1, "machine_scanned": 1, "human_reviewed": 1,
            "behavior_branches_run": 2, "unreviewed": [],
        })
        review["weakest_link"] = "No dynamic behavior was required for this static fixture"
        (delivery / "adversarial_review.json").write_text(json.dumps(review), encoding="utf-8")
        (delivery / "standard_review").mkdir()
        (delivery / "waiver_review").mkdir()
        (delivery / "standard_review" / "report.json").write_text(json.dumps({"decision": "PASS"}), encoding="utf-8")
        (delivery / "waiver_review" / "report.json").write_text(json.dumps({
            "decision": "PASS_WITH_WAIVERS", "stage": "standard_review_with_waivers",
            "standard_auditor_executed": True, "review_completed": True, "standard_findings": [],
        }), encoding="utf-8")
        (delivery / "report.json").write_text(json.dumps({
            "decision": "PASS", "official_standard_decision": "PASS",
            "official_waiver_decision": "PASS_WITH_WAIVERS", "adversarial_decision": "PASS",
            "coverage_decision": "PASS",
        }), encoding="utf-8")
        for row in coverage["deliverables"]:
            path = delivery / row["path"]
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"status": "reviewed"}) if path.suffix == ".json" else "reviewed\n", encoding="utf-8")
            row["status"] = "complete"
            row["sha256"] = "self" if row["path"] == "autoresearch_coverage.json" else hashlib.sha256(path.read_bytes()).hexdigest()
        coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
        process = self.run_cli(
            "validate", "--review", str(delivery / "adversarial_review.json"),
            "--coverage", str(coverage_path), "--delivery-dir", str(delivery),
            "--official-skill", str(self.official),
        )
        self.assertEqual(process.returncode, 0, (process.stdout or "") + (process.stderr or ""))
        self.assertTrue(json.loads(process.stdout)["valid"])

    def test_missing_coverage_requirement_blocks_pass(self):
        artifact = self.root / "artifact.zip"
        artifact.write_bytes(b"x")
        coverage_path = self.root / "coverage.json"
        process = self.run_cli("init-coverage", "--artifact", str(artifact), "--sha256", "a" * 64, "--out", str(coverage_path))
        self.assertEqual(process.returncode, 0)
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
        coverage["requirements"] = coverage["requirements"][1:]
        coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
        delivery = self.root / "missing-delivery"
        process = self.run_cli(
            "validate", "--review", str(self.root / "absent-review.json"),
            "--coverage", str(coverage_path), "--delivery-dir", str(delivery),
            "--official-skill", str(self.root / "absent-official"),
        )
        self.assertEqual(process.returncode, 2)
        output = json.loads(process.stdout)
        self.assertFalse(output["valid"])
        self.assertTrue(any("Missing coverage requirement" in error for error in output["errors"]))
        self.assertTrue(any("Official AutoResearch skill not found" in error for error in output["errors"]))


class BundledOfficialTests(unittest.TestCase):
    SOURCE_CANDIDATES = [
        Path("D:/Desktop/论文任务返修/review_skill-0.3.10-standard-waiver.5_1023"),
        Path("D:/Desktop/论文质检/review_skill-0.3.10-standard-waiver.5_1023"),
    ]

    def find_source_root(self):
        for candidate in self.SOURCE_CANDIDATES:
            if (candidate / "autoresearch-task-qa-legacy-waiver" / "SKILL.md").is_file():
                return candidate
        return None

    def test_default_contract_resolves_bundled_official(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "contract.json"
            process = subprocess.run([
                sys.executable, str(SCRIPTS / "check_autoresearch_integration.py"),
                "contract", "--out", str(out),
            ], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(process.returncode, 0, (process.stdout or "") + (process.stderr or ""))
            contract = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(contract["valid"], contract.get("errors"))
            official = Path(contract["official_skill"])
            self.assertEqual(official.parent, SKILL_ROOT / "official")
            self.assertTrue(official.is_dir())
            baseline = Path(contract["baseline_skill"])
            self.assertEqual(baseline.parent, SKILL_ROOT / "official")
            self.assertTrue(contract["cli_probed"])

    def test_bundled_official_byte_matches_source(self):
        source_root = self.find_source_root()
        if source_root is None:
            self.skipTest("Official source distribution is not present on this machine")
        sync = load_script("sync_official_skills")
        differences = sync.compare(source_root)
        self.assertEqual(sorted(differences), sorted(sync.SKILL_NAMES))
        for name, row in differences.items():
            self.assertTrue(row["identical"], name + " diverged: " + json.dumps(row))
        self.assertEqual(differences["autoresearch-task-qa-legacy-waiver"]["bundled_files"], 54)
        self.assertEqual(differences["autoresearch-baseline-quality"]["bundled_files"], 3)

    def test_sync_check_and_explicit_apply(self):
        sync = load_script("sync_official_skills")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_root = root / "source"
            for name in sync.SKILL_NAMES:
                skill = source_root / name
                (skill / "references").mkdir(parents=True)
                (skill / "SKILL.md").write_text("---\nname: " + name + "\n---\n", encoding="utf-8")
                (skill / "references" / "only.md").write_text("original\n", encoding="utf-8")
            bundled = root / "official"
            for name in sync.SKILL_NAMES:
                skill = bundled / name
                (skill / "references").mkdir(parents=True)
                (skill / "SKILL.md").write_text("---\nname: " + name + "\n---\n", encoding="utf-8")
                (skill / "references" / "only.md").write_text("stale\n", encoding="utf-8")
            original_bundled = sync.BUNDLED_ROOT
            sync.BUNDLED_ROOT = bundled
            try:
                differences = sync.compare(source_root)
                self.assertTrue(all(not row["identical"] for row in differences.values()))
                sync.apply_update(source_root)
                differences = sync.compare(source_root)
                self.assertTrue(all(row["identical"] for row in differences.values()))
            finally:
                sync.BUNDLED_ROOT = original_bundled

    def test_sync_source_is_never_modified(self):
        sync = load_script("sync_official_skills")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_root = root / "source"
            for name in sync.SKILL_NAMES:
                skill = source_root / name
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text("---\nname: " + name + "\n---\n", encoding="utf-8")
            before = sync.snapshot(source_root)
            original_bundled = sync.BUNDLED_ROOT
            sync.BUNDLED_ROOT = root / "official"
            try:
                sync.apply_update(source_root)
            finally:
                sync.BUNDLED_ROOT = original_bundled
            self.assertEqual(before, sync.snapshot(source_root))


class ReviewWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.workspace = load_script("prepare_review_workspace")
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.out_root = self.root / "qa-roots"

    def tearDown(self):
        self.temp.cleanup()

    def make_zip(self, name="artifact.zip", payload=b"hello"):
        path = self.root / name
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("task/evaluate.py", payload)
        return path

    def run_prepare(self, artifact, model, session, task="auto2001", version="v37", root=None):
        args = argparse.Namespace(
            artifact=str(artifact), task_id=task, package_version=version, model=model,
            session_id=session, root=str(root or self.out_root),
            max_files=1000, max_total_bytes=10 * 1024 * 1024, max_file_bytes=10 * 1024 * 1024,
        )
        return self.workspace.prepare(args)

    def test_single_extraction_shared_and_session_isolation(self):
        artifact = self.make_zip()
        first = self.run_prepare(artifact, "gpt-5.6-sol", "sess-a")
        second = self.run_prepare(artifact, "doubao", "sess-b")
        self.assertFalse(first["reused_extraction"])
        self.assertTrue(second["reused_extraction"])
        self.assertEqual(first["workspace"], second["workspace"])
        self.assertEqual(first["extracted"], second["extracted"])
        self.assertNotEqual(first["review_dir"], second["review_dir"])
        workspace = Path(first["workspace"])
        self.assertEqual(len(list((workspace / "reviews").iterdir())), 2)
        self.assertFalse(list(workspace.glob(".extracting-*")))
        self.assertFalse((workspace / ".extract.lock").exists())
        manifest = json.loads((workspace / "workspace.json").read_text(encoding="utf-8"))
        for run_path in (workspace / "reviews").glob("*/run.json"):
            run = json.loads(run_path.read_text(encoding="utf-8"))
            self.assertEqual(run["artifact_sha256"], manifest["artifact_sha256"])
            self.assertIn("never inherit", run["context_policy"])

    def test_same_model_different_sessions_get_distinct_report_dirs(self):
        artifact = self.make_zip()
        first = self.run_prepare(artifact, "mimo-2.6-pro", "conv-1")
        second = self.run_prepare(artifact, "mimo-2.6-pro", "conv-2")
        self.assertTrue(second["reused_extraction"])
        self.assertEqual(first["workspace"], second["workspace"])
        self.assertNotEqual(first["review_dir"], second["review_dir"])
        self.assertIn("mimo-2.6-pro__conv-1", first["review_dir"])
        self.assertIn("mimo-2.6-pro__conv-2", second["review_dir"])

    def test_drift_fails_closed(self):
        artifact = self.make_zip()
        result = self.run_prepare(artifact, "model-a", "sess-a")
        target = Path(result["extracted"]) / "task" / "evaluate.py"
        target.write_bytes(b"tampered")
        verification = self.workspace.verify_workspace(result["workspace"])
        self.assertFalse(verification["valid"])
        self.assertTrue(verification["mismatches"])
        with self.assertRaisesRegex(ValueError, "drift"):
            self.run_prepare(artifact, "model-b", "sess-b")

    def test_unsafe_zip_is_rejected(self):
        path = self.root / "unsafe.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("../evil.txt", b"escape")
        with self.assertRaisesRegex(ValueError, "Unsafe ZIP path"):
            self.run_prepare(path, "model-a", "sess-a")
        self.assertFalse(any(self.out_root.rglob("extracted")))

    def test_new_artifact_hash_creates_new_workspace_and_rebinds_context(self):
        first_artifact = self.make_zip("first.zip", b"version one")
        second_artifact = self.make_zip("second.zip", b"version two")
        first = self.run_prepare(first_artifact, "model-a", "sess-a")
        second = self.run_prepare(second_artifact, "model-a", "sess-a")
        self.assertNotEqual(first["workspace"], second["workspace"])
        self.assertNotEqual(first["artifact_sha256"], second["artifact_sha256"])
        second_run = json.loads(Path(second["run_manifest"]).read_text(encoding="utf-8"))
        self.assertEqual(second_run["artifact_sha256"], second["artifact_sha256"])
        self.assertIn("Prior conversations are untrusted background only", second_run["context_policy"])

    def test_workspace_root_inside_source_directory_is_rejected(self):
        source = self.root / "source-dir"
        source.mkdir()
        (source / "evaluate.py").write_text("print(1)\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "outside"):
            self.run_prepare(source, "model-a", "sess-a", root=source / "qa")

    def test_cli_prepare_and_verify(self):
        artifact = self.make_zip()
        process = subprocess.run([
            sys.executable, str(SCRIPTS / "prepare_review_workspace.py"), "prepare",
            "--artifact", str(artifact), "--task-id", "auto2001", "--package-version", "v37",
            "--model", "cli-model", "--session-id", "cli-sess", "--root", str(self.out_root),
        ], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, (process.stdout or "") + (process.stderr or ""))
        result = json.loads(process.stdout)
        self.assertTrue(result["valid"])
        process = subprocess.run([
            sys.executable, str(SCRIPTS / "prepare_review_workspace.py"), "verify",
            "--workspace", result["workspace"],
        ], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, (process.stdout or "") + (process.stderr or ""))
        self.assertTrue(json.loads(process.stdout)["valid"])


if __name__ == "__main__":
    unittest.main()
