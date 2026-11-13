"""Synthetic final-disposition invariants; never execute an expert package."""
import copy
from pathlib import Path
import tempfile
import unittest

import automation_final as final


class AutomationFinalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "instruction.md").write_text("one\ntwo\n", encoding="utf-8")
        (self.root / "corrupt.json").write_text("{BROKEN", encoding="utf-8")
        self.result = {"decision": "PASS", "processing_errors": [], "summary": {}, "sections": {
            name: {"checks": [{"id": code, "status": "pass", "evidence": ["instruction.md"]}
                               for code in sorted(ids)], "complete": True, "errors": []}
            for name, ids in final.EXPECTED.items()}}
        self.worksheet = {"automation": {"content_read_complete": True, "material_gaps": []}}

    def row(self, result=None, code="QA18", section="core"):
        return next(row for row in (result or self.result)["sections"][section]["checks"] if row["id"] == code)

    def gap(self, code="QA18", section="core"):
        self.row(code=code, section=section)["status"] = "manual"
        self.result["sections"][section]["complete"] = False
        gap = {"section": section, "check_id": code, "kind": "materials_not_provided", "read_complete": True,
               "reviewed_evidence": ["instruction.md#L1-L2"], "missing_material": "缺失历史主会话原件",
               "why_needed": "已有研究摘要未含实际调用会话，不能证明运行条件一致", "next_action": "提交原有会话记录",
               "owner": "author"}
        self.worksheet["automation"]["material_gaps"].append(gap)
        return gap

    def audit(self):
        return final.finalize(self.result, self.worksheet, self.root)

    def test_complete_pass_preserves_90(self):
        report = self.audit()
        self.assertEqual(report["decision"], "PASS")
        self.assertEqual(sum(len(s["checks"]) for s in report["sections"].values()), 90)

    def test_gap_is_terminal_nonpass_and_original_is_unchanged(self):
        self.gap()
        original = copy.deepcopy(self.result)
        report = self.audit()
        self.assertEqual(report["decision"], "MATERIALS_INCOMPLETE")
        self.assertTrue(report["summary"]["review_complete"])
        self.assertEqual(self.row(report)["raw_status"], "manual")
        self.assertEqual(self.row(report)["status"], "material_incomplete")
        self.assertEqual(self.result, original)

    def test_unread_or_unhandled_is_review_incomplete(self):
        self.row()["status"] = "manual"
        self.assertEqual(self.audit()["decision"], "REVIEW_INCOMPLETE")
        self.gap()
        self.worksheet["automation"]["content_read_complete"] = False
        report = self.audit()
        self.assertEqual(report["decision"], "REVIEW_INCOMPLETE")
        self.assertEqual(self.row(report)["status"], "manual")

    def test_known_failure_cannot_be_overwritten(self):
        self.gap()
        self.row()["status"] = "fail"
        report = self.audit()
        self.assertEqual(report["decision"], "FAIL")
        self.assertEqual(self.row(report)["status"], "fail")
        self.assertTrue(report["automation_final"]["errors"])

    def test_valid_gap_retained_alongside_another_failure(self):
        self.gap()
        self.row(code="QA05")["status"] = "fail"
        report = self.audit()
        self.assertEqual(report["decision"], "FAIL")
        self.assertEqual(len(report["missing_materials"]), 1)

    def test_processing_error_never_becomes_material_gap(self):
        self.gap()
        self.result["processing_errors"] = [{"message": "timeout"}]
        report = self.audit()
        self.assertEqual(report["decision"], "REVIEW_INCOMPLETE")
        self.assertEqual(self.row(report)["status"], "manual")

    def test_validation_error_never_becomes_material_gap(self):
        self.gap()
        self.result["sections"]["core"]["errors"] = ["bad worksheet"]
        self.assertEqual(self.audit()["decision"], "REVIEW_INCOMPLETE")

    def test_unread_sources_nested_in_payload_are_not_missing(self):
        self.gap()
        self.result["sections"]["core"]["raw"] = {"trajectory": {"unreviewed_sources": ["sessions.json"]}}
        self.assertEqual(self.audit()["decision"], "REVIEW_INCOMPLETE")

    def test_tool_limit_not_author_material_gap(self):
        gap = self.gap()
        gap["why_needed"] = "工具读取上限，文件超过32MiB"
        self.assertEqual(self.audit()["decision"], "REVIEW_INCOMPLETE")

    def test_gap_requires_real_references_and_locator(self):
        gap = self.gap()
        for ref in ("missing.md", "instruction.md#L99", "../escape", "/absolute"):
            gap["reviewed_evidence"] = [ref]
            self.assertEqual(self.audit()["decision"], "REVIEW_INCOMPLETE")

    def test_damaged_material_requires_existing_path(self):
        gap = self.gap()
        gap["kind"] = "unreadable_source"
        gap["missing_material"] = "会话原件JSON损坏"
        self.assertEqual(self.audit()["decision"], "REVIEW_INCOMPLETE")
        gap["unreadable_source"] = "corrupt.json"
        self.assertEqual(self.audit()["decision"], "MATERIALS_INCOMPLETE")

    def test_nonblocking_platform_scope_not_upgraded(self):
        self.row(code="B-P01", section="supplement").update(status="review", required_for_static_completion=False)
        self.assertEqual(self.audit()["decision"], "PASS")
        self.worksheet["automation"]["material_gaps"].append({
            "section": "supplement", "check_id": "B-P01", "kind": "materials_not_provided", "read_complete": True,
            "reviewed_evidence": ["instruction.md"], "missing_material": "尚无平台日志", "why_needed": "平台尚未运行",
            "next_action": "平台运行", "owner": "platform"})
        self.assertEqual(self.audit()["decision"], "REVIEW_INCOMPLETE")

    def test_duplicate_unknown_gap_and_missing_rows_rejected(self):
        gap = self.gap()
        self.worksheet["automation"]["material_gaps"].append(copy.deepcopy(gap))
        self.assertEqual(self.audit()["decision"], "REVIEW_INCOMPLETE")
        self.worksheet["automation"]["material_gaps"].pop()
        self.result["sections"]["core"]["checks"].pop()
        self.assertEqual(self.audit()["decision"], "REVIEW_INCOMPLETE")

    def test_completed_check_cannot_be_downgraded_by_gap(self):
        self.gap()
        self.row()["status"] = "pass"
        self.assertEqual(self.audit()["decision"], "REVIEW_INCOMPLETE")

    def test_false_complete_without_rows_or_errors_still_not_accepted(self):
        self.result["sections"]["core"]["complete"] = False
        self.assertEqual(self.audit()["decision"], "REVIEW_INCOMPLETE")

    def test_waiver_outcome_preserved(self):
        self.row()["status"] = "pass_with_waivers"
        self.assertEqual(self.audit()["decision"], "PASS_WITH_WAIVERS")

    def test_missing_automation_is_not_auto_pass(self):
        self.worksheet = {}
        self.assertEqual(self.audit()["decision"], "REVIEW_INCOMPLETE")

    def test_exact_manual_reconciliation_error_can_close_only_to_gap(self):
        self.gap()
        self.row().update(status="review_not_finished", review_complete=True,
                          standard_original_findings=[{"owner": "QA18", "status": "manual", "protected": False,
                                                       "effective_status": "review_not_finished"}])
        self.result["sections"]["core"]["errors"] = [
            {"code": "STANDARD_FINDING_UNRECONCILED", "owner": "QA18", "summary": "exact prior manual"}]
        report = self.audit()
        self.assertEqual(report["decision"], "MATERIALS_INCOMPLETE")
        self.assertTrue(report["sections"]["core"]["errors_before_automation"])
        self.assertFalse(report["sections"]["core"]["errors"])

    def test_protected_manual_is_material_incomplete_and_keeps_protection(self):
        self.gap()
        self.row().update(status="review_not_finished", review_complete=True,
                          standard_original_findings=[{"owner": "QA18", "status": "manual", "protected": True,
                                                       "effective_status": "review_not_finished"}])
        self.result["sections"]["core"]["errors"] = [
            {"code": "STANDARD_FINDING_UNRECONCILED", "owner": "QA18", "summary": "protected prior manual"}]
        report = self.audit()
        self.assertEqual(report["decision"], "MATERIALS_INCOMPLETE")
        self.assertEqual(self.row(report)["original_status"], "review_not_finished")
        self.assertTrue(self.row(report)["standard_original_findings"][0]["protected"])
        self.assertEqual(self.row(report)["standard_original_findings"][0]["status"], "manual")
        self.assertTrue(report["sections"]["core"]["errors_before_automation"])

    def test_unprotected_original_fail_is_not_material_incomplete_either(self):
        self.gap()
        self.row().update(status="review_not_finished", review_complete=True,
                          standard_original_findings=[{"owner": "QA18", "status": "fail", "protected": False,
                                                       "effective_status": "review_not_finished"}])
        report = self.audit()
        self.assertEqual(report["decision"], "REVIEW_INCOMPLETE")
        self.assertNotEqual(self.row(report)["status"], "material_incomplete")

    def test_exact_legacy_unfinished_summary_closes_when_all_rows_have_gaps(self):
        self.gap()
        self.row().update(status="review_not_finished", review_complete=True,
                          standard_original_findings=[{"owner": "QA18", "status": "manual", "protected": True,
                                                       "effective_status": "review_not_finished"}])
        self.result["sections"]["core"]["errors"] = [
            {"code": "REVIEW_NOT_FINISHED", "summary": final.LEGACY_UNFINISHED_SUMMARY}]
        report = self.audit()
        self.assertEqual(report["decision"], "MATERIALS_INCOMPLETE")
        self.assertTrue(report["sections"]["core"]["errors_before_automation"])
        self.assertFalse(report["sections"]["core"]["errors"])

    def test_generic_legacy_error_not_closed_if_another_row_unhandled_or_summary_unknown(self):
        self.gap()
        self.row().update(status="review_not_finished", review_complete=True,
                          standard_original_findings=[{"owner": "QA18", "status": "manual", "protected": True,
                                                       "effective_status": "review_not_finished"}])
        self.row(code="QA05").update(status="review_not_finished", review_complete=True)
        self.result["sections"]["core"]["errors"] = [
            {"code": "REVIEW_NOT_FINISHED", "summary": final.LEGACY_UNFINISHED_SUMMARY}]
        self.assertEqual(self.audit()["decision"], "REVIEW_INCOMPLETE")
        self.row(code="QA05")["status"] = "pass"
        self.result["sections"]["core"]["errors"][0]["summary"] = "unknown review error"
        self.assertEqual(self.audit()["decision"], "REVIEW_INCOMPLETE")

    def test_prior_confirmed_failure_or_other_error_not_closed(self):
        self.gap()
        self.row().update(status="review_not_finished", review_complete=True,
                          standard_original_findings=[{"owner": "QA18", "status": "fail", "protected": True,
                                                       "effective_status": "review_not_finished"}])
        self.result["sections"]["core"]["errors"] = [
            {"code": "STANDARD_FINDING_UNRECONCILED", "owner": "QA18", "summary": "protected"}]
        report = self.audit()
        self.assertEqual(report["decision"], "REVIEW_INCOMPLETE")
        self.assertTrue(report["sections"]["core"]["errors"])

    def test_unrelated_owner_or_unknown_error_code_not_closed(self):
        self.gap()
        self.row().update(status="review_not_finished", review_complete=True,
                          standard_original_findings=[{"owner": "QA18", "status": "manual", "protected": False,
                                                       "effective_status": "review_not_finished"}])
        for error in ({"code": "STANDARD_FINDING_UNRECONCILED", "owner": "QA05", "summary": "unrelated"},
                      {"code": "STANDARD_COMPONENT_ERROR", "owner": "QA18", "summary": "schema error"}):
            self.result["sections"]["core"]["errors"] = [error]
            report = self.audit()
            self.assertEqual(report["decision"], "REVIEW_INCOMPLETE")
            self.assertTrue(report["sections"]["core"]["errors"])

    def test_unknown_status_cannot_become_materials_and_completeness_unknown(self):
        self.gap()
        self.row()["status"] = "made_up"
        report = self.audit()
        self.assertEqual(report["decision"], "REVIEW_INCOMPLETE")
        self.assertIsNone(report["automation_final"]["materials_complete"])

    def test_row_itself_unread_cannot_be_fixed_with_complete_flag(self):
        self.gap()
        self.row()["review_complete"] = False
        self.assertEqual(self.audit()["decision"], "REVIEW_INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
