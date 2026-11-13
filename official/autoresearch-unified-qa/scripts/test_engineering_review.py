"""Trusted synthetic engineering fixtures; no task, container or model execution."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import engineering_review as er


class EngineeringReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.write("tests/test.sh", "#!/bin/sh\nrm -f /logs/verifier/reward.json\npython grader.py\n")

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
        return name

    def review(self):
        result = {name: {"summary": "Selected source and existing call chain were read for " + name,
                         "evidence": ["tests/test.sh:1-3"]} for name in er.GROUPS}
        result["score_paths"]["branches"] = {
            name: {"summary": "Existing trusted wrapper determines the " + name + " result before collection",
                   "evidence": ["tests/test.sh:2-3"], "outcome": name + "_protocol_result"}
            for name in er.BRANCHES}
        return result

    def audit(self, review=None, **kwargs):
        return er.audit(self.root, review, **kwargs)

    def group(self, name, review=None, **kwargs):
        return next(row for row in self.audit(review, **kwargs)["checks"] if row["name"] == name)

    def finding(self, group, **kwargs):
        result = {"owner_id": er.GROUPS[group][0],
                  "reason": "An interrupted verifier can leave a consumable placeholder reward at the selected path",
                  "remediation": "Commit the formal result after classification or mark the interruption through the selected protocol",
                  "evidence": ["tests/test.sh:2"]}
        result.update(kwargs)
        return result

    def test_unreviewed_is_not_a_pattern_pass_and_optional_absence_is_nonblocking(self):
        result = self.audit()
        self.assertFalse(result["executed_task"])
        self.assertEqual([row["name"] for row in result["checks"]], list(er.GROUPS))
        for row in result["checks"][:4]:
            self.assertEqual(row["status"], "unreviewed")
            self.assertFalse(row["review_complete"])
            self.assertFalse(row["problems"])
        for row in result["checks"][4:]:
            self.assertEqual(row["status"], "not_applicable")
            self.assertTrue(row["review_complete"])
            self.assertFalse(row["required_for_static_completion"])
        self.assertNotIn("CS01", json.dumps(result))
        self.assertNotIn("CS02", json.dumps(result))

    def test_positioned_observations_do_not_classify_candidate_or_trusted_fault(self):
        self.write("tests/test.sh", "#!/bin/sh\necho 0 > /logs/verifier/reward.txt\npython grader.py\n")
        self.write("tests/grader.py", "try:\n    trusted_asset = load_private_asset()\n    score = evaluate_candidate()\nexcept Exception:\n    write_reward(0)\n")
        result = self.audit()
        broad = next(o for o in result["observations"] if o["kind"] == "broad_exception_region")
        self.assertEqual(broad["ref"], "tests/grader.py:4")
        self.assertEqual(broad["details"]["try_line"], 1)
        self.assertEqual(broad["details"]["try_end_line"], 3)
        self.assertEqual({c["call"] for c in broad["details"]["calls"]}, {"load_private_asset", "evaluate_candidate"})
        self.assertTrue(any(o["kind"] == "formal_reward_operation" and o["line"] == 2 for o in result["observations"]))
        self.assertFalse(any(c["status"] == "fail" for c in result["checks"]))

    def test_no_submission_import_or_execution(self):
        marker = self.root / "executed"
        self.write("tests/grader.py", "from pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('executed')\nraise RuntimeError('must not run')\n")
        with mock.patch("subprocess.run", side_effect=AssertionError("execution forbidden")):
            result = self.audit(self.review())
        self.assertFalse(marker.exists())
        self.assertTrue(all(c["status"] == "pass" for c in result["checks"]))

    def test_source_read_once_and_evidence_reuses_collection(self):
        self.write("task.toml", "[environment]\ngpus = 0\n[verifier]\ntimeout_sec = 600\n")
        review = self.review()
        review["resource_alignment"]["evidence"].append("task.toml:1-2")
        with mock.patch.object(er, "_text", wraps=er._text) as reader:
            self.audit(review)
        calls = [call.args[0].name for call in reader.call_args_list]
        self.assertEqual(calls.count("task.toml"), 1)
        self.assertEqual(calls.count("test.sh"), 1)

    def test_complete_source_paths_require_all_four_evidenced_outcomes(self):
        review = self.review()
        del review["score_paths"]["branches"]["trusted_failure"]
        row = self.group("score_paths", review)
        self.assertEqual(row["status"], "unreviewed")
        self.assertFalse(row["review_complete"])
        self.assertTrue(any("trusted_failure" in v for v in row["limitations"]))

    def test_evidenced_not_applicable_branch_uses_existing_wrapper(self):
        review = self.review()
        review["score_paths"]["branches"]["interrupted"].update(
            not_applicable=True, outcome="not_applicable_to_this_entry",
            summary="The existing trusted parent wrapper owns termination and collection for this child entry")
        row = self.group("score_paths", review)
        self.assertEqual(row["status"], "pass")
        self.assertTrue(row["review_complete"])

    def test_generic_pass_and_bare_failure_are_incomplete(self):
        for change in ({"summary": "pass"}, {"status": "fail"}):
            with self.subTest(change=change):
                review = self.review()
                review["timeout_budget"].update(change)
                row = self.group("timeout_budget", review)
                self.assertEqual(row["status"], "unreviewed")
                self.assertFalse(row["review_complete"])

    def test_material_source_gap_is_separate_from_unfilled_worksheet(self):
        review = self.review()
        review["score_paths"] = {"status": "evidence_limited",
            "summary": "The selected launcher references grader.py but no selected grader is present in the provided source",
            "evidence": ["tests/test.sh:3"]}
        row = self.group("score_paths", review)
        self.assertEqual(row["status"], "evidence_limited")
        self.assertTrue(row["review_complete"])
        review["score_paths"]["evidence"] = ["missing.py:1"]
        self.assertFalse(self.group("score_paths", review)["review_complete"])

    def test_only_precise_confirmed_findings_fail_with_stable_identity(self):
        review = self.review()
        review["score_paths"]["findings"] = [self.finding("score_paths")]
        row = self.group("score_paths", review)
        self.assertEqual(row["status"], "fail")
        self.assertTrue(row["review_complete"])
        finding = row["problems"][0]
        self.assertEqual(finding["owner_id"], "H04")
        self.assertIn("QA09", finding["related_checks"])
        self.assertEqual(finding["code"], self.group("score_paths", review)["problems"][0]["code"])
        for replacement in ({"evidence": ["tests/test.sh"]}, {"reason": "pass"},
                            {"owner_id": "NEW_CHECK"}, {"remediation": ""}):
            with self.subTest(replacement=replacement):
                bad = copy.deepcopy(review)
                bad["score_paths"]["findings"][0].update(replacement)
                self.assertEqual(self.group("score_paths", bad)["status"], "unreviewed")

    def test_timeout_literals_expressions_override_and_seed_loop_are_observations(self):
        self.write("task.toml", "[verifier]\ntimeout_sec = 60\n")
        self.write("tests/grader.py", "deadline = start + total_budget\nfor seed in seeds:\n    run_candidate(timeout=remaining_budget(deadline))\nsetitimer(60)\n")
        self.write("run_config.json", {"verifier_timeout_sec": 180, "timeout_multiplier": 1.2})
        review = self.review()
        review["timeout_budget"]["summary"] = "Existing selected Trial override is 180 seconds and a shared deadline covers initialization, seeds and final collection"
        review["timeout_budget"]["evidence"] += ["task.toml:2", "tests/grader.py:1-4", "run_config.json#/verifier_timeout_sec"]
        result = self.audit(review)
        self.assertEqual(next(r for r in result["checks"] if r["name"] == "timeout_budget")["status"], "pass")
        expressions = [o["excerpt"] for o in result["observations"] if o["kind"] == "timeout_expression"]
        self.assertTrue(any("remaining_budget" in e for e in expressions))
        self.assertTrue(any(o["ref"] == "run_config.json#/verifier_timeout_sec" for o in result["observations"]))
        self.assertFalse(any(r["problems"] for r in result["checks"]))

    def test_equal_limits_can_have_existing_trusted_finalization(self):
        self.write("tests/test.sh", "#!/bin/sh\ntrap finalize EXIT\ntimeout 600 candidate || rc=$?\n")
        review = self.review()
        review["timeout_budget"]["summary"] = "The selected trusted outer wrapper preserves collection after the candidate's 600 second timeout through its existing exit trap"
        self.assertEqual(self.group("timeout_budget", review)["status"], "pass")

    def test_equal_timeout_and_set_e_defect_needs_source_finding(self):
        self.write("tests/test.sh", "#!/bin/sh\nset -e\ntimeout 600 python grader.py\n")
        review = self.review()
        review["timeout_budget"]["findings"] = [self.finding("timeout_budget", evidence=["tests/test.sh:2-3"],
            reason="The selected timeout exits nonzero under set -e before the required candidate-failure submission path",
            remediation="Capture the exit status and finalize according to the declared candidate failure protocol within the effective deadline")]
        row = self.group("timeout_budget", review)
        self.assertEqual(row["status"], "fail")
        self.assertEqual(row["owner_id"], "H04")

    def test_cpu_cuda_image_and_missing_cuda_text_are_not_automatic_failures(self):
        self.write("environment/Dockerfile", "FROM nvidia/cuda:12.8-devel\n")
        self.write("tests/grader.py", "score = cpu_metric(candidate)\n")
        review = self.review()
        review["resource_alignment"]["findings"] = [self.finding("resource_alignment", evidence=["environment/Dockerfile:1"],
            severity="advisory", reason="The selected CPU implementation uses a CUDA devel image with potentially unnecessary dependencies",
            remediation="Consider a compatible lighter image after dependency and scoring checks")]
        result = self.audit(review, config={"environment": {"gpus": 0}, "verifier": {"environment": {"gpus": 0}}})
        row = next(c for c in result["checks"] if c["name"] == "resource_alignment")
        self.assertEqual(row["status"], "pass")
        self.assertFalse(row["problems"])
        self.assertFalse(row["advisories"][0]["blocking"])

    def test_role_requests_and_selected_images_are_distinct_observations(self):
        self.write("task.toml", "[environment]\ngpus = 1\n[verifier.environment]\ngpus = 0\n")
        self.write("tests/Dockerfile", "FROM python:3.12\n")
        cfg = {"environment": {"gpus": 1, "docker_image": "agent:image"}, "verifier": {"environment": {"gpus": 0}}}
        observations = self.audit(config=cfg)["observations"]
        roles = {o["details"]["role"]: o["details"] for o in observations if o["kind"] == "selected_role_environment"}
        self.assertEqual(roles["agent"]["environment"]["gpus"], 1)
        self.assertEqual(roles["verifier"]["environment"]["gpus"], 0)
        self.assertEqual(roles["verifier"]["image_selection"]["source"], "tests_dockerfile")

    def test_chmod_warning_with_recovered_control_preserves_score(self):
        self.write("tests/test.sh", "#!/bin/sh\nchmod 000 /dev/nvidia* || true\npython grader.py\n")
        self.write("trial.log", "chmod: Read-only file system\ntrusted device allowlist applied\nevaluation complete reward=0.45\n")
        review = self.review()
        review["controls_logs"]["summary"] = "The device chmod warning was nonblocking; the existing trusted allowlist applied and scoring completed"
        review["controls_logs"]["evidence"] += ["trial.log:1-3"]
        self.assertEqual(self.group("controls_logs", review)["status"], "pass")

    def test_json_priority_for_current_and_historical_outputs_without_new_sentinel(self):
        self.write("trial/reward.txt", "not a score")
        for value in (-10, -1, 0, 0.3261497734):
            self.write("trial/reward.json", {"accuracy": value, "status": "complete"})
            for historical in (False, True):
                with self.subTest(value=value, historical=historical):
                    result = er.normalize_reward_run(self.root, {"files": ["trial/reward.txt", "trial/reward.json"], "historical": historical})
                    self.assertEqual(result["status"], "pass")
                    self.assertEqual(result["main_score"], value)
                    self.assertEqual(result["selected_file"], "trial/reward.json")

    def test_selected_invalid_json_does_not_fall_back_or_auto_fail_source_review(self):
        self.write("trial/reward.txt", "0.7")
        self.write("trial/reward.json", {"reward": "unavailable"})
        review = self.review()
        review["reward_runs"] = [{"files": ["trial/reward.txt", "trial/reward.json"]}]
        result = self.audit(review)
        self.assertFalse(result["claims"]["has_score"])
        self.assertEqual(result["claims"]["reward_runs"][0]["status"], "fail")
        self.assertFalse(any(c["status"] == "fail" for c in result["checks"]))

    def test_invalid_reward_selection_is_internal_incomplete_and_score_unknown(self):
        for runs in ({}, None, ["not an object"], [{}], [{"files": ["missing/reward.json"]}]):
            with self.subTest(runs=runs):
                review = self.review()
                review["reward_runs"] = runs
                result = self.audit(review)
                row = next(c for c in result["checks"] if c["name"] == "score_scope")
                self.assertEqual(row["status"], "unreviewed")
                self.assertFalse(row["review_complete"])
                self.assertTrue(row["required_for_static_completion"])
                self.assertIsNone(result["claims"]["has_score"])
                self.assertTrue(any(e["group"] == "score_scope" and e["required"] for e in result["errors"]))

    def test_valid_run_facts_survive_another_broken_internal_selection(self):
        self.write("trial/reward.json", {"reward": 0.42})
        review = self.review()
        review["reward_runs"] = [{"files": ["trial/reward.json"]}, {"files": ["missing/reward.json"]}]
        result = self.audit(review)
        self.assertEqual(result["claims"]["reward_runs"][0]["main_score"], 0.42)
        self.assertIsNone(result["claims"]["has_score"])
        self.assertFalse(next(c for c in result["checks"] if c["name"] == "score_scope")["review_complete"])

    def test_receipt_scope_separates_score_and_formal_adoption(self):
        self.write("trial/reward.json", {"reward": 0.3261497734})
        self.write("existing_receipt.json", {"scope": "diagnostic", "eligibility": False})
        review = self.review()
        review["reward_runs"] = [{"files": ["trial/reward.json"]}]
        review["score_scope"].update(formal_adoption=False, score_valid=True,
            summary="The rerun has a finite score; existing scope limits formal adoption until current QC is bound",
            evidence=["existing_receipt.json#/scope", "trial/reward.json#/reward"])
        result = self.audit(review)
        self.assertTrue(result["claims"]["has_score"])
        self.assertTrue(result["claims"]["score_valid"])
        self.assertFalse(result["claims"]["formal_adoption"])
        self.assertEqual(next(c for c in result["checks"] if c["name"] == "score_scope")["status"], "pass")
        self.assertTrue(any(o["ref"] == "existing_receipt.json#/scope" for o in result["observations"]))

    def test_old_formal_and_new_diagnostic_are_not_selected_by_timestamp(self):
        self.write("old_formal/reward.json", {"reward": 0.4})
        self.write("new_diagnostic/reward.json", {"reward": 0.6})
        review = self.review()
        review["reward_runs"] = [{"files": ["old_formal/reward.json"], "historical": True}]
        result = self.audit(review)
        self.assertEqual(result["claims"]["reward_runs"][0]["main_score"], 0.4)
        with self.assertRaises(ValueError):
            er.normalize_reward_run(self.root, {"files": ["old_formal/reward.json", "new_diagnostic/reward.json"]})

    def test_qc_mismatch_is_delivery_note_and_does_not_invalidate_harbor_score(self):
        self.write("delivery_lineage.json", {"selected_trial": 446976526, "qc_trial_id": 440753938,
            "archive_sha256": "archive-hash", "content_fingerprint": "different-algorithm-hash"})
        self.write("trial/reward.json", {"reward": 0.3261497734})
        review = self.review()
        review["reward_runs"] = [{"files": ["trial/reward.json"]}]
        review["delivery_lineage"]["findings"] = [self.finding("delivery_lineage",
            evidence=["delivery_lineage.json#/qc_trial_id"],
            reason="The current QC names an older Trial than the selected rerun",
            remediation="Bind and review existing rerun materials or explicitly select the already certified older formal Trial")]
        result = self.audit(review)
        row = next(c for c in result["checks"] if c["name"] == "delivery_lineage")
        self.assertEqual(row["status"], "pass")
        self.assertTrue(row["advisories"])
        self.assertFalse(row["required_for_static_completion"])
        self.assertTrue(result["claims"]["has_score"])
        self.assertFalse(result["claims"]["delivery_affects_historical_score"])

    def test_provided_unread_reference_is_incomplete_without_new_artifact_demand(self):
        review = self.review()
        review["controls_logs"]["evidence"] = ["missing-existing.log:1"]
        row = self.group("controls_logs", review)
        self.assertEqual(row["status"], "unreviewed")
        self.assertFalse(row["review_complete"])
        review["controls_logs"]["evidence"] = ["@current_inventory"]
        self.assertFalse(self.group("controls_logs", review)["review_complete"])

    def test_filename_guessed_broken_metadata_can_be_reviewed_as_unrelated(self):
        self.write("assets/sample_receipt.json", "{broken historical example")
        row = self.group("score_scope")
        self.assertEqual(row["status"], "unreviewed")
        self.assertFalse(row["review_complete"])
        review = self.review()
        review["score_scope"].update(summary="The malformed asset is a historical example unrelated to the selected entry or Trial",
            evidence=["assets/sample_receipt.json:1", "tests/test.sh:1-3"])
        result = self.audit(review)
        row = next(c for c in result["checks"] if c["name"] == "score_scope")
        self.assertEqual(row["status"], "pass")
        self.assertTrue(row["review_complete"])
        self.assertFalse(result["errors"])
        self.assertTrue(result["collection_limitations"])

    def test_explicit_selected_metadata_location_error_remains_incomplete(self):
        self.write("assets/sample_receipt.json", "{broken historical example")
        review = self.review()
        review["score_scope"]["evidence"] = ["assets/sample_receipt.json#/evaluation_scope"]
        result = self.audit(review)
        row = next(c for c in result["checks"] if c["name"] == "score_scope")
        self.assertEqual(row["status"], "unreviewed")
        self.assertFalse(row["review_complete"])
        self.assertTrue(row["required_for_static_completion"])
        self.assertTrue(any(e["group"] == "score_scope" and e["required"] for e in result["errors"]))

    def test_warning_status_is_nonblocking_and_scope_claims_require_completed_read(self):
        review = self.review()
        review["controls_logs"].update(status="warn", findings=[self.finding("controls_logs")])
        row = self.group("controls_logs", review)
        self.assertEqual(row["status"], "pass")
        self.assertTrue(row["advisories"])
        review["score_scope"].update(formal_adoption="yes", score_valid=True)
        result = self.audit(review)
        self.assertIsNone(result["claims"]["score_valid"])
        self.assertIsNone(result["claims"]["formal_adoption"])

    def test_large_logs_are_bounded_and_unread_selected_receipt_is_not_passed(self):
        path = self.root / "trial.log"
        with path.open("wb") as stream:
            stream.truncate(1024 * 1024 * 1024)
        row = self.group("controls_logs")
        self.assertEqual(row["status"], "unreviewed")
        self.assertFalse(row["review_complete"])
        self.assertTrue(any("read limit" in text for text in row["limitations"]))
        reviewed = self.group("controls_logs", self.review())
        self.assertEqual(reviewed["status"], "pass")
        self.assertTrue(reviewed["review_complete"])
        path.unlink()
        self.write("existing_receipt.json", "x" * (er.SOURCE_LIMIT + 1))
        self.assertEqual(self.group("score_scope")["status"], "unreviewed")

    def test_large_json_reference_uses_streaming_location_not_size_failure(self):
        self.write("existing_receipt.json", {"padding": "p" * (er.EVIDENCE_LIMIT + 50),
            "evaluation_scope": "diagnostic", "formal_gate_eligible": False,
            "nested": {"a/b": [{"x~y": 7}]}})
        review = self.review()
        review["score_scope"].update(summary="The existing large receipt and its selected nested result were read; the scope limits formal adoption",
            evidence=["existing_receipt.json#evaluation_scope", "existing_receipt.json#/nested/a~1b/0/x~0y"],
            formal_adoption=False)
        result = self.audit(review)
        row = next(c for c in result["checks"] if c["name"] == "score_scope")
        self.assertEqual(row["status"], "pass")
        self.assertTrue(row["review_complete"])
        self.assertFalse(result["errors"])
        self.assertTrue(result["collection_limitations"])
        self.assertFalse(result["claims"]["formal_adoption"])
        review["score_scope"]["evidence"] = ["existing_receipt.json#/missing"]
        self.assertEqual(self.group("score_scope", review)["status"], "unreviewed")

    def test_large_line_reference_is_streamed_and_bounds_still_checked(self):
        self.write("existing_stdout.txt", "p" * (er.EVIDENCE_LIMIT + 50) + "\ncompleted score=0.4\n")
        review = self.review()
        review["controls_logs"]["evidence"] = ["existing_stdout.txt:2"]
        result = self.audit(review)
        row = next(c for c in result["checks"] if c["name"] == "controls_logs")
        self.assertEqual(row["status"], "pass")
        self.assertFalse(result["errors"])
        review["controls_logs"]["evidence"] = ["existing_stdout.txt#L3"]
        self.assertEqual(self.group("controls_logs", review)["status"], "unreviewed")

    def test_feedback_scope_field_names_are_observed_without_new_receipt_schema(self):
        self.write("existing_receipt.json", {"evaluation_scope": "selftest", "formal_gate_eligible": False})
        observations = self.audit()["observations"]
        self.assertTrue(any(o["ref"] == "existing_receipt.json#/evaluation_scope" for o in observations))
        self.assertTrue(any(o["ref"] == "existing_receipt.json#/formal_gate_eligible" for o in observations))

    def test_history_docs_unselected_build_and_other_task_are_ignored(self):
        self.write("history/broken.py", "except Exception:\n")
        self.write("docs/example.py", "except Exception:\n")
        self.write("other_task/grader.py", "except Exception:\n")
        self.write("selected/tests/test.sh", "echo complete\n")
        self.write("selected/environment/Dockerfile", "FROM nvidia/cuda:unselected\n")
        self.write("selected/tests/Dockerfile", "FROM nvidia/cuda:unselected\n")
        result = self.audit(task_root="selected", config={"environment": {"docker_image": "selected:agent"},
            "verifier": {"environment": {"docker_image": "selected:verifier"}}})
        refs = [o["path"] for o in result["observations"]]
        self.assertFalse(any(ref and ("Dockerfile" in ref or "other_task" in ref or "history" in ref or "docs" in ref) for ref in refs))

    def test_symlink_escape_cannot_be_read_or_used_as_review_evidence(self):
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside) / "outside.py"
            external.write_text("secret_marker = True\n")
            (self.root / "escape.py").symlink_to(external)
            review = self.review()
            review["timeout_budget"]["evidence"] = ["escape.py:1"]
            row = self.group("timeout_budget", review)
            self.assertEqual(row["status"], "unreviewed")
            self.assertFalse(row["review_complete"])
            self.assertNotIn("secret_marker", json.dumps(self.audit()))


    def test_invalid_selected_output_cannot_be_claimed_valid_or_adopted(self):
        self.write('trial/reward.json', {'reward':'invalid'})
        for field in ('score_valid','formal_adoption'):
            with self.subTest(field=field):
                review=self.review()
                review['reward_runs']=[{'files':['trial/reward.json']}]
                review['score_scope'][field]=True
                result=self.audit(review)
                row=next(r for r in result['checks'] if r['name']=='score_scope')
                self.assertFalse(row['review_complete'])
                self.assertIsNone(result['claims']['has_score'])
                self.assertIsNone(result['claims'][field])
                self.assertTrue(result['errors'])

    def test_failed_run_does_not_cancel_another_real_grade(self):
        self.write('invalid/reward.json', {'reward':'invalid'})
        self.write('valid/reward.json', {'reward':0.4})
        review=self.review()
        review['reward_runs']=[{'files':['invalid/reward.json']},{'files':['valid/reward.json']}]
        review['score_scope']['score_valid']=True
        result=self.audit(review)
        self.assertTrue(result['claims']['has_score'])
        self.assertTrue(result['claims']['score_valid'])
        self.assertFalse(result['errors'])

if __name__ == "__main__":
    unittest.main()
