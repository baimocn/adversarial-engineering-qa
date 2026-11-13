"""Harbor evidence inventory and semantic-review contract, never a task runner.

This module does not import Harbor or package code, build images, or run scripts.
Structural observations are not a substitute for version-specific schema review.
"""
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re

import docker_paths
import evidence_refs
import task_fingerprint
import deployment_review

try:
    import tomllib
except ImportError:
    tomllib = None

LIMIT = 4 * 1024 * 1024
RULESET = "harbor-compatibility-2026-11-04-unified"
INTERNAL_SOURCE = "https://bytedance.larkoffice.com/wiki/A7FUwJBALici6Gku3rWc4EsinLf"
OFFICIAL_SOURCE = "https://docs.harborframework.com/core-concepts/tasks/separate-verifier"
H_IDS = [f"H{i:02d}" for i in range(1, 7)]
H_TITLES = ["任务目录", "版本与配置", "环境与运行路径", "测试入口与 reward", "Job/Trial 调用配置", "NOP 自检记录"]


def bounded_text(path):
    if path.stat().st_size > LIMIT:
        raise ValueError("file exceeds the 4 MiB inspection limit")
    return path.read_text(encoding="utf-8")


def collect(root, files):
    cfg = None
    configs = [p for p in files if Path(p).name == "task.toml" and ".git" not in Path(p).parts]
    configs = sorted(configs, key=lambda p: (len(Path(p).parts), p))
    selected = None
    if configs:
        depth = len(Path(configs[0]).parts)
        nearest = [p for p in configs if len(Path(p).parts) == depth]
        if len(nearest) == 1:
            selected = Path(nearest[0]).parent.as_posix()
    observations = {"task_candidates": [Path(p).parent.as_posix() for p in configs],
                    "task_root": selected, "toml_parser": "tomllib" if tomllib else "unavailable",
                    "config_sections": [], "schema_version": None, "verifier_environment_mode": None,
                    "parse_error": None}
    if selected is not None:
        try:
            raw = bounded_text(root / selected / "task.toml")
            if tomllib:
                cfg = tomllib.loads(raw)
                observations["config_sections"] = list(cfg)
                observations["schema_version"] = cfg.get("schema_version", cfg.get("version"))
                verifier = cfg.get("verifier")
                observations["verifier_environment_mode"] = verifier.get("environment_mode") if isinstance(verifier, dict) else None
            else:
                observations["config_sections"] = re.findall(r"(?m)^\[([^\[\]\n]+)\]", raw)
        except (OSError, ValueError, UnicodeError) as exc:
            observations["parse_error"] = str(exc)
    observations["job_configs"] = [p for p in files if Path(p).name in ("job.yaml", "job.yml", "trial.yaml", "trial.yml")]
    observations["trial_results"] = [p for p in files if Path(p).name == "result.json"]
    return {"ruleset": RULESET, "sources": [INTERNAL_SOURCE, OFFICIAL_SOURCE],
            "target_version": None, "provider": None, "observations": observations,
            "path_contract": docker_paths.inspect(root, selected, cfg, require_separate=True),
            "checks": [], "static_status": "manual", "runtime_status": "not_reviewed"}


def resolve_ref(root, ref):
    return evidence_refs.resolve_ref(root, ref)


def numeric_reward(value):
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def read_reward(path):
    """Read the same finite numeric reward map for current and legacy records.

    Non-score metadata may accompany the metrics. An explicit ``reward`` key
    still owns the main score and cannot be hidden by another numeric field.
    JSON is strict at every stage: duplicate keys and nonfinite numbers cannot
    become valid merely because a record is historical.
    """
    raw = bounded_text(path)
    if path.name == "reward.txt":
        try:
            value = float(raw.strip())
        except ValueError as exc:
            raise ValueError("reward.txt must contain a single numeric value") from exc
        reward = {"reward": value}
    else:
        def reject_constant(value):
            raise ValueError("non-finite JSON constant: " + value)
        def unique(pairs):
            result = {}
            for name, value in pairs:
                if name in result:
                    raise ValueError("duplicate JSON key: " + name)
                result[name] = value
            return result
        def finite_number(raw_value, converter):
            value = converter(raw_value)
            if not numeric_reward(value):
                raise ValueError("non-finite JSON number: " + raw_value)
            return value
        reward = json.loads(raw, parse_constant=reject_constant, object_pairs_hook=unique,
                            parse_float=lambda value: finite_number(value, float),
                            parse_int=lambda value: finite_number(value, int))
    if not isinstance(reward, dict) or not reward:
        raise ValueError("reward must be a nonempty numeric map with finite values, not status strings/bools")
    if "reward" in reward and not numeric_reward(reward["reward"]):
        raise ValueError("main reward is not a finite numeric value")
    metrics = {key: value for key, value in reward.items() if numeric_reward(value)}
    if not metrics:
        raise ValueError("reward must contain finite numeric metrics, not status strings/bools")
    return metrics


