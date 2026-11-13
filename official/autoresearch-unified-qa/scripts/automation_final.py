"""Finalize an Agent-read review without a human disposition step.

The model supplies narrow, cited *material gaps*, never a final acceptance
decision.  This adapter cannot turn a known failure, an unread source, or a
checker error into either PASS or a missing-material disposition.
"""
from __future__ import annotations

import copy
from pathlib import Path
import re

from evidence_refs import resolve_ref


SUCCESS = {"pass", "not_applicable", "pass_with_waivers", "waived"}
EXPECTED = {
    "core": {*(f"G{i:02}" for i in range(1, 4)), *(f"QA{i:02}" for i in range(1, 22)),
             *(f"H{i:02}" for i in range(1, 6)), "T01", "T02"},
    "format": {f"F{i:02}" for i in range(1, 8)},
    "current_standard": {"CS03", "CS04", "CS05"},
    "supplement": {*(f"A{i:02}" for i in range(1, 7)), *(f"B-C{i:02}" for i in range(1, 5)),
                   *(f"B-P{i:02}" for i in range(1, 26)), *(f"B-E{i:02}" for i in range(1, 10)),
                   "B-GPU", "B-ENV", *(f"B-S{i:02}" for i in range(1, 4))},
}
KINDS = {"materials_not_provided", "unreadable_source"}
OWNERS = {"author", "platform", "coordination"}
GAP_STATUSES = {"manual", "review", "review_not_finished"}
LEGACY_UNFINISHED_SUMMARY = "仍有未审明具体原因的项目，应由质检员继续读已有材料，不能转成专家新增补跑要求。"
_TOOL_LIMIT = re.compile(r"(?:工具(?:不支持|限制|超限|异常)|读取(?:上限|限制)|token\s*(?:limit|budget)|context\s*(?:limit|window)|超出.{0,12}(?:读取|工具|上下文)|(?:tool|reader|context).{0,16}(?:unsupported|limit|error)|(?:4|32|64)\s*mi?b.{0,12}(?:limit|上限|限制))", re.I)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _unread_paths(value, path=""):
    """Delivered sources not read are process incompleteness, not material gaps."""
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            here = f"{path}.{key}" if path else key
            if key in {"unreviewed_sources", "unread_sources"} and item:
                found.append(here)
            elif key not in {"templates", "review_template"}:
                found.extend(_unread_paths(item, here))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_unread_paths(item, f"{path}[{index}]"))
    return found


def _errors(result):
    errors = []
    if result.get("processing_errors"):
        errors.append("检查器存在processing_errors；不能归为题包材料不足。")
    for name, section in result.get("sections", {}).items():
        if not isinstance(section, dict):
            errors.append(f"模块{name}结构错误。")
            continue
        for key in ("errors", "validation_errors"):
            if section.get(key):
                errors.append(f"模块{name}存在{key}；先修复内部底稿或检查器错误。")
    for path in _unread_paths(result.get("sections", {}), "sections"):
        errors.append(f"已交来源尚未读完：{path}。")
    return errors


def _validate_rows(result, errors):
    sections = result.get("sections")
    if not isinstance(sections, dict):
        errors.append("统一报告缺少sections。")
        return {}
    if set(sections) != set(EXPECTED):
        errors.append("自动终审须完整包含core/format/current_standard/supplement四模块。")
    indexed = {}
    for name, expected in EXPECTED.items():
        section = sections.get(name, {})
        rows = section.get("checks", []) if isinstance(section, dict) else []
        if not isinstance(rows, list):
            errors.append(f"模块{name}的checks不是数组。")
            continue
        ids = [row.get("id") if isinstance(row, dict) else None for row in rows]
        if len(ids) != len(expected) or set(ids) != expected:
            errors.append(f"模块{name}检查项不完整或重复；必须包含本版90项有效目录。")
        for row in rows:
            if isinstance(row, dict) and row.get("id") in expected:
                indexed[(name, row["id"])] = row
    return indexed


