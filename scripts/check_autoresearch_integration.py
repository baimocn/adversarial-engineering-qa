#!/usr/bin/env python3
"""Verify official AutoResearch skill routing and complete v4 delivery coverage.

This tool reads skills and review evidence only. It never executes or imports
submitted artifact code. Machine coverage is a completeness check, not a claim
that the reviewer semantically understood every cited file.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import validate_review


SKILL_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = SKILL_ROOT / "references" / "autoresearch-v4-coverage.json"
OFFICIAL_NAME = "autoresearch-task-qa-legacy-waiver"
BASELINE_NAME = "autoresearch-baseline-quality"


def strict_json_load(path):
    return validate_review.strict_json_load(path)


def write_json(path, value):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest():
    manifest = strict_json_load(MANIFEST_PATH)
    source = SKILL_ROOT / manifest["source_prompt"]
    if not source.is_file() or sha256_file(source) != manifest["source_prompt_sha256"]:
        raise ValueError("The preserved original v4 prompt is missing or its SHA-256 changed")
    return manifest


def expand_requirements(manifest):
    rows = {row["id"]: dict(row) for row in manifest["requirements"]}
    for group in manifest["id_groups"]:
        for number in range(group["start"], group["end"] + 1):
            suffix = str(number).zfill(group["width"]) if group["width"] else str(number)
            item_id = group["prefix"] + suffix
            if item_id in rows:
                raise ValueError("Duplicate requirement in coverage manifest: " + item_id)
            rows[item_id] = {
                "id": item_id,
                "owner": group["owner"],
                "target": group["target"],
                "pass_rule": "Complete the authoritative check with current evidence and map all findings to verdicts.",
            }
    return [rows[key] for key in sorted(rows)]


def official_candidates():
    return [SKILL_ROOT / "official" / OFFICIAL_NAME]


def resolve_official(explicit=None):
    if explicit:
        candidates = [Path(explicit).expanduser()]
    elif os.environ.get("AUTORESEARCH_QA_SKILL"):
        candidates = [Path(os.environ["AUTORESEARCH_QA_SKILL"]).expanduser()]
    else:
        candidates = official_candidates()
    for candidate in candidates:
        if candidate.is_dir():
            return candidate.resolve(), [str(item) for item in candidates]
    raise ValueError("Official AutoResearch skill not found; searched: " + ", ".join(str(item) for item in candidates))


def resolve_baseline(official_root):
    candidates = [
        official_root.parent / BASELINE_NAME,
        SKILL_ROOT / "official" / BASELINE_NAME,
    ]
    for candidate in candidates:
        if (candidate / "SKILL.md").is_file():
            return candidate.resolve()
    return None


def inspect_official_skill(explicit=None, probe=True):
    errors = []
    manifest = load_manifest()
    try:
        root, searched = resolve_official(explicit)
    except ValueError as exc:
        return {"valid": False, "errors": [str(exc)], "official_skill": None, "baseline_skill": None}
    skill_path = root / "SKILL.md"
    if not skill_path.is_file():
        errors.append("Official SKILL.md is missing")
        text = ""
    else:
        text = skill_path.read_text(encoding="utf-8-sig")
        expected = manifest["official_skill"]
        if ("name: " + expected["name"]) not in text:
            errors.append("Official skill name does not match the required contract")
        if expected["version"] not in text:
            errors.append("Official skill version does not match " + expected["version"])
    hashed = []
    for name in manifest["official_references"]:
        path = root / "references" / name
        if not path.is_file():
            errors.append("Missing official reference: " + name)
        else:
            hashed.append((path, "references/" + name))
    for name in manifest["official_scripts"]:
        path = root / "scripts" / name
        if not path.is_file():
            errors.append("Missing official script: " + name)
        else:
            hashed.append((path, "scripts/" + name))
    if skill_path.is_file():
        hashed.append((skill_path, "SKILL.md"))
    baseline = resolve_baseline(root)
    if baseline is None:
        errors.append("Baseline quality skill was not found beside the official skill or in user skills")
    else:
        baseline_text = (baseline / "SKILL.md").read_text(encoding="utf-8-sig")
        if ("name: " + BASELINE_NAME) not in text and ("name: " + BASELINE_NAME) not in baseline_text:
            errors.append("Baseline skill name does not match its contract")
        if not (baseline / "references" / "baseline-review-method.md").is_file():
            errors.append("Baseline review method reference is missing")
        hashed.append((baseline / "SKILL.md", "baseline/SKILL.md"))
    if probe and not errors:
        entrypoint = root / manifest["official_skill"]["entrypoint"]
        try:
            process = subprocess.run(
                [sys.executable, str(entrypoint), "--help"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(root / "scripts"),
            )
            if process.returncode != 0 or "--standard-review" not in process.stdout or "--review" not in process.stdout or "--out-dir" not in process.stdout:
                errors.append("Official CLI help did not expose the required standard-review/review/out-dir contract")
        except (OSError, subprocess.SubprocessError) as exc:
            errors.append("Official CLI probe failed: " + str(exc))
    fingerprint = hashlib.sha256()
    for path, logical in sorted(hashed, key=lambda item: item[1]):
        fingerprint.update(logical.encode("utf-8"))
        fingerprint.update(b"\0")
        fingerprint.update(sha256_file(path).encode("ascii"))
        fingerprint.update(b"\n")
    return {
        "valid": not errors,
        "errors": errors,
        "official_skill": str(root),
        "official_version": manifest["official_skill"]["version"],
        "baseline_skill": str(baseline) if baseline else None,
        "references_checked": len(manifest["official_references"]),
        "scripts_checked": len(manifest["official_scripts"]),
        "cli_probed": bool(probe and not errors),
        "contract_sha256": fingerprint.hexdigest(),
        "searched": searched,
    }


def command_contract(args):
    result = inspect_official_skill(args.official_skill, probe=not args.no_probe)
    if args.out:
        write_json(args.out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 2


def command_init(args):
    manifest = load_manifest()
    document = {
        "schema_version": "1.0",
        "artifact": {"path": str(Path(args.artifact).resolve()), "sha256": args.sha256},
        "official_contract": {"path": "", "contract_sha256": "", "status": "manual"},
        "requirements": [
            {"id": row["id"], "status": "manual", "evidence": [], "finding_ids": [], "notes": ""}
            for row in expand_requirements(manifest)
        ],
        "deliverables": [
            {"path": name, "status": "missing", "sha256": ""}
            for name in manifest["deliverables"]
        ],
        "coverage_decision": "INCOMPLETE",
        "notes": "Template only. Fill every requirement from current evidence; machine validation does not replace semantic review.",
    }
    write_json(args.out, document)
    print(json.dumps({"requirements": len(document["requirements"]), "deliverables": len(document["deliverables"]), "out": str(Path(args.out).resolve())}, ensure_ascii=False))
    return 0


def read_report(path, label, errors):
    if not path.is_file():
        errors.append(label + " is missing: " + str(path))
        return {}
    try:
        value = strict_json_load(path)
        if not isinstance(value, dict):
            errors.append(label + " must be a JSON object")
            return {}
        return value
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(label + " is unreadable: " + str(exc))
        return {}


def command_validate(args):
    errors = []
    manifest = load_manifest()
    expected_requirements = expand_requirements(manifest)
    delivery = Path(args.delivery_dir).resolve()
    review_path = Path(args.review).resolve()
    coverage_path = Path(args.coverage).resolve()
    review = read_report(review_path, "Adversarial review", errors)
    coverage = read_report(coverage_path, "Coverage record", errors)
    schema = strict_json_load(SKILL_ROOT / "references" / "report-schema.json")
    if review:
        errors.extend("adversarial review: " + item for item in validate_review.validate_review(review, schema))
        if review.get("domain") != "autoresearch_harbor":
            errors.append("Adversarial review must set domain=autoresearch_harbor")
    contract = inspect_official_skill(args.official_skill, probe=not args.no_probe)
    if not contract["valid"]:
        errors.extend("official contract: " + item for item in contract["errors"])
    if coverage:
        contract_row = coverage.get("official_contract", {})
        if contract_row.get("status") != "verified" or contract_row.get("contract_sha256") != contract.get("contract_sha256"):
            errors.append("Coverage record does not bind the current verified official contract fingerprint")
        if contract.get("official_skill") and Path(contract_row.get("path") or ".").resolve() != Path(contract["official_skill"]).resolve():
            errors.append("Coverage record official path does not match the probed official skill")
        rows = coverage.get("requirements")
        if not isinstance(rows, list):
            errors.append("Coverage requirements must be an array")
            rows = []
        by_id = {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str):
                errors.append("Coverage contains a malformed requirement row")
                continue
            if row["id"] in by_id:
                errors.append("Duplicate coverage requirement: " + row["id"])
            by_id[row["id"]] = row
        expected_ids = {row["id"] for row in expected_requirements}
        for item_id in sorted(expected_ids - set(by_id)):
            errors.append("Missing coverage requirement: " + item_id)
        for item_id in sorted(set(by_id) - expected_ids):
            errors.append("Unknown coverage requirement: " + item_id)
        for item_id in sorted(expected_ids & set(by_id)):
            row = by_id[item_id]
            if row.get("status") not in {"pass", "fail", "manual"}:
                errors.append(item_id + ": status must be pass/fail/manual")
            if row.get("status") == "pass" and not row.get("evidence"):
                errors.append(item_id + ": PASS requires current evidence")
            if row.get("status") == "fail" and not row.get("finding_ids"):
                errors.append(item_id + ": FAIL requires linked finding IDs")
        deliverables = coverage.get("deliverables")
        if not isinstance(deliverables, list):
            errors.append("Coverage deliverables must be an array")
            deliverables = []
        delivered = {row.get("path"): row for row in deliverables if isinstance(row, dict)}
        for name in manifest["deliverables"]:
            row = delivered.get(name)
            path = delivery / name
            if row is None:
                errors.append("Missing deliverable record: " + name)
                continue
            if row.get("status") != "complete" or not path.is_file() or path.stat().st_size == 0:
                errors.append("Deliverable is absent, empty or not marked complete: " + name)
                continue
            actual = sha256_file(path)
            if name == "autoresearch_coverage.json" and row.get("sha256") in {"", "self"}:
                continue  # A file cannot contain its own cryptographic hash.
            if row.get("sha256") != actual:
                errors.append("Deliverable SHA-256 mismatch: " + name)
    standard = read_report(delivery / "standard_review" / "report.json", "Official standard report", errors)
    waiver = read_report(delivery / "waiver_review" / "report.json", "Official waiver report", errors)
    final = read_report(delivery / "report.json", "Merged final report", errors)
    standard_decision = standard.get("decision", "INCOMPLETE")
    waiver_decision = waiver.get("decision", "ERROR")
    if standard_decision not in {"PASS", "FAIL", "INCOMPLETE"}:
        errors.append("Official standard decision has an unexpected value")
    if waiver_decision not in {"PASS_WITH_WAIVERS", "FAIL", "ERROR"}:
        errors.append("Official waiver decision has an unexpected value")
    if waiver.get("stage") != "standard_review_with_waivers" or waiver.get("standard_auditor_executed") is not True:
        errors.append("Official waiver report does not prove execution of the original standard auditor")
    if waiver_decision == "PASS_WITH_WAIVERS" and waiver.get("review_completed") is not True:
        errors.append("Official PASS_WITH_WAIVERS lacks review_completed=true")
    coverage_statuses = [row.get("status") for row in coverage.get("requirements", []) if isinstance(row, dict)] if coverage else []
    coverage_decision = "FAIL" if "fail" in coverage_statuses else "INCOMPLETE" if "manual" in coverage_statuses or not coverage_statuses else "PASS"
    adversarial_decision = review.get("standard_decision", "INCOMPLETE") if review else "INCOMPLETE"
    adversarial_effective = adversarial_decision
    if review and adversarial_decision == "FAIL" and review.get("waiver_review", {}).get("decision") == "PASS_WITH_WAIVERS":
        confirmed = [row for row in review.get("findings", []) if row.get("status") == "confirmed"]
        if confirmed and all(row.get("waiver_eligible") for row in confirmed):
            adversarial_effective = "PASS_WITH_WAIVERS"
    # ★★ v2（2026-10-30，从 11 份官方报告反推）：豁免层的「未覆盖项」必须阻断。
    #
    #   0340 实测数据（官方 waiver_report.json）：
    #     decision = "FAIL"，rejected = []，remaining_findings = 10 条
    #     （去重后只有 3 个真实问题：QA05 docstring 指纹 / QA06 ndarray 传递 /
    #      QA11 超时归因）。
    #   ⇒ 只看 `waiver_decision` 一个字段是不够的：decision 可能被上游写错，
    #     或标准层 FAIL 被当成「有 waiver 就算过」。真正决定能不能交的，
    #     是「还有没有未被 accepted 覆盖的 fail」。
    #   规则：remaining_findings 非空 ⇒ 一定存在未豁免的当前实现缺陷 ⇒ FAIL。
    remaining_findings = waiver.get("remaining_findings") or []
    if coverage_decision == "FAIL" or waiver_decision == "FAIL" or adversarial_effective == "FAIL" or remaining_findings:
        computed = "FAIL"
    elif coverage_decision == "INCOMPLETE" or waiver_decision == "ERROR" or standard_decision == "INCOMPLETE" or adversarial_effective == "INCOMPLETE":
        computed = "INCOMPLETE"
    elif standard_decision == "FAIL" or adversarial_effective == "PASS_WITH_WAIVERS" or any(
        row.get("effective_status") == "pass_with_waivers" for row in waiver.get("standard_findings", [])
    ):
        computed = "PASS_WITH_WAIVERS"
    else:
        computed = "PASS"
    if final:
        expected_fields = {
            "official_standard_decision": standard_decision,
            "official_waiver_decision": waiver_decision,
            "adversarial_decision": adversarial_decision,
            "coverage_decision": coverage_decision,
            "decision": computed,
        }
        for key, expected in expected_fields.items():
            if final.get(key) != expected:
                errors.append("Merged report field " + key + " must be " + expected)
    result = {
        "valid": not errors,
        "decision": computed,
        "official_standard_decision": standard_decision,
        "official_waiver_decision": waiver_decision,
        "adversarial_decision": adversarial_decision,
        "coverage_decision": coverage_decision,
        "requirements_expected": len(expected_requirements),
        "requirements_recorded": len(coverage.get("requirements", [])) if coverage else 0,
        "official_contract": contract,
        "errors": errors,
        "note": "valid=true proves contract and delivery consistency only; cited evidence still requires semantic review.",
    }
    if args.out:
        write_json(args.out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if computed == "FAIL" else 2 if computed == "INCOMPLETE" or errors else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    contract = subparsers.add_parser("contract", help="Probe the official and baseline skills without touching an artifact")
    contract.add_argument("--official-skill")
    contract.add_argument("--out")
    contract.add_argument("--no-probe", action="store_true")
    contract.set_defaults(function=command_contract)
    init = subparsers.add_parser("init-coverage", help="Create a complete manual coverage worksheet")
    init.add_argument("--artifact", required=True)
    init.add_argument("--sha256", required=True)
    init.add_argument("--out", required=True)
    init.set_defaults(function=command_init)
    validate = subparsers.add_parser("validate", help="Validate official layering, complete v4 coverage and merged decision")
    validate.add_argument("--review", required=True, help="Adversarial review JSON with domain=autoresearch_harbor")
    validate.add_argument("--coverage", required=True)
    validate.add_argument("--delivery-dir", required=True)
    validate.add_argument("--official-skill")
    validate.add_argument("--out")
    validate.add_argument("--no-probe", action="store_true")
    validate.set_defaults(function=command_validate)
    args = parser.parse_args(argv)
    try:
        return args.function(args)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "decision": "INCOMPLETE", "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