def current_reward_contract(output_dir=None, *, output_paths=None, stage="runtime", main_score_key=None):
    """Check one explicitly selected current scoring invocation, never all history.

    output_dir contains the files from that invocation, or output_paths explicitly
    names those files. Both supported reward filenames may coexist; JSON takes
    precedence under the existing reader contract at every stage.
    main_score_key is an existing adapter's resolved key, not a new author field.
    """
    stage = {"source_package": "source", "runtime_package": "runtime"}.get(stage, stage)
    rows = []
    def add(code, status, message, paths=()):
        rows.append({"code": code, "status": status, "message": message,
                     "evidence": [str(path) for path in paths]})
    if stage not in ("source", "runtime", "history"):
        add("reward_scope_unknown", "manual", "需要明确 source/runtime/history，不能把历史双文件当当前交付。")
        return {"status": "manual", "findings": rows, "scope": stage,
                "selected_file": None, "main_score": None, "main_score_key": None}
    if output_dir is not None and output_paths is not None:
        raise ValueError("select output_dir or explicit output_paths, not both")
    if output_dir is not None:
        directory = Path(output_dir)
        paths = [directory / name for name in ("reward.txt", "reward.json") if (directory / name).is_file()]
    elif output_paths is not None:
        paths = [Path(path) for path in output_paths if Path(path).name in ("reward.txt", "reward.json")]
        paths = list(dict.fromkeys(paths))
    else:
        paths = []
    names = {p.name for p in paths}
    selected = next((p for p in paths if p.name == "reward.json"), paths[0] if paths else None)
    key, score = None, None
    if not paths:
        add("reward_output_unverified" if stage == "source" else "reward_output_missing",
            "manual" if stage == "source" else "fail", "尚未确认当前正式 reward 输出。")
    if selected is not None and stage != "source":
        try:
            if selected.is_symlink() or not selected.is_file():
                raise ValueError("selected reward is not a regular file")
            values = read_reward(selected)
            if not isinstance(values, dict) or not values:
                raise ValueError("reward JSON must be an object")
            if main_score_key is not None:
                if not isinstance(main_score_key, str) or not main_score_key:
                    raise ValueError("main_score_key must be a nonempty existing adapter key")
                key = main_score_key
            elif "reward" in values:
                key = "reward"
            else:
                numbers = [name for name, value in values.items() if numeric_reward(value)]
                key = numbers[0] if len(numbers) == 1 else None
            if key is None:
                add("main_reward_unresolved", "manual", "多个指标未明确主分；核对平台实际读取/适配链，不能把任意数值都当正式 reward。", [selected])
            elif key not in values or not numeric_reward(values[key]):
                raise ValueError("main reward is missing or not a finite numeric value")
            else:
                score = values[key]
        except (OSError, ValueError, UnicodeError) as exc:
            add("reward_output_invalid", "fail", "当前选定 reward 无法读取：" + str(exc), [selected])
    if stage == "source" and selected is not None:
        add("reward_runtime_pending", "manual", "当前源码已声明 reward 输出；实际输出及主分读取由运行阶段核对。", paths)
    return {"status": aggregate(rows), "findings": rows, "scope": stage,
            "selected_file": str(selected) if selected else None, "main_score": score,
            "main_score_key": key, "output_names": sorted(names),
            "historical_dual_file_compatible": stage == "history" and len(paths) > 1}