def _validate_gap(gap, root, indexed, seen):
    if not isinstance(gap, dict):
        raise ValueError("material_gaps条目必须是对象。")
    section, code = gap.get("section"), gap.get("check_id")
    if not isinstance(section, str) or not isinstance(code, str) or (section, code) not in indexed:
        raise ValueError("材料缺口必须精确指向本报告已有检查项。")
    key = (section, code)
    if key in seen:
        raise ValueError(f"材料缺口重复：{section}/{code}。")
    seen.add(key)
    row = indexed[key]
    if row.get("status") not in GAP_STATUSES:
        raise ValueError(f"{section}/{code}不是未结材料项，不能用缺口覆盖既有原判。")
    if row.get("review_complete") is False:
        raise ValueError(f"{section}/{code}自身内容审阅未完成，不能只靠缺口声明结案。")
    for fact in row.get("standard_original_findings", []):
        # Protection prevents waiving a real defect to PASS.  A protected
        # *manual* is still an unresolved factual question, and may terminate
        # as nonpassing MATERIALS_INCOMPLETE after complete, cited reading.
        # Never convert an original confirmed fail into a mere material gap.
        if isinstance(fact, dict) and fact.get("status") == "fail":
            raise ValueError(f"{section}/{code}包含已确认原缺陷，不能改为材料不足。")
    if row.get("required_for_static_completion", True) is not True:
        raise ValueError(f"{section}/{code}是非阻断的平台覆盖备注，不能升级材料不足。")
    if gap.get("kind") not in KINDS or gap.get("owner") not in OWNERS:
        raise ValueError(f"{section}/{code}的kind或owner无效。")
    if gap.get("read_complete") is not True:
        raise ValueError(f"{section}/{code}未完成已有材料阅读。")
    for field in ("missing_material", "why_needed", "next_action"):
        if not _text(gap.get(field)):
            raise ValueError(f"{section}/{code}缺少具体{field}。")
    explanation = " ".join(gap[field] for field in ("missing_material", "why_needed", "next_action"))
    if _TOOL_LIMIT.search(explanation):
        raise ValueError(f"{section}/{code}所述是工具/读取限制，不能归为专家材料不足。")
    refs = gap.get("reviewed_evidence")
    if not isinstance(refs, list) or not refs:
        raise ValueError(f"{section}/{code}需引用已读现有材料及其缺口依据。")
    for ref in refs:
        resolve_ref(root, ref)
    if gap["kind"] == "unreadable_source":
        source = gap.get("unreadable_source")
        if not _text(source):
            raise ValueError(f"{section}/{code}须定位损坏的原始文件。")
        # This proves existence/safe location, not the semantic claim of damage.
        # Actual damage and why it prevents this check must be explained above.
        if "#" in source:
            raise ValueError("unreadable_source须为原文件路径，不能是片段定位。")
        resolve_ref(root, source)
    elif gap.get("unreadable_source"):
        raise ValueError("materials_not_provided不能同时声称现有文件不可读。")
    return key


def _close_manual_reconciliations(output, indexed, valid):
    """An exact old manual finding can terminate as a gap, never as PASS.

    The migration layer calls an undecided manual original finding an input
    reconciliation error.  It also emits one exact summary-only error for that
    same condition.  Only these two semantic dispositions may close here;
    schema, reader, stale-ID and real-failure errors remain in the output.
    """
    gaps = {key: gap for key, gap in valid}
    section = output.get("sections", {}).get("core", {})
    original = section.get("errors", [])
    if not isinstance(original, list):
        return
    unfinished_core = [(key, row) for key, row in indexed.items() if key[0] == "core" and
                       row.get("required_for_static_completion", True) and row.get("status") in GAP_STATUSES]
    all_core_gaps = bool(unfinished_core) and all(
        key in gaps and row.get("review_complete") is True and
        all(isinstance(record, dict) and record.get("status") == "manual"
            for record in row.get("standard_original_findings", [])
            if isinstance(record, dict) and record.get("effective_status") == "review_not_finished")
        for key, row in unfinished_core)
    retained, resolutions = [], []
    for error in original:
        key = ("core", error.get("owner")) if isinstance(error, dict) else None
        row = indexed.get(key, {})
        records = row.get("standard_original_findings", [])
        unresolved = [record for record in records if isinstance(record, dict) and
                      record.get("effective_status") == "review_not_finished"]
        allowed = (isinstance(error, dict) and error.get("code") == "STANDARD_FINDING_UNRECONCILED" and
                   key in gaps and row.get("review_complete") is True and unresolved and
                   all(record.get("owner") == key[1] and record.get("status") == "manual"
                       for record in unresolved))
        if allowed:
            resolutions.append({"original_error": copy.deepcopy(error), "check_id": key[1],
                                "disposition": "materials_incomplete", "material_gap": copy.deepcopy(gaps[key])})
        elif (isinstance(error, dict) and error.get("code") == "REVIEW_NOT_FINISHED" and
              not error.get("owner") and error.get("summary") == LEGACY_UNFINISHED_SUMMARY and all_core_gaps):
            resolutions.append({"original_error": copy.deepcopy(error),
                                "check_ids": [item[0][1] for item in unfinished_core],
                                "disposition": "materials_incomplete",
                                "material_gaps": [copy.deepcopy(gaps[item[0]]) for item in unfinished_core]})
        else:
            retained.append(error)
    if resolutions:
        section["errors_before_automation"] = copy.deepcopy(original)
        section["errors"] = retained
        section["material_gap_error_resolutions"] = resolutions


