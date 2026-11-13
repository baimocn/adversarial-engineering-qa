"""Versioned provider, phase and project GPU policy; reads configuration only.

A supported field is a schema/capability observation, not proof of runtime
isolation or actual GPU availability. Source packages and runtime packages are
intentionally separate: external authors do not need internal image tags.
"""
import json

import docker_paths

INNERFIELD = "innerfield-maso-v1"
MIDO = "mido-2026-11-03"
GENERIC = "generic-harbor"
PROFILES = (INNERFIELD, MIDO, GENERIC)
UNKNOWN = "unknown"
STAGES = ("source_package", "runtime_package")
GPU_TYPES = {"H20", "L20"}
MIDO_SOURCE = "https://tosv.byted.org/obj/eden-internal/100upeupq/mido/harbor-alignment/alignment.html"


def aggregate(statuses):
    return "fail" if "fail" in statuses else "manual" if "manual" in statuses else "pass"


def is_innerfield(profile):
    return profile in (INNERFIELD, MIDO)


def source_stage(stage):
    return stage in ("source", "source_package")


def declared_profile(review):
    """A missing assessor target never silently selects a platform."""
    value = review.get("deployment_profile")
    return value if isinstance(value, str) and value.strip() else UNKNOWN


def environments(config):
    cfg = config if isinstance(config, dict) else {}
    agent = cfg.get("environment", {})
    verifier = cfg.get("verifier", {})
    specific = verifier.get("environment") if isinstance(verifier, dict) else None
    return {"agent": agent if isinstance(agent, dict) else {},
            "verifier": specific if isinstance(specific, dict) else agent if isinstance(agent, dict) else {}}


def gpu_policy(env, selection=None, *, stage="source_package", role="agent"):
    """Separate candidate syntax, safe selection and observed allocation.

    selection is reviewer metadata referencing existing provider evidence, never
    a required task.toml field. A source candidate list is feasible when it
    contains H20/L20; it does not require internal selection logs. Existing
    rejection, selection and allocation evidence still controls the conclusion.
    runtime_package requires actual_type. Merely writing these names does not
    authenticate logs; callers validate evidence and reviewers check its meaning.
    """
    selection = selection if isinstance(selection, dict) else {}
    stage = {"source": "source_package", "runtime": "runtime_package"}.get(stage, stage)
    rows = []
    def add(code, status, message):
        rows.append({"code": code, "status": status, "message": role + ": " + message, "category": "gpu"})
    count = env.get("gpus", 0)
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        add("gpu_count_unresolved", "manual", "有效 gpus 数量无法确定。")
        return rows
    if count > 8:
        add("gpu_count_exceeded", "fail", "GPU 申请超过项目上限 8。")
    if not count:
        return rows
    types = env.get("gpu_types")
    if not isinstance(types, list) or not types or not all(isinstance(v, str) and v.strip() for v in types):
        add("gpu_types_missing", "manual", "申请 GPU 但未明确候选卡型；实际内场只接收 H20/L20。")
        return rows
    cards = {v.strip().upper() for v in types}
    if not cards.intersection(GPU_TYPES):
        add("gpu_type_unsupported", "fail", "候选列表没有 H20/L20，无法选择项目允许卡型。")
        return rows
    refs = selection.get("evidence")
    cited = (isinstance(refs, list) and bool(refs) and all(isinstance(r, str) and r for r in refs)
             and isinstance(selection.get("summary"), str) and bool(selection["summary"].strip()))
    for key in ("runner_supports_candidates", "project_accepts_candidates"):
        if selection.get(key) is False:
            add("gpu_candidates_rejected", "fail", "Runner 或项目明确不接受该候选列表配置。")
    selected = selection.get("selected_type")
    actual = selection.get("actual_type")
    fallback = selection.get("fallback_types")
    for key, value in (("selected_type", selected), ("actual_type", actual)):
        if value is not None and (not isinstance(value, str) or value.strip().upper() not in GPU_TYPES):
            add("gpu_actual_unsupported" if key == "actual_type" else "gpu_selection_unsupported", "fail", key + " 不是允许的 H20/L20。")
        elif isinstance(value, str) and value.strip().upper() not in cards:
            add("gpu_selection_not_candidate", "fail", key + " 不在本题候选列表内。")
    if fallback is not None and (not isinstance(fallback, list)
            or any(not isinstance(v, str) or v.strip().upper() not in GPU_TYPES or v.strip().upper() not in cards for v in fallback)):
        add("gpu_fallback_unsupported", "fail", "仍保留非 H20/L20 或候选之外的回退卡型。")
    if stage == "runtime_package" and not (cited and isinstance(actual, str) and actual.strip().upper() in GPU_TYPES):
        add("gpu_actual_unverified", "manual", "运行阶段须核对实际分配 H20/L20；可选列表或目标型号不能代替实际分配。")
    return rows


