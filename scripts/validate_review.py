#!/usr/bin/env python3
"""Strictly validate review.json structure and cross-field verdict semantics.

Structural rules are loaded from references/report-schema.json. The validator
also rejects duplicate JSON keys and semantic attempts to issue unsupported
PASS verdicts. It never executes the reviewed artifact.
"""

import argparse
import json
import re
import sys
from pathlib import Path


def strict_json_load(path):
    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle, object_pairs_hook=reject_duplicates)


def resolve_ref(schema, root_schema):
    while "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            raise ValueError(f"Unsupported external schema reference: {ref}")
        target = root_schema
        for part in ref[2:].split("/"):
            target = target[part.replace("~1", "/").replace("~0", "~")]
        schema = target
    return schema


def validate_schema(value, schema, root_schema, path="$"):
    schema = resolve_ref(schema, root_schema)
    errors = []
    expected_type = schema.get("type")
    type_checks = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "boolean": lambda item: isinstance(item, bool),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
    }
    if expected_type and not type_checks[expected_type](value):
        return [f"{path}: expected {expected_type}, got {type(value).__name__}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} not in {schema['enum']}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: string shorter than minLength {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: string does not match {schema['pattern']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: value below minimum {schema['minimum']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: fewer than minItems {schema['minItems']}")
        if "items" in schema:
            for index, item in enumerate(value):
                errors.extend(validate_schema(item, schema["items"], root_schema, f"{path}[{index}]"))
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for required in schema.get("required", []):
            if required not in value:
                errors.append(f"{path}: missing required property {required}")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errors.append(f"{path}: unexpected property {key}")
        for key, item in value.items():
            if key in properties:
                errors.extend(validate_schema(item, properties[key], root_schema, f"{path}.{key}"))
    return errors


def duplicate_ids(items, label):
    seen = set()
    errors = []
    for item in items:
        item_id = item.get("id")
        if item_id in seen:
            errors.append(f"{label}: duplicate id {item_id}")
        seen.add(item_id)
    return errors


def evidence_rank(level):
    return {"EV0": 0, "EV1": 1, "EV2": 2, "EV3": 3, "EV4": 4}[level]