def finalize(result, worksheet, root):
    """Return a copy with an automatic, conservative terminal disposition.

    MATERIALS_INCOMPLETE means review of the supplied materials is complete but
    an identified required material is absent/corrupt.  REVIEW_INCOMPLETE means
    review/tool work remains.  Neither outcome is PASS.  Existing failures win.
    """
    output = copy.deepcopy(result)
    root = Path(root).resolve()
    errors = []
    indexed = _validate_rows(output, errors)
    automation = (worksheet or {}).get("automation") if isinstance(worksheet, dict) else None
    if not isinstance(automation, dict):
        automation = {}
        errors.append("缺少Agent自动终审记录automation。")
    if automation.get("content_read_complete") is not True:
        errors.append("Agent尚未声明完整审阅已有内容；不能自动转为材料不足。")
    gaps = automation.get("material_gaps", [])
    if not isinstance(gaps, list):
        gaps = []
        errors.append("automation.material_gaps必须是逐项数组。")
    seen, valid = set(), []
    for gap in gaps:
        try:
            key = _validate_gap(gap, root, indexed, seen)
            valid.append((key, copy.deepcopy(gap)))
        except (OSError, ValueError, TypeError, UnicodeError) as exc:
            errors.append(str(exc))
    if not errors:
        _close_manual_reconciliations(output, indexed, valid)
    errors.extend(_errors(output))
    # No material disposition is applied while the Agent/checker is unfinished.
    if not errors:
        for key, gap in valid:
            row = indexed[key]
            row["raw_status"] = row.get("status")
            row["original_status"] = row.get("status")
            row["status"] = "material_incomplete"
            row["material_gap"] = gap
            row["summary_before_automation"] = row.get("summary", "")
            row["summary"] = gap["missing_material"] + "；" + gap["why_needed"]
            row["responsibility"] = gap["owner"]
            row["remediation"] = gap["next_action"]
        changed = {key[0] for key, _ in valid}
        for name in changed:
            section = output["sections"][name]
            rows = section.get("checks", [])
            if all(row.get("status") in SUCCESS | {"fail", "material_incomplete"} or
                   row.get("required_for_static_completion", True) is False for row in rows):
                section["complete_before_automation"] = section.get("complete", False)
                section["complete"] = True
    failures, unfinished, waivers, missing = [], [], [], []
    for name, section in output.get("sections", {}).items():
        if not isinstance(section, dict):
            continue
        for row in section.get("checks", []):
            if not isinstance(row, dict):
                continue
            item = {"section": name, **row}
            status = row.get("status")
            if status == "fail":
                failures.append(item)
            elif status == "material_incomplete":
                missing.append({**item, **copy.deepcopy(row.get("material_gap", {}))})
            elif status in {"waived", "pass_with_waivers"}:
                waivers.append(item)
            elif status not in SUCCESS and row.get("required_for_static_completion", True):
                unfinished.append(item)
        if not section.get("complete", False):
            unfinished.append({"section": name, "id": "COVERAGE", "status": "review_not_finished",
                               "summary": "本模块尚未完成审阅或校验。"})
    decision = ("FAIL" if failures else "REVIEW_INCOMPLETE" if errors or unfinished else
                "MATERIALS_INCOMPLETE" if missing else "PASS_WITH_WAIVERS" if waivers else "PASS")
    summary = copy.deepcopy(output.get("summary", {}))
    summary.update(decision=decision, review_complete=not errors and not unfinished,
                   failure_count=len(failures), unfinished_count=len(unfinished), waiver_count=len(waivers),
                   material_gap_count=len(missing), failed_checks=failures, unfinished_checks=unfinished,
                   waived_checks=waivers, missing_materials=missing)
    output.update(decision=decision, summary=summary, missing_materials=missing,
                  automation_final={"applied": True, "content_read_complete": automation.get("content_read_complete") is True,
                                    "manual_disposition_required": False, "errors": errors,
                                    "materials_complete": None if errors or unfinished else not missing,
                                    "review_process_complete": not errors and not unfinished,
                                    "evidence_validation_limit": "程序验证引用、结构和已有反证；语义支撑由执行Skill的Agent根据原始材料判断。"})
    return output