def _network(policy, inherited=None):
    """Resolve only supported public/no-network/allowlist values, without guessing."""
    inherited = inherited or ("public", ())
    explicit = "network_mode" in policy or "allowed_hosts" in policy or "allow_internet" in policy
    mode = policy.get("network_mode")
    if mode is None:
        mode = ("no-network" if policy.get("allow_internet") is False else "public"
                if policy.get("allow_internet") is True else inherited[0])
    hosts = policy.get("allowed_hosts", inherited[1] if mode == inherited[0] else [])
    if mode not in ("public", "no-network", "allowlist"):
        return None, explicit, "network_mode 不属于已验证的 public/no-network/allowlist。"
    if hosts is None:
        hosts = []
    if not isinstance(hosts, (list, tuple)) or any(not isinstance(h, str) or not h.strip() for h in hosts):
        return None, explicit, "allowed_hosts 必须是非空字符串列表。"
    if mode == "allowlist" and not hosts:
        return None, explicit, "allowlist 需要明确 allowed_hosts。"
    if mode != "allowlist" and hosts:
        return None, explicit, "allowed_hosts 只在 allowlist 模式有效；不能把无效白名单当约束生效。"
    if "allow_internet" in policy and policy.get("allow_internet") is not None:
        legacy = policy["allow_internet"]
        if not isinstance(legacy, bool) or (legacy is False and mode != "no-network") or (legacy is True and mode == "no-network"):
            return None, explicit, "allow_internet 与 network_mode 矛盾或类型错误。"
    return (mode, tuple(sorted(set(hosts)))), explicit, None