def validate_semantics(review):
    errors = []
    claims = review["claims"]
    behaviors = review["behavior_coverage"]
    attacks = review["adversarial_cases"]
    findings = review["findings"]
    errors.extend(duplicate_ids(claims, "claims"))
    errors.extend(duplicate_ids(behaviors, "behavior_coverage"))
    errors.extend(duplicate_ids(attacks, "adversarial_cases"))
    errors.extend(duplicate_ids(findings, "findings"))

    claim_ids = {item["id"] for item in claims}
    behavior_by_id = {item["id"]: item for item in behaviors}
    finding_ids = {item["id"] for item in findings}

    for claim in claims:
        label = f"claim {claim['id']}"
        for finding_id in claim["finding_ids"]:
            if finding_id not in finding_ids:
                errors.append(f"{label}: unknown finding id {finding_id}")
        for behavior_id in claim["coverage_refs"]:
            if behavior_id not in behavior_by_id:
                errors.append(f"{label}: unknown behavior coverage id {behavior_id}")
        if claim["status"] == "pass":
            if not claim["implementation_evidence"]:
                errors.append(f"{label}: PASS requires implementation evidence")
            if evidence_rank(claim["evidence_level"]) < 2:
                errors.append(f"{label}: PASS requires at least EV2")
            if claim["behavior_required"]:
                if review["mode"] == "static":
                    errors.append(f"{label}: behavior-required claim cannot PASS in static mode")
                if evidence_rank(claim["evidence_level"]) < 3:
                    errors.append(f"{label}: behavior-required PASS requires EV3 or EV4")
                if not claim["coverage_refs"]:
                    errors.append(f"{label}: behavior-required PASS has no coverage references")
                for behavior_id in claim["coverage_refs"]:
                    behavior = behavior_by_id.get(behavior_id)
                    if not behavior:
                        continue
                    if behavior["untested_branches"]:
                        errors.append(f"{label}: PASS references untested branches in {behavior_id}")
                    if not behavior["branches"] or any(branch["status"] != "pass" for branch in behavior["branches"]):
                        errors.append(f"{label}: PASS requires all referenced behavior branches to PASS")
        if claim["status"] == "fail" and not claim["finding_ids"]:
            errors.append(f"{label}: FAIL must link at least one finding")

    for behavior in behaviors:
        if behavior["claim_id"] not in claim_ids:
            errors.append(f"behavior {behavior['id']}: unknown claim id {behavior['claim_id']}")
        for branch in behavior["branches"]:
            if branch["status"] == "pass" and not branch["evidence"]:
                errors.append(f"behavior {behavior['id']} branch {branch['name']}: PASS requires evidence")

    for attack in attacks:
        label = f"adversarial case {attack['id']}"
        if attack["claim_id"] not in claim_ids:
            errors.append(f"{label}: unknown claim id {attack['claim_id']}")
        if attack["status"] == "pass":
            if review["mode"] == "static":
                errors.append(f"{label}: dynamic defense cannot PASS in static mode")
            if not attack["authorization"].strip():
                errors.append(f"{label}: PASS requires recorded execution authorization")
            if not attack["reached_target"] or not attack["reachability_evidence"]:
                errors.append(f"{label}: PASS requires proof that the attack reached the target")
            if attack["early_exit"]["kind"]:
                errors.append(f"{label}: early exit {attack['early_exit']['kind']} cannot be defense PASS")
            if not attack["defense_observed"]:
                errors.append(f"{label}: PASS requires observed defense behavior")
            if not attack["oracle"].strip():
                errors.append(f"{label}: PASS requires a target-property oracle")
            if not attack["control"]["expected_without_defense"].strip() or not attack["control"]["observed"].strip():
                errors.append(f"{label}: PASS requires an explicit control and observed result")
            if attack["core_mechanism"] and (not attack["ablation"]["performed"] or not attack["ablation"]["result"].strip()):
                errors.append(f"{label}: core defense PASS requires ablation evidence")
            if not attack["evidence"]:
                errors.append(f"{label}: PASS requires runtime evidence")

    for finding in findings:
        for claim_id in finding["affected_claim_ids"]:
            if claim_id not in claim_ids:
                errors.append(f"finding {finding['id']}: unknown affected claim {claim_id}")
        # v1.1 责任归属：action 与 responsible 不得互相矛盾
        responsible = finding.get("responsible")
        action = finding.get("action")
        action_implies = {"author_fix": "author", "platform_fix": "platform"}
        if responsible and action and action_implies.get(action, responsible) != responsible:
            errors.append(
                f"finding {finding['id']}: action {action} contradicts responsible {responsible}")
        if action == "record_only" and responsible == "author":
            errors.append(
                f"finding {finding['id']}: record_only cannot be assigned to author — "
                "an author-controlled confirmed defect requires an author_fix action")

    # v1.1 平台源包规则（B-C01–B-C04）：只许 fail 阻断 PASS，不许被一层 PASS 掩盖
    platform_checks = review.get("platform_checks") or []
    errors.extend(duplicate_ids(platform_checks, "platform_checks"))
    platform_check_ids = set()
    for item in platform_checks:
        platform_check_ids.add(item["id"])
        if item["status"] == "fail":
            if not item["evidence"] or not item["note"].strip():
                errors.append(
                    f"platform_check {item['id']}: fail status requires evidence and a note")
    if review["standard_decision"] == "PASS" and any(
            item["status"] == "fail" for item in platform_checks):
        errors.append("decision PASS: platform rule failures remain (B-C01–B-C04)")
    # fail 的平台规则必须落到 findings（落锤→判级，E7 纪律）
    for item in platform_checks:
        if item["status"] == "fail" and not findings:
            errors.append(
                f"platform_check {item['id']}: fail has no finding in findings — "
                "确认错误不得只留在检查层而不进判级")

    for gate_name in ("change_regression", "current_correctness"):
        gate = review[gate_name]
        checks = gate["checks"]
        for check in checks:
            for finding_id in check["finding_ids"]:
                if finding_id not in finding_ids:
                    errors.append(f"{gate_name} check {check['id']}: unknown finding {finding_id}")
        if gate["status"] == "pass":
            if not checks or any(check["status"] != "pass" for check in checks):
                errors.append(f"{gate_name}: gate PASS requires a non-empty all-PASS check list")
        if gate["status"] == "not_applicable":
            if gate_name != "change_regression":
                errors.append(f"{gate_name}: current correctness cannot be not_applicable")
            if not checks or any(check["status"] != "not_applicable" for check in checks):
                errors.append(f"{gate_name}: not_applicable requires explicit not_applicable checks")
        if gate["status"] == "fail" and not any(check["status"] == "fail" for check in checks):
            errors.append(f"{gate_name}: FAIL gate requires at least one failed check")

    coverage = review["coverage_statement"]
    if coverage["files_indexed"] > coverage["files_total"]:
        errors.append("coverage: files_indexed exceeds files_total")
    if coverage["behavior_branches_run"] > coverage["behavior_branches_total"]:
        errors.append("coverage: behavior_branches_run exceeds total")
    if coverage["attacks_reached"] > coverage["attacks_total"]:
        errors.append("coverage: attacks_reached exceeds total")
    branch_total = sum(len(item["branches"]) for item in behaviors)
    if coverage["behavior_branches_total"] != branch_total:
        errors.append(f"coverage: behavior branch total {coverage['behavior_branches_total']} != matrix total {branch_total}")
    if coverage["attacks_total"] != len(attacks):
        errors.append("coverage: attacks_total does not match adversarial_cases length")
    reached_count = sum(1 for item in attacks if item["reached_target"])
    if coverage["attacks_reached"] != reached_count:
        errors.append("coverage: attacks_reached does not match reached_target values")

    confirmed_findings = [item for item in findings if item["status"] == "confirmed"]
    decision = review["standard_decision"]
    if decision == "PASS":
        if review["change_regression"]["status"] not in {"pass", "not_applicable"}:
            errors.append("decision PASS: change regression gate is not PASS/not_applicable")
        if review["current_correctness"]["status"] != "pass":
            errors.append("decision PASS: current correctness gate is not PASS")
        if not claims:
            errors.append("decision PASS: no claims were reviewed")
        for claim in claims:
            if claim["status"] != "pass":
                errors.append(f"decision PASS: claim {claim['id']} is {claim['status']}")
        for behavior in behaviors:
            if behavior["untested_branches"] or not behavior["branches"] or any(branch["status"] != "pass" for branch in behavior["branches"]):
                errors.append(f"decision PASS: behavior coverage {behavior['id']} is incomplete")
        for attack in attacks:
            if attack["status"] != "pass":
                errors.append(f"decision PASS: adversarial case {attack['id']} is {attack['status']}")
        if confirmed_findings:
            errors.append("decision PASS: confirmed findings remain")
        if coverage["unreviewed"]:
            errors.append("decision PASS: unreviewed scope remains")
    if decision == "FAIL":
        has_failure = (
            review["change_regression"]["status"] == "fail"
            or review["current_correctness"]["status"] == "fail"
            or any(item["status"] == "fail" for item in claims + attacks)
            or bool(confirmed_findings)
        )
        if not has_failure:
            errors.append("decision FAIL: no failed gate/item or confirmed finding supports it")

    waiver = review["waiver_review"]
    if not waiver["applicable"]:
        if waiver["decision"] != "ERROR" or waiver["reason_codes"]:
            errors.append("waiver: non-applicable review must use ERROR with no reason codes")
    if waiver["decision"] == "PASS_WITH_WAIVERS":
        if not waiver["applicable"] or not waiver["reason_codes"]:
            errors.append("waiver: PASS_WITH_WAIVERS requires applicability and reason codes")
        if not any(item["waiver_eligible"] for item in confirmed_findings):
            errors.append("waiver: no confirmed finding is marked waiver eligible")
        if decision == "PASS":
            errors.append("waiver: standard PASS cannot also require waiver PASS")
    return errors


def validate_review(review, schema):
    errors = validate_schema(review, schema, schema)
    if errors:
        return errors
    return validate_semantics(review)


def main():
    default_schema = Path(__file__).resolve().parents[1] / "references" / "report-schema.json"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", required=True)
    parser.add_argument("--schema", default=str(default_schema))
    parser.add_argument("--out", help="Optional validation result JSON")
    args = parser.parse_args()
    try:
        review = strict_json_load(args.review)
        schema = strict_json_load(args.schema)
        errors = validate_review(review, schema)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors = [f"input error: {exc}"]
        review = None
    result = {"valid": not errors, "errors": errors, "review": str(Path(args.review).resolve())}
    if args.out:
        out = Path(args.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
