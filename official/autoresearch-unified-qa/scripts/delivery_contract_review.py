"""Trusted, read-only current-standard review; never imports task code.

The groups are internal reading worksheets owned by existing checks, not new
expert fields or numbered gates. A reviewer records concrete facts from the
already supplied source, selected logs and output files. Collection patterns
only locate reading material; neither keywords nor read limits decide failure.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re

import engineering_review as engineering

VERSION = "0.5.0-current.1"
GROUPS = {
    "task_contract": ("QA11",),
    "normalization_anchors": ("QA02",),
    "image_dependency_fit": ("QA15",),
    "infra_capabilities": ("H03",),
    "batch_acceptance": ("H04",),
    "new_intake_protocol": ("H04",),
}
RELATED = {
    "task_contract": ["QA06", "QA09", "H04"],
    "normalization_anchors": ["QA01", "QA03", "QA15", "H04"],
    "image_dependency_fit": ["H03", "QA05"],
    "infra_capabilities": ["QA05", "QA15", "H04"],
    "batch_acceptance": ["QA11", "QA15", "QA21"],
    "new_intake_protocol": ["H01", "H02", "H03", "QA06"],
}
DETAILS = {
    "task_contract": ("goal_metric", "allowed_scope", "submission_contract", "enforced_constraints", "completion_conditions"),
    "normalization_anchors": ("endpoints", "direction_formula", "anchor_values", "protocol_binding", "hardware_calibration"),
    "image_dependency_fit": ("work", "judge"),
    "infra_capabilities": ("dependencies", "environment_compatibility", "control_necessity"),
    "batch_acceptance": ("rollout_evidence", "agent_verifier_separation", "admission_basis"),
    "new_intake_protocol": ("oracle_entry", "dependency_lock", "formal_reward", "gate_penalty"),
}
DETAIL_GUIDANCE = {
    "goal_metric": "Record the actual objective, primary metric, formula, aggregation and direction.",
    "allowed_scope": "Record the files, algorithms and visible data the agent may change or use.",
    "submission_contract": "Record actual submission paths, fields, shapes and the verifier's reader.",
    "enforced_constraints": "Read actual deadlines, AST rules, graph/array shapes and compare them to public instructions.",
    "completion_conditions": "Record when a submission is complete and how this agrees with actual scoring.",
    "endpoints": "Verify starter maps to zero and the stated upper endpoint to one; no new clipping choice is required.",
    "direction_formula": "Record the actual formula and metric direction, including lower-is-better tasks.",
    "anchor_values": "Identify the actual baseline B and upper U consumed by the formal scorer and their provenance.",
    "protocol_binding": "Identify split, scoring protocol and candidate binding; do not subtract values from different splits.",
    "hardware_calibration": "For latency, throughput or fixed wall-clock metrics, check target-hardware formal anchors; missing old records alone do not fail.",
    "work": "Review selected Work resources, image and dependencies against actual compute needs.",
    "judge": "Review selected Judge resources, image and dependencies independently of Work.",
    "dependencies": "Identify required kernel/infra features such as Landlock or bwrap from their actual call chain.",
    "environment_compatibility": "Use actual environment evidence or existing logs if provided; no new runtime proof is required for source review.",
    "control_necessity": "Determine whether a failing control is uniquely necessary or an effective alternative exists.",
    "rollout_evidence": "Select existing run evidence; distinguish a finite actual score from placeholders and absent scoring.",
    "agent_verifier_separation": "Distinguish Agent timeout, Verifier timeout, actual scoring and trajectory review.",
    "admission_basis": "Record current score coverage; historical records provide no admission exception, and no-score/timeout alone adds no rejection or rerun requirement.",
    "oracle_entry": "Identify mandatory solution/solve.sh and its reachable implementation inside solution/; implementation name and language are unrestricted.",
    "dependency_lock": "Review effective dependency pin/lock semantics; a filename alone does not establish reproducibility.",
    "formal_reward": "For every task, use one formal reward file per execution and the numeric reward main key in JSON.",
    "gate_penalty": "For every task, rejected candidate hard-gate cases use the deterministic -10 result.",
}
SOURCE_LIMIT = engineering.SOURCE_LIMIT
TOTAL_LIMIT = engineering.TOTAL_LIMIT
FILE_LIMIT = engineering.FILE_LIMIT
STATUSES = {None, "pass", "fail", "not_applicable", "evidence_limited", "advisory", "warn"}


def _specific(value):
    return engineering._specific(value)


def _task(root, task_root):
    root = Path(root).resolve()
    task = root if task_root in (None, "", ".") else (root / task_root).resolve()
    if not task.is_relative_to(root) or not task.is_dir():
        raise ValueError("task_root must select a directory within the inspected bundle")
    return root, task


def _context(context):
    if context is None:
        context = {}
    if not isinstance(context, dict):
        raise ValueError("context must be a trusted internal object")
    result = copy.deepcopy(context)
    # Old caller fields are inert metadata, never selectors or waiver inputs.
    obsolete = {key: result.pop(key) for key in ("intake_cohort", "rollout_policy", "target_level", "mode") if key in result}
    if obsolete:
        result["ignored_legacy_context"] = obsolete
    result["standard"] = "current"
    return result


def template():
    """An internal worksheet, filled by reading existing material, not by experts."""
    groups = {}
    for name in GROUPS:
        groups[name] = {"status": "unreviewed", "summary": "", "evidence": [],
                        "details": {key: {"summary": "", "evidence": [], "guidance": DETAIL_GUIDANCE[key]}
                                    for key in DETAILS[name]}, "findings": []}
    groups["batch_acceptance"]["details"]["rollout_evidence"].update(
        selected_trial=None, score_valid=None, non_placeholder=None,
        normal_evaluation_completed=None, trajectory_review_passed=None,
        agent_timeout=None, verifier_timeout=None)
    groups["batch_acceptance"]["optional_details"] = {"level_assurance": {
        "summary": "", "evidence": [], "status": "unreviewed", "covered_facets": [],
        "dynamic_evidence": [], "induced_cheat_rollout_verified": None,
        "guidance": "Additional assurance evidence is read as information, without a caller-selected level or whole-level certification. Actual inducement prompts, full executed conversations and results establish dynamic coverage; static facet labels do not."}}
    groups["new_intake_protocol"]["details"]["oracle_entry"].update(entry="solution/solve.sh", implementation_paths=[])
    groups["new_intake_protocol"]["details"]["dependency_lock"].update(locked=None)
    groups["new_intake_protocol"]["details"]["formal_reward"].update(output_files=[], json_main_key=None)
    groups["new_intake_protocol"]["details"]["gate_penalty"].update(value=None)
    groups["normalization_anchors"]["details"]["hardware_calibration"].update(
        hardware_sensitive=None, hardware_mismatch_confirmed=None,
        formal_anchor_reused=None, target_protocol_calibrated=None)
    return {"groups": groups, "reward_runs": [],
            "context_example": {"standard": "current", "package_stage": "source"},
            "notes": ["Pass context via audit(context=...), separately from review.",
                      "Each detail requires a concrete summary and existing evidence; missing material can be evidence_limited.",
                      "Findings require positioned evidence, reason, remediation, code (optional) and explicit blocking boolean.",
                      "No-score/timeout alone only records coverage; the one-hour rejection policy is on hold.",
                      "All tasks require the four protocol items; new_intake_protocol is a retained storage name, not an intake selector.",
                      "Existing reward outputs must still be read; historical outputs never create an admission exception."]}


def _collect(root, task, config):
    observations, limitations = [], []
    # Reuse the trusted collector's selected images/role semantics and cache;
    # its read/parse limits are observations, never author failures here.
    prior, prior_errors, cache = engineering._collect(root, task, config)
    mapping = {"resource_alignment": "image_dependency_fit", "timeout_budget": "task_contract",
               "controls_logs": "infra_capabilities", "score_scope": "batch_acceptance",
               "delivery_lineage": "batch_acceptance", "score_paths": "new_intake_protocol"}
    for observation in prior:
        if observation["group"] in {"resource_alignment", "timeout_budget", "controls_logs", "score_scope", "delivery_lineage"}:
            observations.append({**observation, "group": mapping[observation["group"]],
                                 "observation_only": True})
    limitations.extend({**error, "group": mapping.get(error.get("group"), "task_contract"),
                        "required": False, "observation_only": True} for error in prior_errors)

    def add(kind, group, relative, number=None, excerpt="", **detail):
        observations.append({"kind": kind, "group": group, "path": relative, "line": number,
                             "ref": relative + (":" + str(number) if number else ""),
                             "excerpt": excerpt[:360], "details": detail, "observation_only": True})

    total, seen = sum(len(raw.encode("utf-8")) for raw in cache.values() if isinstance(raw, str)), 0
    patterns = (
        ("task_contract", "public_contract_location", re.compile(r"goal|objective|metric|submission|scope|completion|目标|指标|提交|范围|完成", re.I)),
        ("task_contract", "enforced_constraint_location", re.compile(r"deadline|timeout|ast\.|ndim|\.shape|nonlocal|__|fan.?in|inputs.{0,15}(?:64|4096)", re.I)),
        ("normalization_anchors", "normalization_location", re.compile(r"baseline|upper_bound|calibrat|throughput|latency|wall.?clock|normaliz|归一化|锚点|固定墙钟", re.I)),
        ("infra_capabilities", "infra_dependency_location", re.compile(r"landlock|\bbwrap\b|bubblewrap|seccomp|unshare|/dev/nvidia", re.I)),
        ("new_intake_protocol", "current_protocol_location", re.compile(r"reward\.(?:json|txt)|solve\.sh|lockfile|requirements|hard.?gate|(?:return|reward|score).{0,12}-10", re.I)),
    )
    for base, dirs, names in os.walk(task, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d.lower() not in engineering.EXCLUDED and not (Path(base) / d).is_symlink())
        for name in sorted(names):
            path = Path(base) / name
            if path.suffix.lower() not in {".md", ".py", ".sh", ".bash", ".toml", ".yaml", ".yml", ".json", ".txt", ".log"} and name.lower() != "dockerfile":
                continue
            relative = path.relative_to(root).as_posix()
            seen += 1
            try:
                if relative in cache:
                    raw = cache[relative]
                else:
                    if seen > FILE_LIMIT or total >= TOTAL_LIMIT:
                        raise ValueError("automatic observation budget reached; review selected sources directly")
                    raw = engineering._text(engineering._safe(root, relative), min(SOURCE_LIMIT, TOTAL_LIMIT - total))
                    cache[relative] = raw
                    total += len(raw.encode("utf-8"))
            except (OSError, ValueError, UnicodeError) as exc:
                limitations.append({"group": "task_contract", "path": relative, "error": str(exc),
                                    "required": False, "observation_only": True})
                continue
            for number, line in enumerate(raw.splitlines(), 1):
                for group, kind, pattern in patterns:
                    if pattern.search(line):
                        add(kind, group, relative, number, line,
                            note="Reading location only; confirm actual semantics and public agreement before a finding.")
            if path.suffix.lower() == ".py":
                try:
                    tree = ast.parse(raw, filename=relative)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Compare) and any(isinstance(n, ast.Attribute) and n.attr in {"ndim", "shape"} for n in ast.walk(node)):
                            add("array_constraint_location", "task_contract", relative, node.lineno,
                                ast.get_source_segment(raw, node) or "")
                except (SyntaxError, RecursionError, ValueError) as exc:
                    add("source_parse_limit", "task_contract", relative, excerpt=str(exc),
                        note="Read raw source; parser failure does not establish a task defect.")
    return observations, limitations


def collect(root, *, task_root=None, config=None):
    root, task = _task(root, task_root)
    observations, limitations = _collect(root, task, config)
    return {"executed_task": False, "observations": observations, "errors": [], "collection_limitations": limitations}


def _positioned(ref):
    return isinstance(ref, str) and bool(re.search(r"(?::\d+(?:-\d+)?|#(?:L\d|/|field=|\$\.))", ref))


def audit(root, review=None, *, context=None, task_root=None, config=None):
    root, task = _task(root, task_root)
    observations, limitations = _collect(root, task, config)
    errors, checks = [], []
    try:
        ctx = _context(context)
    except (TypeError, ValueError) as exc:
        errors.append({"group": "batch_acceptance", "error": str(exc), "required": True, "kind": "internal_context"})
        ctx = {"standard": "current"}
    if review is not None and not isinstance(review, dict):
        errors.append({"group": "task_contract", "error": "delivery_contract_review must be an internal reviewer object", "required": True})
        review = None
    review = review or {}
    groups = review.get("groups", review)
    if not isinstance(groups, dict):
        errors.append({"group": "task_contract", "error": "groups must be an object", "required": True})
        groups = {}

    def refs(values, label):
        if not isinstance(values, list) or not values:
            raise ValueError(label + " needs existing evidence references")
        for ref in values:
            if not isinstance(ref, str):
                raise ValueError(label + " evidence must contain strings")
            engineering._resolve_evidence(root, ref)
        return list(dict.fromkeys(values))

    def finding(name, value):
        if (not isinstance(value, dict) or not _specific(value.get("reason"))
                or not _specific(value.get("remediation")) or not isinstance(value.get("blocking"), bool)):
            raise ValueError(name + " findings require concrete reason/remediation and explicit blocking boolean")
        if value.get("owner_id", GROUPS[name][0]) != GROUPS[name][0]:
            raise ValueError(name + " finding owner_id must remain " + GROUPS[name][0])
        evidence = refs(value.get("evidence"), name + ".finding")
        if not all(_positioned(ref) for ref in evidence):
            raise ValueError(name + " findings require positioned evidence, not bare filenames")
        digest = hashlib.sha256(json.dumps([name, value["reason"], evidence], ensure_ascii=False).encode()).hexdigest()[:12]
        code = value.get("code", value.get("key"))
        if code is not None and (not isinstance(code, str) or not code.strip()):
            raise ValueError(name + " finding code must be a nonempty string")
        result = {**copy.deepcopy(value), "code": code or "delivery." + name + "." + digest,
                  "owner_id": GROUPS[name][0], "owner_ids": list(GROUPS[name]),
                  "related_checks": RELATED[name], "evidence": evidence}
        # Unnecessary CPU CUDA image weight is a high-priority recommendation,
        # not a resurrected image-size gate. Resource misuse has its own owner.
        if name == "image_dependency_fit" and (result.get("category") == "unnecessary_heavy_base"
                                                  or result["code"] == "image.unnecessary_heavy_base"):
            result.update(blocking=False, priority="high", severity="advisory")
        return result

    for name, owners in GROUPS.items():
        applicable = True
        optional_absent = name == "batch_acceptance" and not review.get("reward_runs")
        row = {"name": name, "status": "unreviewed", "owner_id": owners[0], "owner_ids": list(owners),
               "related_checks": RELATED[name], "summary": "Await concrete semantic review of existing material.",
               "evidence": [], "details": {}, "findings": [], "problems": [], "advisories": [], "limitations": [],
               "observations": [o for o in observations if o["group"] == name], "review_complete": False,
               "required_for_static_completion": name != "batch_acceptance" or bool(review.get("reward_runs")),
               "applicable": applicable}
        supplied = groups.get(name)
        if optional_absent and supplied is None:
            row.update(status="not_applicable", review_complete=True,
                       summary="No existing runtime outputs are selected; the held no-score policy adds no new execution-evidence requirement.")
        elif supplied is not None:
            try:
                if not isinstance(supplied, dict):
                    raise ValueError(name + " must be an object")
                normalized = row["findings"]

                def record(value):
                    validated = finding(name, value)
                    normalized.append(validated)
                    row["problems" if validated["blocking"] else "advisories"].append(validated)

                # Validate independent findings before the rest of the worksheet.
                # An unrelated bad summary, location or second finding cannot
                # erase a concrete defect whose evidence already resolved.
                raw_findings = supplied.get("findings", [])
                if not isinstance(raw_findings, list):
                    raise ValueError(name + ".findings must be an array")
                finding_errors = []
                for index, value in enumerate(raw_findings):
                    try:
                        record(value)
                    except (OSError, TypeError, ValueError, UnicodeError) as exc:
                        finding_errors.append("findings[" + str(index) + "]: " + str(exc))
                if finding_errors:
                    raise ValueError("; ".join(finding_errors))
                if supplied.get("status") not in STATUSES:
                    raise ValueError(name + " has an unsupported or explicitly unreviewed status")
                if not _specific(supplied.get("summary")):
                    raise ValueError(name + " needs an actual summary, not a generic pass")
                row["summary"] = supplied["summary"]
                row["evidence"] = refs(supplied.get("evidence"), name)
                details = supplied.get("details")
                if not isinstance(details, dict):
                    raise ValueError(name + ".details must contain this group's minimum reading items")
                required_details = DETAILS[name]
                for key in required_details:
                    item = details.get(key)
                    if not isinstance(item, dict) or not _specific(item.get("summary")):
                        raise ValueError(name + ".details." + key + " needs a concrete summary and evidence")
                    if item.get("status") not in {None, "pass", "evidence_limited", "not_applicable", "fail", "advisory"}:
                        raise ValueError(name + ".details." + key + " has invalid status")
                    row["evidence"].extend(refs(item.get("evidence"), name + ".details." + key))
                row["details"] = copy.deepcopy(details)
                if name == "normalization_anchors":
                    hardware = details["hardware_calibration"]
                    keys = ("hardware_sensitive", "hardware_mismatch_confirmed", "formal_anchor_reused", "target_protocol_calibrated")
                    for key in keys:
                        if key in hardware and hardware[key] is not None and not isinstance(hardware[key], bool):
                            raise ValueError("hardware_calibration." + key + " must be boolean or unknown")
                    if all(hardware.get(key) is True for key in keys[:3]) and hardware.get(keys[3]) is False:
                        record({"reason": hardware["summary"], "evidence": hardware["evidence"],
                            "remediation": "Calibrate the formal baseline on the target hardware and the same formal split/protocol before interpreting improvement scores.",
                            "code": "normalization.confirmed_hardware_anchor_mismatch", "blocking": True})
                protocol_limited = False
                if name == "new_intake_protocol":
                    if any(details[key].get("status") == "not_applicable" for key in DETAILS[name]):
                        raise ValueError("All four current delivery protocol items apply to every task")
                    oracle = details["oracle_entry"]
                    entry = oracle.get("entry")
                    if entry is not None and not isinstance(entry, str):
                        raise ValueError("oracle_entry.entry must identify the actual Oracle entry")
                    if entry is None or Path(entry) not in {Path("solution/solve.sh"), Path("/solution/solve.sh")}:
                        if entry is None:
                            protocol_limited = True
                        else:
                            record({"reason": "The reviewed Oracle entry is " + repr(entry) + "; the current standard requires solution/solve.sh.",
                                "evidence": oracle["evidence"], "remediation": "Provide solution/solve.sh as the Oracle entry and keep its implementation inside solution/.",
                                "code": "current.oracle_entry_location", "blocking": True})
                    expected_entry = task / "solution" / "solve.sh"
                    if not expected_entry.is_file() or expected_entry.is_symlink() or (task / "solution").is_symlink():
                        record({"reason": "The selected task does not contain the required regular Oracle entry solution/solve.sh.",
                            "evidence": oracle["evidence"], "remediation": "Deliver solution/solve.sh, which generates the normal submission by invoking an implementation inside solution/.",
                            "code": "current.oracle_entry_missing", "blocking": True})
                    implementations = oracle.get("implementation_paths")
                    if implementations is None or implementations == []:
                        protocol_limited = True
                    elif not isinstance(implementations, list) or not all(isinstance(path, str) and path.strip() for path in implementations):
                        raise ValueError("oracle_entry.implementation_paths must identify the reachable Oracle implementation files")
                    else:
                        solution_root = (task / "solution").resolve()
                        for implementation in implementations:
                            implementation_path = Path(implementation)
                            if implementation_path.is_absolute() and implementation_path.is_relative_to(Path("/solution")):
                                implementation_path = implementation_path.relative_to("/")
                            target = (task / implementation_path).resolve()
                            if implementation_path.is_absolute() or not target.is_relative_to(solution_root):
                                record({"reason": "The reviewed reachable Oracle implementation " + repr(implementation) + " is outside the required solution/ directory.",
                                    "evidence": oracle["evidence"], "remediation": "Move the Oracle implementation into solution/ and update solution/solve.sh to invoke it; the implementation name and language may vary.",
                                    "code": "current.oracle_implementation_location", "blocking": True})
                            elif not target.is_file():
                                raise ValueError("The internal Oracle reading selection does not identify an existing implementation: " + implementation)
                    formal = details["formal_reward"]
                    files = formal.get("output_files")
                    if files is not None and (not isinstance(files, list) or not all(isinstance(f, str) for f in files)):
                        raise ValueError("formal_reward.output_files must be an array of actual formal filenames")
                    outputs_by_directory = {}
                    for file in files or []:
                        outputs_by_directory.setdefault(str(Path(file).parent), set()).add(Path(file).name)
                    if files is not None and (not files or any(len(names) != 1 for names in outputs_by_directory.values())
                                              or any(Path(f).name not in {"reward.json", "reward.txt"} for f in files)):
                        record({"reason": formal["summary"], "evidence": formal["evidence"],
                            "remediation": "Emit exactly one native formal reward file for each execution.",
                            "code": "current.formal_reward_file_choice", "blocking": True})
                    if files is None:
                        protocol_limited = True
                    if files and any(Path(f).name == "reward.json" for f in files):
                        if formal.get("json_main_key") is None:
                            protocol_limited = True
                        elif formal["json_main_key"] != "reward":
                            record({"reason": formal["summary"], "evidence": formal["evidence"],
                                "remediation": "Use the numeric reward main key in the JSON output.",
                                "code": "current.json_reward_main_key", "blocking": True})
                    gate = details["gate_penalty"]
                    if gate.get("value") is not None and (isinstance(gate["value"], bool) or gate["value"] != -10):
                        record({"reason": gate["summary"], "evidence": gate["evidence"],
                            "remediation": "Use the deterministic -10 result for rejected candidate hard-gate cases.",
                            "code": "current.gate_penalty", "blocking": True})
                    if gate.get("value") is None:
                        protocol_limited = True
                    lock = details["dependency_lock"]
                    if lock.get("locked") is not None and not isinstance(lock["locked"], bool):
                        raise ValueError("dependency_lock.locked must be boolean or unknown")
                    if lock.get("locked") is False:
                        record({"reason": lock["summary"], "evidence": lock["evidence"],
                            "remediation": "Lock all effective dependency versions, including transitive/runtime dependencies that affect reproducibility.",
                            "code": "current.dependency_lock", "blocking": True})
                    if lock.get("locked") is None:
                        protocol_limited = True
                row["findings"] = normalized
                row["problems"] = [f for f in normalized if f["blocking"]]
                row["advisories"] = [f for f in normalized if not f["blocking"]]
                if (supplied.get("status") == "fail" or any(details[key].get("status") == "fail" for key in required_details)) and not normalized:
                    raise ValueError(name + " cannot fail without a concrete evidenced finding")
                if supplied.get("status") == "not_applicable" and not optional_absent:
                    raise ValueError(name + " is applicable; use evidenced subitem not_applicable or evidence_limited instead")
                limited = (protocol_limited or supplied.get("status") == "evidence_limited"
                           or any(details[key].get("status") == "evidence_limited" for key in required_details))
                if protocol_limited:
                    row["limitations"].append("The source was read, but one or more required current protocol facts remain unestablished in the internal review.")
                row.update(status="fail" if row["problems"] else "not_applicable" if optional_absent and supplied.get("status") == "not_applicable" else "evidence_limited" if limited else "pass",
                           review_complete=True, evidence=list(dict.fromkeys(row["evidence"])))
            except (OSError, TypeError, ValueError, UnicodeError) as exc:
                row.update(status="fail" if row["problems"] else "unreviewed", review_complete=False)
                row["evidence"] = list(dict.fromkeys(row["evidence"] + [ref for value in row["findings"] for ref in value["evidence"]]))
                row["limitations"].append(str(exc))
                errors.append({"group": name, "error": str(exc), "required": True, "kind": "internal_review_schema"})
        checks.append(row)

    by_name = {row["name"]: row for row in checks}
    runtime = {"status": "not_applicable", "has_score": None, "score_valid": None, "verifier_available": None,
               "agent_timeout": None, "verifier_timeout": None, "selected_trial": None,
               "reward_runs": [], "limitations": [], "certifies_verifier": False, "verifier_verified": False,
               "normal_evaluation_completed": None}
    admission = {"standard": "current", "status": "not_applicable", "admitted": None,
                 "certifies_verifier": False,
                 "basis": "Runtime coverage under one current standard; historical scores and timeout provide no admission exception. No-score alone adds no rejection or rerun requirement."}
    _runtime(root, review, by_name["batch_acceptance"], ctx, runtime, admission, errors, finding_factory=finding)
    assurance = _assurance_notes(root, by_name["batch_acceptance"]["details"].get("level_assurance"))
    protocol = by_name["new_intake_protocol"]
    if not any(error.get("group") == "batch_acceptance" and error.get("required") for error in errors):
        selected_trial = runtime["selected_trial"]
        selected_runs = ([run for run in runtime["reward_runs"] if str(run.get("trial_id")) == str(selected_trial)]
                         if selected_trial is not None else runtime["reward_runs"] if len(runtime["reward_runs"]) == 1 else [])
        if len(selected_runs) == 1 and selected_runs[0].get("scope") == "runtime":
            current = selected_runs[0]
            actual_ref = current.get("selected_file")
            located = []
            for ref in ([actual_ref + ":1"] if actual_ref else []) + protocol["evidence"] + by_name["batch_acceptance"]["evidence"]:
                if not _positioned(ref):
                    continue
                try:
                    engineering._resolve_evidence(root, ref)
                    located = [ref]
                    break
                except (OSError, TypeError, ValueError, UnicodeError):
                    continue
            violations = []
            if len(current.get("output_names", [])) > 1 and located:
                violations.append({"code": "current.selected_run_dual_reward", "blocking": True,
                    "reason": "The explicitly selected current execution produced both reward.json and reward.txt in the same output directory.",
                    "remediation": "Emit exactly one formal reward file per execution.", "evidence": located,
                    "details": {"selected_file": actual_ref, "output_names": current["output_names"]}})
            if actual_ref and Path(actual_ref).name == "reward.json":
                try:
                    values = engineering.harbor_review.read_reward(root / actual_ref)
                except (OSError, TypeError, ValueError, UnicodeError):
                    values = None  # The native invalid-output finding is retained under H04.
                if values is not None and located and ("reward" not in values or current.get("main_score_key") not in {None, "reward"}):
                    violations.append({"code": "current.selected_run_json_main_key", "blocking": True,
                        "reason": "The explicitly selected current JSON output does not establish the required numeric reward main key under the actual reading contract.",
                        "remediation": "Write the actual main score under the numeric reward key and bind the reader to it.", "evidence": located})
            for violation in violations:
                value = finding("new_intake_protocol", violation)
                protocol["findings"].append(value)
                protocol["problems"].append(value)
                protocol["evidence"] = list(dict.fromkeys(protocol["evidence"] + value["evidence"]))
            if violations:
                protocol["status"] = "fail"
                admission.update(status="fail", admitted=False, certifies_verifier=False)
                runtime.update(status="fail", score_valid=False, verifier_available=None,
                               certifies_verifier=False, verifier_verified=False)
    # An internal context/schema error never certifies completion, including
    # when the affected group otherwise defaults to not_applicable.
    for error in errors:
        row = by_name.get(error.get("group"))
        if row and error.get("required"):
            row.update(status="fail" if row["problems"] else "unreviewed", review_complete=False)
            row["limitations"].append(error["error"])
    if any(error.get("group") == "batch_acceptance" and error.get("required") for error in errors):
        runtime.update(status="unreviewed", score_valid=None, verifier_available=None, certifies_verifier=False, verifier_verified=False)
        admission.update(status="unreviewed", admitted=None, certifies_verifier=False)
    for row in checks:
        if row["problems"]:
            # Optional coverage cannot hide an independently evidenced defect.
            # No-score/timeout facts alone never create these problems.
            row["required_for_static_completion"] = True
    required = [row for row in checks if row["required_for_static_completion"]]
    static_status = ("fail" if any(row["problems"] for row in required) else
                     "unreviewed" if any(not row["review_complete"] for row in required) else
                     "evidence_limited" if any(row["status"] == "evidence_limited" for row in required) else "pass")
    return {"version": VERSION, "executed_task": False, "context": ctx, "observations": observations,
            "checks": checks, "template": template(), "errors": errors, "collection_limitations": limitations,
            "claims": {"static": {"status": static_status, "review_complete": all(row["review_complete"] for row in required)},
                       "runtime": runtime, "admission": admission, "assurance_notes": assurance}}


def _runtime(root, review, batch, ctx, runtime, admission, errors, *, finding_factory):
    """Read explicitly selected existing outputs, keeping trials independent."""
    runs = review.get("reward_runs", [])
    detail = batch["details"].get("rollout_evidence", {})
    for key in ("score_valid", "non_placeholder", "normal_evaluation_completed", "trajectory_review_passed", "agent_timeout", "verifier_timeout"):
        if key in detail and detail[key] is not None and not isinstance(detail[key], bool):
            errors.append({"group": "batch_acceptance", "error": "rollout_evidence." + key + " must be boolean or unknown", "required": True})
    runtime.update({key: detail.get(key) for key in ("agent_timeout", "verifier_timeout", "selected_trial", "normal_evaluation_completed")})
    if not isinstance(runs, list):
        errors.append({"group": "batch_acceptance", "error": "reward_runs must be an array of existing outputs", "required": True})
        return
    unreadable_runs = 0
    for index, run in enumerate(runs):
        try:
            native_run = copy.deepcopy(run)
            if isinstance(run, dict):
                if "historical" in run and not isinstance(run["historical"], bool):
                    raise ValueError("reward run historical must be boolean")
                identity = run.get("trial_id")
                if identity is not None and not ((isinstance(identity, str) and identity.strip())
                                                 or (isinstance(identity, int) and not isinstance(identity, bool))):
                    raise ValueError("reward run trial_id must be a nonempty string, integer or unknown")
                if run.get("scope") == "history":
                    if run.get("historical") is False:
                        raise ValueError("reward run scope=history conflicts with historical=false")
                    native_run["historical"] = True
                elif run.get("scope") == "runtime":
                    if run.get("historical") is True:
                        raise ValueError("reward run scope=runtime conflicts with historical=true")
                    native_run["historical"] = False
            normalized = engineering.normalize_reward_run(root, native_run)
            if "scope" in run:
                normalized["declared_scope"] = copy.deepcopy(run["scope"])
                if run["scope"] not in ("history", "runtime"):
                    normalized["native_read_scope"] = normalized["scope"]
                    normalized["scope"] = "unknown"
            normalized["trial_id"] = run.get("trial_id")
            runtime["reward_runs"].append(normalized)
        except (OSError, TypeError, ValueError, UnicodeError) as exc:
            unreadable_runs += 1
            errors.append({"group": "batch_acceptance", "error": "reward_runs[" + str(index) + "]: " + str(exc),
                           "required": True, "kind": "internal_review_selection"})
    if runs:
        has_score = any(isinstance(run.get("main_score"), (int, float)) and not isinstance(run.get("main_score"), bool)
                        and math.isfinite(run["main_score"]) for run in runtime["reward_runs"])
        runtime["has_score"] = True if has_score else None if unreadable_runs else False
    selected = detail.get("selected_trial")
    if selected is not None and not ((isinstance(selected, str) and selected.strip())
                                    or (isinstance(selected, int) and not isinstance(selected, bool))):
        errors.append({"group": "batch_acceptance", "error": "selected_trial must be a nonempty string or integer existing trial identity", "required": True})
        return
    chosen = [run for run in runtime["reward_runs"] if str(run.get("trial_id")) == str(selected)] if selected is not None else runtime["reward_runs"] if len(runtime["reward_runs"]) == 1 else []
    if len(chosen) > 1:
        errors.append({"group": "batch_acceptance", "error": "selected_trial must bind exactly one run; distinct invocations cannot be merged", "required": True})
        return
    if selected is not None and runs and not chosen:
        errors.append({"group": "batch_acceptance", "error": "selected_trial does not identify an existing selected reward run", "required": True})
        return
    current_invalid = bool(chosen and chosen[0].get("scope") == "runtime" and chosen[0]["status"] == "fail"
                           and any(value.get("code") == "reward_output_invalid" for value in chosen[0].get("findings", [])))
    if current_invalid:
        current = chosen[0]
        located = []
        for ref in [current["selected_file"] + ":1"] + batch["evidence"]:
            if not _positioned(ref):
                continue
            try:
                engineering._resolve_evidence(root, ref)
                located = [ref]
                break
            except (OSError, TypeError, ValueError, UnicodeError):
                continue
        if located:
            problem = finding_factory("batch_acceptance", {
                "reason": "The explicitly selected current formal reward was read by the native contract reader and is invalid: "
                          + "; ".join(value["message"] for value in current["findings"] if value.get("code") == "reward_output_invalid"),
                "remediation": "Have the platform verify the authoritative output path and collection; if the artifact is authoritative, fix the task's reward writer to emit a valid finite numeric main score.",
                "evidence": located, "code": "runtime.selected_current_reward_invalid", "blocking": True,
                "responsibility": "author_or_platform", "details": {"selected_file": current["selected_file"],
                    "native_reader_findings": copy.deepcopy(current["findings"])}})
            batch["findings"].append(problem)
            batch["problems"].append(problem)
            batch["evidence"] = list(dict.fromkeys(batch["evidence"] + located))
            batch["status"] = "fail"
        else:
            errors.append({"group": "batch_acceptance", "error": "The current reward reader failed, but the internal selection has no readable positioned location for its invalid artifact or reader binding.",
                           "required": True, "kind": "internal_review_selection"})
    actual = bool(chosen and chosen[0]["status"] == "pass" and chosen[0].get("main_score") is not None)
    valid_score = (actual and detail.get("score_valid") is True and detail.get("non_placeholder") is True
                   and detail.get("normal_evaluation_completed") is True and runtime["verifier_timeout"] is not True)
    valid = valid_score and chosen[0].get("scope") == "runtime"
    if not runs:
        if any(detail.get(key) is not None for key in ("agent_timeout", "verifier_timeout", "normal_evaluation_completed")):
            runtime.update(status="evidence_limited")
            runtime["limitations"].append("No existing current reward is selected; timeout and missing-score facts record coverage without adding a rejection requirement.")
        return
    reviewed = batch["review_complete"] and not batch["problems"]
    runtime.update(status="fail" if current_invalid else "pass" if valid and reviewed else "evidence_limited" if reviewed else "unreviewed",
                   score_valid=True if valid and reviewed else None,
                   verifier_available=True if valid and reviewed else None,
                   certifies_verifier=bool(valid and reviewed), verifier_verified=bool(valid and reviewed))
    if not valid:
        runtime["limitations"].append("Existing material does not establish a finite, non-placeholder valid score for the selected execution; this is a coverage gap, not an expert failure.")
        if chosen and chosen[0].get("scope") == "history":
            runtime["limitations"].append("The selected output is explicitly historical; its score remains a historical fact and does not verify the current execution's Verifier path.")
        elif chosen and chosen[0].get("scope") != "runtime":
            runtime["limitations"].append("The selected output has an unrecognized declared scope; its readable score is retained, while current Verifier coverage remains unverified.")
    admission.update(status=runtime["status"], certifies_verifier=runtime["verifier_verified"])
    if current_invalid and batch["problems"]:
        admission.update(status="fail", admitted=False, certifies_verifier=False)
    # Keep no-score/timeout uncertainty in runtime/admission claims. It must
    # not raise H04 or turn a completed read into a new materials requirement.
    # Additional assurance information never selects a different standard.


def _assurance_notes(root, supplied):
    """Read optional advanced evidence without changing the single L0 route."""
    result = {"status": "not_provided", "certified": False, "evidence": [], "limitations": [], "errors": []}
    if supplied is None:
        return result
    try:
        if not isinstance(supplied, dict) or not _specific(supplied.get("summary")):
            raise ValueError("Additional assurance information needs a concrete summary")
        if supplied.get("status") in {"unreviewed", "manual", "incomplete"}:
            raise ValueError("Additional assurance information is explicitly unreviewed")
        evidence = supplied.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError("Additional assurance information needs existing evidence references")
        dynamic = supplied.get("dynamic_evidence", [])
        if not isinstance(dynamic, list):
            raise ValueError("Additional assurance dynamic_evidence must be an array")
        for ref in evidence + dynamic:
            if not isinstance(ref, str):
                raise ValueError("Additional assurance evidence references must be strings")
            engineering._resolve_evidence(root, ref)
        facets = supplied.get("covered_facets", [])
        if not isinstance(facets, list) or not all(isinstance(facet, str) for facet in facets):
            raise ValueError("Additional assurance covered_facets must be a string array")
        verified = supplied.get("induced_cheat_rollout_verified")
        if verified is not None and not isinstance(verified, bool):
            raise ValueError("Additional assurance induced_cheat_rollout_verified must be boolean or unknown")
        source_suffixes = {".py", ".sh", ".bash", ".toml", ".yaml", ".yml"}
        only_static = bool(dynamic) and all(Path(ref.partition("#")[0].split(":")[0]).suffix.lower() in source_suffixes
            or Path(ref.partition("#")[0].split(":")[0]).name.lower() == "dockerfile" for ref in dynamic)
        established = bool(verified is True and dynamic and not only_static)
        result.update(status="reviewed", summary=supplied["summary"], evidence=list(dict.fromkeys(evidence + dynamic)),
                      covered_facets=copy.deepcopy(facets), dynamic_coverage_verified=established)
        if not established:
            result["limitations"].append("Existing additional information does not establish a completed induced-cheat rollout; this note neither changes the standard nor certifies a level.")
    except (OSError, TypeError, ValueError, UnicodeError) as exc:
        result.update(status="unreviewed")
        result["errors"].append(str(exc))
    return result