def config_findings(config, review=None, task=None, *, stage=None):
    """Shared provider/GPU findings for full review and format precheck.

    Output codes/status/category are stable integration fields. Source-only
    platform uncertainty is separately pending, never a compatibility claim.
    No submitted code or
    Docker is executed; source_package does not demand an internal image tag.
    """
    review = review if isinstance(review, dict) else {}
    cfg = config if isinstance(config, dict) else {}
    profile = declared_profile(review)
    stage = stage or review.get("delivery_stage", "source_package")
    stage = {"source": "source_package", "runtime": "runtime_package"}.get(stage, stage)
    rows = []
    def add(code, status, message, category="constraint"):
        rows.append({"code": code, "status": status, "message": message, "category": category})
    if stage not in STAGES:
        add("delivery_stage_unknown", "manual", "未知交付阶段，需明确 source_package 或 runtime_package。", "config")
        return rows
    if profile not in PROFILES:
        add("provider_unknown", "platform_pending" if source_stage(stage) else "manual",
            "目标 provider/版本尚未确认：" + str(profile) + "；静态检查不据此认定缺陷，也不套用 MASO/Mido 能力或认证运行兼容。", "platform")
    envs = environments(cfg)
    selections = review.get("gpu_selection", {})
    selections = selections if isinstance(selections, dict) else {}
    for role, env in envs.items():
        # These are task/configuration facts, independent of which platform
        # later runs the package. Unknown targets must not skip them.
        for field, maximum in (("cpus", 64), ("gpus", 8)):
            value = env.get(field)
            minimum = 0 if field == "gpus" else 1
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < minimum):
                add("resource_value_invalid", "fail", role + "." + field + " 必须是有效整数。", "config")
            elif isinstance(value, int) and value > maximum:
                add("resource_count_exceeded", "fail", role + "." + field + " 超过项目上限 " + str(maximum) + "。", "config")
        if is_innerfield(profile):
            rows.extend(gpu_policy(env, selections.get(role), stage=stage, role=role))
        phase = cfg.get("agent" if role == "agent" else "verifier", {})
        phase = phase if isinstance(phase, dict) else {}
        if profile == INNERFIELD:
            for label, policy in (("环境启动", env), ("执行阶段", phase)):
                if "storage_mb" in policy:
                    add("storage_unsupported", "fail", role + label + "声明 storage_mb，旧 MASO 路径尚不支持该存储约束。")
                if (policy.get("network_mode") in ("no-network", "allowlist") or policy.get("allowed_hosts")
                        or policy.get("allow_internet") is False or policy.get("network_access") is False):
                    add("network_constraint_unsupported", "fail", role + label + "声明禁网/白名单，旧 MASO 会 warning/联网降级，不能声称生效。")
        elif profile == MIDO:
            for field in ("cpus", "memory_mb", "storage_mb"):
                if field in env and (isinstance(env[field], bool) or not isinstance(env[field], int) or env[field] <= 0):
                    add("resource_value_invalid", "fail", role + "." + field + " 必须是正整数。", "config")
            if "storage_mb" in phase:
                add("storage_wrong_phase", "fail", role + ".storage_mb 不是执行阶段字段，应置于对应 environment。")
            for field in ("network_access", "blocked_hosts"):
                if field in env or field in phase:
                    add("network_field_unsupported", "fail", role + ": " + field + " 未获当前 Mido/Harbor 路径支持，不能宣称生效。")
            network, _, error = _network(env)
            effective, explicit, phase_error = _network(phase, network)
            if error or phase_error:
                add("network_policy_invalid", "fail", role + ": " + (error or phase_error))
            elif role == "agent" and explicit and network != effective:
                add("agent_network_override_mismatch", "fail", "Mido 真 Agent 预设要求 [agent] 网络与 [environment] 一致，不能在 setup 后切换边界。")
            for field in ("tpu",):
                if field in env:
                    add("mido_field_unsupported", "fail", role + " environment." + field + " 当前不支持。")
            if env.get("os", "linux") != "linux":
                add("os_unsupported", "fail", role + " Mido 只支持 Linux sandbox。")
            blocked = ("mcp_servers", "skills_dir") if role == "agent" else ("mcp_servers", "skills_dir", "healthcheck")
            for field in blocked:
                if field in env:
                    add("mido_field_unsupported", "fail", role + " environment." + field + " 当前预设不支持或 Harbor 不读取。")
            if stage == "runtime_package" and (not isinstance(env.get("docker_image"), str) or not env["docker_image"].strip()):
                add("published_image_required", "fail", role + " Mido 运行阶段只接已发布镜像；Dockerfile 构建由平台先完成。", "image")
            user = phase.get("user")
            if user not in (None, "root", 0, "0"):
                add("runtime_user_unverified", "manual", role + " 指定非 root 用户，须据所用镜像确认用户/UID 存在；能力表不保证任意用户名可用。")
        elif profile == GENERIC and any(field in env or field in phase for field in ("storage_mb", "network_mode", "allowed_hosts", "allow_internet", "tpu")):
            add("generic_capability_unverified", "platform_pending" if source_stage(stage) else "manual",
                role + " 自定义 provider 的存储/网络能力尚未验证；源码静态结果不认证目标平台能力。", "platform")
    if profile == MIDO:
        for field in ("steps", "multi_step_reward_strategy"):
            if field in cfg:
                add("mido_multistep_unsupported", "fail", field + " 在当前 Mido 真 Agent 预设路径尚不支持。")
        artifacts = cfg.get("artifacts", [])
        collects = cfg.get("verifier", {}).get("collect", []) if isinstance(cfg.get("verifier"), dict) else []
        for values in (artifacts, collects):
            if isinstance(values, list) and any(isinstance(v, dict) and v.get("service") not in (None, "main") for v in values):
                add("compose_service_unsupported", "fail", "Mido 每 run 单容器，不支持 artifacts/collect 指向 Compose sidecar。", "compose")
    return rows


