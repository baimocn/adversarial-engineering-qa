#!/usr/bin/env python3
"""Validate evidence-backed A/B review worksheets without executing task code.

Semantic judgements are supplied by the reviewing agent/human after reading the
original references. This module checks coverage, local citations, exclusions,
report conditions and monotonic preservation of already-confirmed findings. It
never claims that citation existence proves its interpretation or a runtime run.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path

A_TITLES = [
    "运行未完成或成绩没有对应真实候选", "轨迹实际违规", "题面说明与实际执行不一致",
    "要求优化的内容不参与评分", "承诺的资源不可用", "私有信息或参考解泄漏",
]
P_TITLES = [
    "Docker Hub网络不可达", "APT下载403及连带签名错误", "Python分发、索引或环境兼容",
    "基础镜像引用或拉取授权", "Git访问、锁与推送", "发布包结构或归档损坏",
    "wheel下载拒绝或代理错误", "镜像层上传会话失效", "模型或公开资产下载链路",
    "npm代理认证失败", "镜像manifest、digest或代理异常", "构建上下文资产路径缺失",
    "APT退出100但无首条致命错误", "APT固定版本在当前源缺失", "Python依赖约束冲突",
    "题包准备脚本或资产校验失败", "证书包所需临时目录缺失", "评分资产或锚点装配不一致",
    "准备进程读取源包权限失败", "bootstrap解释器无法启动", "sudoers语法校验失败",
    "Docker Hub manifest明确429", "创建用户UID冲突", "sudo资产所有下载源失败但首因未留存",
    "Python依赖哈希校验失败",
]
E_TITLES = [
    "工作目录可写性预检拦截", "HOME、临时目录、日志或PID权限失败", "Agent超时",
    "其他非零Agent退出", "Agent安全拒绝", "执行终态存在但缺原生摘要",
    "环境健康检查失败", "环境创建或cgroup设置失败", "沙箱生命周期异常",
]
S_TITLES = ["缺评分文件", "Verifier目录下载或回传失败", "非数值评分"]
C_TITLES = ["唯一源任务配置与固定位置", "源包Dockerfile交付及实际镜像分支", "依赖官方源", "npm指定bnpm源"]
CATALOG = {}
for prefix, titles, scope, stage in (
    ("A", A_TITLES, "algorithm_original_A", "static_and_history"),
    ("B-C", C_TITLES, "platform_source", "source"),
    ("B-P", P_TITLES, "platform_runtime", "preparation"),
    ("B-E", E_TITLES, "platform_runtime", "execution"),
    ("B-S", S_TITLES, "platform_runtime", "scoring"),
):
    for index, title in enumerate(titles, 1):
        CATALOG[f"{prefix}{index:02d}"] = {"title": title, "scope": scope, "stage": stage}
CATALOG.update({
    "B-GPU": {"title": "GPU初始化契约与路由", "scope": "platform_runtime", "stage": "execution"},
    "B-ENV": {"title": "平台必需变量注入（不记录值）", "scope": "platform_runtime", "stage": "execution"},
})
STATUSES = {"reviewed_no_finding", "findings", "evidence_limited", "not_applicable"}
A_EXCLUDED_TOPICS = {
    "time_limit", "network_configuration", "gpu_type", "internal_error_classification",
    "malformed_output", "theoretical_attack", "stale_hash", "reference_calibration",
    "seed_visibility", "dev_visibility", "maintenance_only",
}
RUNTIME_IDS = {"A01", "A02"}
STATIC_ROLES = {"instruction", "task_config", "solver_visible", "scorer"}
OWNERS = {"author", "platform", "author_or_platform"}


def template():
    """Internal reviewer worksheet, never an additional expert deliverable."""
    return {
        "schema_version": "1.0",
        "materials": {
            "runtime_available": False,
            "static_files": [],
            "session_inventory": {"complete": False, "evidence": []},
            "sessions": [],
            "candidate_chain": {},
            "platform_logs": [],
            "verifier_branch": {},
        },
        "stage_reviews": {},
        "difficulty": {
            "judgment": None, "reason": "未作难度判断；不作为验收要求", "evidence": [],
            "basis": {"first_valid_improvement": "", "final_score": "", "method_complexity": "", "remaining_space": ""},
        },
        "checks": {code: {"status": "evidence_limited", "reason": "尚未完成逐项阅读",
                          "evidence": [], "findings": []} for code in CATALOG},
    }


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def _refs(root, values):
    """Check local citation existence only; never import, execute or unpickle."""
    good, errors = [], []
    if not isinstance(values, list):
        return [], ["evidence必须为本地引用列表"]
    for value in values:
        item = {"path": value} if isinstance(value, str) else value
        if not isinstance(item, dict) or not _nonempty(item.get("path")):
            errors.append("引用必须含path")
            continue
        path = Path(item["path"])
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"引用越出材料根目录: {item['path']}")
            continue
        resolved = (root / path).resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            errors.append(f"符号链接引用越出材料根目录: {item['path']}")
            continue
        if not resolved.is_file():
            errors.append(f"引用不是可读本地文件: {item['path']}")
            continue
        try:
            with resolved.open("rb") as stream:
                stream.read(1)
        except OSError:
            errors.append(f"引用不可读: {item['path']}")
            continue
        # A location is optional: evidence may identify the entire local file.
        # No arbitrary size/JSON-top-level cutoff is used here.
        good.append(deepcopy(item))
    return good, errors


def _full_ranges(total, ranges):
    if not isinstance(total, int) or isinstance(total, bool) or total < 0 or not isinstance(ranges, list):
        return False
    if total == 0:
        return ranges == []
    ordered = []
    for pair in ranges:
        if not isinstance(pair, list) or len(pair) != 2:
            return False
        first, last = pair
        if any(not isinstance(n, int) or isinstance(n, bool) for n in pair) or first < 1 or last < first or last > total:
            return False
        ordered.append((first, last))
    end = 0
    for first, last in sorted(ordered):
        if first > end + 1:
            return False
        end = max(end, last)
    return end == total


def _material_coverage(root, materials):
    errors, roles = [], set()
    rows = materials.get("static_files", [])
    if not isinstance(rows, list):
        rows = []
        errors.append("materials.static_files须为列表")
    for row in rows:
        if not isinstance(row, dict):
            errors.append("static_files条目须为对象")
            continue
        refs, bad = _refs(root, [{"path": row.get("path", "")}])
        errors.extend(bad)
        if refs and row.get("read_complete") is True:
            role = row.get("role")
            role_values = role if isinstance(role, list) else [role] if isinstance(role, str) else []
            if any(not isinstance(value, str) for value in role_values):
                errors.append("static_files.role须为角色字符串或字符串列表")
            roles.update(value for value in role_values if isinstance(value, str))
    static_complete = STATIC_ROLES <= roles
    sessions, seen, session_errors = [], set(), []
    raw_sessions = materials.get("sessions", [])
    if not isinstance(raw_sessions, list):
        raw_sessions = []
        session_errors.append("materials.sessions须为列表")
    for row in raw_sessions:
        if not isinstance(row, dict):
            session_errors.append("session条目须为对象")
            continue
        sid = row.get("id")
        if not _nonempty(sid) or sid in seen:
            session_errors.append("会话ID缺失或重复")
        else:
            seen.add(sid)
        refs, bad = _refs(root, [{"path": row.get("path", "")}])
        session_errors.extend(bad)
        complete = _full_ranges(row.get("total_messages"), row.get("read_ranges"))
        if not complete or not _nonempty(row.get("count_basis")):
            session_errors.append(f"会话{sid!s}未完整覆盖或缺消息计数依据")
        if row.get("kind") not in {"main", "subagent", "retry", "recovery"}:
            session_errors.append(f"会话{sid!s}的kind无效")
        sessions.append({"id": sid, "path": row.get("path"), "kind": row.get("kind"),
                         "total_messages": row.get("total_messages"), "read_ranges": row.get("read_ranges"),
                         "full_coverage_declared": bool(complete and refs and _nonempty(row.get("count_basis")))})
    inventory = materials.get("session_inventory", {})
    if not isinstance(inventory, dict):
        inventory = {}
    inv_refs, inv_bad = _refs(root, inventory.get("evidence", []))
    runtime_available = materials.get("runtime_available") is True
    sessions_complete = bool(runtime_available and sessions and not session_errors and
                             inventory.get("complete") is True and inv_refs and not inv_bad and
                             any(row["kind"] == "main" for row in sessions))
    # These are reviewer coverage attestations, not independently parsed sessions.
    return {
        "static_complete": static_complete, "static_roles_read": sorted(roles),
        "runtime_available": runtime_available, "sessions_complete": sessions_complete,
        "sessions": sessions, "session_inventory_complete_declared": inventory.get("complete") is True,
        "errors": errors + session_errors + inv_bad,
        "verification_limit": "模块仅校验本地引用与覆盖声明的结构；未自动证明审阅者实际阅读或语义结论正确",
    }


def _chain_ready(root, materials):
    chain = materials.get("candidate_chain", {})
    if not isinstance(chain, dict):
        return False
    refs, errors = _refs(root, chain.get("evidence", []))
    return bool(refs and not errors and all(_nonempty(chain.get(key)) for key in
                ("solver_final", "verifier_input", "raw_metrics", "authoritative_reward"))
                and chain.get("correspondence_reviewed") is True)


def _branch_ready(root, materials):
    branch = materials.get("verifier_branch", {})
    if not isinstance(branch, dict):
        return False
    refs, errors = _refs(root, branch.get("evidence", []))
    return bool(refs and not errors and isinstance(branch.get("selected"), str) and branch.get("selected") in
                {"inherit_solver", "tests_dockerfile", "explicit_verifier_image"} and
                all(_nonempty(branch.get(key)) for key in
                    ("tests_assembly", "dependencies", "artifacts_transfer", "independent_sandbox", "private_visibility")))


def _finding(root, code, value, stage, materials):
    """Apply A report conditions; B incidents need facts and evidenced attribution."""
    if not isinstance(value, dict):
        return None, ["finding须为对象"]
    item = deepcopy(value)
    refs, errors = _refs(root, value.get("evidence", []))
    for key in ("id", "title", "root_cause", "impact", "action", "owner_basis"):
        if not _nonempty(value.get(key)):
            errors.append(f"finding缺{key}")
    if not refs:
        errors.append("finding缺可读的直接证据引用")
    if not isinstance(value.get("owner"), str) or value.get("owner") not in OWNERS:
        errors.append("owner须为author/platform/author_or_platform")
    if value.get("owner") == "author_or_platform":
        for key in ("author_option", "platform_option"):
            if not _nonempty(value.get(key)):
                errors.append(f"责任未定须给出{key}")
    facts = value.get("facts", {})
    if not isinstance(facts, dict):
        facts = {}
        errors.append("facts须为对象")
    topic = value.get("topic")
    exclusion = None
    if code.startswith("A") and isinstance(topic, str) and topic in A_EXCLUDED_TOPICS:
        actual_boundary_violation = (code == "A02" and facts.get("operation_succeeded") is True and
                                     facts.get("repairable_technical_boundary") is True)
        formal_private_use = (code == "A06" and facts.get("solver_access_proven") is True and
                              (facts.get("direct_formal_target_utility") is True or facts.get("actually_used") is True))
        if not (actual_boundary_violation or formal_private_use):
            exclusion = "属于原A明确排除项；仅在其他模块按其独立规则审查"
    if code in {"A01", "A03", "A04", "A05"}:
        for key in ("contract", "actual_execution", "normal_trigger", "actual_impact"):
            if not _nonempty(facts.get(key)):
                errors.append(f"原A{code}缺事实{key}")
        if code == "A01":
            if facts.get("occurred") is not True:
                errors.append("A01须为已发生问题")
            if facts.get("solver_abandoned") is True:
                exclusion = "solver自行放弃或主动终止，不按A01提出修改"
        elif facts.get("compliant_submission_affected") is not True:
            errors.append(f"{code}须证明正常合规提交受影响")
        if code == "A04" and facts.get("output_entirely_unused") is not True:
            errors.append("A04须证明要求优化/产出的内容完全未进入评分")
        if code == "A05" and not (facts.get("normal_call_failed") is True or facts.get("inevitable_source_failure") is True):
            errors.append("A05须有正常调用实际失败或源码必然失败的证据")
        chain = materials.get("candidate_chain", {})
        if isinstance(chain, dict) and chain.get("valid_scoring_completed") is True:
            if not _nonempty(facts.get("counterevidence_review")):
                errors.append("已有有效成绩时须复核反证，不能忽略对应关系")
            if code == "A01" and facts.get("claim") in {"current_unscored", "current_incomplete"}:
                errors.append("当前候选有效评分完成与本项未完成断言冲突")
    if code == "A02":
        for key in ("technical_boundary", "successful_action", "actual_effect", "failed_boundary", "non_disruptive_repair"):
            if not _nonempty(facts.get(key)):
                errors.append(f"A02缺事实{key}")
        if facts.get("operation_succeeded") is not True:
            errors.append("A02只有请求/理论方式不能确认为实际违规")
        if facts.get("repairable_technical_boundary") is not True:
            exclusion = "未证明可修复且不破坏正常研究用途的技术边界，不向作者/rollout报告"
        if facts.get("rule_compliance") != "noncompliant" or (not isinstance(facts.get("score_trust"), str) or facts.get("score_trust") not in {"credible", "not_credible"}):
            errors.append("A02须分别填写规则不合规与成绩可信性")
    if code == "A06":
        for key in ("private_content", "private_classification", "access_or_reconstruction", "external_dependency", "actual_use"):
            if not _nonempty(facts.get(key)):
                errors.append(f"A06缺事实{key}")
        if facts.get("solver_access_proven") is not True:
            errors.append("A06须证实solver可见/获得或可以重建；目录名/URL不足")
        if not (facts.get("direct_formal_target_utility") is True or facts.get("actually_used") is True):
            errors.append("A06须证明直接解题用途或本次已实际使用")
        if facts.get("depends_on_external") is True and facts.get("external_obtained") is not True:
            errors.append("A06依赖包外材料时须证明本次成功取得")
    if facts.get("recovered_without_contamination") is True and (code in {"A01", "A03", "A05"} or code.startswith("B-")):
        exclusion = "已有证据证明错误恢复且未污染候选或成绩，不保留为返修项"
    if code.startswith("B-"):
        for key in ("first_confirmed_failure", "minimal_repair_point"):
            if not _nonempty(facts.get(key)):
                errors.append(f"平台问题缺事实{key}")
        if code.startswith(("B-P", "B-E", "B-S")) or code in {"B-GPU", "B-ENV"}:
            if facts.get("occurred") is not True:
                errors.append("平台运行原因族须有已发生错误，不能仅匹配配置/关键词")
        if code == "B-C02" and stage == "runtime" and topic == "docker_image_present":
            exclusion = "docker_image源包禁配规则不适用于平台生成的运行配置"
    if code in {"A01", "A02", "A04", "A06"} and facts.get("independent_reread") is not True:
        errors.append(f"{code}关键文件须独立重读复核")
    item.update({"check_ids": [code], "scope": CATALOG[code]["scope"], "evidence": refs,
                 "owner_required": True, "provenance": "human_or_model_evidence_review",
                 "evidence_verification": "local_reference_exists_only"})
    if exclusion:
        item["excluded_reason"] = exclusion
        return item, errors
    return item, errors


def apply_review(root, review=None, *, package_stage="source", known_findings=None, task_id="本题"):
    """Return all 49 A/B rows, limitations and evidence-backed repair actions.

    ``known_findings`` is caller-supplied independently established output. Its
    confirmed failures survive any worksheet no-finding/recovery declaration.
    This module never grants legacy waivers; the unified caller owns that policy.
    """
    root = Path(root).resolve()
    errors = []
    if not isinstance(package_stage, str) or package_stage not in {"source", "runtime", "combined"}:
        errors.append({"check_id": "context", "message": "package_stage须为source/runtime/combined"})
        package_stage = "source"
    if review is None:
        review = {}
    if not isinstance(review, dict):
        errors.append({"check_id": "schema", "message": "supplement审阅底稿须为对象"})
        review = {}
    materials = review.get("materials", {})
    if not isinstance(materials, dict):
        materials = {}
        errors.append({"check_id": "materials", "message": "materials须为对象"})
    materials_coverage = _material_coverage(root, materials)
    errors.extend({"check_id": "materials", "message": msg} for msg in materials_coverage["errors"])
    platform_stages_read = set()
    platform_stages_present = set()
    platform_logs = materials.get("platform_logs", [])
    if not isinstance(platform_logs, list):
        platform_logs = []
        errors.append({"check_id": "materials", "message": "platform_logs须为列表"})
    for log in platform_logs:
        if not isinstance(log, dict):
            continue
        log_refs, bad = _refs(root, [{"path": log.get("path", "")}])
        errors.extend({"check_id": "materials", "message": msg} for msg in bad)
        if log_refs and not bad and isinstance(log.get("stage"), str):
            platform_stages_present.add(log["stage"])
            if log.get("read_complete") is True:
                platform_stages_read.add(log["stage"])
    materials_coverage["platform_stages_read"] = sorted(platform_stages_read)
    checks = review.get("checks", {})
    if not isinstance(checks, dict):
        checks = {}
        errors.append({"check_id": "schema", "message": "checks须为对象"})
    for unknown in sorted(set(checks) - set(CATALOG)):
        errors.append({"check_id": str(unknown), "message": "未知增量检查编号"})
    stage_reviews = review.get("stage_reviews", {})
    if not isinstance(stage_reviews, dict):
        stage_reviews = {}
    coverage, findings, excluded = {}, [], []
    for code, metadata in CATALOG.items():
        inherited = False
        row = checks.get(code)
        if row is None and metadata["stage"] in {"preparation", "execution", "scoring"}:
            row = stage_reviews.get(metadata["stage"])
            inherited = row is not None
        row = row if isinstance(row, dict) else {}
        row_errors, refs = [], []
        requested = row.get("status", "not_reviewed")
        if not isinstance(requested, str):
            row_errors.append("status须为字符串")
            requested = "evidence_limited"
        status = requested
        if requested not in STATUSES | {"not_reviewed"}:
            row_errors.append("不支持的status")
            status = "evidence_limited"
        refs, bad = _refs(root, row.get("evidence", []))
        row_errors.extend(bad)
        if requested in {"reviewed_no_finding", "findings", "not_applicable"}:
            if not _nonempty(row.get("reason")):
                row_errors.append("须说明逐项判断依据reason")
            if not refs:
                row_errors.append("须有可读的本地证据引用；不能空填通过")
        if code.startswith("A") and requested == "reviewed_no_finding":
            if code in RUNTIME_IDS and materials_coverage["runtime_available"]:
                if not materials_coverage["sessions_complete"]:
                    row_errors.append("主/子/恢复/重试会话未完整覆盖，不能宣称轨迹审查完成")
                if code == "A01" and not _chain_ready(root, materials):
                    row_errors.append("最终候选至权威reward对应链尚未完成核对")
            elif code not in RUNTIME_IDS and not materials_coverage["static_complete"]:
                row_errors.append("题面、配置、solver可见材料及评分实现尚未完成静态通读")
        if code in RUNTIME_IDS and not materials_coverage["runtime_available"]:
            # Original A explicitly skips trajectory/difficulty without runtime.
            # A confirmed supplied finding remains retained below.
            if requested not in {"findings"}:
                status = "skipped_no_runtime"
        elif code in RUNTIME_IDS and requested == "not_applicable":
            row_errors.append("已有运行材料时A01/A02不能以不适用跳过完整会话阅读")
        if code in {"A03", "A04", "A05", "A06", "B-C01", "B-C02", "B-C03"} and requested == "not_applicable":
            if not (code.startswith("B-C") and package_stage == "runtime"):
                row_errors.append("本项不能整体标为不适用；应完成静态检查")
        if code == "B-C02" and requested == "reviewed_no_finding" and not _branch_ready(root, materials):
            row_errors.append("需核对实际Verifier分支、装配、依赖、移交与独立私有边界")
        if code.startswith("B-C") and package_stage == "runtime" and requested == "reviewed_no_finding":
            # A platform-generated runtime package is not a source-package pass.
            row_errors.append("只读运行包不能宣称源包四项已通过；引用源包或记不适用/覆盖限制")
        if metadata["stage"] in {"preparation", "execution", "scoring"}:
            if requested == "reviewed_no_finding" and metadata["stage"] not in platform_stages_read:
                row_errors.append("缺本阶段已完整阅读的平台日志；不能以未匹配错误词视为通过")
            if requested == "not_applicable" and code not in {"B-GPU", "B-ENV"}:
                row_errors.append("平台运行原因族缺材料时记覆盖限制，不能整项标为不适用")
        if inherited and requested == "reviewed_no_finding":
            declared = row.get("coverage", {})
            if not isinstance(declared, dict) or declared.get("complete") is not True:
                row_errors.append("阶段汇总须声明完整阅读本阶段已有材料，不能靠未命中关键词批量通过")
        raw_findings = row.get("findings", [])
        if not isinstance(raw_findings, list):
            raw_findings = []
            row_errors.append("findings须为列表")
        if inherited:
            # Stage inheritance is for coverage, never clone a finding into all
            # 25/9/3 families; each incident must identify its own check_id.
            raw_findings = [f for f in raw_findings if isinstance(f, dict) and f.get("check_id") == code]
        accepted = []
        for value in raw_findings:
            item, bad = _finding(root, code, value, package_stage, materials)
            row_errors.extend(bad)
            if item is None:
                continue
            if item.get("excluded_reason"):
                excluded.append(item)
            elif not bad:
                accepted.append(item)
                findings.append(item)
        if accepted:
            status = "findings"
        elif requested == "findings":
            if not raw_findings:
                row_errors.append("findings状态必须包含本项具体发现")
            status = "evidence_limited" if row_errors else "reviewed_no_finding"
        if status == "reviewed_no_finding" and requested != "reviewed_no_finding" and code.startswith("A"):
            if code in RUNTIME_IDS and not materials_coverage["sessions_complete"]:
                row_errors.append("排除一条疑似发现不能代替完整轨迹审查")
            elif code not in RUNTIME_IDS and not materials_coverage["static_complete"]:
                row_errors.append("排除一条疑似发现不能代替完整静态审查")
        if row_errors and status not in {"findings", "skipped_no_runtime"}:
            status = "evidence_limited"
        if requested == "not_reviewed" and code not in RUNTIME_IDS:
            status = "not_reviewed"
        errors.extend({"check_id": code, "message": msg} for msg in row_errors)
        limit = row.get("coverage_limit", {})
        limit_recorded = (isinstance(limit, dict) and limit.get("kind") in
                          {"not_executed", "materials_not_provided"} and
                          _nonempty(limit.get("details")) and _nonempty(limit.get("next_action")) and
                          _nonempty(row.get("reason")))
        if metadata["stage"] in {"preparation", "execution", "scoring"}:
            # An unread delivered log is not a missing-platform-material waiver.
            if metadata["stage"] in platform_stages_present and metadata["stage"] not in platform_stages_read:
                limit_recorded = False
        record_complete = ((status in {"reviewed_no_finding", "findings", "not_applicable"} and not row_errors) or
                           status == "skipped_no_runtime" or
                           (status == "evidence_limited" and limit_recorded and not row_errors))
        coverage[code] = {**metadata, "status": status, "coverage_record_complete": record_complete,
                          "coverage_limit": deepcopy(limit) if isinstance(limit, dict) else {}, "requested_status": requested,
                          "reason": row.get("reason", "未提供本项审阅记录"), "evidence": refs,
                          "coverage_origin": "stage_review" if inherited else "item_review",
                          "owner_required": bool(accepted), "action": [f["action"] for f in accepted],
                          "execution": "not_executed_by_module",
                          "fact_basis": "historical_or_static_evidence" if refs else "materials_not_provided"}
    # Already-confirmed findings are append-only input to this merger. A new
    # worksheet no-finding statement is never an override operation.
    for old in known_findings or []:
        if not isinstance(old, dict):
            errors.append({"check_id": "known_findings", "message": "已确认发现须为对象"})
            continue
        state = str(old.get("status", old.get("state", ""))).lower()
        if old.get("confirmed") is not True and state not in {"fail", "confirmed", "invalid", "failure"}:
            continue
        copied = deepcopy(old)
        copied["provenance"] = "preserved_independent_confirmed_finding"
        copied["cannot_be_cleared_by_worksheet"] = True
        findings.append(copied)
        code = copied.get("check_id", copied.get("id"))
        if isinstance(code, str) and code in coverage:
            coverage[code]["status"] = "findings"
            coverage[code]["owner_required"] = True
            if copied.get("action"):
                coverage[code]["action"].append(copied["action"])
    # Merge only same cause AND same repair action. Keep all linked A/B IDs and
    # original evidence rather than hiding a confirmed issue by category order.
    merged = []
    index = {}
    for item in findings:
        key = tuple(str(item.get(k, "")).strip() for k in ("root_cause", "action"))
        if not all(key) or key not in index:
            if all(key):
                index[key] = len(merged)
            merged.append(item)
        else:
            target = merged[index[key]]
            for field in ("check_ids", "evidence"):
                for value in item.get(field, []):
                    if value not in target.setdefault(field, []):
                        target[field].append(value)
            if item.get("cannot_be_cleared_by_worksheet"):
                target["cannot_be_cleared_by_worksheet"] = True
    static_codes = ["A03", "A04", "A05", "A06"] + [f"B-C{i:02d}" for i in range(1, 5)]
    static_review_complete = materials_coverage["static_complete"] and all(
        coverage[code]["status"] in {"reviewed_no_finding", "findings", "not_applicable"} and
        coverage[code]["coverage_record_complete"] for code in static_codes)
    coverage_record_complete = all(row["coverage_record_complete"] for row in coverage.values())
    complete = all(row["status"] in {"reviewed_no_finding", "findings", "not_applicable", "skipped_no_runtime"}
                   for row in coverage.values()) and not errors and materials_coverage["static_complete"] and (
                       not materials_coverage["runtime_available"] or materials_coverage["sessions_complete"])
    report = {
        "module": "supplement_A_B", "schema_version": "1.0", "package_stage": package_stage,
        "status": "FINDINGS" if merged else "COMPLETE" if complete else "LIMITED",
        "review_complete": complete,
        "static_review_complete": static_review_complete,
        "coverage_record_complete": coverage_record_complete,
        "provided_runtime_review_complete": (not materials_coverage["runtime_available"] or materials_coverage["sessions_complete"]) and
                                             platform_stages_present <= platform_stages_read,
        "coverage": coverage, "findings": merged,
        "excluded_findings": excluded, "validation_errors": errors,
        "materials_coverage": materials_coverage,
        "actions": [{"check_ids": f.get("check_ids", [f.get("check_id", f.get("id"))]),
                     "owner": f.get("owner", "not_established"), "action": f.get("action", "保留原已确认发现并按原证据处理"),
                     "owner_required": True} for f in merged],
        "runtime": {"executed_by_module": False, "network_access": False,
                    "score_or_source_files_modified": False,
                    "claim": "只读材料审查，未运行题包或平台；静态与历史事实不代表当前端到端运行通过"},
    }
    report["algorithm_output"] = algorithm_output(root, task_id, review, report)
    return report


def algorithm_output(root, task_id, review, result):
    """Render original A's <=100-code-point conclusion and non-gating difficulty.

    This function only consumes already-evaluated A findings and coverage. It
    never converts platform B defects into an A defect or invents difficulty.
    Full evidence remains unabridged outside the short main conclusion.
    """
    root = Path(root).resolve()
    review = review if isinstance(review, dict) else {}
    result = result if isinstance(result, dict) else {}
    materials = review.get("materials", {})
    materials = materials if isinstance(materials, dict) else {}
    coverage = result.get("coverage", {})
    coverage = coverage if isinstance(coverage, dict) else {}
    material_coverage = result.get("materials_coverage", {})
    material_coverage = material_coverage if isinstance(material_coverage, dict) else {}
    full_id = " ".join(str(task_id or "本题").split()) or "本题"
    shown_id = full_id if len(full_id) <= 42 else full_id[:41] + "…"
    a_ids = {f"A{i:02d}" for i in range(1, 7)}
    details = []
    for finding in result.get("findings", []):
        if not isinstance(finding, dict):
            continue
        codes = finding.get("check_ids", [])
        codes = codes if isinstance(codes, list) else []
        codes = [value for value in codes if isinstance(value, str) and value in a_ids]
        single = finding.get("check_id", finding.get("id"))
        if isinstance(single, str) and single in a_ids and single not in codes:
            codes.append(single)
        if codes:
            detail = deepcopy(finding)
            detail["algorithm_check_ids"] = codes
            details.append(detail)
    static_complete = bool(material_coverage.get("static_complete")) and all(
        isinstance(coverage.get(code), dict) and
        coverage[code].get("status") in {"reviewed_no_finding", "findings"} and
        coverage[code].get("coverage_record_complete") is True for code in ("A03", "A04", "A05", "A06"))
    runtime_available = material_coverage.get("runtime_available") is True
    runtime_complete = (not runtime_available) or (material_coverage.get("sessions_complete") is True and all(
        isinstance(coverage.get(code), dict) and
        coverage[code].get("status") in {"reviewed_no_finding", "findings"} and
        coverage[code].get("coverage_record_complete") is True for code in ("A01", "A02")))
    a_complete = static_complete and runtime_complete
    if details:
        first = details[0]
        label = {"author": "出题人", "platform": "rollout", "author_or_platform": "出题人或rollout"}.get(first.get("owner") if isinstance(first.get("owner"), str) else "")
        owner_text = f"[{label}] " if label else "[负责方见证据明细] "
        action = " ".join(str(first.get("action") or first.get("title") or "修复已确认问题").split())
        impact = " ".join(str(first.get("impact") or first.get("root_cause") or "原因见证据明细").split())
        extra = f"另有{len(details)-1}项，详见明细。" if len(details) > 1 else ""
        prefix = f"{shown_id}：{owner_text}"
        suffix = f"。{extra}"
        available = max(2, 100 - len(prefix) - len(suffix) - 1)
        action_budget = max(1, int(available * 0.6))
        impact_budget = max(1, available - action_budget)
        def clipped(text, budget):
            return text if len(text) <= budget else text[:max(0, budget - 1)] + "…"
        main = f"{prefix}{clipped(action, action_budget)}；{clipped(impact, impact_budget)}{suffix}"
        conclusion = "must_modify"
    elif a_complete:
        main = f"{shown_id}：无必须修改。"
        conclusion = "no_must_modify"
    else:
        main = f"{shown_id}：原A六类审查尚未完成，不能给出“无必须修改”结论。"
        conclusion = "review_incomplete"
    if len(main) > 100:
        main = main[:99] + "…"
    difficulty = {"status": "not_judged", "judgment": None, "reason": "未提供有证据的难度判断，不猜测难度",
                  "evidence": [], "basis": {}, "acceptance_gate": False, "notes": []}
    raw_difficulty = review.get("difficulty", {})
    raw_difficulty = raw_difficulty if isinstance(raw_difficulty, dict) else {}
    judgment = raw_difficulty.get("judgment")
    if not runtime_available:
        difficulty.update(status="not_applicable", reason="未提供运行材料；按原A不作难度判断")
    elif judgment is not None:
        chain = materials.get("candidate_chain", {})
        chain = chain if isinstance(chain, dict) else {}
        refs, ref_errors = _refs(root, raw_difficulty.get("evidence", []))
        basis = raw_difficulty.get("basis", {})
        basis = basis if isinstance(basis, dict) else {}
        basis_keys = ("first_valid_improvement", "final_score", "method_complexity", "remaining_space")
        notes = list(ref_errors)
        if not isinstance(judgment, str) or judgment not in {"明确偏易", "有偏易迹象", "暂不判偏易"}:
            notes.append("难度判断仅接受原A的三个枚举")
        if not refs or not _nonempty(raw_difficulty.get("reason")) or not all(_nonempty(basis.get(key)) for key in basis_keys):
            notes.append("难度判断须有本地证据、理由及改善时间/最终成绩/方法复杂度/剩余空间依据")
        score_contested = any(isinstance(item.get("facts"), dict) and item["facts"].get("score_trust") == "not_credible"
                              for item in details)
        if not (runtime_complete and _chain_ready(root, materials) and chain.get("valid_scoring_completed") is True and
                chain.get("score_trust") == "credible") or score_contested:
            notes.append("现有运行材料/候选成绩对应链尚不能支持可信成绩后的难度判断")
        if notes:
            difficulty.update(reason="难度依据不足，未采纳判断；不影响验收结论", notes=notes)
        else:
            difficulty.update(status="reviewed", judgment=judgment, reason=raw_difficulty["reason"],
                              evidence=refs, basis=deepcopy(basis))
    return {
        "task_id": full_id, "main_conclusion": main, "main_conclusion_unicode_length": len(main),
        "conclusion": conclusion, "review_complete": a_complete,
        "coverage_basis": "static_and_history" if a_complete and runtime_available else "static_only" if a_complete else "incomplete",
        "evidence_details": details,
        "coverage_limitations": ["未提供运行材料，A01/A02及难度未审；静态无必须修改不代表历史运行已验收"] if not runtime_available else
                                ([] if runtime_complete else ["已提供的运行会话或候选成绩链尚未完成审查"]),
        "difficulty": difficulty,
        "scope": "original_algorithm_A_only",
        "note": "主结论限100个Unicode字符；证据明细不受此限制。难度与质量问题分开，不作为验收硬门。",
    }


def validate(root, review, **kwargs):
    """Return worksheet validation errors; no semantic judgement is automated."""
    return apply_review(root, review, **kwargs)["validation_errors"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, nargs="?")
    parser.add_argument("--review", type=Path)
    parser.add_argument("--package-stage", choices=["source", "runtime", "combined"], default="source")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--task-id", default="本题")
    parser.add_argument("--template", action="store_true")
    args = parser.parse_args()
    if args.template:
        result = template()
    else:
        if args.root is None:
            parser.error("需要材料根目录，或使用--template")
        review = json.loads(args.review.read_text(encoding="utf-8")) if args.review else None
        result = apply_review(args.root, review, package_stage=args.package_stage, task_id=args.task_id)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
