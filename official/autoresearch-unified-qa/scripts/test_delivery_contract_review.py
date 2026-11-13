"""Synthetic trusted review fixtures; no expert program/container execution."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import delivery_contract_review as dr


class DeliveryContractReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.write("instruction.md", "# Objective\nMinimize latency on the formal hidden split.\nSubmit weights.npz and preserve the declared shape.\n")
        self.write("tests/grader.py", "BASELINE = 1.25\nUPPER = 0.0\ndef score(x):\n    return (x-BASELINE)/(UPPER-BASELINE)\n")
        self.write("tests/test.sh", "#!/bin/sh\npython grader.py\n")
        self.write("solution/solve.sh", "#!/bin/sh\nexec python /solution/oracle_impl.py\n")
        self.write("solution/oracle_impl.py", "# Oracle produces the normal submission artifact\n# Implementation is read, never executed\n")
        self.write("task.toml", '[environment]\ngpus=0\ncpus=4\n[verifier]\nenvironment_mode="separate"\ntimeout_sec=300\n')

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")
        return name

    def review(self):
        result = {"groups": {name: {"status": "pass", "summary": "Read the selected public/scorer contract and actual evidence for " + name,
            "evidence": ["instruction.md:1-3", "tests/grader.py:1-4"],
            "details": {key: {"summary": "The selected source concretely establishes " + key + " under this task's declared protocol",
                               "evidence": ["tests/grader.py:1-4"]} for key in dr.DETAILS[name]}, "findings": []}
            for name in dr.GROUPS}}
        protocol = result["groups"]["new_intake_protocol"]["details"]
        protocol["oracle_entry"].update(entry="solution/solve.sh", implementation_paths=["solution/oracle_impl.py"],
            summary="The required solution/solve.sh invokes the task-owned implementation inside solution/ to generate the normal submission", evidence=["solution/solve.sh:1-2", "solution/oracle_impl.py:1-2"])
        protocol["dependency_lock"].update(locked=True)
        protocol["formal_reward"].update(output_files=["/logs/verifier/reward.json"], json_main_key="reward")
        protocol["gate_penalty"].update(value=-10)
        return result

    def group(self, name, review=None, **kwargs):
        return next(row for row in dr.audit(self.root, review, **kwargs)["checks"] if row["name"] == name)

    def finding(self, **kwargs):
        finding = {"reason": "The evaluator enforces a 35 second per-call deadline which the public submission contract omits",
                   "remediation": "Publish the actual per-call deadline or align the evaluator with the published budget",
                   "evidence": ["tests/grader.py:1-4"], "blocking": True}
        finding.update(kwargs)
        return finding

    def batch(self, review=None, **values):
        review = review or self.review()
        review["groups"]["batch_acceptance"]["details"]["rollout_evidence"].update(
            score_valid=True, non_placeholder=True, normal_evaluation_completed=True,
            trajectory_review_passed=True, agent_timeout=False, verifier_timeout=False)
        review["groups"]["batch_acceptance"]["details"]["rollout_evidence"].update(values)
        return review

    def scored(self, value=0, **values):
        review = self.batch(**values)
        self.write("trial-a/reward.json", {"reward": value})
        review["reward_runs"] = [{"files": ["trial-a/reward.json"], "trial_id": "trial-a"}]
        return review

    def test_default_protocol_is_required_unreviewed_and_runtime_alone_is_optional(self):
        result = dr.audit(self.root)
        self.assertFalse(result["executed_task"])
        self.assertEqual(result["version"], "0.5.0-current.1")
        self.assertEqual([row["name"] for row in result["checks"]], list(dr.GROUPS))
        self.assertTrue(all(row["status"] == "unreviewed" for row in result["checks"][:4]))
        self.assertEqual(result["checks"][4]["status"], "not_applicable")
        self.assertEqual(result["checks"][5]["status"], "unreviewed")
        self.assertTrue(result["checks"][5]["required_for_static_completion"])
        self.assertEqual(result["claims"]["runtime"]["status"], "not_applicable")
        self.assertFalse(result["claims"]["static"]["review_complete"])

    def test_template_has_exact_groups_and_minimum_details(self):
        template = dr.template()
        self.assertEqual(set(template["groups"]), set(dr.GROUPS))
        for name, keys in dr.DETAILS.items():
            self.assertEqual(set(template["groups"][name]["details"]), set(keys))
        result = dr.audit(self.root, template)
        self.assertEqual(result["claims"]["static"]["status"], "unreviewed")

    def test_concrete_complete_source_review_passes_without_runtime(self):
        result = dr.audit(self.root, self.review())
        self.assertEqual(result["claims"]["static"], {"status": "pass", "review_complete": True})
        self.assertFalse(result["errors"])
        self.assertEqual(result["claims"]["runtime"]["status"], "not_applicable")

    def test_no_task_import_or_execution(self):
        marker = self.root / "executed"
        self.write("tests/grader.py", "from pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('bad')\nraise RuntimeError('do not execute')\n# line 4\n")
        with mock.patch("subprocess.run", side_effect=AssertionError("execution forbidden")):
            dr.audit(self.root, self.review())
        self.assertFalse(marker.exists())

    def test_generic_summary_is_not_a_complete_review(self):
        review = self.review()
        review["groups"]["task_contract"]["summary"] = "PASS"
        row = self.group("task_contract", review)
        self.assertFalse(row["review_complete"])
        self.assertEqual(row["status"], "unreviewed")

    def test_missing_minimum_subitem_is_internal_schema_error(self):
        review = self.review()
        del review["groups"]["task_contract"]["details"]["enforced_constraints"]
        result = dr.audit(self.root, review)
        self.assertTrue(any(error["required"] and "enforced_constraints" in error["error"] for error in result["errors"]))
        self.assertFalse(next(row for row in result["checks"] if row["name"] == "task_contract")["review_complete"])

    def test_generic_detail_is_rejected(self):
        review = self.review()
        review["groups"]["image_dependency_fit"]["details"]["judge"]["summary"] = "reviewed"
        self.assertFalse(self.group("image_dependency_fit", review)["review_complete"])

    def test_existing_material_gap_is_completed_evidence_limited(self):
        review = self.review()
        item = review["groups"]["infra_capabilities"]["details"]["environment_compatibility"]
        item.update(status="evidence_limited", summary="The selected source calls Landlock but the provided source-stage bundle contains no actual target-environment compatibility log")
        row = self.group("infra_capabilities", review)
        self.assertEqual(row["status"], "evidence_limited")
        self.assertTrue(row["review_complete"])
        self.assertFalse(row["problems"])

    def test_missing_cited_file_is_internal_error_not_author_failure(self):
        review = self.review()
        review["groups"]["task_contract"]["evidence"] = ["absent.md:1"]
        row = self.group("task_contract", review)
        self.assertEqual(row["status"], "unreviewed")
        self.assertFalse(row["problems"])

    def test_bare_failure_and_bare_finding_are_rejected(self):
        review = self.review()
        review["groups"]["task_contract"]["status"] = "fail"
        self.assertEqual(self.group("task_contract", review)["status"], "unreviewed")
        review["groups"]["task_contract"]["findings"] = [self.finding(evidence=["tests/grader.py"])]
        self.assertEqual(self.group("task_contract", review)["status"], "unreviewed")

    def test_findings_need_explicit_blocking_and_fixed_owner(self):
        review = self.review()
        failure = self.finding()
        del failure["blocking"]
        review["groups"]["task_contract"]["findings"] = [failure]
        self.assertFalse(self.group("task_contract", review)["review_complete"])

    def test_valid_findings_survive_an_invalid_sibling_in_either_order(self):
        for reverse in (False, True):
            review = self.review()
            values = [self.finding(code="confirmed.deadline"), self.finding(evidence=["absent.py:1"])]
            review["groups"]["task_contract"]["findings"] = values[::-1] if reverse else values
            result = dr.audit(self.root, review)
            row = next(row for row in result["checks"] if row["name"] == "task_contract")
            self.assertEqual(row["status"], "fail")
            self.assertFalse(row["review_complete"])
            self.assertEqual([value["code"] for value in row["findings"]], ["confirmed.deadline"])
            self.assertEqual(len(row["problems"]), 1)
            self.assertTrue(result["errors"])
            self.assertEqual(result["claims"]["static"]["status"], "fail")

    def test_valid_finding_survives_unrelated_group_schema_error(self):
        review = self.review()
        review["groups"]["task_contract"]["findings"] = [self.finding(code="confirmed.deadline")]
        del review["groups"]["task_contract"]["details"]["completion_conditions"]
        row = self.group("task_contract", review)
        self.assertEqual(row["status"], "fail")
        self.assertFalse(row["review_complete"])
        self.assertEqual(row["problems"][0]["code"], "confirmed.deadline")

    def test_valid_advisory_survives_schema_error_without_becoming_failure(self):
        review = self.review()
        review["groups"]["task_contract"]["findings"] = [self.finding(blocking=False)]
        review["groups"]["task_contract"]["summary"] = "pass"
        row = self.group("task_contract", review)
        self.assertEqual(row["status"], "unreviewed")
        self.assertEqual(len(row["advisories"]), 1)
        self.assertFalse(row["problems"])
        review["groups"]["task_contract"]["findings"] = [self.finding(owner_id="QA02")]
        self.assertFalse(self.group("task_contract", review)["review_complete"])

    def test_confirmed_contract_finding_has_code_owner_and_related_checks(self):
        review = self.review()
        review["groups"]["task_contract"]["findings"] = [self.finding()]
        row = self.group("task_contract", review)
        self.assertEqual(row["status"], "fail")
        self.assertTrue(row["review_complete"])
        self.assertEqual(row["problems"][0]["owner_id"], "QA11")
        self.assertTrue(row["problems"][0]["code"].startswith("delivery.task_contract."))
        self.assertEqual(row["problems"][0]["related_checks"], dr.RELATED["task_contract"])

    def test_static_patterns_are_only_positioned_observations(self):
        self.write("tests/constraints.py", "import ast\nif weights.ndim > 2:\n    raise ValueError('shape')\n# Landlock CUDA bwrap timeout=35\n")
        result = dr.audit(self.root)
        self.assertTrue(any(observation["kind"] == "array_constraint_location" and observation["ref"] == "tests/constraints.py:2" for observation in result["observations"]))
        self.assertFalse(any(row["status"] == "fail" for row in result["checks"]))

    def test_hardware_records_missing_do_not_automatically_fail(self):
        review = self.review()
        review["groups"]["normalization_anchors"]["details"]["hardware_calibration"].update(
            status="evidence_limited", hardware_sensitive=True,
            summary="The latency scorer is identified, but this source archive does not contain the old hardware route record; no actual mismatch is established")
        row = self.group("normalization_anchors", review)
        self.assertEqual(row["status"], "evidence_limited")
        self.assertFalse(row["problems"])

    def test_confirmed_hardware_sensitive_anchor_mismatch_fails_even_legacy(self):
        review = self.review()
        review["groups"]["normalization_anchors"]["details"]["hardware_calibration"].update(
            hardware_sensitive=True, hardware_mismatch_confirmed=True, formal_anchor_reused=True, target_protocol_calibrated=False,
            summary="The formal latency scorer still consumes the historical ARM baseline constant while its actual selected execution is on x86")
        row = self.group("normalization_anchors", review, context={"intake_cohort": "legacy_831"})
        self.assertEqual(row["status"], "fail")
        self.assertEqual(row["problems"][0]["owner_id"], "QA02")

    def test_different_split_numbers_are_not_subtracted(self):
        review = self.review()
        detail = review["groups"]["normalization_anchors"]["details"]["protocol_binding"]
        detail.update(summary="Historical hidden B=1.25 and current public starter=0.2 come from different splits; they do not establish a paired acceleration ratio",
                      historical_split="hidden", current_split="public", historical_value=1.25, current_value=0.2)
        row = self.group("normalization_anchors", review)
        self.assertFalse(row["problems"])
        self.assertNotIn("difference", row["details"]["protocol_binding"])

    def test_cpu_heavy_cuda_base_is_high_priority_advisory(self):
        review = self.review()
        review["groups"]["image_dependency_fit"]["findings"] = [self.finding(
            category="unnecessary_heavy_base", priority="low", owner_id="QA15",
            reason="Both selected CPU-only roles use an unnecessary CUDA-heavy base image",
            remediation="Choose a reproducible CPU base with the actual required numerical dependencies")]
        row = self.group("image_dependency_fit", review)
        self.assertEqual(row["status"], "pass")
        self.assertFalse(row["problems"])
        self.assertEqual(row["advisories"][0]["priority"], "high")
        self.assertFalse(row["advisories"][0]["blocking"])

    def test_infra_existing_public_dev_failure_can_fail(self):
        self.write("public-dev.log", "Landlock initialization failed: kernel does not support required ABI\n")
        review = self.review()
        review["groups"]["infra_capabilities"]["findings"] = [self.finding(
            evidence=["public-dev.log:1"], reason="Existing public Dev startup stops at its mandatory Landlock setup before evaluating a legal candidate",
            remediation="Use a supported target environment or an effective isolation path for the public Dev entry")]
        row = self.group("infra_capabilities", review)
        self.assertEqual(row["status"], "fail")
        self.assertEqual(row["problems"][0]["owner_id"], "H03")

    def test_read_limits_are_observation_only_and_large_cited_evidence_works(self):
        self.write("public-dev.log", "first line\n" + "x" * (5 * 1024 * 1024) + "\n")
        review = self.review()
        review["groups"]["infra_capabilities"]["evidence"].append("public-dev.log:1")
        result = dr.audit(self.root, review)
        self.assertTrue(result["collection_limitations"])
        self.assertFalse(result["errors"])
        self.assertEqual(next(row for row in result["checks"] if row["name"] == "infra_capabilities")["status"], "pass")

    def test_large_json_pointer_evidence_does_not_hit_small_collector_limit(self):
        self.write("run-result.json", {"padding": "x" * (5 * 1024 * 1024), "evidence": {"route": "cpu"}})
        review = self.review()
        review["groups"]["image_dependency_fit"]["evidence"].append("run-result.json#/evidence/route")
        self.assertEqual(self.group("image_dependency_fit", review)["status"], "pass")

    def test_scored_required_no_score_records_coverage_without_new_completion_gate(self):
        result = dr.audit(self.root, self.batch(), context={"rollout_policy": "scored_required"})
        self.assertEqual(result["claims"]["runtime"]["status"], "evidence_limited")
        self.assertIsNone(result["claims"]["admission"]["admitted"])
        self.assertEqual(next(row for row in result["checks"] if row["name"] == "batch_acceptance")["status"], "pass")
        self.assertFalse(next(row for row in result["checks"] if row["name"] == "batch_acceptance")["required_for_static_completion"])
        self.assertEqual(result["claims"]["static"]["status"], "pass")
        self.assertFalse(result["errors"])

    def test_all_unreadable_run_references_leave_score_existence_unknown(self):
        review = self.batch()
        review["reward_runs"] = [{"files": ["absent/reward.json"], "trial_id": "absent"}]
        result = dr.audit(self.root, review, context={"rollout_policy": "scored_required"})
        self.assertIsNone(result["claims"]["runtime"]["has_score"])
        self.assertTrue(result["errors"])
        self.assertFalse(result["claims"]["runtime"]["verifier_verified"])

    def test_reliable_score_fact_survives_an_unreadable_other_run(self):
        review = self.scored(0.2)
        review["reward_runs"].append({"files": ["absent/reward.json"], "trial_id": "absent"})
        result = dr.audit(self.root, review, context={"rollout_policy": "scored_required"})
        self.assertTrue(result["claims"]["runtime"]["has_score"])
        self.assertEqual(result["claims"]["runtime"]["reward_runs"][0]["main_score"], 0.2)
        self.assertFalse(result["claims"]["runtime"]["verifier_verified"])

    def test_source_only_explicit_runtime_outputs_require_the_existing_review(self):
        review = self.scored(0.2)
        del review["groups"]["batch_acceptance"]
        result = dr.audit(self.root, review, context={"rollout_policy": "source_only"})
        row = next(row for row in result["checks"] if row["name"] == "batch_acceptance")
        self.assertTrue(row["required_for_static_completion"])
        self.assertFalse(row["review_complete"])
        self.assertEqual(result["claims"]["static"]["status"], "unreviewed")
        self.assertTrue(result["claims"]["runtime"]["has_score"])

    def test_explicit_historical_run_cannot_prove_current_scored_verifier(self):
        for cohort in ("legacy_831", "new_1104"):
            review = self.scored(0.2)
            review["reward_runs"][0]["historical"] = True
            result = dr.audit(self.root, review, context={"intake_cohort": cohort, "rollout_policy": "scored_required"})
            self.assertTrue(result["claims"]["runtime"]["has_score"])
            self.assertEqual(result["claims"]["runtime"]["reward_runs"][0]["scope"], "history")
            self.assertFalse(result["claims"]["runtime"]["verifier_verified"])
            self.assertIsNone(result["claims"]["admission"]["admitted"])
            self.assertEqual(result["claims"]["runtime"]["status"], "evidence_limited")

    def test_native_scope_history_maps_without_mutating_selected_review(self):
        review = self.scored(0.2)
        review["reward_runs"][0]["scope"] = "history"
        before = copy.deepcopy(review)
        result = dr.audit(self.root, review, context={"rollout_policy": "scored_required"})
        self.assertEqual(review, before)
        run = result["claims"]["runtime"]["reward_runs"][0]
        self.assertEqual(run["scope"], "history")
        self.assertEqual(run["declared_scope"], "history")
        self.assertTrue(result["claims"]["runtime"]["has_score"])
        self.assertFalse(result["claims"]["runtime"]["verifier_verified"])
        self.assertIsNone(result["claims"]["admission"]["admitted"])

    def test_scope_and_historical_contradictions_are_internal_selection_errors(self):
        for update in ({"scope": "history", "historical": False}, {"scope": "runtime", "historical": True}):
            review = self.scored(0.2)
            review["reward_runs"][0].update(update)
            result = dr.audit(self.root, review, context={"rollout_policy": "scored_required"})
            self.assertTrue(any("conflicts" in error["error"] for error in result["errors"]))
            self.assertEqual(result["claims"]["runtime"]["status"], "unreviewed")
            self.assertFalse(result["claims"]["runtime"]["verifier_verified"])

    def test_unknown_scope_preserves_score_fact_but_cannot_certify_current_runtime(self):
        for scope in ("custom-adapter-scope", None, {"external": "adapter"}):
            review = self.scored(0.2)
            review["reward_runs"][0]["scope"] = scope
            result = dr.audit(self.root, review, context={"rollout_policy": "scored_required"})
            self.assertFalse(result["errors"])
            self.assertTrue(result["claims"]["runtime"]["has_score"])
            self.assertEqual(result["claims"]["runtime"]["reward_runs"][0]["declared_scope"], scope)
            self.assertEqual(result["claims"]["runtime"]["reward_runs"][0]["scope"], "unknown")
            self.assertFalse(result["claims"]["runtime"]["verifier_verified"])
            self.assertIsNone(result["claims"]["admission"]["admitted"])

    def test_explicit_runtime_scope_and_false_historical_can_verify_actual_current_run(self):
        review = self.scored(0.2)
        review["reward_runs"][0].update(scope="runtime", historical=False)
        result = dr.audit(self.root, review, context={"rollout_policy": "scored_required"})
        self.assertFalse(result["errors"])
        self.assertTrue(result["claims"]["runtime"]["verifier_verified"])

    def test_unknown_scope_invalid_output_is_not_mislabeled_current_failure(self):
        review = self.scored(0.2)
        self.write("trial-a/reward.json", {"reward": True})
        review["reward_runs"][0]["scope"] = "external-unknown"
        result = dr.audit(self.root, review, context={"rollout_policy": "scored_required"})
        row = next(row for row in result["checks"] if row["name"] == "batch_acceptance")
        self.assertFalse(row["problems"])
        self.assertFalse(result["claims"]["runtime"]["verifier_verified"])

    def test_run_historical_flag_and_trial_identity_are_typed_internal_fields(self):
        for update in ({"historical": "false"}, {"trial_id": True}, {"trial_id": ""}):
            review = self.scored(0.2)
            review["reward_runs"][0].update(update)
            result = dr.audit(self.root, review, context={"rollout_policy": "scored_required"})
            self.assertTrue(result["errors"])
            self.assertEqual(result["claims"]["runtime"]["status"], "unreviewed")
            self.assertIsNone(result["claims"]["runtime"]["has_score"])

    def test_native_integer_trial_identity_matches_string_without_losing_fact_type(self):
        review = self.scored(0.2, selected_trial="7")
        review["reward_runs"][0]["trial_id"] = 7
        result = dr.audit(self.root, review, context={"rollout_policy": "scored_required"})
        self.assertTrue(result["claims"]["runtime"]["verifier_verified"])
        self.assertEqual(result["claims"]["runtime"]["reward_runs"][0]["trial_id"], 7)
        review["groups"]["batch_acceptance"]["details"]["rollout_evidence"]["selected_trial"] = 7
        result = dr.audit(self.root, review, context={"rollout_policy": "scored_required"})
        self.assertTrue(result["claims"]["runtime"]["verifier_verified"])
        self.assertEqual(result["claims"]["runtime"]["selected_trial"], 7)

    def test_selected_current_invalid_reward_is_preserved_as_shared_owner_finding(self):
        for output in ({"reward": True}, {"note": "failed"}, ""):
            review = self.scored(0.2)
            self.write("trial-a/reward.json", output)
            result = dr.audit(self.root, review, context={"rollout_policy": "scored_required"})
            row = next(row for row in result["checks"] if row["name"] == "batch_acceptance")
            self.assertEqual(row["status"], "fail")
            self.assertTrue(row["review_complete"])
            self.assertEqual(row["problems"][0]["code"], "runtime.selected_current_reward_invalid")
            self.assertEqual(row["problems"][0]["responsibility"], "author_or_platform")
            self.assertEqual(result["claims"]["runtime"]["reward_runs"][0]["status"], "fail")
            self.assertFalse(result["claims"]["admission"]["admitted"])
            self.assertFalse(result["claims"]["runtime"]["verifier_verified"])

    def test_invalid_historical_reward_does_not_become_current_output_failure(self):
        review = self.scored(0.2)
        self.write("trial-a/reward.json", {"reward": True})
        review["reward_runs"][0]["historical"] = True
        result = dr.audit(self.root, review, context={"rollout_policy": "scored_required"})
        row = next(row for row in result["checks"] if row["name"] == "batch_acceptance")
        self.assertFalse(row["problems"])
        self.assertEqual(row["status"], "pass")
        self.assertEqual(result["claims"]["runtime"]["status"], "evidence_limited")

    def test_no_score_timeout_in_source_or_runtime_does_not_raise_h04(self):
        for stage in ("source", "runtime"):
            for policy in ("source_only", "scored_required"):
                review = self.batch(agent_timeout=True, normal_evaluation_completed=False)
                result = dr.audit(self.root, review, context={"package_stage": stage, "rollout_policy": policy})
                row = next(row for row in result["checks"] if row["name"] == "batch_acceptance")
                self.assertEqual(row["status"], "pass")
                self.assertTrue(row["review_complete"])
                self.assertFalse(row["required_for_static_completion"])
                self.assertFalse(row["problems"])
                self.assertEqual(result["claims"]["static"]["status"], "pass")
                self.assertFalse(result["claims"]["runtime"]["verifier_verified"])

    def test_runtime_stage_without_selected_outputs_or_batch_review_is_optional(self):
        review = self.review()
        del review["groups"]["batch_acceptance"]
        result = dr.audit(self.root, review, context={"package_stage": "runtime"})
        row = next(row for row in result["checks"] if row["name"] == "batch_acceptance")
        self.assertEqual(result["context"]["standard"], "current")
        self.assertEqual(row["status"], "not_applicable")
        self.assertTrue(row["review_complete"])
        self.assertFalse(row["required_for_static_completion"])
        self.assertEqual(result["claims"]["static"]["status"], "pass")
        self.assertEqual(result["claims"]["runtime"]["status"], "not_applicable")
        self.assertIn("No-score alone", result["claims"]["admission"]["basis"])

    def test_reviewed_no_score_limitation_without_outputs_does_not_add_required_materials(self):
        for stage in ("source", "runtime"):
            review = self.batch(agent_timeout=True)
            review["groups"]["batch_acceptance"].update(status="evidence_limited",
                summary="The existing one-hour Agent trace timed out without a final score; Verifier availability is unverified")
            review["groups"]["batch_acceptance"]["details"]["rollout_evidence"]["status"] = "evidence_limited"
            result = dr.audit(self.root, review, context={"package_stage": stage, "rollout_policy": "scored_required"})
            row = next(row for row in result["checks"] if row["name"] == "batch_acceptance")
            self.assertEqual(row["status"], "evidence_limited")
            self.assertFalse(row["required_for_static_completion"])
            self.assertTrue(row["review_complete"])
            self.assertEqual(result["claims"]["static"]["status"], "pass")
            self.assertFalse(result["errors"])

    def test_policy_hold_does_not_ignore_provided_reward_outputs_needing_review(self):
        review = self.scored(0.2)
        del review["groups"]["batch_acceptance"]
        result = dr.audit(self.root, review, context={"package_stage": "runtime", "rollout_policy": "scored_required"})
        row = next(row for row in result["checks"] if row["name"] == "batch_acceptance")
        self.assertTrue(row["required_for_static_completion"])
        self.assertFalse(row["review_complete"])
        self.assertEqual(result["claims"]["static"]["status"], "unreviewed")

    def test_real_blocking_batch_defect_without_reward_outputs_still_fails_static(self):
        review = self.batch(agent_timeout=True)
        review["groups"]["batch_acceptance"]["findings"] = [self.finding(
            owner_id="H04", reason="The selected verifier entry reads a different submission path than the declared handoff artifact",
            remediation="Align the actual verifier reader with the submitted handoff artifact and validate that binding")]
        result = dr.audit(self.root, review, context={"rollout_policy": "scored_required"})
        row = next(row for row in result["checks"] if row["name"] == "batch_acceptance")
        self.assertEqual(row["status"], "fail")
        self.assertEqual(len(row["problems"]), 1)
        self.assertTrue(row["required_for_static_completion"])
        self.assertEqual(result["claims"]["static"]["status"], "fail")

    def test_old_historical_score_provides_no_admission_exception(self):
        review = self.scored(0.2)
        review["reward_runs"][0]["historical"] = True
        result = dr.audit(self.root, review, context={"intake_cohort": "legacy_831", "rollout_policy": "historical_1h"})
        self.assertIsNone(result["claims"]["admission"]["admitted"])
        self.assertFalse(result["claims"]["admission"]["certifies_verifier"])
        self.assertFalse(result["claims"]["runtime"]["verifier_verified"])

    def test_current_selected_run_is_not_contaminated_by_separate_historical_run(self):
        review = self.scored(0.2, selected_trial="trial-a")
        self.write("old-trial/reward.json", {"reward": 0.9})
        review["reward_runs"].append({"files": ["old-trial/reward.json"], "trial_id": "old", "historical": True})
        result = dr.audit(self.root, review, context={"rollout_policy": "scored_required"})
        self.assertTrue(result["claims"]["runtime"]["verifier_verified"])
        self.assertTrue(result["claims"]["admission"]["certifies_verifier"])

    def test_actual_zero_normal_evaluation_proves_runtime(self):
        result = dr.audit(self.root, self.scored(0), context={"rollout_policy": "scored_required"})
        self.assertTrue(result["claims"]["runtime"]["verifier_verified"])
        self.assertTrue(result["claims"]["runtime"]["has_score"])
        self.assertTrue(result["claims"]["admission"]["certifies_verifier"])

    def test_negative_gate_result_alone_does_not_prove_normal_path(self):
        result = dr.audit(self.root, self.scored(-10, normal_evaluation_completed=False), context={"rollout_policy": "scored_required"})
        self.assertTrue(result["claims"]["runtime"]["has_score"])
        self.assertFalse(result["claims"]["runtime"]["verifier_verified"])
        self.assertIsNone(result["claims"]["admission"]["admitted"])

    def test_placeholder_is_not_valid_score_even_if_numeric(self):
        result = dr.audit(self.root, self.scored(0, non_placeholder=False), context={"rollout_policy": "scored_required"})
        self.assertFalse(result["claims"]["runtime"]["verifier_verified"])

    def test_agent_timeout_with_actual_score_can_prove_current_runtime(self):
        result = dr.audit(self.root, self.scored(0.2, agent_timeout=True), context={"package_stage": "runtime"})
        self.assertEqual(result["context"]["standard"], "current")
        self.assertTrue(result["claims"]["runtime"]["verifier_verified"])
        self.assertTrue(result["claims"]["runtime"]["agent_timeout"])

    def test_verifier_timeout_is_not_agent_timeout(self):
        result = dr.audit(self.root, self.scored(0.2, agent_timeout=True, verifier_timeout=True), context={"rollout_policy": "scored_required"})
        self.assertFalse(result["claims"]["runtime"]["verifier_verified"])
        self.assertEqual(result["claims"]["runtime"]["status"], "evidence_limited")

    def test_historical_one_hour_timeout_does_not_admit_a_task(self):
        result = dr.audit(self.root, self.batch(agent_timeout=True, normal_evaluation_completed=False),
                          context={"intake_cohort": "legacy_831", "rollout_policy": "historical_1h"})
        self.assertIsNone(result["claims"]["admission"]["admitted"])
        self.assertFalse(result["claims"]["admission"]["certifies_verifier"])
        self.assertFalse(result["claims"]["runtime"]["verifier_verified"])

    def test_old_policy_values_are_inert_for_every_cohort(self):
        for cohort in ("new_1104", "unspecified"):
            result = dr.audit(self.root, self.batch(agent_timeout=True), context={"intake_cohort": cohort, "rollout_policy": "historical_1h"})
            self.assertFalse(result["errors"])
            self.assertEqual(result["context"]["standard"], "current")
            self.assertNotIn("rollout_policy", result["context"])
            self.assertIsNone(result["claims"]["admission"]["admitted"])

    def test_selected_run_binding_does_not_merge_conflicting_trials(self):
        review = self.scored(0.2)
        self.write("trial-b/reward.json", {"reward": 0.9})
        review["reward_runs"].append({"files": ["trial-b/reward.json"], "trial_id": "trial-b"})
        result = dr.audit(self.root, review, context={"rollout_policy": "scored_required"})
        self.assertFalse(result["claims"]["runtime"]["verifier_verified"])
        review["groups"]["batch_acceptance"]["details"]["rollout_evidence"]["selected_trial"] = "trial-a"
        result = dr.audit(self.root, review, context={"rollout_policy": "scored_required"})
        self.assertTrue(result["claims"]["runtime"]["verifier_verified"])
        self.assertEqual(result["claims"]["runtime"]["reward_runs"][0]["main_score"], 0.2)

    def test_one_run_cannot_combine_output_files_from_different_trials(self):
        review = self.scored(0.2)
        self.write("trial-b/reward.txt", "0.9\n")
        review["reward_runs"][0]["files"].append("trial-b/reward.txt")
        result = dr.audit(self.root, review, context={"rollout_policy": "scored_required"})
        self.assertTrue(result["errors"])
        self.assertEqual(result["claims"]["runtime"]["status"], "unreviewed")

    def test_old_cohort_label_cannot_waive_current_dual_reward_failure(self):
        review = self.scored(0.2)
        self.write("trial-a/reward.txt", "0.9\n")
        review["reward_runs"][0]["files"].append("trial-a/reward.txt")
        result = dr.audit(self.root, review, context={"intake_cohort": "legacy_831", "rollout_policy": "scored_required"})
        self.assertFalse(result["claims"]["runtime"]["verifier_verified"])
        self.assertEqual(result["claims"]["runtime"]["reward_runs"][0]["main_score"], 0.2)
        self.assertEqual(next(row for row in result["checks"] if row["name"] == "new_intake_protocol")["status"], "fail")

    def test_current_protocol_is_mandatory_without_any_intake_selection(self):
        self.assertEqual(self.group("new_intake_protocol")["status"], "unreviewed")
        self.assertTrue(self.group("new_intake_protocol")["required_for_static_completion"])
        self.assertEqual(self.group("new_intake_protocol", context={"intake_cohort": "new_1104"})["status"], "unreviewed")
        self.assertEqual(self.group("new_intake_protocol", self.review(), context={"intake_cohort": "new_1104"})["status"], "pass")

    def test_current_protocols_apply_without_a_required_reference_filename(self):
        review = self.review()
        details = review["groups"]["new_intake_protocol"]["details"]
        self.write("solution/solver.rs", "fn main() {}\n")
        details["oracle_entry"].update(summary="The solution/solve.sh entry invokes the Rust Oracle implementation inside solution and emits a normal submission", implementation_paths=["solution/solver.rs"], language="Rust")
        details["formal_reward"].update(output_files=["reward.json", "reward.txt"], json_main_key="score")
        details["gate_penalty"]["value"] = -2
        details["dependency_lock"]["locked"] = False
        row = self.group("new_intake_protocol", review, context={"intake_cohort": "new_1104"})
        self.assertEqual(row["status"], "fail")
        self.assertEqual({finding["code"] for finding in row["problems"]},
                         {"current.formal_reward_file_choice", "current.json_reward_main_key", "current.gate_penalty", "current.dependency_lock"})
        self.assertFalse(any("reference.py" in finding["reason"] for finding in row["problems"]))

    def test_formal_output_declarations_do_not_combine_different_trial_directories(self):
        review = self.review()
        formal = review["groups"]["new_intake_protocol"]["details"]["formal_reward"]
        formal.update(output_files=["trial-a/reward.json", "trial-b/reward.txt"], json_main_key="reward",
                      summary="Separate observed trials each emit one formal file; JSON and text outputs belong to different invocations")
        row = self.group("new_intake_protocol", review, context={"intake_cohort": "new_1104"})
        self.assertEqual(row["status"], "pass")
        self.assertFalse(row["problems"])

    def test_formal_output_declarations_detect_same_directory_dual_files(self):
        review = self.review()
        review["groups"]["new_intake_protocol"]["details"]["formal_reward"].update(
            output_files=["trial-a/reward.json", "trial-a/reward.txt"], json_main_key="reward")
        row = self.group("new_intake_protocol", review, context={"intake_cohort": "new_1104"})
        self.assertEqual(row["status"], "fail")
        self.assertTrue(any(value["code"] == "current.formal_reward_file_choice" for value in row["problems"]))

    def test_every_old_or_unknown_cohort_still_requires_all_four_protocol_items(self):
        for cohort in ("legacy_831", "new_1104", "unspecified", "unknown-batch"):
            review = self.review()
            review["groups"]["new_intake_protocol"]["details"]["dependency_lock"]["locked"] = False
            result = dr.audit(self.root, review, context={"intake_cohort": cohort,
                "mode": "legacy-waiver", "rollout_policy": "historical_1h", "target_level": "L0"})
            row = next(row for row in result["checks"] if row["name"] == "new_intake_protocol")
            self.assertTrue(row["applicable"])
            self.assertTrue(row["required_for_static_completion"])
            self.assertEqual(row["status"], "fail")
            self.assertEqual(result["context"]["standard"], "current")
            self.assertNotIn("intake_cohort", result["context"])
            self.assertTrue(any(value["code"] == "current.dependency_lock" for value in row["problems"]))

    def test_protocol_cannot_be_marked_not_applicable(self):
        for part in dr.DETAILS["new_intake_protocol"]:
            review = self.review()
            review["groups"]["new_intake_protocol"]["details"][part]["status"] = "not_applicable"
            result = dr.audit(self.root, review)
            row = next(row for row in result["checks"] if row["name"] == "new_intake_protocol")
            self.assertFalse(row["review_complete"])
            self.assertEqual(row["status"], "unreviewed")
            self.assertTrue(result["errors"])

    def test_missing_required_solve_entry_is_a_current_defect(self):
        review = self.review()
        (self.root / "solution/solve.sh").unlink()
        review["groups"]["new_intake_protocol"]["details"]["oracle_entry"]["evidence"] = ["task.toml:1-6"]
        row = self.group("new_intake_protocol", review, context={"intake_cohort": "legacy_831"})
        self.assertEqual(row["status"], "fail")
        self.assertTrue(any(value["code"] == "current.oracle_entry_missing" for value in row["problems"]))

    def test_oracle_implementation_must_be_inside_solution_directory(self):
        review = self.review()
        self.write("reference.py", "# Actual Oracle implementation outside solution\n")
        self.write("solution/solve.sh", "#!/bin/sh\nexec python /reference.py\n")
        review["groups"]["new_intake_protocol"]["details"]["oracle_entry"].update(
            implementation_paths=["reference.py"], summary="The required solve.sh currently invokes the root-level reference.py implementation")
        row = self.group("new_intake_protocol", review)
        self.assertEqual(row["status"], "fail")
        self.assertTrue(any(value["code"] == "current.oracle_implementation_location" for value in row["problems"]))

    def test_reference_implementation_name_and_language_are_not_fixed(self):
        review = self.review()
        self.write("solution/search.rs", "fn main() {}\n")
        review["groups"]["new_intake_protocol"]["details"]["oracle_entry"].update(
            implementation_paths=["solution/search.rs"], language="Rust")
        self.assertFalse((self.root / "solution/reference.py").exists())
        row = self.group("new_intake_protocol", review)
        self.assertEqual(row["status"], "pass")
        self.assertFalse(row["problems"])

    def test_task_and_container_solution_paths_identify_the_same_required_entry(self):
        for entry in ("./solution/solve.sh", "solution/./solve.sh", "/solution/solve.sh"):
            review = self.review()
            review["groups"]["new_intake_protocol"]["details"]["oracle_entry"].update(
                entry=entry, implementation_paths=["/solution/oracle_impl.py"])
            self.assertEqual(self.group("new_intake_protocol", review)["status"], "pass")

    def test_oracle_can_be_implemented_in_solve_sh_itself(self):
        review = self.review()
        self.write("solution/solve.sh", "#!/bin/sh\nprintf 'normal artifact' > /app/submission/output.txt\n")
        review["groups"]["new_intake_protocol"]["details"]["oracle_entry"]["implementation_paths"] = ["solution/solve.sh"]
        self.assertEqual(self.group("new_intake_protocol", review)["status"], "pass")

    def test_symlinked_solution_directory_does_not_establish_required_local_oracle(self):
        review = self.review()
        (self.root / "solution").rename(self.root / "outside-oracle")
        (self.root / "solution").symlink_to(self.root / "outside-oracle", target_is_directory=True)
        review["groups"]["new_intake_protocol"]["details"]["oracle_entry"]["evidence"] = ["task.toml:1-6"]
        row = self.group("new_intake_protocol", review)
        self.assertEqual(row["status"], "fail")
        self.assertTrue(any(value["code"] == "current.oracle_entry_missing" for value in row["problems"]))

    def test_alternate_official_entry_field_cannot_waive_required_solve_sh(self):
        review = self.review()
        review["groups"]["new_intake_protocol"]["details"]["oracle_entry"].update(
            entry="reference/run.sh", official_equivalent=True)
        row = self.group("new_intake_protocol", review)
        self.assertEqual(row["status"], "fail")
        self.assertTrue(any(value["code"] == "current.oracle_entry_location" for value in row["problems"]))

    def test_unestablished_lock_fact_cannot_become_a_protocol_pass(self):
        review = self.review()
        del review["groups"]["new_intake_protocol"]["details"]["dependency_lock"]["locked"]
        row = self.group("new_intake_protocol", review)
        self.assertEqual(row["status"], "evidence_limited")
        self.assertTrue(row["review_complete"])
        self.assertFalse(row["problems"])

    def test_all_candidate_hard_gate_results_require_numeric_minus_ten(self):
        for value in (-2, 0, True, "-10"):
            review = self.review()
            review["groups"]["new_intake_protocol"]["details"]["gate_penalty"]["value"] = value
            row = self.group("new_intake_protocol", review)
            self.assertEqual(row["status"], "fail")
            self.assertTrue(any(problem["code"] == "current.gate_penalty" for problem in row["problems"]))
        self.assertEqual(self.group("new_intake_protocol", self.review())["status"], "pass")

    def test_undetermined_oracle_implementation_is_a_completed_material_limitation(self):
        review = self.review()
        review["groups"]["new_intake_protocol"]["details"]["oracle_entry"]["implementation_paths"] = []
        row = self.group("new_intake_protocol", review)
        self.assertTrue(row["review_complete"])
        self.assertEqual(row["status"], "evidence_limited")
        self.assertFalse(row["problems"])

    def test_actual_multi_metric_json_without_reward_main_key_fails_current_standard(self):
        review = self.scored(0.2)
        self.write("trial-a/reward.json", {"accuracy": 0.8, "latency": 0.2})
        result = dr.audit(self.root, review)
        row = next(row for row in result["checks"] if row["name"] == "new_intake_protocol")
        self.assertEqual(row["status"], "fail")
        self.assertTrue(any(problem["code"] == "current.selected_run_json_main_key" for problem in row["problems"]))
        self.assertFalse(result["claims"]["runtime"]["verifier_verified"])

    def test_empty_invalid_json_with_dual_output_retains_failure_without_crashing(self):
        review = self.scored(0.2)
        self.write("trial-a/reward.json", "")
        self.write("trial-a/reward.txt", "0.2\n")
        review["reward_runs"][0]["files"].append("trial-a/reward.txt")
        result = dr.audit(self.root, review)
        self.assertEqual(result["claims"]["static"]["status"], "fail")
        self.assertFalse(result["claims"]["runtime"]["verifier_verified"])

    def test_invalid_optional_assurance_note_does_not_change_l0_completion(self):
        review = self.review()
        review["groups"]["batch_acceptance"]["details"]["level_assurance"] = {
            "summary": "Additional prior evidence is selected for inspection", "evidence": [123]}
        result = dr.audit(self.root, review)
        self.assertEqual(result["claims"]["assurance_notes"]["status"], "unreviewed")
        self.assertTrue(result["claims"]["assurance_notes"]["errors"])
        self.assertFalse(result["errors"])
        self.assertEqual(result["claims"]["static"]["status"], "pass")

    def test_old_cohort_label_cannot_disable_current_gate_penalty(self):
        review = self.review()
        review["groups"]["new_intake_protocol"]["details"]["gate_penalty"]["value"] = -2
        row = self.group("new_intake_protocol", review, context={"intake_cohort": "legacy_831"})
        self.assertEqual(row["status"], "fail")
        self.assertTrue(any(value["code"] == "current.gate_penalty" for value in row["problems"]))

    def test_selected_current_dual_output_fails_after_native_score_read(self):
        review = self.scored(0.2)
        self.write("trial-a/reward.txt", "0.9\n")
        review["reward_runs"][0]["files"].append("trial-a/reward.txt")
        result = dr.audit(self.root, review, context={"intake_cohort": "new_1104", "rollout_policy": "scored_required"})
        protocol = next(row for row in result["checks"] if row["name"] == "new_intake_protocol")
        self.assertEqual(protocol["status"], "fail")
        self.assertEqual(result["claims"]["runtime"]["reward_runs"][0]["main_score"], 0.2)
        self.assertFalse(result["claims"]["admission"]["admitted"])

    def test_selected_current_single_metric_alias_is_not_the_required_reward_key(self):
        review = self.scored(0.2)
        self.write("trial-a/reward.json", {"score": 0.2})
        result = dr.audit(self.root, review, context={"intake_cohort": "new_1104", "rollout_policy": "scored_required"})
        protocol = next(row for row in result["checks"] if row["name"] == "new_intake_protocol")
        self.assertEqual(protocol["status"], "fail")
        self.assertTrue(any(finding["code"] == "current.selected_run_json_main_key" for finding in protocol["problems"]))

    def test_old_level_selector_does_not_change_current_l0_review(self):
        result = dr.audit(self.root, self.review(), context={"target_level": "L1"})
        self.assertFalse(result["errors"])
        self.assertEqual(result["claims"]["static"]["status"], "pass")
        self.assertNotIn("target_level", result["claims"])
        self.assertFalse(result["claims"]["assurance_notes"]["certified"])

    def test_additional_assurance_missing_facets_is_informational(self):
        review = self.review()
        review["groups"]["batch_acceptance"]["details"]["level_assurance"] = {
            "summary": "Existing source was reviewed for private recovery and trivial shortcuts; no prior induced-cheat rollout is included",
            "evidence": ["tests/grader.py:1-4"], "covered_facets": ["private_recovery", "trivial_full_score", "verifier_vulnerabilities"]}
        result = dr.audit(self.root, review, context={"target_level": "L2", "rollout_policy": "source_only"})
        batch = next(row for row in result["checks"] if row["name"] == "batch_acceptance")
        self.assertTrue(batch["review_complete"])
        self.assertEqual(batch["status"], "pass")
        self.assertFalse(batch["required_for_static_completion"])
        self.assertEqual(result["claims"]["runtime"]["status"], "not_applicable")
        self.assertEqual(result["claims"]["static"]["status"], "pass")
        self.assertFalse(batch["problems"])

    def test_unspecified_level_does_not_certify_advanced_assurance(self):
        result = dr.audit(self.root, self.scored(0.2), context={"rollout_policy": "scored_required"})
        self.assertNotIn("target_level", result["claims"])
        self.assertFalse(result["claims"]["assurance_notes"]["certified"])

    def level(self, review, level="L2", **values):
        facets = ["private_recovery", "trivial_full_score", "verifier_vulnerabilities"]
        if level == "L2":
            facets += ["timing_replay", "evaltool_inference", "induced_cheat_rollout"]
        review["groups"]["batch_acceptance"]["details"]["level_assurance"] = {
            "summary": "The existing evidence was read for the requested assurance facets and its actual coverage is recorded here",
            "evidence": ["tests/grader.py:1-4"], "covered_facets": facets, **values}
        return review

    def test_extra_facet_labels_do_not_establish_dynamic_coverage_or_select_a_level(self):
        result = dr.audit(self.root, self.level(self.review()), context={"target_level": "L2", "rollout_policy": "source_only"})
        row = next(row for row in result["checks"] if row["name"] == "batch_acceptance")
        self.assertTrue(row["review_complete"])
        self.assertEqual(row["status"], "pass")
        self.assertEqual(result["claims"]["static"]["status"], "pass")
        self.assertFalse(result["claims"]["assurance_notes"]["dynamic_coverage_verified"])
        self.assertFalse(result["claims"]["assurance_notes"]["certified"])
        self.assertFalse(row["problems"])

    def test_old_level_field_cannot_reenable_a_missing_score_gate(self):
        result = dr.audit(self.root, self.level(self.review(), "L1"), context={"target_level": "L1", "rollout_policy": "source_only"})
        row = next(row for row in result["checks"] if row["name"] == "batch_acceptance")
        self.assertEqual(row["status"], "pass")
        self.assertFalse(row["required_for_static_completion"])
        self.assertFalse(result["claims"]["assurance_notes"]["certified"])

    def test_actual_normal_evaluation_and_additional_facets_do_not_certify_a_level(self):
        result = dr.audit(self.root, self.level(self.scored(0.2), "L1"), context={"target_level": "L1", "rollout_policy": "scored_required"})
        self.assertTrue(result["claims"]["runtime"]["verifier_verified"])
        self.assertEqual(result["claims"]["assurance_notes"]["status"], "reviewed")
        self.assertFalse(result["claims"]["assurance_notes"]["certified"])

    def test_extra_assurance_without_induced_rollout_does_not_reject_current_l0(self):
        result = dr.audit(self.root, self.level(self.scored(0.2)), context={"target_level": "L2", "rollout_policy": "scored_required"})
        self.assertTrue(result["claims"]["runtime"]["verifier_verified"])
        self.assertFalse(result["claims"]["assurance_notes"]["dynamic_coverage_verified"])
        self.assertEqual(result["claims"]["static"]["status"], "pass")

    def test_additional_dynamic_declaration_cannot_point_only_at_static_grader(self):
        review = self.level(self.scored(0.2), induced_cheat_rollout_verified=True, dynamic_evidence=["tests/grader.py:1-4"])
        result = dr.audit(self.root, review, context={"target_level": "L2", "rollout_policy": "scored_required"})
        self.assertFalse(result["claims"]["assurance_notes"]["dynamic_coverage_verified"])
        self.assertEqual(result["claims"]["static"]["status"], "pass")

    def test_additional_dynamic_evidence_is_read_without_whole_level_certification(self):
        self.write("adversarial-run/conversation.log", "Actual inducement prompt: fabricate the score\nComplete executed assistant conversation: refused and submitted a legal artifact\nActual selected result: normal evaluation completed at reward=0.2\n")
        review = self.level(self.scored(0.2), induced_cheat_rollout_verified=True,
                            dynamic_evidence=["adversarial-run/conversation.log:1-3"])
        result = dr.audit(self.root, review, context={"target_level": "L2", "rollout_policy": "scored_required"})
        self.assertTrue(result["claims"]["assurance_notes"]["dynamic_coverage_verified"])
        self.assertFalse(result["claims"]["assurance_notes"]["certified"])
        self.assertEqual(result["claims"]["static"]["status"], "pass")

    def test_historical_score_with_advanced_notes_still_cannot_certify_current_verifier(self):
        self.write("adversarial-run/conversation.log", "Actual inducement prompt and complete session with its result\n")
        review = self.level(self.scored(0.2), induced_cheat_rollout_verified=True,
                            dynamic_evidence=["adversarial-run/conversation.log:1"])
        review["reward_runs"][0]["historical"] = True
        result = dr.audit(self.root, review, context={"intake_cohort": "legacy_831", "target_level": "L2", "rollout_policy": "historical_1h"})
        self.assertIsNone(result["claims"]["admission"]["admitted"])
        self.assertFalse(result["claims"]["runtime"]["verifier_verified"])
        self.assertFalse(result["claims"]["assurance_notes"]["certified"])

    def test_invalid_internal_shapes_and_path_escape_are_not_silent(self):
        for review in ([], {"groups": []}, {"groups": {"task_contract": []}}):
            result = dr.audit(self.root, review)
            self.assertTrue(result["errors"])
            self.assertTrue(any(error["required"] for error in result["errors"]))
        with self.assertRaises(ValueError):
            dr.audit(self.root, task_root="..")

    def test_no_unrelated_new_numbered_checks_or_fixed_rollout_duration(self):
        result = dr.audit(self.root, self.review())
        serialized = json.dumps(result)
        for forbidden in ("CS02", "50G", "3sigma", "10800"):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual({row["owner_id"] for row in result["checks"]}, {"QA11", "QA02", "QA15", "H03", "H04"})


if __name__ == "__main__":
    unittest.main()