def trial_task_identity(root, task_root, config, result, binding=None):
    """Names locate a task; cited human review links its version. Never authenticates logs."""
    if task_root is None:
        return {"status": "manual", "basis": "task_root_unknown"}
    task = config.get("task") if isinstance(config.get("task"), dict) else {}
    cfg = {}
    if tomllib:
        cfg = tomllib.loads(bounded_text(task_root / "task.toml"))
    metadata = cfg.get("metadata") if isinstance(cfg.get("metadata"), dict) else {}
    names = {task_root.name}
    for name in (cfg.get("name"), metadata.get("name")):
        if isinstance(name, str) and name.strip():
            names.add(name)
    identities = []
    for value in (task.get("name"), result.get("task_name")):
        if isinstance(value, str) and value.strip():
            identities.append(value.strip())
    raw_path = task.get("path")
    if isinstance(raw_path, str) and raw_path.strip() and raw_path not in (".", "/"):
        identities.append(PurePosixPath(raw_path.replace("\\", "/")).name)
    mismatches = [name for name in identities if name not in names]
    digest = hashlib.sha256((task_root / "task.toml").read_bytes()).hexdigest()
    for value in (task.get("task_toml_sha256"), result.get("task_toml_sha256")):
        if value is not None and value != digest:
            raise ValueError("Harbor Trial task.toml hash disagrees with the inspected task")
    if binding is None:
        if mismatches:
            raise ValueError("Harbor Trial identifies a different task; a reviewed task mapping is required")
        return {"status": "manual", "basis": "name_only" if identities else "identity_missing"}
    if not isinstance(binding, dict) or not isinstance(binding.get("summary"), str) or not binding["summary"].strip():
        raise ValueError("trial_task_binding requires a semantic version-mapping summary")
    binding_refs = binding.get("evidence")
    if not isinstance(binding_refs, list) or not binding_refs:
        raise ValueError("trial_task_binding requires real package evidence")
    paths = [resolve_ref(root, ref) for ref in binding_refs]
    for path in paths:
        if not bounded_text(path).strip():
            raise ValueError("trial_task_binding evidence cannot be empty")
    if mismatches:
        # Renaming must be explicit in the cited mapping, not inferred from arbitrary logs.
        # JSON/text provenance records are reviewed by the human; this only prevents a
        # weak reference to an unrelated file from hiding contradictory task names.
        mapping_text = "\n".join(bounded_text(path) for path in paths
                                  if path.name not in ("config.json", "result.json", "task.toml", "trial.log", "test-stdout.txt"))
        if not mapping_text or not all(name in mapping_text for name in mismatches) or not any(name in mapping_text for name in names):
            raise ValueError("different-task evidence needs an explicit cited mapping of old and current task names")
    return {"status": "pass", "basis": "reviewed_evidence", "evidence": binding_refs,
            "summary": binding["summary"], "authenticity_verified": False}


def validate_trial_evidence(root, refs, task_root=None, binding=None):
    """Prefer a supplied NOP Trial, with separate identity/version review."""
    paths = [resolve_ref(root, ref) for ref in refs]
    results = [p for p in paths if p.name == "result.json"]
    nop_results = []
    for result_path in results:
        # Probe both same-Trial headers so inconsistent identities or a malformed
        # NOP file still reach the strict checks below. Supplemental candidates
        # must not determine H06 merely because their references appear first.
        for path, field in ((result_path.parent / "config.json", "agent"),
                            (result_path, "agent_info")):
            if path not in paths:
                continue
            try:
                document = json.loads(bounded_text(path))
            except (OSError, ValueError, UnicodeError):
                continue  # Selection only; selected Trial files are read strictly below.
            agent = document.get(field) if isinstance(document, dict) else None
            if isinstance(agent, dict) and agent.get("name") == "nop":
                nop_results.append(result_path)
                break
    for result_path in nop_results or results:
        trial = result_path.parent
        config = trial / "config.json"
        json_reward = trial / "verifier" / "reward.json"
        text_reward = trial / "verifier" / "reward.txt"
        reward_path = json_reward if json_reward.is_file() else text_reward
        logs = [p for p in paths if p in (trial / "trial.log", trial / "verifier" / "test-stdout.txt")]
        if config not in paths or reward_path not in paths or not logs:
            continue
        result = json.loads(bounded_text(result_path))
        config_value = json.loads(bounded_text(config))
        if not isinstance(config_value, dict) or not config_value or not isinstance(result, dict):
            raise ValueError("Harbor trial config/result must be nonempty objects")
        agent_config = config_value.get("agent")
        agent_info = result.get("agent_info")
        if not isinstance(agent_config, dict) or not isinstance(agent_config.get("name"), str) or not agent_config["name"].strip():
            raise ValueError("H06 requires config.json agent.name")
        if not isinstance(agent_info, dict) or agent_info.get("name") != agent_config["name"]:
            raise ValueError("H06 requires consistent config/result Agent names")
        if result.get("verifier_environment_mode") != "separate":
            raise ValueError("H06 requires result.json verifier_environment_mode = separate")
        solver_id, verifier_id = result.get("agent_sandbox_id"), result.get("verifier_sandbox_id")
        if solver_id and verifier_id and solver_id == verifier_id:
            raise ValueError("Solver and Verifier evidence identifies the same sandbox")
        if result.get("exception_info"):
            raise ValueError("Harbor trial has exception_info; cannot claim successful run evidence")
        if not result.get("finished_at"):
            raise ValueError("Harbor trial is missing finished_at")
        verifier = result.get("verifier_result")
        rewards = verifier.get("rewards") if isinstance(verifier, dict) else None
        expected = read_reward(reward_path)
        if not isinstance(rewards, dict) or not rewards or not all(numeric_reward(v) for v in rewards.values()):
            raise ValueError("Harbor result.verifier_result.rewards must contain finite numeric rewards")
        if set(rewards) != set(expected) or any(not math.isclose(rewards[k], v, rel_tol=1e-9, abs_tol=1e-12) for k, v in expected.items()):
            raise ValueError("Harbor result rewards disagree with the selected reward file")
        if not any(bounded_text(log).strip() for log in logs):
            raise ValueError("Harbor trial log evidence is empty")
        identity = trial_task_identity(root, task_root, config_value, result, binding)
        return {"trial_dir": trial.relative_to(root.resolve()).as_posix(), "agent": agent_config["name"],
                "verifier_environment_mode": "separate", "rewards": expected, "task_binding": identity}
    raise ValueError("H06 pass requires config.json, result.json, verifier/reward.*, and trial.log or verifier/test-stdout.txt from the same trial")


