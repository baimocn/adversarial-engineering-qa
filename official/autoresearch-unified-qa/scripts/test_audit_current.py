"""Isolated current-entry behavior fixtures, never expert task conclusions.

Every package, score, session and reviewer statement below is synthetic test
data. The complete 90-row worksheet and both six-group source reviews exercise
the trusted validator; no submitted program, container or model is executed.
"""
import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock
import zipfile

import audit_current as current
import delivery_contract_review as delivery
import engineering_review as engineering


class AuditCurrentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.root = self.base / "isolated-synthetic-package"
        self.root.mkdir()
        self.write("instruction.md", "# Synthetic fixture objective\nSubmit predictions in /logs/artifacts/candidate.json.\nThe fixed metric compares the two predictions to Judge-owned labels; maximize accuracy.\nCandidate arrays have length two; rejected candidates receive -10.\nPublic feedback is optional. This package exists only for validator tests.\n")
        self.write("task.toml", 'artifacts=["/logs/artifacts"]\n[environment]\ndocker_image="python:3.11.9-slim@sha256:' + "a" * 64 + '"\ncpus=2\ngpus=0\nmemory_mb=1024\n[agent]\ntimeout_sec=3600\n[verifier]\nenvironment_mode="separate"\ntimeout_sec=300\n')
        self.write("tests/test.sh", "#!/bin/sh\nexec python /tests/grader.py --submission /logs/artifacts/candidate.json\n")
        self.write("tests/grader.py", '''import argparse
import json
from pathlib import Path

def score(payload):
    predictions = payload.get("predictions") if isinstance(payload, dict) else None
    if not isinstance(predictions, list) or len(predictions) != 2:
        return -10
    return sum(a == b for a, b in zip(predictions, (1, 0))) / 2

def main():
    args = argparse.ArgumentParser()
    args.add_argument("--submission", required=True)
    selected = args.parse_args()
    output = Path("/logs/verifier/reward.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    payload = json.loads(Path(selected.submission).read_text())
    value = score(payload)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps({"reward": value}))
    temporary.replace(output)

if __name__ == "__main__":
    main()
''')
        self.write("solution/solve.sh", "#!/bin/sh\nexec python /solution/oracle_impl.py\n")
        self.write("solution/oracle_impl.py", 'from pathlib import Path\nimport json\npath = Path("/logs/artifacts/candidate.json")\npath.parent.mkdir(parents=True, exist_ok=True)\npath.write_text(json.dumps({"predictions": [1, 0]}))\n')
        self.write("requirements.lock", "# No external Python packages; stdlib follows the pinned base-image digest.\n")
        self.write("evidence/synthetic-only.json", {"synthetic_test_fixture": True,
            "trial_id": "isolated-fixture", "candidate": "candidate.json",
            "scope": "source", "formal_adoption": False,
            "note": "Authored test data; neither a real expert score nor a task execution."})
        self.oracle_refs = ["solution/solve.sh:1-2", "solution/oracle_impl.py:1-5"]
        self.grader_refs = ["tests/test.sh:1-2", "tests/grader.py:1-25"]
        self.contract_refs = ["instruction.md:1-5", "task.toml:1-11"]

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")
        return name

    def complete_coverage(self, review):
        records = current.materials(self.root)
        review["coverage"] = {"content_read_complete": True, "algorithm_a_independent_reread": True,
            "sources": [{"path": record["path"], "sha256": record["sha256"],
                "disposition": "read" if record["kind"] == "text" else "binary_manifest",
                "read_ranges": [[1, record["lines"]]] if record.get("lines") else []} for record in records]}
        return review

    def worksheet(self):
        review = current.inspect(self.root)["review_template"]
        for row in review["checks"]:
            row.update(status="pass", summary="Isolated CPU fixture: " + row["scope"] +
                "; the pinned image, separate Judge, fixed two-value input and selected source were read for this validator case.",
                evidence=self.contract_refs + self.grader_refs, findings=[])
        notes = {
            "score_paths": "The selected Judge unlinks the old formal result, evaluates the actual candidate and atomically replaces reward.json after scoring; no task code is run by this test.",
            "timeout_budget": "The CPU fixture declares Agent 3600 seconds and independent Verifier 300 seconds; the fixed two-element scorer has no nested long-running timer.",
            "resource_alignment": "Both fresh roles select the same pinned CPU image, gpus=0 and cpus=2; the grader uses only Python stdlib.",
            "controls_logs": "The supplied source writes only the candidate output and Judge result; no Landlock, bwrap or GPU hiding control is necessary for this isolated fixture.",
            "score_scope": "The only supplied metadata explicitly identifies authored synthetic data with formal_adoption=false; no actual runtime verification or real expert score is claimed.",
            "delivery_lineage": "The synthetic evidence identifies isolated-fixture as a test-only trial and is not an external delivery ledger or a claim of formal adoption.",
        }
        review["engineering"] = {name: {"summary": text, "evidence": self.grader_refs + self.contract_refs,
            "details": text, "findings": []} for name, text in notes.items()}
        review["engineering"]["score_paths"]["branches"] = {
            "valid_candidate": {"summary": "A two-element predictions list is compared to the fixed Judge labels before atomic reward commit", "evidence": self.grader_refs, "outcome": "finite_reward_after_scoring"},
            "candidate_rejected": {"summary": "The explicit payload/length guard returns candidate hard-gate score -10 before result commit", "evidence": ["tests/grader.py:5-9"], "outcome": "candidate_gate_minus_ten"},
            "trusted_failure": {"summary": "Unhandled trusted setup, filesystem or reader failure exits without the post-scoring replace; source does not convert it into a valid zero", "evidence": self.grader_refs, "outcome": "no_new_committed_reward"},
            "interrupted": {"summary": "The previous result is removed before reading and the final path is replaced only after completed computation; an interrupted temporary write is not formal reward", "evidence": ["tests/grader.py:15-22"], "outcome": "no_partial_formal_reward"},
        }
        groups = {}
        for name, keys in delivery.DETAILS.items():
            groups[name] = {"status": "pass", "summary": "Isolated source review of " + name +
                ": pinned CPU roles, two-element artifact interface and fixed Judge-owned metric agree in the provided source.",
                "evidence": self.contract_refs + self.grader_refs,
                "details": {key: {"summary": self.detail_summary(key), "evidence": self.contract_refs + self.grader_refs} for key in keys}, "findings": []}
        protocol = groups["new_intake_protocol"]["details"]
        protocol["oracle_entry"].update(entry="solution/solve.sh", implementation_paths=["solution/oracle_impl.py"], evidence=self.oracle_refs)
        protocol["dependency_lock"].update(locked=True, evidence=["requirements.lock:1", "task.toml:1-7"])
        protocol["formal_reward"].update(output_files=["/logs/verifier/reward.json"], json_main_key="reward")
        protocol["gate_penalty"].update(value=-10)
        review["delivery_contract"] = {"groups": groups, "reward_runs": []}
        return self.complete_coverage(review)

    def detail_summary(self, key):
        return {
            "goal_metric": "The goal is accuracy on the fixed two-label Judge comparison; maximize sum of matches divided by two.",
            "allowed_scope": "The candidate controls only predictions in the transferred JSON artifact; the Judge-owned label comparison is fixed.",
            "submission_contract": "The grader reads predictions from the declared /logs/artifacts/candidate.json path and accepts exactly two values.",
            "enforced_constraints": "The explicit array length/type guard matches the public length-two contract and its documented -10 rejection.",
            "completion_conditions": "The normal path consumes the selected candidate before the final atomic reward.json commit.",
            "endpoints": "For this authored fixture the stated score endpoints are zero accuracy and one accuracy; no latency hardware anchor is used.",
            "direction_formula": "The explicit fixed metric is higher-is-better sum of two matches divided by two.",
            "anchor_values": "The synthetic protocol uses baseline B=0 and upper U=1; these are validator fixture facts rather than real expert measurements.",
            "protocol_binding": "The selected source binds its two predictions to the fixed Judge-owned comparison; unrelated trial splits are not subtracted.",
            "hardware_calibration": "This fixed accuracy calculation is hardware-insensitive; no timing or fixed-wall-clock anchor is borrowed.",
            "work": "Work selects the pinned Python CPU image with cpus=2 and gpus=0 and needs only the Python stdlib.",
            "judge": "Judge is a separate fresh environment reusing the pinned CPU image and uploads the task-owned tests entry.",
            "dependencies": "No kernel isolation feature is called; only the pinned Python stdlib and ordinary filesystem operations are used.",
            "environment_compatibility": "The provided source has no Landlock/bwrap requirement; no actual provider startup is claimed by this source-only fixture.",
            "control_necessity": "Protected Judge code is supplied independently; there is no sole failing GPU-hiding or nested kernel control in this source.",
            "rollout_evidence": "No executed task rollout is selected; authored metadata is explicitly synthetic and does not certify Verifier availability.",
            "agent_verifier_separation": "Agent and Verifier timeout declarations are independent; no-score or budget timeout alone adds no new rejection rule.",
            "admission_basis": "Only current source and supplied test artifacts are reviewed; no historical or one-hour admission exception is claimed.",
            "oracle_entry": "The required solution/solve.sh invokes solution/oracle_impl.py, which produces the normal predictions artifact rather than reward.",
            "dependency_lock": "There are no external Python dependencies; the entire stdlib runtime is bound to the explicit base-image digest and the lock note.",
            "formal_reward": "The scorer writes only /logs/verifier/reward.json, with the finite primary numeric reward key, after computing the metric.",
            "gate_penalty": "The source rejects an invalid predictions shape with the exact candidate hard-gate result -10.",
        }[key]

    def fact(self, rule="reward_protocol", **values):
        return {"rule": rule, "reason": "The selected current scoring writer emits a boolean instead of a finite numeric main reward",
            "remediation": "Write the completed numeric main reward under the reward key at the authoritative result path",
            "responsibility": "author", "evidence": ["tests/grader.py:19-22"], **values}

    def check(self, review, code):
        return next(row for row in review["checks"] if row["id"] == code)

    def assert_inspection_failure(self, report):
        self.assertEqual(report["decision"], "FAIL")
        self.assertEqual(report["result"], "不通过")
        self.assertTrue(report["inspection_issues"])
        self.assertTrue(all(issue["responsibility"] == "inspection" for issue in report["inspection_issues"]))

    def cli(self, review=None, *, source=None, out=None, prepare=False):
        out = out or self.base / "output"
        argv = [str(source or self.root), "--out-dir", str(out)]
        if prepare:
            argv.append("--prepare-only")
        else:
            review_path = self.base / "internal-review.json"
            review_path.write_text(json.dumps(review if review is not None else self.worksheet()))
            argv += ["--review", str(review_path)]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = current.main(argv)
        return code, json.loads(output.getvalue().splitlines()[-1]), out

    def test_complete_synthetic_worksheet_passes_all_ninety_rows_and_twelve_groups(self):
        result = current.inspect(self.root, self.worksheet())
        self.assertEqual(result["decision"], "PASS", result["inspection_issues"])
        self.assertEqual(result["result"], "通过")
        self.assertEqual(len(result["checks"]), 90)
        self.assertEqual(result["coverage_counts"], {"core": 31, "format": 7, "current_standard": 3, "supplement": 49})
        for component in ("engineering", "delivery_contract"):
            self.assertEqual(len(result["facts"][component]["checks"]), 6)
            self.assertTrue(all(row["review_complete"] for row in result["facts"][component]["checks"]))
        self.assertFalse(result["task_code_executed"])
        final_out = self.base / "complete-final-json"
        current.write(result, final_out)
        final_json = current.read_json(final_out / "report.json")

        def assert_final_nodes(value):
            if isinstance(value, dict):
                self.assertNotIn("review_template", value)
                self.assertNotIn("template", value)
                self.assertNotEqual(value.get("status"), "unreviewed")
                for nested in value.values():
                    assert_final_nodes(nested)
            elif isinstance(value, list):
                for nested in value:
                    assert_final_nodes(nested)

        assert_final_nodes(final_json)

    def test_nonproject_l2_adversarial_coverage_is_recommendation_and_does_not_poison_qa17(self):
        review = self.worksheet()
        self.check(review, "QA20").update(status="fail", findings=[self.fact("adversarial_rollout",
            reason="The isolated fixture includes no induced-cheat rollout, so this additional dynamic coverage is unverified", blocking=True, level="L0")])
        result = current.inspect(self.root, review)
        self.assertEqual(result["decision"], "PASS")
        self.assertEqual(result["recommendations"][0]["level"], "L2")
        self.assertFalse(result["recommendations"][0]["blocking"])
        self.assertEqual(next(row for row in result["checks"] if row["id"] == "QA17")["result"], "通过")

    def test_module_l2_recommendation_cannot_be_retyped_by_an_arbitrary_code_prefix(self):
        review = self.worksheet()
        review["engineering"]["score_paths"]["findings"] = [{
            "rule": "adversarial_rollout", "code": "current.adversarial_score_probe", "owner_id": "H04",
            "reason": "The synthetic fixture includes no induced timing-replay attack rollout",
            "remediation": "Consider the additional induced timing-replay verification when reviewing advanced coverage",
            "responsibility": "author", "evidence": ["tests/grader.py:5-9"], "blocking": True}]
        result = current.inspect(self.root, review)
        self.assertEqual(result["decision"], "PASS")
        self.assertTrue(any(fact.get("code") == "current.adversarial_score_probe" and fact["level"] == "L2"
                            for fact in result["recommendations"]))
        self.assertEqual(next(row for row in result["checks"] if row["id"] == "QA17")["result"], "通过")

    def test_continuing_project_method_space_requirement_blocks_without_becoming_l0(self):
        # Nov 7 meeting steering preserves the project's G01/G03 requirements;
        # their algorithmic L1/L2 labels are retained instead of relabelling L0.
        review = self.worksheet()
        self.check(review, "G01").update(status="fail", findings=[self.fact("method_space",
            reason="The isolated two-value artifact interface provides no substantive algorithmic research space",
            remediation="Expose a meaningful candidate method interface under the continuing project requirement",
            level="L0", blocking=False)])
        result = current.inspect(self.root, review)
        self.assertEqual(result["decision"], "FAIL")
        fact = next(value for value in result["findings"] if value["rule"] == "method_space")
        self.assertTrue(fact["blocking"])
        self.assertEqual(fact["level"], "L1")
        self.assertEqual(fact["requirement_source"], "project_continuation")
        self.assertEqual(next(row for row in result["checks"] if row["id"] == "QA17")["result"], "通过")

    def test_continuing_project_reference_requirement_blocks_without_becoming_l0(self):
        review = self.worksheet()
        self.check(review, "G03").update(status="fail", findings=[self.fact("reference_calibration",
            reason="The synthetic Oracle attains normalized score one outside the continuing project Reference interval",
            remediation="Improve the task's Reference calibration under the continuing project G03 requirement",
            level="L0", blocking=False)])
        result = current.inspect(self.root, review)
        self.assertEqual(result["decision"], "FAIL")
        fact = next(value for value in result["findings"] if value["rule"] == "reference_calibration")
        self.assertTrue(fact["blocking"])
        self.assertEqual(fact["level"], "L2")
        self.assertEqual(fact["requirement_source"], "project_continuation")
        self.assertEqual(next(row for row in result["checks"] if row["id"] == "QA17")["result"], "通过")

    def test_scientific_project_finding_shared_under_h04_does_not_become_a_harbor_failure(self):
        review = self.worksheet()
        review["engineering"]["score_paths"]["findings"] = [{
            "rule": "reference_calibration", "code": "review.project_reference_interval", "owner_id": "H04",
            "reason": "The supplied synthetic score comparison violates the continuing project Reference calibration requirement",
            "remediation": "Repair project Reference calibration while retaining the independently valid Harbor scoring path",
            "responsibility": "author", "evidence": ["tests/grader.py:5-9"], "blocking": False}]
        result = current.inspect(self.root, review)
        self.assertEqual(result["decision"], "FAIL")
        self.assertTrue(any(fact.get("rule") == "reference_calibration" and fact["level"] == "L2" and fact["blocking"]
                            for fact in result["findings"]))
        self.assertEqual(next(row for row in result["checks"] if row["id"] == "QA17")["result"], "通过")

    def test_current_l0_finding_cannot_be_downgraded_by_supplied_level_or_blocking(self):
        review = self.worksheet()
        self.check(review, "CS04")["findings"] = [self.fact(blocking=False, level="L2")]
        result = current.inspect(self.root, review)
        self.assertEqual(result["decision"], "FAIL")
        self.assertTrue(result["findings"][0]["blocking"])
        self.assertEqual(result["findings"][0]["level"], "L0")

    def test_current_invalid_reward_is_an_actual_failure(self):
        self.write("run/reward.json", {"reward": True})
        review = self.worksheet()
        review["delivery_contract"]["reward_runs"] = [{"files": ["run/reward.json"], "trial_id": 1}]
        result = current.inspect(self.root, review)
        self.assertEqual(result["decision"], "FAIL")
        self.assertTrue(any(fact.get("code") == "runtime.selected_current_reward_invalid" for fact in result["findings"]))

    def test_missing_oracle_entry_is_a_current_failure(self):
        (self.root / "solution/solve.sh").unlink()
        review = self.worksheet()
        review["delivery_contract"]["groups"]["new_intake_protocol"]["details"]["oracle_entry"]["evidence"] = ["task.toml:1-11"]
        result = current.inspect(self.root, review)
        self.assertEqual(result["decision"], "FAIL")
        self.assertTrue(any(fact.get("code") == "current.oracle_entry_missing" for fact in result["findings"]))

    def test_old_context_fields_cannot_disable_default_protocols(self):
        review = self.worksheet()
        review.update(context={"mode": "legacy-waiver", "intake_cohort": "legacy_831", "target_level": "L0"})
        review["delivery_contract"]["groups"]["new_intake_protocol"]["details"]["gate_penalty"]["value"] = -2
        result = current.inspect(self.root, review)
        self.assertEqual(result["decision"], "FAIL")
        self.assertTrue(any(fact.get("code") == "current.gate_penalty" for fact in result["findings"]))

    def test_unknown_provider_source_is_platform_scope_not_a_failure(self):
        review = self.worksheet()
        review.update(provider="unknown", context={"provider": "unknown", "package_stage": "source"})
        result = current.inspect(self.root, review)
        self.assertEqual(result["decision"], "PASS")
        self.assertEqual(result["platform_runtime_status"], "not_executed")

    def platform_scope_review(self):
        review = self.worksheet()
        group = review["delivery_contract"]["groups"]["infra_capabilities"]
        group["details"]["environment_compatibility"].update(status="evidence_limited",
            summary="The source was read completely, but no target-provider startup log is included; actual dynamic environment compatibility remains unverified")
        group["findings"] = [{"rule": "platform_scope", "owner_id": "H03", "blocking": False,
            "reason": "The source-only fixture provides no executed target-provider startup evidence",
            "remediation": "Have the platform verify the actual target capabilities when a runtime is selected; no new expert proof is required for the source review",
            "responsibility": "platform", "evidence": ["task.toml:1-11"]}]
        return review

    def test_only_infra_dynamic_environment_compatibility_may_be_platform_scope(self):
        result = current.inspect(self.root, self.platform_scope_review())
        self.assertEqual(result["decision"], "PASS")
        self.assertTrue(any(note.get("group") == "infra_capabilities" for note in result["platform_notes"]))
        self.assertFalse(result["facts"]["delivery_contract"]["claims"]["runtime"]["verifier_verified"])

    def test_one_platform_scope_note_does_not_clear_unreviewed_dependencies_in_same_group(self):
        review = self.platform_scope_review()
        review["delivery_contract"]["groups"]["infra_capabilities"]["details"]["dependencies"].update(
            status="evidence_limited", summary="The selected dependency reading remains incomplete independently of target-provider startup compatibility")
        self.assert_inspection_failure(current.inspect(self.root, review))

    def test_missing_or_duplicate_row_cannot_pass(self):
        for operation in ("missing", "duplicate"):
            review = self.worksheet()
            if operation == "missing":
                review["checks"].pop()
            else:
                review["checks"].append(copy.deepcopy(review["checks"][0]))
            self.assert_inspection_failure(current.inspect(self.root, review))

    def test_required_engineering_and_delivery_groups_cannot_be_skipped(self):
        for component, name in (("engineering", "score_paths"), ("delivery_contract", "task_contract")):
            review = self.worksheet()
            rows = review[component].get("groups", review[component])
            del rows[name]
            result = current.inspect(self.root, review)
            self.assert_inspection_failure(result)
            self.assertEqual(len(result["checks"]), 90)

    def test_blank_default_prepare_template_cannot_be_promoted_to_pass(self):
        prepared = current.inspect(self.root)
        result = current.inspect(self.root, prepared["review_template"])
        self.assert_inspection_failure(result)

    def test_bad_reference_is_inspection_failure_not_author_repair(self):
        review = self.worksheet()
        self.check(review, "QA02")["evidence"] = ["absent.json#/baseline"]
        result = current.inspect(self.root, review)
        self.assert_inspection_failure(result)
        self.assertFalse(current.repair_actions(result)["author"])

    def test_internal_schema_version_and_standard_must_match_current(self):
        for change in ({"schema_version": 999}, {"standard": "legacy-waiver"}):
            review = self.worksheet()
            review.update(change)
            self.assert_inspection_failure(current.inspect(self.root, review))

    def test_malformed_coverage_is_reported_as_inspection_failure(self):
        review = self.worksheet()
        review["coverage"] = [{"not": "an object"}]
        code, _, out = self.cli(review)
        self.assertEqual(code, 1)
        self.assert_inspection_failure(current.read_json(out / "report.json"))

    def test_coverage_cannot_omit_reading_or_algorithm_a_independent_reread(self):
        for flag in ("content_read_complete", "algorithm_a_independent_reread"):
            review = self.worksheet()
            review["coverage"][flag] = False
            self.assert_inspection_failure(current.inspect(self.root, review))

    def test_source_hash_binds_the_exact_read_version(self):
        review = self.worksheet()
        self.write("instruction.md", (self.root / "instruction.md").read_text() + "Changed after the recorded review.\n")
        self.assert_inspection_failure(current.inspect(self.root, review))

    def test_source_mutation_during_the_audit_prevents_a_pass(self):
        review = self.worksheet()
        real_audit = engineering.audit

        def audit_then_mutate(*args, **kwargs):
            result = real_audit(*args, **kwargs)
            self.write("instruction.md", (self.root / "instruction.md").read_text() + "Changed during the isolated validator call.\n")
            return result

        with mock.patch.object(engineering, "audit", side_effect=audit_then_mutate):
            self.assert_inspection_failure(current.inspect(self.root, review))

    def test_read_ranges_must_cover_all_lines_and_all_sources(self):
        for operation in ("gap", "missing", "wrong_hash"):
            review = self.worksheet()
            source = next(row for row in review["coverage"]["sources"] if row["path"] == "tests/grader.py")
            if operation == "gap":
                source["read_ranges"] = [[1, 5], [7, 25]]
            elif operation == "missing":
                review["coverage"]["sources"].remove(source)
            else:
                source["sha256"] = "0" * 64
            self.assert_inspection_failure(current.inspect(self.root, review))

    def test_binary_assets_are_bound_to_the_manifest(self):
        path = self.root / "data/asset.bin"
        path.parent.mkdir()
        path.write_bytes(b"\0\xfffixture")
        review = self.worksheet()
        result = current.inspect(self.root, review)
        self.assertEqual(result["decision"], "PASS")
        next(row for row in review["coverage"]["sources"] if row["path"] == "data/asset.bin")["disposition"] = "unreviewed"
        self.assert_inspection_failure(current.inspect(self.root, review))

    def test_large_supplied_text_is_fully_bound_without_becoming_an_author_failure(self):
        self.write("evidence/large.log", "Synthetic authored test log\n" + "x" * (5 * 1024 * 1024) + "\n")
        review = self.worksheet()
        record = next(row for row in review["coverage"]["sources"] if row["path"] == "evidence/large.log")
        self.assertEqual(record["read_ranges"], [[1, 2]])
        self.assertEqual(current.inspect(self.root, review)["decision"], "PASS")
        record["read_ranges"] = [[1, 1]]
        self.assert_inspection_failure(current.inspect(self.root, review))

    def test_utf8_character_crossing_prefix_boundary_still_requires_text_read_coverage(self):
        self.write("evidence/chinese.txt", "a" * 4095 + "中文\nsecond line\n")
        record = next(row for row in current.materials(self.root) if row["path"] == "evidence/chinese.txt")
        self.assertEqual(record["kind"], "text")
        self.assertEqual(record["lines"], 2)
        review = self.worksheet()
        self.assertEqual(current.inspect(self.root, review)["decision"], "PASS")
        source = next(row for row in review["coverage"]["sources"] if row["path"] == "evidence/chinese.txt")
        source.update(disposition="binary_manifest", read_ranges=[])
        self.assert_inspection_failure(current.inspect(self.root, review))

    def test_prepare_writes_internal_controls_without_a_final_report_or_pass(self):
        code, output, out = self.cli(prepare=True)
        self.assertEqual(code, 0)
        self.assertEqual(output["operation"], "prepared")
        self.assertFalse(output["final_result_available"])
        self.assertNotIn("decision", output)
        self.assertTrue((out / "inspection/review_template.json").is_file())
        for name in ("report.json", "report.md", "report.txt", "return_to_expert.txt"):
            self.assertFalse((out / name).exists())

    def test_prepare_cannot_leave_a_stale_final_pass_in_the_same_output(self):
        out = self.base / "reused-output"
        out.mkdir()
        for name in ("report.json", "report.md", "report.txt", "return_to_expert.txt"):
            (out / name).write_text('{"decision":"PASS","result":"通过"}')
        code, output, _ = self.cli(prepare=True, out=out)
        self.assertEqual(code, 0)
        self.assertFalse(output["final_result_available"])
        for name in ("report.json", "report.md", "report.txt", "return_to_expert.txt"):
            self.assertFalse((out / name).exists())

    def test_final_output_cannot_overwrite_the_selected_internal_review(self):
        out = self.base / "colliding-output"
        out.mkdir()
        selected = out / "report.json"
        selected.write_text(json.dumps(self.worksheet()))
        before = selected.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            current.main([str(self.root), "--out-dir", str(out), "--review", str(selected)])
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(selected.read_bytes(), before)
        self.assertFalse((out / "report.md").exists())

    def test_prepare_cannot_be_combined_with_a_review_and_destroy_a_prior_output(self):
        out = self.base / "prepare-review-output"
        out.mkdir()
        selected = out / "report.json"
        selected.write_text(json.dumps(self.worksheet()))
        before = selected.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            current.main([str(self.root), "--out-dir", str(out), "--prepare-only", "--review", str(selected)])
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(selected.read_bytes(), before)

    def test_known_findings_survive_later_finding_and_row_schema_errors(self):
        review = self.worksheet()
        self.check(review, "QA06")["findings"] = [self.fact(), {"rule": "unknown"}]
        self.check(review, "QA21")["summary"] = "pass"
        result = current.inspect(self.root, review)
        self.assertEqual(result["decision"], "FAIL")
        self.assertTrue(any(fact.get("check_id") == "QA06" and fact.get("rule") == "reward_protocol" for fact in result["findings"]))
        self.assertTrue(result["inspection_issues"])
        self.assertTrue(current.repair_actions(result)["author"])

    def test_known_finding_survives_bad_summary_and_outer_evidence_on_its_own_row(self):
        review = self.worksheet()
        row = self.check(review, "QA06")
        row.update(summary="pass", evidence=["missing-reader.py:1"], findings=[self.fact()])
        result = current.inspect(self.root, review)
        self.assertEqual(result["decision"], "FAIL")
        self.assertTrue(any(fact.get("check_id") == "QA06" for fact in result["findings"]))
        self.assertTrue(result["inspection_issues"])

    def test_duplicate_json_keys_are_rejected_as_an_inspection_failure(self):
        review_path = self.base / "duplicate-review.json"
        review_path.write_text('{"schema_version":1,"schema_version":999}')
        out = self.base / "duplicate-json-output"
        with contextlib.redirect_stdout(io.StringIO()):
            code = current.main([str(self.root), "--out-dir", str(out), "--review", str(review_path)])
        self.assertEqual(code, 1)
        self.assert_inspection_failure(current.read_json(out / "report.json"))

    def test_audit_and_cli_do_not_execute_or_modify_package_programs(self):
        marker = self.base / "MUST_NOT_BE_CREATED"
        self.write("unsafe_candidate.py", "from pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('executed')\n")
        review = self.worksheet()
        before = {path.relative_to(self.root).as_posix(): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        with mock.patch("subprocess.run", side_effect=AssertionError("submitted execution forbidden")):
            result = current.inspect(self.root, review)
            code, _, _ = self.cli(review)
        self.assertEqual(result["decision"], "PASS")
        self.assertEqual(code, 0)
        self.assertFalse(marker.exists())
        after = {path.relative_to(self.root).as_posix(): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(before, after)

    def test_unsafe_zip_and_tar_paths_never_escape_extraction(self):
        for suffix in ("zip", "tar"):
            archive = self.base / ("unsafe." + suffix)
            if suffix == "zip":
                with zipfile.ZipFile(archive, "w") as stream:
                    stream.writestr("../escaped.txt", "unsafe")
            else:
                with tarfile.open(archive, "w") as stream:
                    entry = tarfile.TarInfo("../escaped.txt")
                    entry.size = 6
                    stream.addfile(entry, io.BytesIO(b"unsafe"))
            with self.assertRaises(ValueError):
                current.unpack(archive, self.base / ("extract-" + suffix))
        self.assertFalse((self.base / "escaped.txt").exists())

    def test_unsafe_archive_cli_returns_inspection_fail_without_executing_it(self):
        archive = self.base / "bad-input.zip"
        with zipfile.ZipFile(archive, "w") as stream:
            stream.writestr("../escaped.txt", "unsafe")
        code, output, out = self.cli(source=archive)
        self.assertEqual(code, 1)
        self.assertEqual(output["decision"], "FAIL")
        self.assert_inspection_failure(current.read_json(out / "report.json"))
        self.assertFalse((self.base / "escaped.txt").exists())

    def test_legacy_mode_flags_cannot_select_a_different_entry_route(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            current.main([str(self.root), "--out-dir", str(self.base / "wrong-route"), "--mode", "legacy-waiver"])
        self.assertEqual(raised.exception.code, 2)

    def test_historical_script_names_dispatch_to_the_same_current_cli(self):
        for name in ("audit_auto.py", "audit_unified.py"):
            script = Path(current.__file__).with_name(name)
            out = self.base / (name + "-prepared")
            prepared = subprocess.run([sys.executable, str(script), str(self.root), "--out-dir", str(out), "--prepare-only"],
                capture_output=True, text=True, timeout=30)
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            message = json.loads(prepared.stdout.splitlines()[-1])
            self.assertEqual(message["operation"], "prepared")
            self.assertFalse(message["final_result_available"])
            self.assertFalse((out / "report.json").exists())
            template = current.read_json(out / "inspection/review_template.json")
            self.assertEqual(template["standard"], "current-2189")
            rejected = subprocess.run([sys.executable, str(script), str(self.root), "--out-dir", str(self.base / (name + "-old-route")),
                "--mode", "legacy-waiver"], capture_output=True, text=True, timeout=30)
            self.assertEqual(rejected.returncode, 2)
            self.assertIn("unrecognized arguments", rejected.stderr)

    def test_tar_links_and_special_files_are_forbidden(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE):
            archive = self.base / ("unsafe-" + kind.decode() + ".tar")
            with tarfile.open(archive, "w") as stream:
                entry = tarfile.TarInfo("linked")
                entry.type = kind
                entry.linkname = "../outside"
                stream.addfile(entry)
            with self.assertRaises(ValueError):
                current.unpack(archive, self.base / ("extract-" + kind.decode()))

    def test_normal_zip_and_tar_inputs_produce_the_same_binary_pass(self):
        review = self.worksheet()
        for suffix in ("zip", "tar"):
            archive = self.base / ("safe." + suffix)
            if suffix == "zip":
                with zipfile.ZipFile(archive, "w") as stream:
                    for path in self.root.rglob("*"):
                        if path.is_file():
                            stream.write(path, path.relative_to(self.root).as_posix())
            else:
                with tarfile.open(archive, "w") as stream:
                    for path in self.root.rglob("*"):
                        if path.is_file():
                            stream.add(path, arcname=path.relative_to(self.root).as_posix(), recursive=False)
            code, output, out = self.cli(review, source=archive, out=self.base / ("safe-output-" + suffix))
            self.assertEqual(code, 0)
            self.assertEqual(output["decision"], "PASS")
            self.assertEqual(current.read_json(out / "report.json")["result"], "通过")

    def test_final_cli_writes_only_the_two_public_results(self):
        for bad in (False, True):
            review = self.worksheet()
            if bad:
                self.check(review, "QA06")["findings"] = [self.fact()]
            code, output, out = self.cli(review, out=self.base / ("final-" + str(bad)))
            self.assertEqual(code, int(bad))
            self.assertIn(output["decision"], {"PASS", "FAIL"})
            self.assertEqual(output["result"], "不通过" if bad else "通过")
            for name in ("report.json", "report.md", "report.txt", "return_to_expert.txt"):
                self.assertTrue((out / name).is_file())


if __name__ == "__main__":
    unittest.main()
