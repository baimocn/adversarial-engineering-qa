"""QA15 evidence collection and conservative resource checks; no task execution."""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
import deployment_review

LIMITS = {"score_seconds": 7200, "gpu_count": 8, "gpu_types": ["H20", "L20"], "cpu_cores": 64}
MULTI_SEED_SCORE_SECONDS = 28800
SCORE_TIME_POLICY = "单seed评分≤7200秒；同一候选完成全部协议seed的累计评分≤28800秒；Baseline/Reference分别计算，不合并研究轨迹、重试或不同候选。"
FIELDS = ("score_seconds", "gpu_count", "gpu_type", "cpu_cores", "peak_memory_mb", "peak_storage_mb")


def score_time_budget(row):
    """Optional reviewer metadata identifies a complete multi-seed score, not a new author artifact."""
    seeds = row.get("evaluation_seeds")
    if seeds is None:
        return {"seed_count": 1, "scope": "single_seed", "limit_seconds": LIMITS["score_seconds"]}
    if (not isinstance(seeds, list) or not seeds
            or any(isinstance(s, bool) or not isinstance(s, (str, int)) or not str(s).strip() for s in seeds)
            or len({str(s) for s in seeds}) != len(seeds)):
        raise ValueError("evaluation_seeds must list distinct actual protocol seeds; reviewer metadata only")
    source = Path(row.get("source_path") or "")
    if len(seeds) > 1 and len(source.parts) >= 3 and source.parts[-3] in ("baseline_runs", "reference_runs") and source.name == "result.json":
        raise ValueError("a per-seed formal result cannot be relabeled as a complete multi-seed total")
    return {"seed_count": len(seeds), "scope": "multi_seed_total" if len(seeds) > 1 else "single_seed",
            "limit_seconds": MULTI_SEED_SCORE_SECONDS if len(seeds) > 1 else LIMITS["score_seconds"]}


def formal_seed_totals(current, rows):
    """Sum complete per-role seed records once; never sum Baseline and Reference or retries."""
    expected = {}
    for ref in current.get("formal_run_paths", []):
        path = Path(ref)
        if len(path.parts) >= 3 and path.parts[-3] in ("baseline_runs", "reference_runs"):
            expected.setdefault(path.parent.parent.as_posix(), set()).add(ref)
    seeds = {o["path"]: o.get("seed") for o in current.get("observations", []) if isinstance(o, dict) and o.get("path")}
    totals = []
    for group, paths in expected.items():
        grouped = {}
        for row in rows:
            if row.get("scope") == "score" and row.get("source_path") in paths:
                grouped.setdefault(row["source_path"], []).append(row)
        selected_paths = sorted(grouped)
        # Unknown duplicate observations cannot hide a known duration for the same result.
        selected = [next((row for row in grouped[ref] if row.get("score_seconds") is not None), grouped[ref][0])
                    for ref in selected_paths]
        actual_seeds = [seeds.get(ref) for ref in selected_paths]
        if (len(paths) < 2 or set(selected_paths) != paths
                or any(r.get("score_seconds") is None for r in selected)
                or any(isinstance(s, bool) or not isinstance(s, (str, int)) or not str(s).strip() for s in actual_seeds)
                or len({str(s) for s in actual_seeds}) != len(actual_seeds)):
            continue
        known = {ref: {r["score_seconds"] for r in records if r.get("score_seconds") is not None}
                 for ref, records in grouped.items()}
        conflicts = [ref for ref, values in known.items() if len(values) > 1]
        # Even conflicting duplicates cannot erase an overrun proved by every known alternative.
        lower_bound = sum(min(known[ref]) for ref in selected_paths)
        totals.append({"role_runs_path": group, "evaluation_seeds": actual_seeds,
                       "score_seconds": None if conflicts else sum(r["score_seconds"] for r in selected),
                       "score_seconds_lower_bound": lower_bound,
                       "timing_conflicts": conflicts,
                       "evidence": list(dict.fromkeys(ref for r in selected for ref in r["evidence"])),
                       "source_paths": sorted(paths)})
    return totals