def aggregate(rows):
    statuses = {row["status"] for row in rows}
    return "fail" if "fail" in statuses else "manual" if "manual" in statuses else "pass"


def hidden_contract(root, declaration):
    """Validate references for an explicit semantic review, not a directory convention."""
    if declaration is None:
        return {"status": "manual", "summary": "Hidden 评测材料必需；尚未复核供给方式、实际材料及评分调用关系。"}
    if not isinstance(declaration, dict) or declaration.get("mode") not in ("prebuilt", "generated", "injected"):
        raise ValueError("hidden_review.mode must be prebuilt, generated, or injected")
    if not isinstance(declaration.get("summary"), str) or not declaration["summary"].strip():
        raise ValueError("hidden_review requires a specific material-supply and grading-use summary")
    refs = declaration.get("evidence")
    if not isinstance(refs, list) or not refs:
        raise ValueError("hidden_review requires real source/configuration evidence")
    for ref in refs:
        resolve_ref(root, ref)
    assets = declaration.get("asset_paths", [])
    if not isinstance(assets, list):
        raise ValueError("hidden_review.asset_paths must be an array")
    if declaration["mode"] == "prebuilt" and not assets:
        return {"status": "manual", "summary": "预置 Hidden 需要引用实际数据文件；目录名或 README 不能替代材料。"}
    for ref in assets:
        path = resolve_ref(root, ref)
        if not path.stat().st_size or path.name.lower() in (".gitkeep", ".keep", ".ds_store", "readme.md", "readme.txt"):
            raise ValueError("hidden_review asset_paths must reference nonempty actual data, not placeholders")
    return {**declaration, "status": "pass", "basis": "reviewed_evidence",
            "note": "仅核验声明与文件引用；材料用途、隔离和生成/注入可用性由语义复核负责。"}


