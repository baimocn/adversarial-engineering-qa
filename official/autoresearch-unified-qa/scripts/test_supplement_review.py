"""Synthetic policy regressions; no task code, Docker or network is run."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import supplement_review as sr


class SupplementReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name in ("instruction.md", "task.toml", "visible.py", "scorer.py", "main.json", "child.json", "inventory.json", "platform.log"):
            (self.root / name).write_text("synthetic evidence only\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def worksheet(self):
        review = sr.template()
        review["materials"]["static_files"] = [
            {"role": role, "path": path, "read_complete": True} for role, path in
            (("instruction", "instruction.md"), ("task_config", "task.toml"),
             ("solver_visible", "visible.py"), ("scorer", "scorer.py"))]
        review["materials"]["verifier_branch"] = {
            "selected": "inherit_solver", "tests_assembly": "upload to new sandbox",
            "dependencies": "preinstalled", "artifacts_transfer": "copy final candidate",
            "independent_sandbox": "new sandbox", "private_visibility": "not visible to solver",
            "evidence": ["task.toml", "scorer.py"]}
        for code in sr.CATALOG:
            if code.startswith("A") or code.startswith("B-C"):
                review["checks"][code] = {"status": "reviewed_no_finding", "reason": "Reviewed actual contract and code.",
                    "evidence": ["instruction.md", "task.toml", "scorer.py"], "findings": []}
        return review

    def runtime(self, review):
        review["materials"]["runtime_available"] = True
        review["materials"]["sessions"] = [
            {"id": "main", "path": "main.json", "kind": "main", "total_messages": 60,
             "read_ranges": [[1, 30], [31, 60]], "count_basis": "all original messages"},
            {"id": "child", "path": "child.json", "kind": "subagent", "total_messages": 2,
             "read_ranges": [[1, 2]], "count_basis": "entire child export"}]
        review["materials"]["session_inventory"] = {"complete": True, "evidence": ["inventory.json"]}
        review["materials"]["candidate_chain"] = {
            "solver_final": "candidate-v1", "verifier_input": "candidate-v1", "raw_metrics": "metric=0.2",
            "authoritative_reward": "reward=0.2", "correspondence_reviewed": True,
            "valid_scoring_completed": True, "evidence": ["platform.log"]}
        return review

    def failure(self):
        return {"id": "issue-1", "title": "wrong file", "root_cause": "input path mismatch", "impact": "wrong score",
            "action": "unify actual input path", "owner": "author", "owner_basis": "source-controlled path",
            "evidence": ["scorer.py", "instruction.md"],
            "facts": {"contract": "allowed candidate", "actual_execution": "reader chooses wrong file",
                "normal_trigger": "submit conforming method", "actual_impact": "wrong candidate scored",
                "compliant_submission_affected": True, "counterevidence_review": "score belongs to old candidate"}}

    def set_finding(self, review, code, item):
        review["checks"][code].update(status="findings", findings=[item])
        return sr.apply_review(self.root, review)

    def test_all_49_categories_and_no_automatic_pass(self):
        r = sr.apply_review(self.root)
        self.assertEqual(len(r["coverage"]), 49)
        self.assertEqual(r["status"], "LIMITED")
        self.assertFalse(r["review_complete"])
        self.assertEqual(r["coverage"]["A01"]["status"], "skipped_no_runtime")
        self.assertEqual(r["coverage"]["A03"]["status"], "not_reviewed")

    def test_missing_runtime_does_not_skip_static(self):
        r = sr.apply_review(self.root, self.worksheet())
        self.assertEqual(r["coverage"]["A02"]["status"], "skipped_no_runtime")
        self.assertEqual(r["coverage"]["A06"]["status"], "reviewed_no_finding")
        self.assertEqual(r["coverage"]["B-P01"]["status"], "evidence_limited")

    def test_no_evidence_cannot_be_filled_as_pass(self):
        w = self.worksheet()
        w["checks"]["A03"]["evidence"] = []
        self.assertEqual(sr.apply_review(self.root, w)["coverage"]["A03"]["status"], "evidence_limited")

    def test_all_child_sessions_required(self):
        w = self.runtime(self.worksheet())
        self.assertEqual(sr.apply_review(self.root, w)["coverage"]["A02"]["status"], "reviewed_no_finding")
        w["materials"]["sessions"][1]["read_ranges"] = [[2, 2]]
        r = sr.apply_review(self.root, w)
        self.assertEqual(r["coverage"]["A02"]["status"], "evidence_limited")
        self.assertFalse(r["materials_coverage"]["sessions_complete"])

    def test_summary_only_cannot_prove_full_read(self):
        w = self.runtime(self.worksheet())
        w["materials"]["sessions"][0]["read_ranges"] = [[50, 60]]
        self.assertEqual(sr.apply_review(self.root, w)["coverage"]["A01"]["status"], "evidence_limited")

    def test_missing_candidate_chain(self):
        w = self.runtime(self.worksheet())
        w["materials"]["candidate_chain"].pop("verifier_input")
        self.assertEqual(sr.apply_review(self.root, w)["coverage"]["A01"]["status"], "evidence_limited")

    def test_confirmed_failure_survives_no_finding(self):
        known = {"id": "old", "check_id": "A03", "status": "fail", "action": "fix mismatch"}
        r = sr.apply_review(self.root, self.worksheet(), known_findings=[known])
        self.assertEqual(r["status"], "FINDINGS")
        self.assertEqual(r["coverage"]["A03"]["status"], "findings")
        self.assertTrue(r["findings"][0]["cannot_be_cleared_by_worksheet"])
        self.assertEqual(known["status"], "fail")

    def test_a_exclusion_not_new_hard_requirement(self):
        w, item = self.worksheet(), self.failure()
        item["topic"] = "reference_calibration"
        r = self.set_finding(w, "A03", item)
        self.assertEqual(r["findings"], [])
        self.assertEqual(len(r["excluded_findings"]), 1)

    def test_compliant_submission_impact_required(self):
        w, item = self.worksheet(), self.failure()
        item["facts"].pop("compliant_submission_affected")
        r = self.set_finding(w, "A03", item)
        self.assertEqual(r["findings"], [])
        self.assertEqual(r["coverage"]["A03"]["status"], "evidence_limited")

    def test_a2_request_without_success(self):
        w, item = self.runtime(self.worksheet()), self.failure()
        item["facts"] = {"technical_boundary": "protected file", "successful_action": "write requested",
            "actual_effect": "none", "failed_boundary": "unknown", "non_disruptive_repair": "private mount",
            "operation_succeeded": False, "repairable_technical_boundary": True,
            "rule_compliance": "noncompliant", "score_trust": "credible", "independent_reread": True}
        self.assertEqual(self.set_finding(w, "A02", item)["findings"], [])

    def test_a6_url_not_successful_external_access(self):
        w, item = self.worksheet(), self.failure()
        item["facts"] = {"private_content": "private labels", "private_classification": "hidden answers",
            "access_or_reconstruction": "URL only", "external_dependency": "external data", "actual_use": "not used",
            "solver_access_proven": True, "direct_formal_target_utility": True,
            "depends_on_external": True, "external_obtained": False, "independent_reread": True}
        self.assertEqual(self.set_finding(w, "A06", item)["findings"], [])

    def test_valid_score_requires_counterevidence(self):
        w, item = self.runtime(self.worksheet()), self.failure()
        item["facts"].pop("counterevidence_review")
        self.assertEqual(self.set_finding(w, "A03", item)["findings"], [])

    def test_scored_candidate_cannot_be_reported_unscored(self):
        w, item = self.runtime(self.worksheet()), self.failure()
        item["facts"].update(occurred=True, claim="current_unscored", independent_reread=True)
        r = self.set_finding(w, "A01", item)
        self.assertEqual(r["findings"], [])
        self.assertTrue(any("冲突" in e["message"] for e in r["validation_errors"]))

    def test_no_platform_logs_not_pass(self):
        w = self.worksheet()
        w["checks"].pop("B-P01")
        w["stage_reviews"]["preparation"] = {"status": "reviewed_no_finding", "reason": "No keyword",
            "evidence": ["task.toml"], "coverage": {"complete": True}}
        self.assertEqual(sr.apply_review(self.root, w)["coverage"]["B-P01"]["status"], "evidence_limited")

    def test_stage_coverage_inherits_but_findings_not_repeated(self):
        w = self.worksheet()
        for code in list(w["checks"]):
            if code.startswith("B-P"):
                del w["checks"][code]
        w["materials"]["platform_logs"] = [{"stage": "preparation", "path": "platform.log", "read_complete": True}]
        item = self.failure()
        item["check_id"] = "B-P12"
        item["facts"].update(first_confirmed_failure="COPY missing", minimal_repair_point="context", occurred=True)
        w["stage_reviews"]["preparation"] = {"status": "reviewed_no_finding", "reason": "All actual logs read",
            "evidence": ["platform.log"], "coverage": {"complete": True}, "findings": [item]}
        r = sr.apply_review(self.root, w)
        self.assertEqual(r["coverage"]["B-P12"]["status"], "findings")
        self.assertEqual(r["coverage"]["B-P11"]["status"], "reviewed_no_finding")
        self.assertEqual(len(r["findings"]), 1)

    def test_runtime_image_not_source_violation(self):
        w, item = self.worksheet(), self.failure()
        item["topic"] = "docker_image_present"
        item["facts"].update(first_confirmed_failure="field present", minimal_repair_point="runtime config")
        w["checks"]["B-C02"].update(status="findings", findings=[item])
        r = sr.apply_review(self.root, w, package_stage="runtime")
        self.assertFalse(any(f.get("topic") == "docker_image_present" for f in r["findings"]))

    def test_both_verifier_build_branches_allowed(self):
        for branch in ("inherit_solver", "tests_dockerfile", "explicit_verifier_image"):
            w = self.worksheet()
            w["materials"]["verifier_branch"]["selected"] = branch
            self.assertEqual(sr.apply_review(self.root, w)["coverage"]["B-C02"]["status"], "reviewed_no_finding")

    def test_branch_details_required(self):
        w = self.worksheet()
        w["materials"]["verifier_branch"] = {}
        self.assertEqual(sr.apply_review(self.root, w)["coverage"]["B-C02"]["status"], "evidence_limited")

    def test_uncertain_owner_needs_both_options(self):
        w, item = self.worksheet(), self.failure()
        item["owner"] = "author_or_platform"
        self.assertEqual(self.set_finding(w, "A03", item)["findings"], [])
        item.update(author_option="change path", platform_option="provide mount")
        self.assertEqual(len(self.set_finding(w, "A03", item)["findings"]), 1)

    def test_same_cause_and_action_merge(self):
        w = self.worksheet()
        a = self.failure()
        b = deepcopy(a)
        b["facts"].update(first_confirmed_failure="path mismatch", minimal_repair_point="source", occurred=True)
        self.set_finding(w, "A03", a)
        r = self.set_finding(w, "B-P12", b)
        self.assertEqual(len(r["findings"]), 1)
        self.assertEqual(r["findings"][0]["check_ids"], ["A03", "B-P12"])

    def test_recovered_error_recorded_without_repair(self):
        w, item = self.worksheet(), self.failure()
        item["facts"].update(first_confirmed_failure="network", minimal_repair_point="retry",
            occurred=True, recovered_without_contamination=True)
        r = self.set_finding(w, "B-P01", item)
        self.assertEqual(r["findings"], [])
        self.assertEqual(len(r["excluded_findings"]), 1)

    def test_no_code_execution_and_no_path_escape(self):
        (self.root / "payload.py").write_text("raise RuntimeError('must not execute')")
        w = self.worksheet()
        w["checks"]["A03"]["evidence"] = ["payload.py", "../escape"]
        r = sr.apply_review(self.root, w)
        self.assertEqual(r["coverage"]["A03"]["status"], "evidence_limited")
        self.assertFalse(r["runtime"]["network_access"])

    def test_full_coverage_has_real_complete_path(self):
        w = self.runtime(self.worksheet())
        for stage in ("preparation", "execution", "scoring"):
            w["materials"]["platform_logs"].append({"stage": stage, "path": "platform.log", "read_complete": True})
        for code in sr.CATALOG:
            if code.startswith(("B-P", "B-E", "B-S")) or code in {"B-GPU", "B-ENV"}:
                w["checks"][code] = {"status": "reviewed_no_finding", "reason": "Actual stage logs read in full",
                    "evidence": ["platform.log"], "findings": []}
        r = sr.apply_review(self.root, w)
        self.assertEqual(r["validation_errors"], [])
        self.assertTrue(r["review_complete"])
        self.assertEqual(r["status"], "COMPLETE")
        self.assertFalse(r["runtime"]["executed_by_module"])

    def test_a2_actual_boundary_violation_not_hidden_by_network_exclusion_tag(self):
        w, item = self.runtime(self.worksheet()), self.failure()
        item["topic"] = "network_configuration"
        item["facts"] = {"technical_boundary": "isolated external execution", "successful_action": "remote compute returned",
            "actual_effect": "candidate uses forbidden remote results", "failed_boundary": "sandbox execution isolation",
            "non_disruptive_repair": "block specific forbidden execution endpoint", "operation_succeeded": True,
            "repairable_technical_boundary": True, "rule_compliance": "noncompliant", "score_trust": "credible",
            "independent_reread": True}
        r = self.set_finding(w, "A02", item)
        self.assertEqual(len(r["findings"]), 1)
        self.assertEqual(r["excluded_findings"], [])

    def source_static_complete_with_platform_limits(self):
        w = self.worksheet()
        for code in ("A01", "A02"):
            w["checks"][code] = {"status": "evidence_limited", "reason": "未提供历史运行材料", "findings": [], "evidence": []}
        for code, metadata in sr.CATALOG.items():
            if metadata["stage"] in {"preparation", "execution", "scoring"}:
                w["checks"][code] = {"status": "evidence_limited", "reason": "本轮源包审查，未执行平台运行且未提供该阶段日志",
                    "coverage_limit": {"kind": "not_executed", "details": "该阶段尚无本次平台运行日志",
                                       "next_action": "由平台运行后按需导出既有日志；不要求作者补造"}, "findings": [], "evidence": []}
        return w

    def test_source_complete_with_explicit_nonblocking_platform_limits(self):
        w = self.source_static_complete_with_platform_limits()
        r = sr.apply_review(self.root, w)
        self.assertTrue(r["static_review_complete"])
        self.assertTrue(r["coverage_record_complete"])
        self.assertFalse(r["review_complete"])
        self.assertEqual(r["coverage"]["B-P01"]["status"], "evidence_limited")
        self.assertFalse(r["runtime"]["executed_by_module"])

    def test_delivered_unread_logs_cannot_hide_as_not_executed_limit(self):
        w = self.source_static_complete_with_platform_limits()
        w["materials"]["platform_logs"] = [{"stage": "preparation", "path": "platform.log", "read_complete": False}]
        r = sr.apply_review(self.root, w)
        self.assertFalse(r["coverage_record_complete"])
        self.assertFalse(r["provided_runtime_review_complete"])
        self.assertTrue(r["static_review_complete"])

    def test_algorithm_no_review_does_not_claim_no_must_modify(self):
        r = sr.apply_review(self.root, task_id="auto0001")
        out = r["algorithm_output"]
        self.assertEqual(out["conclusion"], "review_incomplete")
        self.assertIn("尚未完成", out["main_conclusion"])
        self.assertLessEqual(len(out["main_conclusion"]), 100)

    def test_algorithm_static_only_no_finding_keeps_runtime_limit(self):
        r = sr.apply_review(self.root, self.worksheet(), task_id="auto0001")
        out = r["algorithm_output"]
        self.assertEqual(out["main_conclusion"], "auto0001：无必须修改。")
        self.assertEqual(out["coverage_basis"], "static_only")
        self.assertTrue(out["coverage_limitations"])
        self.assertEqual(out["difficulty"]["status"], "not_applicable")
        self.assertFalse(out["difficulty"]["acceptance_gate"])

    def test_algorithm_does_not_mix_platform_only_findings(self):
        w, issue = self.worksheet(), self.failure()
        issue["facts"].update(first_confirmed_failure="COPY absent", minimal_repair_point="context", occurred=True)
        r = self.set_finding(w, "B-P12", issue)
        self.assertEqual(r["status"], "FINDINGS")
        self.assertEqual(r["algorithm_output"]["conclusion"], "no_must_modify")
        self.assertEqual(r["algorithm_output"]["evidence_details"], [])

    def test_algorithm_short_main_preserves_full_evidence(self):
        w, issue = self.worksheet(), self.failure()
        issue["action"] = "修复实际评分输入路径" * 60
        issue["impact"] = "当前候选未被按约定评分" * 60
        self.set_finding(w, "A03", issue)
        r = sr.apply_review(self.root, w, task_id="AutoRe0577")
        out = r["algorithm_output"]
        self.assertEqual(out["conclusion"], "must_modify")
        self.assertLessEqual(out["main_conclusion_unicode_length"], 100)
        self.assertIn("[出题人]", out["main_conclusion"])
        self.assertIn("；当前候选", out["main_conclusion"])
        self.assertEqual(out["evidence_details"][0]["action"], issue["action"])
        self.assertEqual(out["evidence_details"][0]["impact"], issue["impact"])

    def difficulty_worksheet(self):
        w = self.runtime(self.worksheet())
        w["difficulty"] = {"judgment": "有偏易迹象", "reason": "首次改善较早，但仍有方法改进余地",
            "evidence": ["main.json", "platform.log"], "basis": {
                "first_valid_improvement": "实际首次改善出现在第15次响应",
                "final_score": "正式reward=0.2", "method_complexity": "简单特征重组",
                "remaining_space": "仍有高阶方法可尝试"}}
        return w

    def test_difficulty_only_accepted_after_credible_score_and_full_runtime(self):
        w = self.difficulty_worksheet()
        before = sr.apply_review(self.root, w)
        self.assertEqual(before["algorithm_output"]["difficulty"]["status"], "not_judged")
        w["materials"]["candidate_chain"]["score_trust"] = "credible"
        after = sr.apply_review(self.root, w)
        difficulty = after["algorithm_output"]["difficulty"]
        self.assertEqual(difficulty["status"], "reviewed")
        self.assertEqual(difficulty["judgment"], "有偏易迹象")
        self.assertFalse(difficulty["acceptance_gate"])
        self.assertEqual(before["status"], after["status"])
        w["materials"]["sessions"][1]["read_ranges"] = []
        self.assertEqual(sr.apply_review(self.root, w)["algorithm_output"]["difficulty"]["status"], "not_judged")

    def test_unsupported_difficulty_does_not_create_acceptance_failure(self):
        w = self.difficulty_worksheet()
        w["materials"]["candidate_chain"]["score_trust"] = "credible"
        baseline = sr.apply_review(self.root, w)
        w["difficulty"]["judgment"] = "简单题应不通过"
        r = sr.apply_review(self.root, w)
        self.assertEqual(r["algorithm_output"]["difficulty"]["status"], "not_judged")
        self.assertEqual(r["validation_errors"], baseline["validation_errors"])
        self.assertEqual(r["findings"], baseline["findings"])
        self.assertEqual(r["status"], baseline["status"])

    def test_untrusted_score_finding_blocks_difficulty(self):
        w = self.difficulty_worksheet()
        w["materials"]["candidate_chain"]["score_trust"] = "credible"
        known = {"check_id": "A02", "status": "confirmed", "facts": {"score_trust": "not_credible"},
                 "owner": "author", "action": "restore protected grader", "impact": "score contaminated"}
        r = sr.apply_review(self.root, w, known_findings=[known])
        self.assertEqual(r["algorithm_output"]["difficulty"]["status"], "not_judged")
        self.assertEqual(r["algorithm_output"]["conclusion"], "must_modify")

    def test_difficulty_missing_basis_does_not_guess(self):
        w = self.difficulty_worksheet()
        w["materials"]["candidate_chain"]["score_trust"] = "credible"
        w["difficulty"]["basis"].pop("remaining_space")
        self.assertEqual(sr.apply_review(self.root, w)["algorithm_output"]["difficulty"]["status"], "not_judged")
        w["materials"]["runtime_available"] = False
        self.assertEqual(sr.apply_review(self.root, w)["algorithm_output"]["difficulty"]["status"], "not_applicable")

    def test_malformed_internal_fields_do_not_crash_validator(self):
        w = self.worksheet()
        w["materials"]["static_files"][0]["role"] = ["instruction", {}]
        w["materials"]["verifier_branch"]["selected"] = []
        w["checks"]["A03"]["status"] = []
        r = sr.apply_review(self.root, w, package_stage=[])
        self.assertFalse(r["review_complete"])
        self.assertTrue(r["validation_errors"])

    def test_large_top_level_array_reference_accepted(self):
        (self.root / "large.json").write_text('["' + 'x' * (4 * 1024 * 1024 + 1) + '"]')
        w = self.worksheet()
        w["checks"]["A03"]["evidence"] = ["large.json"]
        self.assertEqual(sr.apply_review(self.root, w)["coverage"]["A03"]["status"], "reviewed_no_finding")


if __name__ == "__main__":
    unittest.main()