def assess(root, task, config, review, resolve_ref):
    profile = declared_profile(review)
    stage = review.get("delivery_stage", "source_package")
    def cited(value, label):
        if not isinstance(value, dict) or not isinstance(value.get("summary"), str) or not value["summary"].strip():
            raise ValueError(f"{label} requires a semantic summary")
        refs = value.get("evidence")
        if not isinstance(refs, list) or not refs:
            raise ValueError(f"{label} requires existing evidence")
        for ref in refs:
            resolve_ref(root, ref)
        return refs
    basis = review.get("deployment_basis")
    refs = []
    resolution = "assessor_target" if profile in PROFILES else "unresolved"
    # Reuse the existing internal evidence object. Neither task filenames,
    # image tags nor a submission's self-description select a platform.
    candidate = basis.get("deployment_profile", basis.get("profile")) if isinstance(basis, dict) else None
    if profile not in PROFILES and isinstance(basis, dict) and (candidate in PROFILES or basis.get("evidence")):
        refs = cited(basis, "deployment_basis")
        observed = set()
        for ref in refs:
            path = resolve_ref(root, ref)
            if path.suffix.lower() != ".json" or path.stat().st_size > 1024 * 1024:
                continue  # Optional inference budget, never a review/material gate.
            try:
                def unique(pairs):
                    result = {}
                    for key, value in pairs:
                        if key in result:
                            raise ValueError("duplicate platform evidence key")
                        result[key] = value
                    return result
                record = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
            except (OSError, ValueError, UnicodeError):
                continue
            if not isinstance(record, dict):
                continue
            values = [record.get("deployment_profile")]
            for container, key in (("context", "provider"), ("platform", "deployment_profile"), ("runner", "deployment_profile")):
                child = record.get(container)
                if isinstance(child, dict):
                    values.append(child.get(key))
            observed.update(value for value in values if isinstance(value, str) and value in PROFILES)
        if candidate in PROFILES and observed and observed != {candidate}:
            raise ValueError("deployment_basis profile conflicts with selected existing platform record")
        if candidate in PROFILES or len(observed) == 1:
            profile = candidate if candidate in PROFILES else next(iter(observed))
            resolution = "existing_evidence"
    elif profile == GENERIC:
        refs = cited(basis, "generic deployment_basis")
    effective_review = {**review, "deployment_profile": profile}
    selections = review.get("gpu_selection", {})
    if not isinstance(selections, dict):
        raise ValueError("gpu_selection must be an object keyed by agent/verifier")
    for role, selection_data in selections.items():
        if role not in ("agent", "verifier"):
            raise ValueError("gpu_selection role must be agent or verifier")
        refs += cited(selection_data, "gpu_selection." + role)
    envs = environments(config)
    source = (task / "task.toml").relative_to(root.resolve()).as_posix() if task else None
    findings = [{**row, "evidence": [source] if source else []} for row in config_findings(config, effective_review, task)]
    def finding(code, status, message, category="config", evidence=None):
        findings.append({"code": code, "status": status, "message": message, "category": category,
                         "evidence": evidence if evidence is not None else [source] if source else []})
    if not isinstance(config, dict):
        finding("config_unavailable", "manual", "有效 task.toml 尚未解析，不能确认目标平台能力。")
    selection = docker_paths.image_selection(task, config)
    agent_compose = bool(task and not envs["agent"].get("docker_image")
                         and not (task / "environment/Dockerfile").is_file()
                         and docker_paths.compose_files(task / "environment"))
    compose_review = review.get("compose_review")
    if compose_review is not None:
        compose_refs = cited(compose_review, "compose_review")
        if (compose_review.get("selection") not in ("unused", "selected", "unverified")
                or not isinstance(compose_review.get("roles"), list) or not compose_review["roles"]
                or any(role not in ("agent", "verifier") for role in compose_review["roles"])):
            raise ValueError("compose_review needs selection and agent/verifier roles")
    for role, directory in (("agent", "environment"), ("verifier", "tests")):
        compose_files = docker_paths.compose_files(task / directory) if task else []
        if compose_files:
            finding("compose_unsupported", "fail", f"{role} 正式目录含 Compose，按项目每 sandbox 单容器交付。", "compose",
                    [p.relative_to(root.resolve()).as_posix() for p in compose_files])
        elif compose_review and role in compose_review["roles"] and compose_review["selection"] == "selected":
            finding("compose_unsupported", "fail", f"{role} 已选用 Compose，与本项目单容器约定冲突。", "compose", compose_refs)
    capability = review.get("capability_review")
    if capability is None:
        pending = source_stage(stage) and profile not in PROFILES
        finding("capability_unreviewed", "platform_pending" if pending else "manual",
                "目标平台约束能力尚未验证；题包静态约束实现仍由QA05按已有源码审阅，不要求专家填写provider。", "constraint", [])
    else:
        evidence = cited(capability, "capability_review")
        state, outcome = capability.get("status"), capability.get("outcome")
        if state not in ("pass", "manual", "fail") or outcome not in ("effective", "not_required", "unverified", "warning_only", "network_fallback"):
            raise ValueError("capability_review needs status and a supported outcome")
        status = "fail" if state == "fail" or outcome in ("warning_only", "network_fallback") else "pass" if state == "pass" and outcome in ("effective", "not_required") else "manual"
        if status == "manual" and source_stage(stage) and profile not in PROFILES:
            status = "platform_pending"
        finding("capability_semantic_review", status, capability["summary"], "constraint", evidence)
    pending = [{**row, "required_for_static_completion": False, "responsibility": "platform"}
               for row in findings if row["status"] == "platform_pending"]
    findings = [row for row in findings if row["status"] != "platform_pending"]
    status = aggregate([f["status"] for f in findings])
    config_status = aggregate([f["status"] for f in findings if f["category"] != "compose"])
    problem_text = "；".join(f["message"] for f in findings if f["status"] != "pass")
    platform_text = "；".join(row["message"] for row in pending)
    return {"profile": profile, "delivery_stage": stage, "status": status, "config_status": config_status,
            "compose_status": aggregate([f["status"] for f in findings if f["category"] == "compose"]),
            "constraint_status": aggregate([f["status"] for f in findings if f["category"] == "constraint"]),
            "gpu_status": aggregate([f["status"] for f in findings if f["category"] == "gpu"]),
            "innerfield_compliant": is_innerfield(profile) and status == "pass",
            "runtime_verified": False, "capability_source": MIDO_SOURCE if profile == MIDO else None,
            "platform_status": "unverified", "platform_findings": pending,
            "provider_resolution": {"source": resolution, "profile": profile, "evidence": list(dict.fromkeys(refs))},
            "effective_environments": envs, "image_selection": selection, "agent_compose_selected": agent_compose,
            "config_source": source, "compose_review": compose_review, "basis": basis,
            "gpu_selection": selections, "capability_review": capability, "findings": findings,
            "summary": (problem_text or "已完成已交配置的静态核对；这不是实机运行、隔离或GPU到卡证明。") + ("；平台待验证：" + platform_text if platform_text else ""),
            "evidence": list(dict.fromkeys(refs + [r for f in findings + pending for r in f["evidence"]])),
            "remediation": "按实际 provider/版本、阶段修正不支持字段及冲突；候选与实际 GPU 分开核对。",
            "acceptance_evidence": "实际配置、镜像、调用和现有日志相互一致；warning/fallback 不能作为约束生效证据。"}