def artifact_contract(root, cfg, review):
    requested = review.get("submission_paths", ["/workspace/solution"])
    if not isinstance(requested, list) or not requested or any(not isinstance(p, str) or not p.startswith("/") or ".." in PurePosixPath(p).parts for p in requested):
        raise ValueError("submission_paths must list absolute Verifier input paths")
    override = review.get("artifact_override")
    if override is not None:
        if not isinstance(override, dict) or not isinstance(override.get("summary"), str) or not override["summary"].strip() or not isinstance(override.get("evidence"), list) or not override["evidence"]:
            raise ValueError("artifact_override requires a target-version Job override summary and real evidence")
        for ref in override["evidence"]:
            resolve_ref(root, ref)
        return {"status": "manual", "submission_paths": requested, "override": override,
                "summary": "存在 Job/版本级 artifacts 覆盖声明；需按目标版本人工核对有效配置与移交路径。"}
    if not isinstance(cfg, dict):
        return {"status": "manual", "submission_paths": requested, "summary": "未获得可解析配置，不能确认 artifacts 移交。"}
    artifacts = cfg.get("artifacts", [])
    if not isinstance(artifacts, list):
        return {"status": "fail", "submission_paths": requested, "summary": "task.toml 顶层 artifacts 必须是列表；默认移交目录不能抵消无效配置。"}
    # Harbor transfers /logs/artifacts to a separate Verifier by default. Extra
    # paths need explicit artifacts; an empty list does not disable this default.
    sources, ambiguous = [PurePosixPath("/logs/artifacts")], False
    for entry in artifacts:
        source = entry.get("source") if isinstance(entry, dict) else entry
        if not isinstance(source, str) or not source.startswith("/") or ".." in PurePosixPath(source).parts:
            return {"status": "fail", "submission_paths": requested, "summary": "artifacts 条目需是绝对源路径或含绝对 source 的对象。"}
        if any(c in source for c in "*?[") or (isinstance(entry, dict) and entry.get("service", "main") != "main"):
            ambiguous = True
        else:
            sources.append(PurePosixPath(source))
    uncovered = [p for p in requested if not any(PurePosixPath(p) == s or s in PurePosixPath(p).parents for s in sources)]
    status = "pass" if not uncovered else "manual" if ambiguous else "fail"
    return {"status": status, "submission_paths": requested, "sources": [str(p) for p in sources],
            "default_sources": ["/logs/artifacts"], "uncovered": uncovered,
            "ambiguous_extra_sources": ambiguous,
            "summary": "尚有未覆盖读取路径，且 artifacts 包含静态无法确定的 glob/service；需人工复核。" if uncovered and ambiguous else
                       "artifacts 未覆盖评分读取路径：" + "、".join(uncovered) if uncovered else
                       "读取路径已由默认 /logs/artifacts 或显式源路径覆盖；运行移交另看 Trial 证据。"}


