"""Pure provider/stage, actual-card and reward regressions; no task execution."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import deployment_review as policy
import harbor_review
import test_audit_format_repair as format_fixtures

class ProviderPolicyTests(unittest.TestCase):
    def setUp(self):
        self.cfg = {"environment": {"gpus": 0, "network_mode": "no-network", "storage_mb": 1024}, "agent": {"network_mode": "no-network"}, "verifier": {"environment_mode": "separate", "network_mode": "public"}}
    def rows(self, profile=policy.MIDO, stage="source", cfg=None):
        return policy.config_findings(self.cfg if cfg is None else cfg, {"deployment_profile": profile, "delivery_stage": stage})
    def codes(self, **kw):
        return {r["code"]: r["status"] for r in self.rows(**kw)}
    def test_same_constraints_maso_rejected_mido_supported(self):
        old = self.codes(profile=policy.INNERFIELD)
        self.assertEqual(old["storage_unsupported"], "fail")
        self.assertEqual(old["network_constraint_unsupported"], "fail")
        self.assertFalse(self.rows())
    def test_unknown_does_not_default_to_maso_or_pass(self):
        for value in ("unknown", "mido-future"):
            self.assertEqual([(r["code"], r["status"]) for r in self.rows(value)], [("provider_unknown", "platform_pending")])
            self.assertEqual([(r["code"], r["status"]) for r in self.rows(value, stage="runtime")], [("provider_unknown", "manual")])
    def test_versioned_storage_and_network_rules_apply_to_both_roles_and_stages(self):
        cfg = {"environment": {"gpus": 0, "storage_mb": 1024, "network_mode": "allowlist", "allowed_hosts": ["data.test"], "docker_image": "registry/agent:v1"},
               "agent": {"network_mode": "allowlist", "allowed_hosts": ["data.test"]},
               "verifier": {"environment_mode": "separate", "network_mode": "no-network",
                            "environment": {"gpus": 0, "storage_mb": 2048, "network_mode": "no-network", "docker_image": "registry/verifier:v1"}}}
        for stage in ("source", "runtime"):
            with self.subTest(stage=stage):
                self.assertFalse(self.rows(stage=stage, cfg=cfg))
                old = self.codes(profile=policy.INNERFIELD, stage=stage, cfg=cfg)
                self.assertEqual(old["storage_unsupported"], "fail")
                self.assertEqual(old["network_constraint_unsupported"], "fail")
                unknown = self.rows(profile="mido-future", stage=stage, cfg=cfg)
                self.assertEqual([(row["code"], row["status"]) for row in unknown], [("provider_unknown", "platform_pending" if stage == "source" else "manual")])
    def test_mido_partial_support_does_not_become_maso_unsupported(self):
        self.cfg["agent"]["user"] = "researcher"
        rows = self.rows()
        self.assertEqual([(row["code"], row["status"]) for row in rows], [("runtime_user_unverified", "manual")])
        self.assertFalse(any("unsupported" in row["code"] for row in rows))
    def test_agent_must_preserve_network_but_verifier_can_override(self):
        self.cfg["agent"]["network_mode"] = "public"
        self.assertEqual(self.codes()["agent_network_override_mismatch"], "fail")
        self.cfg["agent"]["network_mode"] = "no-network"
        self.assertFalse(self.rows())
    def test_allowlist_order_is_not_boundary_difference(self):
        self.cfg["environment"].update(network_mode="allowlist", allowed_hosts=["a.test", "b.test"])
        self.cfg["agent"].update(network_mode="allowlist", allowed_hosts=["b.test", "a.test"])
        self.assertFalse(self.rows())
        self.cfg["agent"]["allowed_hosts"] = ["c.test"]
        self.assertEqual(self.codes()["agent_network_override_mismatch"], "fail")
    def test_invalid_or_ineffective_network_policy_fails(self):
        for mutation in ({"network_mode": "magic"}, {"network_mode": "allowlist", "allowed_hosts": []}, {"network_mode": "public", "allowed_hosts": ["a.test"]}):
            cfg = deepcopy(self.cfg)
            cfg["environment"].update(mutation)
            self.assertEqual(self.codes(cfg=cfg)["network_policy_invalid"], "fail")
    def test_unsupported_fields_are_not_silently_enabled(self):
        for section, name, value, code in [("environment", "os", "windows", "os_unsupported"), ("environment", "mcp_servers", [], "mido_field_unsupported"), ("environment", "skills_dir", "skills", "mido_field_unsupported"), ("environment", "tpu", {}, "mido_field_unsupported"), ("environment", "blocked_hosts", ["x"], "network_field_unsupported"), ("agent", "storage_mb", 100, "storage_wrong_phase")]:
            cfg = deepcopy(self.cfg)
            cfg[section][name] = value
            self.assertEqual(self.codes(cfg=cfg)[code], "fail", name)
        for field in ("mcp_servers", "skills_dir", "healthcheck"):
            cfg = deepcopy(self.cfg)
            cfg["verifier"]["environment"] = {field: {}}
            self.assertEqual(self.codes(cfg=cfg)["mido_field_unsupported"], "fail")
    def test_multistep_and_sidecars_unsupported(self):
        for key in ("steps", "multi_step_reward_strategy"):
            cfg = deepcopy(self.cfg)
            cfg[key] = []
            self.assertEqual(self.codes(cfg=cfg)["mido_multistep_unsupported"], "fail")
        self.cfg["artifacts"] = [{"source": "/data", "service": "db"}]
        self.assertEqual(self.codes()["compose_service_unsupported"], "fail")
    def test_source_dockerfile_vs_runtime_published_images(self):
        self.assertNotIn("published_image_required", self.codes())
        self.assertEqual(self.codes(stage="runtime")["published_image_required"], "fail")
        self.cfg["environment"]["docker_image"] = "registry/task:v1"
        self.assertNotIn("published_image_required", self.codes(stage="runtime"))
        self.cfg["verifier"]["environment"] = {}
        self.assertEqual(self.codes(stage="runtime")["published_image_required"], "fail")
    def test_partial_user_support_requires_image_review(self):
        self.cfg["agent"]["user"] = "missing-user"
        self.assertEqual(self.codes()["runtime_user_unverified"], "manual")

class GpuPolicyTests(unittest.TestCase):
    def setUp(self):
        self.env = {"gpus": 1, "gpu_types": ["H20", "A100"]}
        self.selection = {"runner_supports_candidates": True, "project_accepts_candidates": True, "selected_type": "H20", "fallback_types": ["H20"], "summary": "Existing runner selection excludes fallback to A100.", "evidence": ["allocation.log"]}
    def status(self, **kwargs):
        return policy.aggregate([r["status"] for r in policy.gpu_policy(self.env, kwargs.pop("selection", self.selection), **kwargs)])
    def test_source_feasible_mixed_candidates_pass_without_selection_record(self):
        self.assertEqual(self.status(selection={}), "pass")
        self.assertEqual(self.status(), "pass")
    def test_existing_rejection_or_unsupported_selection_still_fails(self):
        for key, value in (("project_accepts_candidates", False), ("runner_supports_candidates", False), ("fallback_types", ["H20", "A100"]), ("selected_type", "A100")):
            self.assertEqual(self.status(selection={**self.selection, key: value}), "fail")
        selected = deepcopy(self.selection)
        selected.pop("evidence")
        self.assertEqual(self.status(selection=selected), "pass")
    def test_source_existing_actual_unsupported_card_is_not_waived(self):
        for stage in ("source", "runtime"):
            self.assertEqual(self.status(stage=stage, selection={**self.selection, "actual_type": "A100"}), "fail")
    def test_runtime_needs_actual_card_and_evidence(self):
        self.assertEqual(self.status(stage="runtime"), "manual")
        self.assertEqual(self.status(stage="runtime", selection={**self.selection, "actual_type": "H20"}), "pass")
        self.assertEqual(self.status(stage="runtime", selection={**self.selection, "actual_type": "A100"}), "fail")
        self.assertEqual(self.status(stage="runtime", selection={"actual_type": "H20", "summary": "Existing allocation.", "evidence": ["allocation.log"]}), "pass")
        self.assertEqual(self.status(stage="runtime", selection={"actual_type": "H20"}), "manual")
    def test_approved_candidates_and_zero_gpu(self):
        self.env["gpu_types"] = ["H20", "L20"]
        self.assertEqual(self.status(selection={}), "pass")
        self.env["gpu_types"] = ["A100"]
        self.assertEqual(self.status(selection={}), "fail")
        self.env["gpus"] = 0
        self.assertEqual(self.status(selection={}), "pass")

class CurrentRewardContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def check(self, stage="runtime", **kw):
        return harbor_review.current_reward_contract(self.root, stage=stage, **kw)
    def test_either_file_individually_allowed(self):
        for name, text in (("reward.txt", ".25"), ("reward.json", '{"reward":0.25}')):
            path = self.root / name
            path.write_text(text)
            result = self.check()
            self.assertEqual(result["status"], "pass", result)
            self.assertEqual(result["main_score"], .25)
            path.unlink()
    def test_current_and_historical_dual_files_keep_json_priority(self):
        (self.root / "reward.txt").write_text(".1")
        (self.root / "reward.json").write_text('{"reward":0.25}')
        current = self.check()
        self.assertEqual(current["status"], "pass", current)
        self.assertEqual(current["main_score"], .25)
        self.assertEqual(Path(current["selected_file"]).name, "reward.json")
        old = self.check(stage="history")
        self.assertEqual(old["status"], "pass", old)
        self.assertEqual(old["main_score"], .25)
        self.assertTrue(old["historical_dual_file_compatible"])
        source = self.check(stage="source")
        self.assertEqual(source["status"], "manual")
        self.assertEqual(Path(source["selected_file"]).name, "reward.json")
        self.assertEqual([row["code"] for row in source["findings"]], ["reward_runtime_pending"])
    def test_source_two_possible_writers_are_not_actual_dual_outputs(self):
        result = harbor_review.current_reward_contract(output_paths=["/logs/verifier/reward.txt", "/logs/verifier/reward.json"], stage="source")
        self.assertEqual(result["status"], "manual")
    def test_identifiable_legacy_metric_or_existing_adapter(self):
        path = self.root / "reward.json"
        path.write_text('{"accuracy":0.8}')
        self.assertEqual(self.check()["main_score"], .8)
        path.write_text('{"accuracy":0.8,"latency":0.1}')
        self.assertEqual(self.check()["status"], "manual")
        self.assertEqual(self.check(main_score_key="accuracy")["main_score"], .8)
    def test_bad_main_score_duplicate_keys_and_nonfinite_fail(self):
        for raw in ('{"reward":true}', '{"reward":NaN}', '{"reward":1,"reward":2}', '{"reward":"0.5"}'):
            (self.root / "reward.json").write_text(raw)
            self.assertEqual(self.check()["status"], "fail", raw)

class FormatProviderConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = format_fixtures.FormatRepairTests()
        self.fixture.setUp()
    def tearDown(self):
        self.fixture.tearDown()
    def test_same_provider_rule_for_full_and_format(self):
        path = self.fixture.task / "task.toml"
        path.write_text(path.read_text().replace("gpus=0", 'gpus=0\nstorage_mb=1024\nnetwork_mode="no-network"'))
        review = self.fixture.review()
        review["deployment_profile"] = policy.MIDO
        review = self.fixture.review(resolve=True) | {"deployment_profile": policy.MIDO}
        self.assertEqual(self.fixture.assess(review)["decision"], "PASS_WITH_WAIVERS")
        review["deployment_profile"] = policy.INNERFIELD
        self.assertEqual(self.fixture.assess(review)["decision"], "FAIL")
        review["deployment_profile"] = "unknown"
        scan = format_fixtures.audit.inventory(self.fixture.root, review)
        self.assertFalse(any(x["code"] == "PROVIDER_UNKNOWN" for x in scan["semantic_observations"]))

    def test_source_mixed_candidates_pass_format_without_new_selection_logs(self):
        path = self.fixture.task / "task.toml"
        path.write_text(path.read_text().replace("gpus=0", 'gpus=1\ngpu_types=["A100","H20","L20"]'))
        (self.fixture.root / "optimization_evidence/old_A100_result.json").write_text('{"gpu":"A100","old_score":0.1}')
        for profile in (policy.INNERFIELD, policy.MIDO):
            with self.subTest(profile=profile):
                review = self.fixture.review(resolve=True) | {"task_type": "gpu", "deployment_profile": profile}
                scan = format_fixtures.audit.inventory(self.fixture.root, review)
                self.assertFalse(any("GPU" in row["code"] for row in scan["issues"] + scan["semantic_observations"]))
                result = self.fixture.assess(review)
                self.assertEqual(result["decision"], "PASS_WITH_WAIVERS", result)
                self.assertFalse(result["task_code_executed"])

    def test_source_existing_bad_actual_allocation_is_not_historical_waiver(self):
        path = self.fixture.task / "task.toml"
        path.write_text(path.read_text().replace("gpus=0", 'gpus=1\ngpu_types=["H20","A100"]'))
        for profile in (policy.INNERFIELD, policy.MIDO):
            for role in ("agent", "verifier"):
                with self.subTest(profile=profile, role=role):
                    review = self.fixture.review(resolve=True) | {"task_type": "gpu", "deployment_profile": profile,
                        "gpu_selection": {role: {"actual_type": "A100", "summary": "Existing current allocation is A100.",
                                                 "evidence": ["workspace/harbor_task/task.toml"]}}}
                    result = self.fixture.assess(review)
                    self.assertEqual(result["decision"], "FAIL", result)
                    self.assertTrue(any(row["code"] == "GPU_ACTUAL_UNSUPPORTED" for row in result["current_findings"]))

    def test_unknown_provider_requires_review_instead_of_claiming_supported_or_unsupported(self):
        path = self.fixture.task / "task.toml"
        path.write_text(path.read_text().replace("gpus=0", 'gpus=0\nstorage_mb=1024\nnetwork_mode="no-network"'))
        review = self.fixture.review(resolve=False) | {"deployment_profile": "mido-future"}
        scan = format_fixtures.audit.inventory(self.fixture.root, review)
        self.assertFalse(scan["issues"])
        self.assertNotIn("PROVIDER_UNKNOWN", {row["code"] for row in scan["semantic_observations"]})
        result = self.fixture.assess(review)
        self.assertEqual(result["decision"], "PASS_WITH_WAIVERS", result)

if __name__ == "__main__":
    unittest.main()
