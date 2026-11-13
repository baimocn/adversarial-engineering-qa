"""Synthetic contract tests only: no task code, Docker or training is executed."""
import copy
import unittest

import implementation_review as qa
import resource_review
import test_implementation_review as fixtures
import test_audit_collection as collection_fixtures


class HardwareDeploymentIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ImplementationReviewTests()
        self.fixture.setUp()
        self.root = self.fixture.root

    def tearDown(self):
        self.fixture.tearDown()

    def run_review(self, mutate=None, config=None):
        if config:
            with (self.root / "task.toml").open("a") as stream:
                stream.write(config)
        review = self.fixture.review()
        if mutate:
            mutate(review)
        return qa.apply_review(self.fixture.report(), review, self.root)

    @staticmethod
    def statuses(report):
        return {r["id"]: r["status"] for r in report["checks"]}

    @staticmethod
    def gpu_review(review):
        resources = review["resource_review"]
        resources["hardware_review"]["task_type"] = "gpu"
        resources["estimate"] = {**resources["runs"][0], "gpu_count": 1, "gpu_type": "H20",
                                 "basis": "Target configuration and existing code support H20 feasibility."}

    def test_cpu_task_actual_agent_or_verifier_gpu_is_not_hidden_by_zero_estimate(self):
        for section in ("environment", "verifier.environment"):
            with self.subTest(section=section):
                original = (self.root / "task.toml").read_text()
                report = self.run_review(config=f'\n[{section}]\ngpus=1\ngpu_types=["H20"]\n')
                self.assertEqual(self.statuses(report)["QA15"], "fail")
                self.assertIn("CPU题不得增加GPU", report["resource_review"]["summary"])
                (self.root / "task.toml").write_text(original)

    def test_unknown_task_type_cannot_pass_resource_gate(self):
        report = self.run_review(lambda review: review["resource_review"].pop("hardware_review"))
        self.assertEqual(self.statuses(report)["QA15"], "manual")
        self.assertNotEqual(report["summary"]["decision"], "PASS")

    def test_gpu_target_and_hardware_review_pass(self):
        report = self.run_review(self.gpu_review, '\n[environment]\ngpus=1\ngpu_types=["H20", "L20"]\n')
        self.assertEqual(self.statuses(report)["QA15"], "pass")
        self.assertEqual(report["harbor"]["deployment_contract"]["status"], "pass")

    def test_mixed_candidates_share_deployment_and_resource_policy(self):
        report = self.run_review(self.gpu_review, '\n[environment]\ngpus=1\ngpu_types=["H20", "A100"]\n')
        self.assertEqual(self.statuses(report)["QA15"], "pass", report["resource_review"])
        self.assertEqual(report["harbor"]["deployment_contract"]["gpu_status"], "pass")
        self.assertFalse(report["harbor"]["deployment_contract"]["runtime_verified"])

    def test_existing_valid_selection_remains_accepted(self):
        def selected(review):
            self.gpu_review(review)
            choice = {"runner_supports_candidates": True, "project_accepts_candidates": True,
                      "selected_type": "H20", "fallback_types": ["H20"],
                      "summary": "Existing current runner chooses H20 with no A100 fallback.", "evidence": ["task.toml"]}
            review["harbor"]["gpu_selection"] = {"agent": choice, "verifier": dict(choice)}
        report = self.run_review(selected, '\n[environment]\ngpus=1\ngpu_types=["H20", "A100"]\n')
        self.assertEqual(self.statuses(report)["QA15"], "pass", report["resource_review"])
        self.assertEqual(report["harbor"]["deployment_contract"]["gpu_status"], "pass")

    def test_existing_current_bad_allocation_fails_both_resource_and_deployment(self):
        for role in ("agent", "verifier"):
            with self.subTest(role=role):
                def selected(review):
                    self.gpu_review(review)
                    review["harbor"]["gpu_selection"] = {role: {
                        "actual_type": "A100", "summary": "Existing current provider allocation is A100.",
                        "evidence": ["task.toml"]}}
                original = (self.root / "task.toml").read_text()
                report = self.run_review(selected, '\n[environment]\ngpus=1\ngpu_types=["H20", "A100"]\n')
                self.assertEqual((self.statuses(report)["QA15"], self.statuses(report)["QA17"]), ("fail", "fail"))
                self.assertIn("gpu_actual_unsupported", {row["code"] for row in report["harbor"]["deployment_contract"]["findings"]})
                (self.root / "task.toml").write_text(original)

    def test_unknown_provider_does_not_inherit_maso_capabilities(self):
        def mutate(review):
            review["harbor"]["deployment_profile"] = "mido-future"
        report = self.run_review(mutate, '\n[environment]\nstorage_mb=1024\nnetwork_mode="no-network"\n')
        deployment = report["harbor"]["deployment_contract"]
        self.assertEqual(deployment["config_status"], "pass")
        self.assertFalse(deployment["innerfield_compliant"])
        self.assertEqual(self.statuses(report)["QA17"], "pass")
        self.assertEqual([row["code"] for row in deployment["platform_findings"]], ["provider_unknown"])
        self.assertFalse(deployment["runtime_verified"])

    def test_source_unknown_platform_completes_h02_h03_qa05_without_runtime_claim(self):
        def mutate(review):
            review["harbor"].update(provider="unknown", deployment_profile="unknown", target_version="unknown", version_basis="unknown")
            review["harbor"].pop("capability_review")
        report = self.run_review(mutate, '\n[environment]\nstorage_mb=1024\nnetwork_mode="no-network"\n')
        statuses = self.statuses(report)
        self.assertEqual((statuses["QA05"], statuses["QA17"]), ("pass", "pass"))
        self.assertEqual([row["status"] for row in report["harbor"]["checks"]][1:3], ["pass", "pass"])
        self.assertEqual(report["harbor"]["platform_review"]["status"], "unverified")
        self.assertFalse(report["harbor"]["deployment_contract"]["runtime_verified"])

    def test_source_unknown_keeps_cpu_resource_contradiction_and_formal_hardware_gaps(self):
        def unknown(review):
            review["harbor"].update(provider="unknown", deployment_profile="unknown")
        original = (self.root / "task.toml").read_text()
        report = self.run_review(unknown, '\n[environment]\ngpus=1\ngpu_types=["H20"]\n')
        self.assertEqual(self.statuses(report)["QA15"], "fail")
        (self.root / "task.toml").write_text(original)
        for affected in (False, True):
            def unverified(review):
                unknown(review)
                review["resource_review"]["hardware_review"].update(score_comparability="unverified", affects_formal_scores=affected)
            report = self.run_review(unverified)
            self.assertEqual(self.statuses(report)["QA15"], "manual" if affected else "pass")
            self.assertEqual(report["resource_review"]["hardware_review"]["score_status"], "manual" if affected else "pass")

    def test_mido_does_not_bypass_project_cpu_gpu_policy(self):
        def mutate(review):
            review["harbor"]["deployment_profile"] = "mido-2026-11-03"
        report = self.run_review(mutate, '\n[environment]\ngpus=1\ngpu_types=["H20"]\n')
        self.assertEqual(self.statuses(report)["QA15"], "fail")
        self.assertIn("CPU题不得增加GPU", report["resource_review"]["summary"])

    def test_target_estimate_cannot_hide_unsupported_verifier_gpu(self):
        report = self.run_review(self.gpu_review,
            '\n[environment]\ngpus=1\ngpu_types=["H20"]\n[verifier.environment]\ngpus=1\ngpu_types=["A100"]\n')
        status = self.statuses(report)
        self.assertEqual((status["QA15"], status["QA17"]), ("fail", "fail"))
        self.assertEqual(report["harbor"]["checks"][1]["status"], "fail")

    def test_gpu_estimate_zero_or_unidentified_card_requires_review(self):
        for field, value in (("gpu_count", 0), ("gpu_type", None)):
            with self.subTest(field=field):
                def mutate(review):
                    self.gpu_review(review)
                    review["resource_review"]["estimate"][field] = value
                original = (self.root / "task.toml").read_text()
                report = self.run_review(mutate, '\n[environment]\ngpus=1\ngpu_types=["H20"]\n')
                self.assertEqual(self.statuses(report)["QA15"], "manual")
                (self.root / "task.toml").write_text(original)

    def test_generic_gpu_does_not_claim_innerfield_compliance(self):
        def mutate(review):
            self.gpu_review(review)
            review["resource_review"]["estimate"]["gpu_type"] = "A100"
            review["harbor"].update(deployment_profile="generic-harbor",
                deployment_basis={"summary": "Synthetic provider supports A100.", "evidence": ["task.toml"]})
        report = self.run_review(mutate, '\n[environment]\ngpus=1\ngpu_types=["A100"]\n')
        self.assertEqual(self.statuses(report)["QA15"], "pass")
        self.assertFalse(report["harbor"]["deployment_contract"]["innerfield_compliant"])
        self.assertIn("generic-harbor", qa.compact_markdown(report))

    def test_current_unsupported_constraint_controls_qa05_and_qa17(self):
        report = self.run_review(config='\n[environment]\nstorage_mb=1024\n')
        status = self.statuses(report)
        self.assertEqual((status["QA05"], status["QA17"]), ("fail", "fail"))
        self.assertIn("storage_mb", qa.compact_markdown(report))
        self.assertIn("目标部署能力", qa.compact_markdown(report))

    def test_unknown_capability_blocks_reviewed_pass(self):
        report = self.run_review(lambda review: review["harbor"].pop("capability_review"))
        status = self.statuses(report)
        self.assertEqual((status["QA05"], status["QA17"]), ("manual", "manual"))

    def test_current_network_fallback_blocks_qa05_and_h02(self):
        def mutate(review):
            review["harbor"]["capability_review"]["outcome"] = "network_fallback"
        report = self.run_review(mutate)
        self.assertEqual(self.statuses(report)["QA05"], "fail")
        self.assertEqual(report["harbor"]["checks"][1]["status"], "fail")

    def test_changed_hardware_only_propagates_for_affected_formal_scores(self):
        for affected in (False, True):
            for comparison, expected in (("reused_without_validation", "fail"), ("unverified", "manual"), ("revalidated", "pass")):
                with self.subTest(affected=affected, comparison=comparison):
                    def mutate(review):
                        review["resource_review"]["hardware_review"].update(
                            score_comparability=comparison, affects_formal_scores=affected)
                    report = self.run_review(mutate)
                    status = self.statuses(report)
                    self.assertEqual(status["QA15"], expected)
                    formal = expected if affected else "pass"
                    self.assertEqual((status["QA03"], status["QA13"]), (formal, formal))
                    gate = next(r for r in report["content_gates"]["checks"] if r["id"] == "G03")
                    self.assertEqual(gate["status"], formal)
                    if formal != "pass":
                        self.assertEqual(gate["reason_code"], "HARDWARE_SCORE_COMPARABILITY")

    def test_different_calibration_machine_does_not_invalidate_formal_scores(self):
        def mutate(review):
            self.gpu_review(review)
            resources = review["resource_review"]
            resources["runs"].append({**resources["runs"][0], "run_id": "calibration", "scope": "training",
                                      "gpu_type": "A100", "gpu_count": 1})
            resources["hardware_review"].update(affects_formal_scores=False,
                summary="A100 calibration only; target estimate uses H20, formal scores retain original hardware labels.")
        report = self.run_review(mutate, '\n[environment]\ngpus=1\ngpu_types=["H20"]\n')
        status = self.statuses(report)
        self.assertEqual([status[key] for key in ("QA03", "QA13", "QA15")], ["pass"] * 3)

    def test_affected_formal_paths_require_real_evidence_and_cannot_claim_unaffected(self):
        review = self.fixture.review()["resource_review"]
        hardware = review["hardware_review"]
        ref = "optimization_evidence/baseline_runs/seed_1/result.json"
        hardware.update(affected_formal_runs=[ref], score_comparability="unverified")
        current = resource_review.collect(self.root, qa.inventory(self.root))
        with self.assertRaises(ValueError):
            resource_review.apply_review(current, review, self.root, qa.review_evidence)
        path = self.root / ref
        path.parent.mkdir(parents=True)
        path.write_text('{}')
        result = resource_review.apply_review(current, review, self.root, qa.review_evidence)
        self.assertTrue(result["hardware_review"]["affects_formal_scores"])
        self.assertEqual(result["hardware_review"]["score_status"], "manual")
        hardware["affects_formal_scores"] = False
        with self.assertRaisesRegex(ValueError, "cannot be declared unaffected"):
            resource_review.apply_review(current, review, self.root, qa.review_evidence)


class DeploymentBatchConsistencyTests(unittest.TestCase):
    def test_pass_cannot_hide_deployment_or_hardware_defects(self):
        fixture = collection_fixtures.AuditCollectionTests()
        baseline = fixture.passing_report()
        for part in ("deployment", "findings", "hardware", "score", "old_schema"):
            with self.subTest(part=part):
                report = copy.deepcopy(baseline)
                if part == "deployment":
                    report["harbor"]["deployment_contract"]["status"] = "manual"
                elif part == "findings":
                    report["harbor"]["deployment_contract"]["findings"] = [{"status": "fail"}]
                elif part == "hardware":
                    report["resource_review"]["hardware_review"]["status"] = "manual"
                elif part == "score":
                    report["resource_review"]["hardware_review"]["score_status"] = "fail"
                else:
                    report["schema_version"] = 5
                self.assertTrue(collection_fixtures.COLLECTION.validate_report(report))


if __name__ == "__main__":
    unittest.main()