def apply_review(current, review, root):
    if not isinstance(review, dict):
        raise ValueError("review.harbor must include the five Harbor compatibility conclusions")
    review = dict(review)
    static_source = deployment_review.source_stage(review.get("delivery_stage", "source_package"))
    rows = review.get("checks")
    if (not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows)
            or len(rows) != len({r.get("id") for r in rows})
            or {r.get("id") for r in rows} not in (set(H_IDS[:5]), set(H_IDS))):
        raise ValueError("Harbor review must contain H01–H05 exactly once; legacy H06 is optional")
    # H06 is accepted only for old worksheet compatibility. Its status and
    # references never participate in current QA or trigger Trial inspection.
    rows = [row for row in rows if row["id"] != "H06"]
    for field in ("target_version", "provider", "version_basis"):
        if review.get(field) is None or review.get(field) == "":
            review[field] = "unknown"
        if not isinstance(review.get(field), str) or not review[field].strip():
            raise ValueError(f"Harbor {field} must be a string when supplied")
    selected = review.get("task_root", current["observations"].get("task_root"))
    task_root = (root / selected).resolve() if isinstance(selected, str) else None
    if task_root and not task_root.is_relative_to(root.resolve()):
        raise ValueError("Harbor task_root cannot escape the inspected bundle")
    declaration = review.get("path_contract")
    if not isinstance(declaration, dict) or declaration.get("profile") not in docker_paths.PROFILES:
        raise ValueError("Harbor path_contract requires an explicit supported profile")
    if not isinstance(declaration.get("profile_basis"), str) or not declaration["profile_basis"].strip():
        raise ValueError("Harbor path_contract requires profile_basis")
    adapter_refs = declaration.get("adapter_evidence", [])
    if not isinstance(adapter_refs, list):
        raise ValueError("Harbor path_contract.adapter_evidence must be an array")
    for ref in adapter_refs:
        resolve_ref(root, ref)
    cfg = None
    if task_root and (task_root / "task.toml").is_file() and tomllib:
        try:
            cfg = tomllib.loads(bounded_text(task_root / "task.toml"))
        except (OSError, ValueError, UnicodeError):
            pass  # H02 owns TOML syntax; never infer config fields from malformed text.
    config_shape_errors = []
    if isinstance(cfg, dict):
        for section in ("environment", "agent", "verifier"):
            if section in cfg and not isinstance(cfg[section], dict):
                config_shape_errors.append(f"task.toml 的 {section} 必须是 table，不能是标量或列表。")
        if isinstance(cfg.get("verifier"), dict) and "environment" in cfg["verifier"] and not isinstance(cfg["verifier"]["environment"], dict):
            config_shape_errors.append("task.toml 的 verifier.environment 必须是 table，不能是标量或列表。")
    path_contract = docker_paths.inspect(root, selected, cfg, declaration, require_separate=True)
    hidden = hidden_contract(root, review.get("hidden_review"))
    artifacts = artifact_contract(root, cfg, review)
    deployment = deployment_review.assess(root, task_root, cfg, review, resolve_ref)
    manual_resolution = declaration.get("manual_resolution")
    if manual_resolution is not None:
        if not isinstance(manual_resolution, dict):
            raise ValueError("path_contract.manual_resolution must be an object")
        reason, refs = manual_resolution.get("summary"), manual_resolution.get("evidence")
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 500 or not isinstance(refs, list) or not refs:
            raise ValueError("path_contract.manual_resolution requires concise summary and real evidence")
        for ref in refs:
            resolve_ref(root, ref)
        path_contract["manual_resolution"] = manual_resolution
    path_contract["adapter_evidence"] = adapter_refs
    final = []
    for row in sorted(rows, key=lambda r: r["id"]):
        check_id, status = row["id"], row.get("status")
        if status not in ("pass", "fail", "manual", "not_applicable"):
            raise ValueError(f"{check_id}: invalid Harbor status")
        if status == "not_applicable" and check_id not in ("H05", "H06"):
            raise ValueError(f"{check_id}: required Harbor check cannot be skipped")
        reason, refs = row.get("summary"), row.get("evidence", [])
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 220 or not isinstance(refs, list):
            raise ValueError(f"{check_id}: concise summary and evidence array required")
        paths = [resolve_ref(root, ref) for ref in refs]
        if status == "pass" and not refs:
            raise ValueError(f"{check_id}: passing requires evidence")
        if check_id in ("H01", "H02") and status == "pass":
            if not task_root or not (task_root / "task.toml").is_file():
                raise ValueError(f"{check_id}: no task.toml at the selected task root")
            if task_root / "task.toml" not in paths:
                raise ValueError(f"{check_id}: cite the selected task.toml")
        if check_id == "H02" and status == "pass":
            if not static_source and (review["target_version"] == "unknown" or review["version_basis"] == "unknown"):
                raise ValueError("H02: unknown version basis cannot pass")
            if tomllib:
                tomllib.loads(bounded_text(task_root / "task.toml"))
        if check_id == "H01" and status == "pass":
            environment = cfg.get("environment") if isinstance(cfg, dict) else None
            verifier_cfg = cfg.get("verifier") if isinstance(cfg, dict) else None
            verifier_env = verifier_cfg.get("environment") if isinstance(verifier_cfg, dict) else None
            os_name = (verifier_env or environment or {}).get("os") if isinstance(verifier_env or environment or {}, dict) else None
            test_name = "test.bat" if os_name == "windows" else "test.sh"
            selection = path_contract.get("image_selection", {})
            required = [task_root / "instruction.md", task_root / "task.toml"]
            if not isinstance(environment, dict) or not environment.get("docker_image"):
                if not docker_paths.compose_files(task_root / "environment"):
                    required.append(task_root / "environment/Dockerfile")
            if selection.get("source") in ("agent_build", "agent_image", "tests_dockerfile"):
                required.append(task_root / "tests" / test_name)
            missing = [p.relative_to(task_root).as_posix() for p in required if not p.is_file() or p.is_symlink()]
            if missing:
                status = "fail"
                reason = "任务交付缺少：" + "、".join(missing)
            elif hidden["status"] != "pass":
                status = "manual"
                reason = hidden["summary"]
        if check_id == "H02" and status == "pass":
            verifier = cfg.get("verifier") if isinstance(cfg, dict) else None
            if not isinstance(verifier, dict) or verifier.get("environment_mode") != "separate":
                status = "fail"
                reason = 'task.toml 的 [verifier] 必须显式设置 environment_mode = "separate"。'
        if check_id == "H02" and artifacts["status"] == "fail":
            status, reason = "fail", artifacts["summary"]
        elif check_id == "H02" and status == "pass" and artifacts["status"] == "manual":
            status, reason = "manual", artifacts["summary"]
        if check_id == "H02" and config_shape_errors:
            status, reason = "fail", "；".join(config_shape_errors)[:220]
            refs = list(dict.fromkeys(refs + [(task_root / "task.toml").relative_to(root.resolve()).as_posix()]))
        if (check_id == "H03" and status == "pass" and not static_source and review["provider"] == "unknown"
                and deployment["profile"] not in deployment_review.PROFILES):
            raise ValueError("H03: unknown provider cannot pass")
        if check_id == "H03":
            if path_contract["status"] == "fail":
                status = "fail"
                problems = [f for f in path_contract["findings"] if f["status"] == "fail"]
                reason = ("路径检查不通过：" + "；".join(p["message"] for p in problems))[:220]
                refs = sorted(set(refs + [r for p in problems for r in p["evidence"]]))
            elif path_contract["status"] == "manual" and status == "pass" and (not manual_resolution or (declaration["profile"] == "custom" and not adapter_refs)):
                status = "manual"
                reason = "路径存在静态无法解析项；需提供 path_contract.manual_resolution 的真实证据后才能通过。"
            elif status == "pass":
                environment = cfg.get("environment", {}) if isinstance(cfg, dict) else {}
                environment = environment if isinstance(environment, dict) else {}
                agent_build = task_root / "environment/Dockerfile"
                if not agent_build.is_file() and docker_paths.compose_files(task_root / "environment"):
                    agent_build = docker_paths.compose_files(task_root / "environment")[0]
                required_refs = {task_root / "task.toml"} if environment.get("docker_image") else {agent_build}
                if path_contract.get("image_selection", {}).get("source") == "tests_dockerfile":
                    required_refs.add(task_root / "tests/Dockerfile")
                elif path_contract.get("image_selection", {}).get("source") == "verifier_image":
                    required_refs.add(task_root / "task.toml")
                elif path_contract.get("image_selection", {}).get("source") == "tests_compose":
                    required_refs.update(docker_paths.compose_files(task_root / "tests"))
                else:
                    required_refs.add(task_root / "tests" / ("test.bat" if environment.get("os") == "windows" else "test.sh"))
                if not required_refs <= set(paths):
                    status = "manual"
                    reason = "H03 须引用实际选中的镜像/构建配置和 tests 供给入口，复核独立依赖、上传或预置路径。"
        platform_status = deployment["config_status"] if check_id == "H02" else deployment["compose_status"] if check_id == "H03" else "pass"
        if platform_status != "pass":
            status = deployment_review.aggregate([status, platform_status])
            reason = (reason + "；" + deployment["summary"])[:220]
            refs = list(dict.fromkeys(refs + deployment["evidence"]))
        final.append({"id": check_id, "title": H_TITLES[H_IDS.index(check_id)], "status": status,
                      "summary": reason, "evidence": refs})
    current = dict(current)
    current.update({k: review[k] for k in ("target_version", "provider", "version_basis")})
    current["task_root"] = selected
    current["path_contract"] = path_contract
    current["hidden_review"] = hidden
    current["artifact_contract"] = artifacts
    current["deployment_contract"] = deployment
    version_pending = static_source and (review["target_version"] == "unknown" or review["version_basis"] == "unknown")
    current["platform_review"] = {"status": "unverified", "runtime_verified": False,
        "profile": deployment["profile"], "responsibility": "platform",
        "version_basis_pending": version_pending,
        "limitations": deployment.get("platform_findings", []) + ([{
            "code": "target_version_unverified", "status": "platform_pending", "required_for_static_completion": False,
            "message": "目标Harbor版本/运行适配尚未验证；不影响已完成的源码结构、路径与评分契约静态检查。"}] if version_pending else [])}
    current["config_shape_errors"] = config_shape_errors
    current["trial_evidence"] = None
    current["checks"] = final + [{"id": "H06", "title": H_TITLES[5],
        "status": "not_applicable", "summary": "已移出当前验收范围。", "evidence": []}]
    current["static_status"] = aggregate(final)
    current["runtime_status"] = "not_required"
    current["qa17_status"] = aggregate(final)
    return current


def summary(harbor):
    static = {"pass": "通过", "fail": "不通过", "manual": "未完成"}[harbor["static_status"]]
    return f"Harbor 格式/接口：{static}。"
