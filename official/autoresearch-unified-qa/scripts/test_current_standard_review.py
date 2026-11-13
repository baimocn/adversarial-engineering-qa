"""Positive, negative, and scope-boundary fixtures; never run task/Docker/model code."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import current_standard_review as csr

class CurrentStandardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cfg = {"environment": {"docker_image": "registry.example/task:v1"}, "verifier": {"environment_mode": "separate"}}

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data) if not isinstance(data, str) else data)
        return name

    def check(self, code, review=None, stage="source", config=None):
        result = csr.audit(self.root, config=self.cfg if config is None else config, review=review, stage=stage)
        return next(row for row in result["checks"] if row["id"] == code)

    def test_fixed_order_and_no_execution(self):
        result = csr.audit(self.root)
        self.assertEqual([r["id"] for r in result["checks"]], ["CS03", "CS04", "CS05"])
        self.assertFalse(result["executed_task"])

    def test_removed_build_and_size_checks_are_not_run_or_reported(self):
        self.write("environment/Dockerfile", "FROM python:latest\nRUN pip install numpy\n")
        review = {"builds": [{"dockerfile": "missing/Dockerfile"}],
                  "images": [{"source": "missing-size.json"}]}
        with mock.patch.object(csr, "_read", wraps=csr._read) as read:
            result = csr.audit(self.root, review=review, stage="runtime",
                               config={"environment": {"docker_image": "python:latest"}})
        self.assertEqual([row["id"] for row in result["checks"]], ["CS03", "CS04", "CS05"])
        self.assertFalse(any("Dockerfile" in call.args[1] or "size" in call.args[1]
                             for call in read.call_args_list))
        report = json.dumps(result, ensure_ascii=False)
        for removed in ("CS01", "CS02", "锁文件", "镜像体积", "50G", "missing-size"):
            self.assertNotIn(removed, report)

    def test_template_has_no_build_or_image_submission_requirements(self):
        self.assertEqual(set(csr.template()), {"reward_runs", "agent_runs", "note"})

    def reward_review(self, values, historical=False):
        files = []
        for name, value in values.items():
            files.append(self.write("trial/verifier/" + name, value))
        return {"reward_runs": [{"run_id": "same-trial", "files": files, "historical": historical}]}

    def test_current_dual_output_is_compatible(self):
        review = self.reward_review({"reward.txt": "0.42", "reward.json": {"reward": 0.42}})
        self.assertEqual(self.check("CS03", review)["status"], "pass")

    def test_current_dual_uses_json_even_when_txt_is_invalid(self):
        review = self.reward_review({"reward.txt": "not a score", "reward.json": {"reward": 0.38}})
        for stage in ("source", "runtime", "history"):
            with self.subTest(stage=stage):
                self.assertEqual(self.check("CS03", review, stage=stage)["status"], "pass")
                row = self.check("CS04", review, stage=stage)
                self.assertEqual(row["status"], "pass")
                contract = next(o["native_contract"] for o in self.check("CS03", review, stage=stage)["observations"]
                                if "native_contract" in o)
                self.assertEqual(contract["main_score"], 0.38)

    def test_dual_cannot_fall_back_to_txt_when_selected_json_is_invalid(self):
        review = self.reward_review({"reward.txt": "0.42", "reward.json": {"reward": float("nan")}})
        self.assertEqual(self.check("CS04", review)["status"], "fail")

    def test_no_new_negative_score_protocol(self):
        for value in (-10, -11, 0):
            with self.subTest(value=value):
                self.assertEqual(self.check("CS04", self.reward_review({"reward.json": {"score": value}}))["status"], "pass")

    def test_historical_dual_is_compatible_without_rerun(self):
        review = self.reward_review({"reward.txt": "0.42", "reward.json": {"reward": 0.38}}, True)
        self.assertEqual(self.check("CS03", review)["status"], "pass")
        self.assertEqual(self.check("CS04", review)["status"], "pass")

    def test_two_trials_cannot_be_miscombined_as_dual(self):
        self.write("trial1/reward.txt", "0.4")
        self.write("trial2/reward.json", {"reward": 0.5})
        review = {"reward_runs": [{"files": ["trial1/reward.txt", "trial2/reward.json"]}]}
        row = self.check("CS03", review)
        self.assertEqual(row["status"], "review")
        self.assertFalse(row["problems"])

    def test_cleanup_both_filenames_is_not_dual_output(self):
        self.write("tests/test.sh", "rm -f /logs/verifier/reward.txt /logs/verifier/reward.json\necho 0.4 > /logs/verifier/reward.txt\n")
        row = self.check("CS03")
        self.assertNotEqual(row["status"], "fail")

    def test_single_accuracy_keeps_current_compatibility_without_new_receipt(self):
        row = self.check("CS04", self.reward_review({"reward.json": {"accuracy": 0.8}}))
        self.assertEqual(row["status"], "pass")

    def test_historical_single_accuracy_keeps_compatibility(self):
        row = self.check("CS04", self.reward_review({"reward.json": {"accuracy": 0.8}}, historical=True))
        self.assertEqual(row["status"], "pass")

    def test_runtime_single_accuracy_without_new_chain_is_compatible(self):
        row = self.check("CS04", self.reward_review({"reward.json": {"accuracy": 0.8}}), stage="runtime")
        self.assertEqual(row["status"], "pass")

    def test_multimetric_without_mapping_requires_actual_chain_review(self):
        row = self.check("CS04", self.reward_review({"reward.json": {"accuracy": 0.8, "latency": 10}}))
        self.assertEqual(row["status"], "review")

    def test_explicit_non_numeric_reward_cannot_hide_behind_accuracy(self):
        row = self.check("CS04", self.reward_review({"reward.json": {"reward": "failed", "accuracy": 0.8}}))
        self.assertEqual(row["status"], "fail")

    def test_duplicate_reward_key_rejected_by_native_reader(self):
        row = self.check("CS04", self.reward_review({"reward.json": '{"reward":0.5,"reward":0.8}'}))
        self.assertEqual(row["status"], "fail")

    def test_historical_duplicate_reward_key_cannot_pass(self):
        review = self.reward_review({"reward.json": '{"reward":0.5,"reward":0.8}'}, historical=True)
        row = self.check("CS04", review)
        self.assertEqual(row["status"], "review")
        self.assertTrue(any("duplicate JSON key" in message for message in row["limitations"]))

    def test_metadata_is_compatible_for_current_and_historical_unique_main_score(self):
        for value in ({"accuracy": 0.8, "status": "ok"}, {"reward": 0.8, "status": "ok"}):
            for historical in (False, True):
                with self.subTest(value=value, historical=historical):
                    review = self.reward_review({"reward.txt": "bad", "reward.json": value}, historical=historical)
                    self.assertEqual(self.check("CS03", review)["status"], "pass")
                    self.assertEqual(self.check("CS04", review)["status"], "pass")

    def test_metadata_does_not_hide_multiple_unmapped_metrics(self):
        for historical in (False, True):
            with self.subTest(historical=historical):
                review = self.reward_review({"reward.json": {"accuracy": 0.8, "latency": 10, "status": "ok"}}, historical=historical)
                self.assertEqual(self.check("CS04", review)["status"], "review")

    def test_historical_invalid_main_scores_remain_unresolved(self):
        for raw in ('{"reward":true}', '{"reward":NaN}', '{"reward":1e999}', '{"reward":' + '9' * 400 + '}'):
            with self.subTest(raw=raw[:80]):
                review = self.reward_review({"reward.json": raw}, historical=True)
                self.assertEqual(self.check("CS04", review)["status"], "review")

    def test_existing_adapter_and_receipt_can_identify_main_score(self):
        review = self.reward_review({"reward.json": {"accuracy": 0.8, "latency": 10}})
        self.write("reader.py", "value = data['accuracy']\n")
        self.write("receipt.json", {"source_reward": "trial/verifier/reward.json", "score_key": "accuracy", "reward": 0.8})
        review["reward_runs"][0]["score_mapping"] = {"key": "accuracy", "reader_source": "reader.py", "runtime_evidence": "receipt.json"}
        self.assertEqual(self.check("CS04", review)["status"], "pass")

    def test_multimetric_existing_reader_chain_needs_no_new_json_receipt(self):
        review = self.reward_review({"reward.json": {"accuracy": 0.8, "latency": 10}})
        self.write("reader.py", "data = json.loads(Path('trial/verifier/reward.json').read_text())\nvalue = data['accuracy']\n")
        review["reward_runs"][0]["score_mapping"] = {"key": "accuracy", "reader_source": "reader.py"}
        for stage in ("source", "runtime", "history"):
            with self.subTest(stage=stage):
                self.assertEqual(self.check("CS04", review, stage=stage)["status"], "pass")

    def test_multimetric_existing_text_log_can_bind_reader(self):
        review = self.reward_review({"reward.json": {"accuracy": 0.8, "latency": 10}})
        self.write("reader.py", "value = data['accuracy']\n")
        self.write("existing-read.log", "reader.py read trial/verifier/reward.json key accuracy -> 0.8\n")
        review["reward_runs"][0]["score_mapping"] = {"key": "accuracy", "reader_source": "reader.py", "runtime_evidence": "existing-read.log"}
        self.assertEqual(self.check("CS04", review)["status"], "pass")

    def test_multimetric_existing_json_log_can_use_original_shape(self):
        review = self.reward_review({"reward.json": {"accuracy": 0.8, "latency": 10}})
        self.write("reader.py", "value = data['accuracy']\n")
        self.write("original-log.json", {"input_path": "trial/verifier/reward.json", "metric": "accuracy", "value": 0.8})
        review["reward_runs"][0]["score_mapping"] = {"key": "accuracy", "reader_source": "reader.py", "runtime_evidence": "original-log.json"}
        self.assertEqual(self.check("CS04", review)["status"], "pass")

    def test_multimetric_unbound_key_cannot_be_hand_passed(self):
        review = self.reward_review({"reward.json": {"accuracy": 0.8, "latency": 10}})
        self.write("reader.py", "value = data['accuracy']\n")
        review["reward_runs"][0]["score_mapping"] = {"key": "accuracy", "reader_source": "reader.py", "status": "pass"}
        self.assertEqual(self.check("CS04", review)["status"], "review")

    def test_multimetric_contradictory_existing_receipt_still_fails(self):
        review = self.reward_review({"reward.json": {"accuracy": 0.8, "latency": 10}})
        self.write("reader.py", "value = data['accuracy']\n")
        self.write("receipt.json", {"source_reward": "another/reward.json", "score_key": "accuracy", "reward": 0.8})
        review["reward_runs"][0]["score_mapping"] = {"key": "accuracy", "reader_source": "reader.py", "runtime_evidence": "receipt.json"}
        self.assertEqual(self.check("CS04", review)["status"], "fail")

    def test_adapter_cannot_override_bad_reward_value(self):
        review = self.reward_review({"reward.json": {"reward": "bad", "accuracy": 0.8}})
        review["reward_runs"][0]["score_mapping"] = {"key": "accuracy", "status": "pass"}
        self.assertEqual(self.check("CS04", review)["status"], "fail")

    def agent_review(self, count, reason="timeout", complete=True):
        self.write("agent_result.json", {"exit_reason": reason})
        self.write("session.json", {"agent_role": "main", "complete": complete, "messages": [{"role": "assistant", "response_id": str(i)} for i in range(count)]})
        return {"agent_runs": [{"run_id": "a", "result_source": "agent_result.json", "session_source": "session.json"}]}

    def test_more_than_50_actual_main_responses_pass(self):
        self.assertEqual(self.check("CS05", self.agent_review(51))["status"], "pass")

    def test_exactly_50_complete_main_responses_fail(self):
        self.assertEqual(self.check("CS05", self.agent_review(50))["status"], "fail")

    def test_partial_fewer_than_51_does_not_prove_failure(self):
        self.assertEqual(self.check("CS05", self.agent_review(20, complete=False))["status"], "review")

    def test_partial_more_than_50_is_a_sufficient_lower_bound(self):
        self.assertEqual(self.check("CS05", self.agent_review(51, complete=False))["status"], "pass")

    def test_automatic_submission_uses_same_response_threshold(self):
        self.assertEqual(self.check("CS05", self.agent_review(51, reason="auto_submit"))["status"], "pass")

    def test_normal_exit_has_no_50_response_requirement(self):
        self.assertEqual(self.check("CS05", self.agent_review(1, reason="completed"))["status"], "not_applicable")

    def test_normal_exit_does_not_require_new_session_fields(self):
        self.write("agent_result.json", {"exit_reason": "completed"})
        self.assertEqual(self.check("CS05", {"agent_runs": [{"result_source": "agent_result.json"}]})["status"], "not_applicable")

    def test_tool_and_subagent_counts_do_not_substitute(self):
        review = self.agent_review(0)
        self.write("session.json", {"agent_role": "main", "complete": True, "messages": [{"role": "tool"}] * 200 + [{"role": "assistant", "agent_id": "worker"}] * 100})
        self.assertEqual(self.check("CS05", review)["status"], "fail")

    def test_assistant_labeled_tool_outputs_do_not_substitute(self):
        review = self.agent_review(0)
        self.write("session.json", {"agent_role": "main", "complete": True,
                                    "messages": [{"role": "assistant", "type": "function_call_output", "response_id": str(i)} for i in range(100)]})
        self.assertEqual(self.check("CS05", review)["status"], "fail")

    def test_native_response_ids_deduplicate_repeated_full_exports(self):
        review = self.agent_review(0)
        self.write("session.json", {"agent_role": "main", "complete": True,
                                    "responses": [{"id": "resp_one", "type": "response", "output": []}] * 100})
        self.assertEqual(self.check("CS05", review)["status"], "fail")

    def test_native_ids_deduplicate_messages_export(self):
        review = self.agent_review(0)
        self.write("session.json", {"agent_role": "main", "complete": True,
                                    "messages": [{"role": "assistant", "id": "resp_one"}] * 70})
        self.assertEqual(self.check("CS05", review)["status"], "fail")

    def test_completion_id_is_used_when_response_id_is_null(self):
        review = self.agent_review(0)
        self.write("session.json", {"agent_role": "main", "complete": True,
                                    "messages": [{"role": "assistant", "response_id": None, "completion_id": "completion_one"}] * 70})
        self.assertEqual(self.check("CS05", review)["status"], "fail")

    def test_tool_role_cannot_be_recast_as_response(self):
        review = self.agent_review(0)
        self.write("session.json", {"agent_role": "main", "complete": True,
                                    "responses": [{"role": "tool", "type": "response", "id": str(i), "output": []} for i in range(70)]})
        self.assertEqual(self.check("CS05", review)["status"], "fail")

    def test_subagent_role_in_response_array_is_excluded(self):
        review = self.agent_review(0)
        self.write("session.json", {"agent_role": "main", "complete": True,
                                    "responses": [{"type": "response", "agent_type": "worker", "id": str(i)} for i in range(100)]})
        self.assertEqual(self.check("CS05", review)["status"], "fail")

    def test_qa_agent_session_does_not_prove_solver_response_requirement(self):
        review = self.agent_review(70)
        self.write("session.json", {"agent_role": "main", "agent_type": "QA-Agent", "complete": True,
                                    "messages": [{"role": "assistant", "response_id": str(i)} for i in range(70)]})
        row = self.check("CS05", review)
        self.assertEqual(row["status"], "review")
        self.assertTrue(any("QA-Agent" in note for note in row["limitations"]))

    def test_qa_agent_result_is_not_auto_detected_as_solver_run(self):
        self.write("agent_result.json", {"exit_reason": "timeout", "agent_type": "qa_agent"})
        row = self.check("CS05")
        self.assertEqual(row["status"], "review")
        self.assertFalse(row["required_for_static_completion"])

    def test_result_selector_cannot_discard_parent_qa_scope(self):
        review = self.agent_review(70)
        self.write("agent_result.json", {"agent_type": "QA-Agent", "agent_result": {"exit_reason": "timeout"}})
        review["agent_runs"][0]["result_path"] = ["agent_result"]
        row = self.check("CS05", review)
        self.assertEqual(row["status"], "review")
        self.assertTrue(any("QA-Agent" in note for note in row["limitations"]))

    def test_result_selector_cannot_discard_intermediate_qa_scope(self):
        review = self.agent_review(70)
        self.write("agent_result.json", {"data": {"agent_type": "QA-Agent", "run": {"exit_reason": "timeout"}}})
        review["agent_runs"][0]["result_path"] = ["data", "run"]
        self.assertEqual(self.check("CS05", review)["status"], "review")

    def test_session_selector_cannot_discard_parent_qa_scope(self):
        review = self.agent_review(70)
        self.write("session.json", {"agent_type": "QA-Agent", "data": {"agent_role": "main", "complete": True,
                                    "messages": [{"role": "assistant", "response_id": str(i)} for i in range(70)]}})
        review["agent_runs"][0]["session_path"] = ["data"]
        self.assertEqual(self.check("CS05", review)["status"], "review")

    def test_mixed_qa_and_solver_responses_do_not_inflate_solver_count(self):
        review = self.agent_review(0)
        self.write("session.json", {"agent_role": "main", "complete": True,
                                    "responses": [{"type": "response", "id": str(i)} for i in range(50)] +
                                                 [{"type": "response", "agent_type": "qa-agent", "id": "qa" + str(i)} for i in range(50)]})
        self.assertEqual(self.check("CS05", review)["status"], "fail")

    def test_response_ids_deduplicate_response_blocks(self):
        review = self.agent_review(1)
        self.write("session.json", {"agent_role": "main", "complete": True, "messages": [{"role": "assistant", "response_id": "one"}] * 100})
        self.assertEqual(self.check("CS05", review)["status"], "fail")

    def test_experiment_round_array_never_counts_as_llm_responses(self):
        review = self.agent_review(0)
        self.write("session.json", {"agent_role": "main", "rounds": [{"round": i} for i in range(100)]})
        self.assertEqual(self.check("CS05", review)["status"], "review")

    def test_empty_review_cannot_skip_provided_timeout_result(self):
        self.agent_review(70)
        row = self.check("CS05")
        self.assertEqual(row["status"], "review")
        self.assertTrue(row["required_for_static_completion"])

    def test_session_declared_subagent_never_passes_main_requirement(self):
        review = self.agent_review(70)
        self.write("session.json", {"agent_role": "worker", "complete": True, "messages": [{"role": "assistant"}] * 70})
        self.assertEqual(self.check("CS05", review)["status"], "review")

    def test_path_escape_rejected_as_review_not_executed(self):
        review = {"agent_runs": [{"result_source": "../secret.json"}]}
        self.assertEqual(self.check("CS05", review)["status"], "review")

    def test_jsonl_model_response_records_are_counted_once(self):
        review = self.agent_review(0)
        lines = [{"type": "session_meta", "payload": {"agent_role": "main"}}]
        lines += [{"type": "llm_response", "payload": {"response_id": str(i), "agent_role": "main"}} for i in range(51)]
        lines += [{"type": "session_end", "payload": {"complete": True}}]
        self.write("session.jsonl", "\n".join(json.dumps(line) for line in lines))
        review["agent_runs"][0]["session_source"] = "session.jsonl"
        self.assertEqual(self.check("CS05", review)["status"], "pass")

    def test_jsonl_qa_metadata_survives_parser_and_cannot_prove_solver_count(self):
        review = self.agent_review(0)
        lines = [{"type": "session_meta", "payload": {"agent_role": "main", "agent_type": "QA-Agent"}}]
        lines += [{"type": "llm_response", "payload": {"id": str(i)}} for i in range(70)]
        lines += [{"type": "session_end", "payload": {"complete": True}}]
        self.write("session.jsonl", "\n".join(json.dumps(line) for line in lines))
        review["agent_runs"][0]["session_source"] = "session.jsonl"
        self.assertEqual(self.check("CS05", review)["status"], "review")

    def test_jsonl_tool_payload_cannot_be_recast_as_model_responses(self):
        review = self.agent_review(0)
        lines = [{"type": "session_meta", "payload": {"agent_role": "main"}}]
        lines += [{"type": "llm_response", "payload": {"type": "function_call_output", "id": str(i)}} for i in range(100)]
        lines += [{"type": "session_end", "payload": {"complete": True}}]
        self.write("session.jsonl", "\n".join(json.dumps(line) for line in lines))
        review["agent_runs"][0]["session_source"] = "session.jsonl"
        self.assertEqual(self.check("CS05", review)["status"], "review")

    def test_native_event_blocks_cannot_be_counted_as_responses(self):
        review = self.agent_review(0)
        lines = [{"type": "session_meta", "payload": {"agent_role": "main"}}]
        lines += [{"type": "response_item", "payload": {"role": "assistant", "type": "function_call"}} for i in range(100)]
        lines += [{"type": "session_end", "payload": {"complete": True}}]
        self.write("session.jsonl", "\n".join(json.dumps(line) for line in lines))
        review["agent_runs"][0]["session_source"] = "session.jsonl"
        self.assertEqual(self.check("CS05", review)["status"], "review")

    def test_historical_selector_still_requires_boolean(self):
        review = self.reward_review({"reward.txt": "0.42", "reward.json": {"reward": 0.42}})
        review["reward_runs"][0]["historical"] = "false"
        row = self.check("CS03", review)
        self.assertEqual(row["status"], "review")
        self.assertTrue(row["required_for_static_completion"])

    def test_uuid_identity_is_not_assumed_to_be_subagent_role(self):
        review = self.agent_review(70)
        self.write("session.json", {"agent_role": "main", "agent_id": "session-uuid-01", "complete": True,
                                    "messages": [{"role": "assistant", "agent_id": "session-uuid-01", "response_id": str(i)} for i in range(70)]})
        self.assertEqual(self.check("CS05", review)["status"], "pass")

    def test_one_platform_pending_run_does_not_hide_another_unresolved_multimetric(self):
        first = self.reward_review({"reward.json": {"accuracy": 0.8, "latency": 10}})
        self.write("another/reward.json", {"accuracy": 0.7})
        first["reward_runs"].append({"run_id": "other", "files": ["another/reward.json"]})
        row = self.check("CS04", first)
        self.assertEqual(row["status"], "review")
        self.assertTrue(row["required_for_static_completion"])

if __name__ == "__main__":
    unittest.main()