def collect(root, files, config=None, trajectory_paths=None):
    observations, errors, formal, agent_scores = [], [], [], []
    for relative in files:
        path = Path(relative)
        is_formal = path.name == "result.json" and len(path.parts) >= 3 and path.parts[-3] in ("baseline_runs", "reference_runs")
        is_trajectory = relative in (trajectory_paths or []) or ("expert_evidence" in path.parts and path.name.startswith("trajectory") and path.suffix == ".json")
        if not is_formal and not is_trajectory and path.name not in ("run_summary.json", "run.json"):
            continue
        if is_formal:
            formal.append(relative)
        try:
            target = root / relative
            if target.stat().st_size > 4 * 1024 * 1024:
                raise ValueError("resource JSON exceeds 4 MiB; inspect raw log separately")
            data = json.loads(target.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("resource JSON must be an object")
            if is_trajectory:
                rounds = data.get("rounds", [])
                if isinstance(rounds, list):
                    for row in rounds:
                        if isinstance(row, dict) and str(row.get("status", "")).lower() in ("ok", "success", "pass", "complete", "completed"):
                            if isinstance(row.get("score"), (int, float)) and not isinstance(row["score"], bool) and math.isfinite(row["score"]):
                                agent_scores.append({"source_path": relative, "round": row.get("round")})
            observations.append({"path": relative, "role": data.get("role"), "seed": data.get("seed"),
                                 "execution": data.get("execution"), "protocol": data.get("protocol")})
        except (OSError, ValueError, UnicodeError) as exc:
            errors.append({"path": relative, "error": str(exc)})
    cfg = config if isinstance(config, dict) else {}
    verifier = cfg.get("verifier", {})
    env = cfg.get("environment", {})
    venv = verifier.get("environment", env) if isinstance(verifier, dict) else env
    return {"status": "manual", "summary": "QA15 已启用；等待结合日志、轨迹和B/R实现估算完整单轮耗时、GPU数量及CPU核数。",
            "limits": {**LIMITS, "multi_seed_score_seconds": MULTI_SEED_SCORE_SECONDS}, "score_time_policy": SCORE_TIME_POLICY,
            "formal_run_paths": sorted(formal), "agent_scores": agent_scores, "observations": observations,
            "parse_errors": errors, "declared_environment": env, "declared_verifier_environment": venv,
            "declared_verifier_timeout": verifier.get("timeout_sec") if isinstance(verifier, dict) else None,
            "evidence": [], "runs": [], "enforcement_review": None}


def hardware_review(current, review, estimate, root, validate_evidence, deployment=None):
    """Reviewer metadata connects task intent and existing hardware evidence."""
    data = review.get("hardware_review", {})
    if not isinstance(data, dict):
        raise ValueError("hardware_review must be an object")
    refs = validate_evidence(root, data.get("evidence", []), "hardware_review")
    kind = data.get("task_type", "unknown")
    comparison = data.get("score_comparability", "unverified")
    if kind not in ("cpu", "gpu", "unknown") or comparison not in ("same_hardware", "revalidated", "unverified", "reused_without_validation"):
        raise ValueError("hardware_review has unsupported task_type or score_comparability")
    affected = data.get("affected_formal_runs", [])
    if not isinstance(affected, list):
        raise ValueError("affected_formal_runs must be an array")
    for ref in affected:
        parts = Path(ref).parts
        if len(parts) < 3 or parts[-3] not in ("baseline_runs", "reference_runs") or parts[-1] != "result.json":
            raise ValueError("affected_formal_runs must name formal B/R result.json files")
    refs += validate_evidence(root, affected, "hardware affected_formal_runs")
    formal_effect = data.get("affects_formal_scores", bool(affected))
    if not isinstance(formal_effect, bool):
        raise ValueError("affects_formal_scores must be boolean")
    if affected and not formal_effect:
        raise ValueError("affected formal runs cannot be declared unaffected")
    gaps, problems, platform_pending = [], [], []
    profile = (deployment or {}).get("profile", deployment_review.UNKNOWN)
    stage = (deployment or {}).get("delivery_stage", "source_package")
    unknown_source_target = deployment_review.source_stage(stage) and profile not in deployment_review.PROFILES
    if kind == "unknown":
        gaps.append("CPU/GPU任务性质尚未据实判定")
    if not refs or not isinstance(data.get("summary"), str) or not data["summary"].strip():
        gaps.append("任务性质与换卡成绩可比性的现有依据")
    if comparison == "unverified":
        if unknown_source_target and not formal_effect:
            platform_pending.append("验收目标硬件未指定；现有材料不认证换卡实测或目标平台成绩，未宣称受影响的正式分数不因此失败。")
        else:
            gaps.append("当前成绩的硬件归属/换卡影响尚未确认")
    if comparison == "reused_without_validation":
        problems.append("旧卡成绩未经复核直接作为新卡成绩，不能据此声称目标硬件结果")
    envs = (deployment or {}).get("effective_environments", {
        "agent": current.get("declared_environment", {}), "verifier": current.get("declared_verifier_environment", {})})
    actual = [(name, env.get("gpus", 0)) for name, env in envs.items() if isinstance(env, dict)]
    if kind == "cpu":
        if estimate.get("gpu_count", 0) not in (None, 0) or any(isinstance(n, (int, float)) and not isinstance(n, bool) and n > 0 for _, n in actual):
            problems.append("CPU题不得增加GPU；资源估算与Solver/Verifier实际申请均须为0")
    elif kind == "gpu":
        if estimate.get("gpu_count") == 0:
            gaps.append("GPU题的资源估算为0GPU，需核对与实际评分硬件的一致性")
        if not any(isinstance(n, (int, float)) and not isinstance(n, bool) and n > 0 for _, n in actual):
            gaps.append("GPU题的实际Solver/Verifier GPU申请尚未对应")
        if not estimate.get("gpu_type"):
            gaps.append("GPU评分硬件的估算型号尚未据实说明")
    if deployment_review.is_innerfield(profile):
        for role, env in envs.items():
            if not isinstance(env, dict):
                continue
            count = env.get("gpus", 0)
            types = env.get("gpu_types")
            if isinstance(count, (int, float)) and not isinstance(count, bool) and count > 0:
                selections = (deployment or {}).get("gpu_selection", {})
                selections = selections if isinstance(selections, dict) else {}
                for row in deployment_review.gpu_policy(env, selections.get(role), stage=stage, role=role):
                    if row["status"] == "fail":
                        problems.append(row["message"])
                    elif row["status"] == "manual":
                        gaps.append(row["message"])
    status = "fail" if problems else "manual" if gaps else "pass"
    score_status = "fail" if comparison == "reused_without_validation" else "manual" if comparison == "unverified" or not refs or not data.get("summary") else "pass"
    return {**data, "task_type": kind, "score_comparability": comparison, "status": status,
            "score_status": score_status if formal_effect else "pass", "affects_formal_scores": formal_effect,
            "affected_formal_runs": affected, "problems": problems, "gaps": gaps,
            "platform_pending": platform_pending, "platform_status": "unverified" if platform_pending else "not_executed",
            "evidence": list(dict.fromkeys(refs + ([(deployment or {})["config_source"]] if (deployment or {}).get("config_source") else []))),
            "summary": "；".join(problems + gaps + platform_pending) or data.get("summary", ""),
            "remediation": "按任务性质核对当前Solver/Verifier资源。换卡只复核受影响的成绩或耗时，并引用已有配置、说明或运行记录；旧测量保留原硬件标签。",
            "acceptance_evidence": "CPU题不申请GPU；GPU题的实际目标卡型为H20/L20；受影响正式分数有目标硬件对应依据，不能只改型号沿用旧分。"}


def apply_review(current, review, root, validate_evidence, deployment=None):
    """Accept a supported whole-task estimate; detailed allocation proofs optional."""
    if review is None:
        return current
    if not isinstance(review, dict):
        raise ValueError("resource_review must be an object")
    refs = validate_evidence(root, review.get("evidence", []), "resource_review")
    rows = review.get("runs", [])
    if not isinstance(rows, list):
        raise ValueError("resource_review.runs must be an array")
    problems, checked = [], []
    def numbers(row, label):
        for field in FIELDS:
            value = row.get(field)
            if field == "gpu_type" or value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
                raise ValueError(f"{label}.{field}: require a finite nonnegative value")
            if field in ("gpu_count", "cpu_cores") and int(value) != value:
                raise ValueError(f"{label}.{field}: require an integer")
    for index, row in enumerate(rows):
        label = f"resource_review.runs[{index}]"
        if not isinstance(row, dict) or not row.get("run_id"):
            raise ValueError(f"{label}: run_id is required")
        evidence = validate_evidence(root, row.get("evidence", []), label, required=True)
        if row.get("source_path"):
            validate_evidence(root, [row["source_path"]], label + ".source_path", required=True)
        if row.get("scope") not in ("score", "training", "verifier", "setup", "agent_run"):
            raise ValueError(f"{label}: specify score/training/verifier/setup/agent_run scope")
        rounds = row.get("covered_rounds", [])
        if not isinstance(rounds, list) or any(isinstance(n, bool) or not isinstance(n, int) or n < 1 for n in rounds):
            raise ValueError(f"{label}.covered_rounds: require positive round numbers")
        numbers(row, label)
        budget = score_time_budget(row) if row["scope"] == "score" else None
        if budget and row.get("score_seconds") is not None and row["score_seconds"] > budget["limit_seconds"]:
            problems.append(f"{row['run_id']} {'多seed累计评分' if budget['seed_count'] > 1 else '单seed评分'} {row['score_seconds']}s 超过{budget['limit_seconds']}s")
        checked.append({**row, "evidence": evidence, **({"score_time_budget": budget} if budget else {})})
    totals = formal_seed_totals(current, checked)
    for total in totals:
        elapsed = total["score_seconds"] if total["score_seconds"] is not None else total["score_seconds_lower_bound"]
        if elapsed > MULTI_SEED_SCORE_SECONDS:
            qualifier = "累计评分" if total["score_seconds"] is not None else "累计评分已知下界"
            problems.append(f"{total['role_runs_path']} 全部{len(total['evaluation_seeds'])}个seed{qualifier} {elapsed}s 超过{MULTI_SEED_SCORE_SECONDS}s")
    estimate = review.get("estimate")
    if estimate is not None and not isinstance(estimate, dict):
        raise ValueError("resource_review.estimate must be an object")
    # Existing full score records also work; the new estimate is only needed
    # when the reviewer combines logs, source complexity and configuration.
    if estimate is None:
        scores = [row for row in rows if row["scope"] == "score"]
        formal = set(current.get("formal_run_paths", []))
        if formal:
            scores = [row for row in scores if row.get("source_path") in formal or score_time_budget(row)["seed_count"] > 1]
        if scores:
            # Complete multi-seed role totals are alternatives, never B+R combined.
            timed = scores + [t for t in totals if t["score_seconds"] is not None]
            representative = max(timed, key=lambda r: r.get("score_seconds") if r.get("score_seconds") is not None else -1)
            if representative in totals:
                # Carry non-time metadata from this role's actual score record, not a different candidate/role.
                origin = next(row for row in scores if row.get("source_path") in representative["source_paths"])
                estimate = {**origin, **representative}
                estimate.pop("source_path", None)  # A total is not a relabelled per-seed result.
            else:
                estimate = dict(representative)
            for field in ("score_seconds", "gpu_count", "cpu_cores"):
                values = [row.get(field) for row in scores]
                estimate[field] = max(values) if all(v is not None for v in values) else None
            estimate["score_seconds"] = representative.get("score_seconds") if all(r.get("score_seconds") is not None for r in scores) else None
            estimate["basis"] = ("已有同一角色已交正式seed记录的累计资源观测；协议完整性另按G03核对，Baseline/Reference分别计算。" if representative in totals else
                                 "已有单seed或完整评分记录的代表性资源观测；未生成多seed累计值时，不代表已验证整轮8小时上限。")
            estimate["time_accounting"] = representative.get("time_accounting") or ("同一角色已交正式seed的训练/重载/评分累计；协议完整性另按G03核对。" if representative in totals else None)
            estimate["evidence"] = list(dict.fromkeys(ref for row in scores for ref in row["evidence"]))
    estimate = estimate or {}
    numbers(estimate, "resource_review.estimate")
    estimate_budget = score_time_budget(estimate)
    er = validate_evidence(root, estimate.get("evidence", []), "resource estimate")
    missing = []
    # A supported target estimate may differ from old calibration measurements,
    # but already supplied score records cannot silently contradict it. This is
    # a reviewer explanation over existing evidence, not a new required artifact.
    conflicts = []
    for row in checked:
        if row["scope"] != "score":
            continue
        for field in ("score_seconds", "gpu_count", "cpu_cores"):
            observed, proposed = row.get(field), estimate.get(field)
            if field == "score_seconds" and score_time_budget(row)["seed_count"] != estimate_budget["seed_count"]:
                continue  # Per-seed duration and a full protocol total are different units.
            if observed is not None and proposed is not None and observed > proposed:
                conflicts.append(f"{row['run_id']}.{field} 已给观测为{observed}，高于目标估算{proposed}")
        hardware_data = review.get("hardware_review", {})
        same_hardware = isinstance(hardware_data, dict) and hardware_data.get("score_comparability") == "same_hardware"
        if same_hardware and row.get("gpu_count") and estimate.get("gpu_count") and row.get("gpu_type") and estimate.get("gpu_type"):
            observed_type = str(row["gpu_type"]).strip().upper()
            proposed_type = str(estimate["gpu_type"]).strip().upper()
            if observed_type != proposed_type:
                conflicts.append(f"{row['run_id']}.gpu_type={row['gpu_type']} 与估算{estimate['gpu_type']}不同，但声明same_hardware")
    for total in totals:
        if total["score_seconds"] is not None and len(total["evaluation_seeds"]) == estimate_budget["seed_count"] and estimate.get("score_seconds") is not None and total["score_seconds"] > estimate["score_seconds"]:
            conflicts.append(f"{total['role_runs_path']} 多seed累计观测{total['score_seconds']}，高于目标累计估算{estimate['score_seconds']}")
        elif total.get("timing_conflicts"):
            conflicts.append(f"{total['role_runs_path']} 同一seed结果有不同耗时记录：" + "、".join(total["timing_conflicts"]))
    reconciliation = estimate.get("observation_reconciliation")
    reconciliation_refs = []
    if reconciliation is not None:
        if not isinstance(reconciliation, dict) or not isinstance(reconciliation.get("summary"), str) or not reconciliation["summary"].strip():
            raise ValueError("resource estimate observation_reconciliation requires a concrete summary")
        reconciliation_refs = validate_evidence(root, reconciliation.get("evidence", []), "resource observation reconciliation", required=True)
    if conflicts and reconciliation is None:
        missing.append("已有完整评分观测与估算存在未解释差异：" + "；".join(conflicts)
                       + "；请引用已有材料说明历史校准、目标配置或方法变化")
    for field, label in (("score_seconds", "完整一轮评分耗时"), ("gpu_count", "GPU数量"), ("cpu_cores", "CPU核数")):
        value = estimate.get(field)
        if value is None:
            missing.append(label)
        elif value > (estimate_budget["limit_seconds"] if field == "score_seconds" else LIMITS[field]):
            maximum = estimate_budget["limit_seconds"] if field == "score_seconds" else LIMITS[field]
            problems.append(f"估算{label} {value} 超过上限{maximum}")
    if not estimate.get("time_accounting"):
        missing.append("计时包含的阶段")
    if not estimate.get("basis") or not er:
        missing.append("可引用的日志/实现估算依据")
    gpu_type = estimate.get("gpu_type")
    if deployment_review.is_innerfield((deployment or {}).get("profile", deployment_review.UNKNOWN)) and estimate.get("gpu_count") and gpu_type and (not re.search(r"\b(?:H20|L20)\b", str(gpu_type), re.I)
            or any(model.upper() not in LIMITS["gpu_types"] for model in
                   re.findall(r"\b(?:[A-Z]{1,4}\d{2,4}[A-Z]*|RTX\s*\d{3,4})\b", str(gpu_type), re.I))):
        problems.append(f"估算依赖非允许GPU {gpu_type}；需说明H20/L20可行性")
    for name in ("declared_environment", "declared_verifier_environment"):
        env = current.get(name, {})
        if isinstance(env, dict):
            for key, maximum in (("cpus", 64), ("gpus", 8)):
                value = env.get(key)
                if isinstance(value, (int, float)) and not isinstance(value, bool) and value > maximum:
                    problems.append(f"{name}.{key} 请求{value} 超过{maximum}")
    hardware = hardware_review(current, review, estimate, root, validate_evidence, deployment)
    problems.extend(hardware["problems"])
    missing.extend(hardware["gaps"])
    conclusion = review.get("status", "manual")
    if conclusion not in ("pass", "manual", "fail"):
        raise ValueError("QA15 cannot be skipped")
    if conclusion == "fail" and (not refs or not review.get("summary")):
        raise ValueError("resource_review fail needs evidence and explanation")
    status = "fail" if problems or conclusion == "fail" else "manual" if missing or conclusion != "pass" else "pass"
    summary = ("；".join(problems) if problems else "缺少：" + "、".join(missing) if missing else
               review.get("summary") or f"估算完整一轮{estimate['score_seconds']}秒、{estimate['gpu_count']}GPU、{estimate['cpu_cores']}CPU，符合资源上限。")
    covered = {r.get("source_path") for r in rows if r.get("scope") == "score"}
    covered_scores = {(r.get("source_path"), n) for r in rows for n in r.get("covered_rounds", [])}
    # Coverage and deployment details are observations, not new mandatory gates.
    return {**current, "status": status, "summary": summary, "estimate": estimate, "runs": checked,
            "score_time_policy": SCORE_TIME_POLICY, "estimate_score_time_budget": estimate_budget, "formal_seed_totals": totals,
            "observation_conflicts": conflicts, "observation_reconciliation": reconciliation,
            "hardware_review": hardware,
            "platform_pending": hardware.get("platform_pending", []),
            "enforcement_review": review.get("enforcement_review"),
            "missing_run_paths": sorted(set(current.get("formal_run_paths", [])) - covered),
            "missing_agent_scores": [r for r in current.get("agent_scores", []) if (r["source_path"], r["round"]) not in covered_scores],
            "problems": problems, "gaps": missing,
            "evidence": list(dict.fromkeys(refs + er + reconciliation_refs + hardware["evidence"] + [ref for row in rows for ref in row["evidence"]])),
            "feasibility_summary": review.get("feasibility_summary", estimate.get("basis", "")),
            "remediation": "" if status == "pass" else review.get("remediation") or
                (hardware["remediation"] if hardware["status"] != "pass" else
                 "降低上述超限资源需求，或说明并验证目标硬件上的可行配置。" if problems else
                 "在专家说明中补充" + "、".join(missing or ["资源估算结论"]) + "；可引用现有B/R日志、轨迹和实现，无需逐轮补配额或cgroup证明。确实无法推断时补一轮代表性运行摘要。"),
            "acceptance_evidence": "" if status == "pass" else review.get("acceptance_evidence") or
                (hardware["acceptance_evidence"] if hardware["status"] != "pass" else
                 "一份有来源的完整单轮资源估算：单seed≤7200秒，多seed整轮累计≤28800秒；GPU≤8张、CPU≤64核；内场GPU仅H20/L20，标明实测与推断及包含的运行阶段。")}
