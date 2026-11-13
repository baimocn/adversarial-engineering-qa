import json
from pathlib import Path
import tempfile
import unittest

import harbor_review as harbor
import task_fingerprint


def valid_review():
    """Reviewed fixture conclusions; tests check contracts, not semantic accuracy."""
    return {"target_version": "official-docs@2026-09-30", "version_basis": harbor.OFFICIAL_SOURCE,
            "path_contract": {"profile": "harbor-environment-v1", "profile_basis": harbor.OFFICIAL_SOURCE},
            "provider": "docker", "deployment_profile": "innerfield-maso-v1", "task_root": ".",
            "capability_review": {"status": "pass", "outcome": "not_required",
                "summary": "Synthetic task does not rely on unsupported constraints.", "evidence": ["task.toml"]},
            "hidden_review": {"mode": "prebuilt", "summary": "cases.json 仅进入 Verifier，由私有评分器读取。",
                              "evidence": ["tests/test.sh", "tests/Dockerfile"], "asset_paths": ["tests/hidden_assets/cases.json"]},
            "checks": [
                {"id": "H01", "status": "pass", "summary": "任务根目录、入口和测试数据存在。", "evidence": ["task.toml", "instruction.md", "tests/test.sh", "tests/hidden_assets/cases.json"]},
                {"id": "H02", "status": "pass", "summary": "已按目标模型阅读配置字段。", "evidence": ["task.toml"]},
                {"id": "H03", "status": "pass", "summary": "Agent 与 Verifier 分别由 Dockerfile 构建。", "evidence": ["environment/Dockerfile", "tests/Dockerfile"]},
                {"id": "H04", "status": "pass", "summary": "test.sh 写入标准 reward 文件。", "evidence": ["tests/test.sh"]},
                {"id": "H05", "status": "not_applicable", "summary": "单任务包未附批量调用配置。", "evidence": []},
                {"id": "H06", "status": "not_applicable", "summary": "未提供 Harness 运行记录，未进行实跑。", "evidence": []}]}


class HarborReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        (self.root / "task.toml").write_text('artifacts = ["/workspace/solution"]\n[metadata]\nname = "fixture"\n[verifier]\nenvironment_mode = "separate"\n')
        (self.root / "instruction.md").write_text("Fixture task")
        (self.root / "environment").mkdir()
        (self.root / "environment/Dockerfile").write_text("FROM python:3.11-slim\nWORKDIR /app\n")
        (self.root / "tests").mkdir()
        (self.root / "tests/Dockerfile").write_text("FROM python:3.11-slim\nCOPY . /tests\n")
        (self.root / "tests/test.sh").write_text("mkdir -p /logs/verifier\necho 1 > /logs/verifier/reward.txt\n")
        (self.root / "tests/hidden_assets").mkdir()
        (self.root / "tests/hidden_assets/cases.json").write_text('{"cases": [1]}')

    def tearDown(self):
        self.temp.cleanup()

    def facts(self):
        return harbor.collect(self.root, [p.relative_to(self.root).as_posix() for p in self.root.rglob('*') if p.is_file()])

    def apply(self, value):
        return harbor.apply_review(self.facts(), value, self.root)

    def trial_evidence(self, review):
        return harbor.validate_trial_evidence(self.root, review["checks"][5]["evidence"], self.root, review.get("trial_task_binding"))

    def test_runtime_compose_forces_h03_failure_despite_pass_and_unused(self):
        for directory in ("environment", "tests"):
            for name in harbor.docker_paths.COMPOSE_NAMES:
                for profile in ("innerfield-maso-v1", "generic-harbor"):
                    with self.subTest(directory=directory, name=name, profile=profile):
                        compose = self.root / directory / name
                        compose.write_text("services: {}\n")
                        review = valid_review()
                        review["deployment_profile"] = profile
                        review["deployment_basis"] = {"summary": "Explicit provider evidence.", "evidence": ["task.toml"]}
                        review["compose_review"] = {"selection": "unused", "roles": ["agent", "verifier"],
                            "summary": "Declared unused.", "evidence": ["task.toml"]}
                        result = self.apply(review)
                        self.assertEqual(result["checks"][2]["status"], "fail")
                        self.assertEqual(result["qa17_status"], "fail")
                        compose.unlink()

    def test_harbor_cited_explicit_locations_are_checked(self):
        review = valid_review()
        review["hidden_review"]["evidence"] = ["tests/hidden_assets/cases.json#cases[0]"]
        self.apply(review)
        for ref in ("tests/test.sh:999", "tests/hidden_assets/cases.json#absent"):
            with self.subTest(ref=ref):
                review["hidden_review"]["evidence"] = [ref]
                with self.assertRaises(ValueError):
                    self.apply(review)

    def test_inventory_is_not_a_pass(self):
        self.assertEqual(self.facts()["static_status"], "manual")
        self.assertEqual(self.facts()["observations"]["task_root"], ".")

    def test_static_pass_does_not_claim_execution(self):
        result = self.apply(valid_review())
        self.assertEqual(result["static_status"], "pass")
        self.assertEqual(result["runtime_status"], "not_required")
        self.assertEqual(result["qa17_status"], "pass")
        self.assertIsNone(result["trial_evidence"])
        self.assertNotIn("NOP", harbor.summary(result))

    def test_missing_six_part_review_cannot_pass(self):
        with self.assertRaises(ValueError):
            self.apply({})

    def test_unknown_version_cannot_pass_config_review(self):
        review = valid_review()
        review["target_version"] = "unknown"
        result = self.apply(review)
        self.assertEqual(result["static_status"], "pass")
        self.assertTrue(result["platform_review"]["version_basis_pending"])
        review["delivery_stage"] = "runtime_package"
        with self.assertRaises(ValueError):
            self.apply(review)

    def test_unknown_provider_cannot_pass_environment_review(self):
        review = valid_review()
        review["provider"] = "unknown"
        review["deployment_profile"] = "unknown"
        result = self.apply(review)
        self.assertEqual(result["static_status"], "pass")
        self.assertEqual(result["platform_review"]["status"], "unverified")
        self.assertFalse(result["platform_review"]["runtime_verified"])
        review["delivery_stage"] = "runtime_package"
        with self.assertRaises(ValueError):
            self.apply(review)

    def test_source_unknown_metadata_does_not_hide_real_path_or_config_failure(self):
        review = valid_review()
        review.update(provider="unknown", deployment_profile="unknown", target_version="unknown", version_basis="unknown")
        review.pop("capability_review")
        result = self.apply(review)
        self.assertEqual((result["checks"][1]["status"], result["checks"][2]["status"]), ("pass", "pass"))
        (self.root / "task.toml").write_text((self.root / "task.toml").read_text().replace('"separate"', '"shared"'))
        result = self.apply(review)
        self.assertEqual(result["checks"][1]["status"], "fail")
        self.assertEqual(result["static_status"], "fail")

    def test_reward_interface_failure_is_qa17_failure(self):
        review = valid_review()
        review["checks"][3]["status"] = "fail"
        review["checks"][3]["summary"] = "入口仅输出 stdout，未实现 reward 文件写入。"
        self.assertEqual(self.apply(review)["qa17_status"], "fail")

    def test_required_checks_cannot_be_skipped(self):
        review = valid_review()
        review["checks"][2]["status"] = "not_applicable"
        with self.assertRaises(ValueError):
            self.apply(review)

    def test_path_escape_rejected(self):
        review = valid_review()
        review["task_root"] = ".."
        with self.assertRaises(ValueError):
            self.apply(review)

    def test_explicit_path_profile_required(self):
        review = valid_review()
        del review["path_contract"]
        with self.assertRaisesRegex(ValueError, "profile"):
            self.apply(review)

    def test_wrong_teaching_dockerfile_cannot_be_overridden(self):
        review = valid_review()
        review["path_contract"]["profile"] = "teaching-task-root-v1"
        result = self.apply(review)
        self.assertEqual(result["checks"][2]["status"], "fail")
        self.assertEqual(result["qa17_status"], "fail")

    def test_fake_manual_resolution_reference_rejected(self):
        review = valid_review()
        review["path_contract"]["manual_resolution"] = {"summary": "已复核。", "evidence": ["missing.txt"]}
        with self.assertRaisesRegex(ValueError, "not a file"):
            self.apply(review)

    def test_manual_resolution_cannot_override_definite_failure(self):
        review = valid_review()
        review["path_contract"] = {"profile": "teaching-task-root-v1", "profile_basis": "fixture",
                                  "manual_resolution": {"summary": "口头声称可以运行。", "evidence": ["task.toml"]}}
        result = self.apply(review)
        self.assertEqual(result["checks"][2]["status"], "fail")

    def trial(self, value=1.25):
        folder = self.root / "run-a"
        (folder / "verifier").mkdir(parents=True)
        (folder / "config.json").write_text(json.dumps({"task": {"path": "fixture", "hash_profile": task_fingerprint.PROFILE,
            "task_content_sha256": task_fingerprint.fingerprint(self.root)["task_content_sha256"]}, "agent": {"name": "nop"}}))
        (folder / "result.json").write_text(json.dumps({"finished_at": "2026-09-08T06:00:00Z", "exception_info": None,
                                                     "agent_info": {"name": "nop"}, "verifier_environment_mode": "separate",
                                                     "verifier_result": {"rewards": {"reward": value}}}))
        (folder / "verifier/reward.txt").write_text(str(value))
        (folder / "trial.log").write_text("Fixture verifier completed")
        review = valid_review()
        review["checks"][5] = {"id": "H06", "status": "pass", "summary": "同一 trial 的结果与 reward 一致。",
                                "evidence": ["run-a/config.json", "run-a/result.json", "run-a/verifier/reward.txt", "run-a/trial.log"]}
        review["checks"][4] = {"id": "H05", "status": "pass", "summary": "已复核 NOP Trial 调用配置。",
                                "evidence": ["run-a/config.json"]}
        review["trial_task_binding"] = {"summary": "已人工核对 config.json 指向本题版本和任务配置。",
                                        "evidence": ["run-a/config.json", "task.toml"]}
        return review

    def test_above_one_reward_is_accepted(self):
        self.assertEqual(self.trial_evidence(self.trial(1.25))["rewards"], {"reward": 1.25})

    def test_negative_reward_is_not_harness_failure(self):
        self.assertEqual(self.trial_evidence(self.trial(-0.5))["rewards"], {"reward": -0.5})

    def test_reward_mismatch_rejected(self):
        review = self.trial()
        (self.root / "run-a/verifier/reward.txt").write_text("0.0")
        with self.assertRaisesRegex(ValueError, "disagree"):
            self.trial_evidence(review)

    def test_nan_rejected(self):
        review = self.trial(float('nan'))
        with self.assertRaises(ValueError):
            self.trial_evidence(review)

    def test_exception_cannot_be_successful_evidence(self):
        review = self.trial()
        path = self.root / "run-a/result.json"
        result = json.loads(path.read_text())
        result["exception_info"] = {"exception_type": "VerifierTimeoutError"}
        path.write_text(json.dumps(result))
        with self.assertRaisesRegex(ValueError, "exception_info"):
            self.trial_evidence(review)

    def test_fake_runtime_status_does_not_claim_scoring_success(self):
        review = valid_review()
        review["runtime_status"] = "verified"
        result = self.apply(review)
        self.assertEqual(result["runtime_status"], "not_required")
        self.assertIsNone(result["trial_evidence"])

    def test_reward_json_precedence(self):
        review = self.trial()
        (self.root / "run-a/verifier/reward.json").write_text('{"score":1.25,"status":"ok"}')
        review["checks"][5]["evidence"].append("run-a/verifier/reward.json")
        with self.assertRaisesRegex(ValueError, "disagree"):
            self.trial_evidence(review)

    def test_trial_reward_metadata_does_not_change_numeric_result_binding(self):
        review = self.trial()
        (self.root / "run-a/verifier/reward.json").write_text('{"score":1.25,"status":"ok"}')
        review["checks"][5]["evidence"].append("run-a/verifier/reward.json")
        path = self.root / "run-a/result.json"
        value = json.loads(path.read_text())
        value["verifier_result"]["rewards"] = {"score": 1.25}
        path.write_text(json.dumps(value))
        self.assertEqual(self.trial_evidence(review)["rewards"], {"score": 1.25})

    def test_missing_or_malformed_legacy_nop_does_not_gate_qa17(self):
        review = valid_review()
        review["checks"][5] = {"id": "H06", "status": "fail", "summary": "未交 NOP。", "evidence": ["missing-nop.json#bad"]}
        actual = self.apply(review)
        self.assertEqual(actual["checks"][5]["status"], "not_applicable")
        self.assertEqual(actual["qa17_status"], "pass")
        review["checks"].pop()
        self.assertEqual(self.apply(review)["qa17_status"], "pass")

    def test_generated_hidden_does_not_need_named_data_directory(self):
        review = valid_review()
        (self.root / "tests/generate.py").write_text("# fixed private generator; inspected, never executed")
        review["hidden_review"] = {"mode": "generated", "summary": "私有生成器按固定规则生成，由 test.sh 调用。",
                                  "evidence": ["tests/generate.py", "tests/test.sh"]}
        review["checks"][0]["evidence"] = ["task.toml", "tests/test.sh", "tests/generate.py"]
        (self.root / "tests/hidden_assets/cases.json").unlink()
        (self.root / "tests/hidden_assets").rmdir()
        self.assertEqual(self.apply(review)["checks"][0]["status"], "pass")

    def test_prebuilt_hidden_can_use_other_directory(self):
        review = valid_review()
        (self.root / "tests/private").mkdir()
        (self.root / "tests/hidden_assets/cases.json").rename(self.root / "tests/private/cases.json")
        review["checks"][0]["evidence"][-1] = "tests/private/cases.json"
        review["hidden_review"]["asset_paths"] = ["tests/private/cases.json"]
        self.assertEqual(self.apply(review)["checks"][0]["status"], "pass")

    def test_hidden_directory_alone_cannot_pass_without_review(self):
        review = valid_review()
        del review["hidden_review"]
        self.assertEqual(self.apply(review)["checks"][0]["status"], "manual")

    def test_injected_hidden_needs_real_configuration_evidence(self):
        review = valid_review()
        review["hidden_review"] = {"mode": "injected", "summary": "平台评分前注入私有数据。", "evidence": ["missing-mount.json"]}
        with self.assertRaisesRegex(ValueError, "not a file"):
            self.apply(review)

    def test_placeholder_is_not_prebuilt_hidden(self):
        review = valid_review()
        (self.root / "tests/hidden_assets/README.md").write_text("TODO data")
        review["hidden_review"]["asset_paths"] = ["tests/hidden_assets/README.md"]
        with self.assertRaisesRegex(ValueError, "actual data"):
            self.apply(review)

    def test_missing_and_mismatched_artifacts_cannot_pass(self):
        for prefix in ("", 'artifacts = ["/wrong/path"]\n', '[verifier.artifacts]\nsource = "/workspace/solution"\n'):
            with self.subTest(prefix=prefix):
                (self.root / "task.toml").write_text(prefix + '[verifier]\nenvironment_mode = "separate"\n')
                result = self.apply(valid_review())
                self.assertEqual(result["checks"][1]["status"], "fail")

    def test_default_artifacts_directory_needs_no_explicit_declaration(self):
        for prefix in ("", "artifacts = []\n"):
            with self.subTest(prefix=prefix):
                (self.root / "task.toml").write_text(prefix + '[verifier]\nenvironment_mode = "separate"\n')
                review = valid_review()
                review["submission_paths"] = ["/logs/artifacts", "/logs/artifacts/model/checkpoint.bin"]
                result = self.apply(review)
                self.assertEqual(result["artifact_contract"]["status"], "pass")
                self.assertIn("/logs/artifacts", result["artifact_contract"]["sources"])
                self.assertEqual(result["checks"][1]["status"], "pass")

    def test_mixed_default_and_extra_paths_need_explicit_extra_source(self):
        review = valid_review()
        review["submission_paths"] = ["/logs/artifacts/model.bin", "/workspace/solution"]
        (self.root / "task.toml").write_text('[verifier]\nenvironment_mode = "separate"\n')
        result = self.apply(review)["artifact_contract"]
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["uncovered"], ["/workspace/solution"])
        (self.root / "task.toml").write_text('artifacts = ["/workspace/solution"]\n[verifier]\nenvironment_mode = "separate"\n')
        self.assertEqual(self.apply(review)["artifact_contract"]["status"], "pass")

    def test_default_directory_does_not_mask_invalid_artifact_configuration(self):
        review = valid_review()
        review["submission_paths"] = ["/logs/artifacts/model.bin"]
        for value in ('"/logs/artifacts"', '{source="/logs/artifacts"}', '[4]', '[{destination="local"}]'):
            with self.subTest(value=value):
                (self.root / "task.toml").write_text('artifacts = ' + value + '\n[verifier]\nenvironment_mode = "separate"\n')
                self.assertEqual(self.apply(review)["artifact_contract"]["status"], "fail")

    def test_default_artifacts_path_is_not_a_text_prefix_match(self):
        review = valid_review()
        review["submission_paths"] = ["/logs/artifacts-other/model.bin"]
        (self.root / "task.toml").write_text('[verifier]\nenvironment_mode = "separate"\n')
        self.assertEqual(self.apply(review)["artifact_contract"]["status"], "fail")

    def test_extra_glob_does_not_block_already_covered_paths(self):
        (self.root / "task.toml").write_text('artifacts = ["/workspace/solution", "/other/*.bin"]\n[verifier]\nenvironment_mode = "separate"\n')
        result = self.apply(valid_review())["artifact_contract"]
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["ambiguous_extra_sources"])

    def test_artifact_destination_does_not_relocate_source(self):
        (self.root / "task.toml").write_text('artifacts = [{source = "/workspace/solution", destination = "other"}]\n[verifier]\nenvironment_mode = "separate"\n')
        result = self.apply(valid_review())
        self.assertEqual(result["artifact_contract"]["status"], "pass")

    def test_multiple_artifact_files_and_custom_submission_paths(self):
        (self.root / "task.toml").write_text('artifacts = ["/app/code.py", {source="/models/model.bin"}]\n[verifier]\nenvironment_mode = "separate"\n')
        review = valid_review()
        review["submission_paths"] = ["/app/code.py", "/models/model.bin"]
        self.assertEqual(self.apply(review)["artifact_contract"]["status"], "pass")

    def test_one_child_artifact_cannot_cover_whole_submission_directory(self):
        (self.root / "task.toml").write_text('artifacts = ["/workspace/solution/code.py"]\n[verifier]\nenvironment_mode = "separate"\n')
        self.assertEqual(self.apply(valid_review())["artifact_contract"]["status"], "fail")

    def test_documented_job_override_remains_manual(self):
        (self.root / "task.toml").write_text('[verifier]\nenvironment_mode = "separate"\n')
        (self.root / "job.yaml").write_text('artifacts: ["/workspace/solution"]')
        review = valid_review()
        review["artifact_override"] = {"summary": "目标版本 Job 指定有效 artifacts。", "evidence": ["job.yaml"]}
        self.assertEqual(self.apply(review)["checks"][1]["status"], "manual")

    def test_legacy_nop_agent_identity_is_outside_current_gate(self):
        review = self.trial()
        (self.root / "run-a/config.json").write_text("{bad")
        (self.root / "run-a/result.json").write_text("{bad")
        (self.root / "run-a/verifier/reward.txt").write_text("NaN")
        (self.root / "run-a/trial.log").write_text("")
        actual = self.apply(review)
        self.assertEqual(actual["qa17_status"], "pass")
        self.assertIsNone(actual["trial_evidence"])

    def mixed_trials(self):
        review = self.trial()
        nop_refs = review["checks"][5]["evidence"]
        candidate_refs = [ref.replace("run-a/", "run-b/") for ref in nop_refs]
        for source, target in zip(nop_refs, candidate_refs):
            target_path = self.root / target
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes((self.root / source).read_bytes())
        for filename, field in (("config.json", "agent"), ("result.json", "agent_info")):
            path = self.root / "run-b" / filename
            value = json.loads(path.read_text())
            value[field]["name"] = "oracle"
            path.write_text(json.dumps(value))
        return review, nop_refs, candidate_refs

    def test_legacy_nop_references_do_not_trigger_trial_inspection(self):
        from unittest.mock import patch
        review, nop_refs, candidate_refs = self.mixed_trials()
        for refs in (candidate_refs + nop_refs, nop_refs + candidate_refs):
            review["checks"][5]["evidence"] = refs
            with patch.object(harbor, "validate_trial_evidence", side_effect=AssertionError("retired NOP gate called")):
                actual = self.apply(review)
            self.assertEqual(actual["qa17_status"], "pass")
            self.assertIsNone(actual["trial_evidence"])

    def test_candidate_cannot_hide_nop_exception(self):
        review, nop_refs, candidate_refs = self.mixed_trials()
        path = self.root / "run-a/result.json"
        result = json.loads(path.read_text())
        result["exception_info"] = {"exception_type": "VerifierTimeoutError"}
        path.write_text(json.dumps(result))
        for refs in (candidate_refs + nop_refs, nop_refs + candidate_refs):
            with self.subTest(first=refs[0]):
                review["checks"][5]["evidence"] = refs
                with self.assertRaisesRegex(ValueError, "exception_info"):
                    self.trial_evidence(review)

    def test_candidate_cannot_complete_nop_with_another_trial_reward(self):
        review, nop_refs, candidate_refs = self.mixed_trials()
        nop_refs.remove("run-a/verifier/reward.txt")
        review["checks"][5]["evidence"] = candidate_refs + nop_refs
        with self.assertRaisesRegex(ValueError, "from the same trial"):
            self.trial_evidence(review)

    def test_candidate_cannot_hide_malformed_nop_result(self):
        review, nop_refs, candidate_refs = self.mixed_trials()
        (self.root / "run-a/result.json").write_text("{invalid json")
        review["checks"][5]["evidence"] = candidate_refs + nop_refs
        with self.assertRaises(json.JSONDecodeError):
            self.trial_evidence(review)

    def test_legacy_nop_needs_no_task_binding(self):
        review, nop_refs, candidate_refs = self.mixed_trials()
        del review["trial_task_binding"]
        review["checks"][5]["evidence"] = candidate_refs + nop_refs
        self.assertEqual(self.apply(review)["qa17_status"], "pass")

    def test_relocated_host_task_path_is_not_rejected(self):
        review = self.trial()
        config_path = self.root / "run-a/config.json"
        config = json.loads(config_path.read_text())
        config["task"]["path"] = "/unavailable/original/host/fixture"
        config_path.write_text(json.dumps(config))
        self.assertEqual(self.trial_evidence(review)["task_binding"]["status"], "pass")

    def test_same_name_without_version_binding_is_manual(self):
        review = self.trial()
        del review["trial_task_binding"]
        self.assertEqual(self.trial_evidence(review)["task_binding"]["status"], "manual")

    def test_legacy_trial_uses_reviewed_version_evidence_without_new_hash(self):
        review = self.trial()
        path = self.root / "run-a/config.json"
        value = json.loads(path.read_text())
        value["task"].pop("task_content_sha256")
        value["task"].pop("hash_profile")
        path.write_text(json.dumps(value))
        self.assertEqual(self.trial_evidence(review)["task_binding"]["status"], "pass")

    def test_other_task_cannot_be_hidden_by_weak_binding(self):
        review = self.trial()
        config_path = self.root / "run-a/config.json"
        config = json.loads(config_path.read_text())
        config["task"]["path"] = "/old/other-task"
        del config["task"]["task_content_sha256"]
        config_path.write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, "explicit cited mapping"):
            self.trial_evidence(review)

    def test_reviewed_explicit_task_rename_mapping_is_recorded(self):
        review = self.trial()
        config_path = self.root / "run-a/config.json"
        config = json.loads(config_path.read_text())
        config["task"]["path"] = "/old/other-task"
        config_path.write_text(json.dumps(config))
        (self.root / "provenance.txt").write_text("other-task was renamed to fixture; reviewer compared submission sources and task configuration.")
        review["trial_task_binding"]["evidence"].append("provenance.txt")
        actual = self.trial_evidence(review)
        self.assertEqual(actual["task_binding"]["basis"], "reviewed_evidence")
        self.assertFalse(actual["task_binding"]["authenticity_verified"])

    def test_hash_mismatch_cannot_be_overridden_by_manual_binding(self):
        review = self.trial()
        config_path = self.root / "run-a/config.json"
        config = json.loads(config_path.read_text())
        config["task"]["task_toml_sha256"] = "0" * 64
        config_path.write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, "hash disagrees"):
            self.trial_evidence(review)


class CompatibleRewardContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_dual_outputs_keep_json_precedence_without_new_gate(self):
        (self.root / "reward.txt").write_text("999")
        (self.root / "reward.json").write_text('{"accuracy": 0.8}')
        for stage in ("source", "runtime", "history"):
            with self.subTest(stage=stage):
                actual = harbor.current_reward_contract(self.root, stage=stage)
                self.assertNotEqual(actual["status"], "fail")
                self.assertEqual(Path(actual["selected_file"]).name, "reward.json")
                self.assertFalse(any(row["code"] in {"current_dual_reward", "source_reward_writers_unresolved"} for row in actual["findings"]))
                if stage != "source":
                    self.assertEqual(actual["main_score"], 0.8)
                    self.assertEqual(actual["main_score_key"], "accuracy")

    def test_selected_bad_json_is_not_hidden_by_finite_text_output(self):
        (self.root / "reward.txt").write_text("0.8")
        for raw in ('{"reward": NaN}', '{"reward": true}', '{"reward": "ok"}', '{"reward": 1, "reward": 2}'):
            with self.subTest(raw=raw):
                (self.root / "reward.json").write_text(raw)
                for stage in ("runtime", "history"):
                    with self.subTest(stage=stage):
                        actual = harbor.current_reward_contract(self.root, stage=stage)
                        self.assertEqual(actual["status"], "fail")
                        self.assertIsNone(actual["main_score"])

    def test_current_and_historical_unique_metric_allow_non_score_metadata(self):
        (self.root / "reward.txt").write_text("not a score")
        for raw, expected_key in (("{\"accuracy\":0.8,\"status\":\"ok\",\"details\":{\"valid\":true}}", "accuracy"),
                                  ("{\"reward\":0.8,\"status\":\"ok\"}", "reward")):
            (self.root / "reward.json").write_text(raw)
            for stage in ("runtime", "history"):
                with self.subTest(raw=raw, stage=stage):
                    actual = harbor.current_reward_contract(self.root, stage=stage)
                    self.assertEqual(actual["status"], "pass")
                    self.assertEqual(actual["main_score"], 0.8)
                    self.assertEqual(actual["main_score_key"], expected_key)

    def test_metadata_does_not_resolve_multiple_numeric_metrics(self):
        (self.root / "reward.json").write_text('{"accuracy":0.8,"latency":10,"status":"ok"}')
        for stage in ("runtime", "history"):
            with self.subTest(stage=stage):
                actual = harbor.current_reward_contract(self.root, stage=stage)
                self.assertEqual(actual["status"], "manual")
                self.assertIsNone(actual["main_score"])
                mapped = harbor.current_reward_contract(self.root, stage=stage, main_score_key="accuracy")
                self.assertEqual(mapped["main_score"], 0.8)

    def test_nested_duplicate_and_nonfinite_numbers_rejected_at_all_stages(self):
        for raw in ('{"accuracy":0.8,"metadata":{"x":1,"x":2}}',
                    '{"accuracy":0.8,"latency":1e999}', '{"reward":' + '9' * 400 + '}'):
            (self.root / "reward.json").write_text(raw)
            for stage in ("runtime", "history"):
                with self.subTest(raw=raw[:80], stage=stage):
                    self.assertEqual(harbor.current_reward_contract(self.root, stage=stage)["status"], "fail")


if __name__ == '__main__':
    unittest.main()
