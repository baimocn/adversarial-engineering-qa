#!/usr/bin/env python3
"""Generic current-standard deterministic gate.

The effective 2026-11-14 profile is binary: external PASS/FAIL. Package-specific
values live in config/profiles/*.json and config/rule_catalog.json, not in this
executor. Static PASS is not Docker/Harbor/Hidden runtime approval.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CURRENT_PROFILE = "current-20261114"


def jload(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def jwrite(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_profile(name: str) -> dict:
    profiles = REPO / "config" / "profiles"
    data = jload(profiles / f"{name}.json")
    parent = data.get("extends")
    if parent:
        data = deep_merge(load_profile(parent), data)
    data["profile"] = name
    return data


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def p(root: Path, rel: str) -> Path:
    return root / rel


def add(findings: list[dict], rule: str, ok: bool, reason: str, evidence: str,
        blocking: bool = True) -> None:
    if not blocking:
        status = "platform_scope"
    else:
        status = "pass" if ok else "fail"
    findings.append({
        "rule": rule,
        "status": status,
        "blocking": blocking and not ok,
        "reason": reason,
        "evidence": evidence,
    })


def parse_toml_shallow(raw: str) -> dict:
    out: dict = {"tables": set(), "top": {}, "lines": []}
    table = ""
    for i, line in enumerate(raw.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = re.match(r"^\[([^\]]+)\]\s*$", stripped)
        if m:
            table = m.group(1).strip()
            out["tables"].add(table)
            continue
        m = re.match(r"^([A-Za-z0-9_.-]+)\s*=\s*(.+?)\s*$", stripped)
        if m:
            key, value = m.group(1), m.group(2)
            if not table:
                out["top"][key] = value
            out["lines"].append((i, table, key, value, line))
    return out


def ast_digest_like_guard(tree: ast.AST) -> str:
    """Mirror contract_guard.ast_digest canonicalization without importing task code."""
    tree = ast.parse(ast.unparse(tree))
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr):
            if isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                body.pop(0)

    def canonical(value):
        if isinstance(value, ast.AST):
            return {"type": type(value).__name__, **{
                key: canonical(child) for key, child in ast.iter_fields(value)
                if child is not None and child != []}}
        if isinstance(value, list):
            return [canonical(child) for child in value]
        return value

    encoded = json.dumps(canonical(tree), sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def task_config(task: Path, findings: list[dict], cfg: dict) -> None:
    raw = text(task / "task.toml")
    parsed = parse_toml_shallow(raw)
    active_lines = [x for x in parsed["lines"] if not x[4].lstrip().startswith("#")]
    docker_image_lines = [x for x in active_lines if x[2].strip() == "docker_image"]
    tcfg = cfg["task_config"]
    add(findings, "canonical_task_toml", (task / "task.toml").is_file(),
        "effective profile resolves current task from configured task.toml",
        str(task / "task.toml"))
    add(findings, "no_expert_docker_image", not docker_image_lines,
        "expert source task.toml has no active docker_image; platform selects/builds image",
        "task.toml lines " + ",".join(str(x[0]) for x in docker_image_lines))
    add(findings, "separate_verifier", tcfg["separate_marker"] in raw and "separate" in raw,
        "independent Verifier sandbox remains required", "task.toml:[verifier]")
    add(findings, "artifacts_solution", tcfg["artifacts_value"] in raw,
        "candidate handoff path must match the current contract", "task.toml:artifacts")


def reward_protocol(task: Path, findings: list[dict], cfg: dict) -> None:
    rcfg = cfg["reward"]
    tests = task / "tests"
    grader = text(tests / "grader.py")
    test_sh = text(tests / "test.sh")
    source = grader + "\n" + test_sh
    formal = rcfg["formal_file"]
    historical = rcfg["historical_file"]
    json_write = bool(re.search(re.escape(formal), grader, re.I) and
                      re.search(r"_atomic_write|open\(|write_reward|json\.dumps", grader, re.I))
    txt_publish_lines = []
    for i, line in enumerate(grader.splitlines(), 1):
        low = line.lower()
        if historical.lower() not in low:
            continue
        cleanup = re.search(r"\brm\s+-f|clean_stale|cleanup|清理|废弃", line, re.I)
        write = re.search(r"_atomic_write|open\(|write_reward|json\.dumps|\bcp\b|\becho\b|>\s*\S", line, re.I)
        if write and not cleanup:
            txt_publish_lines.append((i, line.strip()))
    txt_write = bool(txt_publish_lines)
    stale_cleanup = "clean_stale_rewards" in grader or bool(
        re.search(r"rm\s+-f[^\n]*" + re.escape(historical) + r"[^\n]*" + re.escape(formal), test_sh, re.I))
    add(findings, "single_formal_reward", bool(json_write) and not txt_write and stale_cleanup,
        "one formal reward file; stale reward cleanup is explicit",
        "tests/grader.py; tests/test.sh")
    add(findings, "no_reward_txt_publish", not txt_write,
        "historical reward file must not be published as a second formal reward",
        "tests/grader.py")

    hard_value = str(rcfg["hard_gate_value"])
    hard_gate = bool(re.search(r"^HARD_GATE\s*=\s*" + re.escape(hard_value) + r"(?:\.0+)?\b", grader, re.M)
                     and "CANDIDATE_REJECT_CODES" in grader)
    trusted_fault = all(token in grader for token in rcfg["trusted_fault_tokens"])
    no_zero_on_failure = any(marker in grader for marker in rcfg["no_score_markers"])
    add(findings, "hard_gate_minus_10", hard_gate,
        "current standard uses candidate hard gate " + hard_value,
        "tests/grader.py:HARD_GATE/CANDIDATE_REJECT_CODES")
    add(findings, "trusted_fault_no_score", trusted_fault and no_zero_on_failure,
        "credible grader/environment faults must be error/no-score, not ordinary 0 or hard gate",
        "tests/grader.py:TRUSTED_FAULT_CODES/NOT_READY")
    add(findings, "no_ordinary_zero_failure", "write_reward(0" not in source.replace(" ", ""),
        "failure paths must not publish ordinary 0.0 as a normal score",
        "tests/grader.py; tests/test.sh")


def public_contract(task: Path, findings: list[dict], cfg: dict) -> None:
    ccfg = cfg["public_contract"]
    instr = text(task / "instruction.md")
    protocol_path = task / "environment/public_eval/protocol.json"
    protocol = jload(protocol_path) if protocol_path.is_file() else {}
    boundary = protocol.get("implementation_boundary", {})
    syntax = boundary.get("static_syntax_restrictions", {})
    imports = boundary.get("staged_import_whitelist", {})
    guard = text(task / "tests/contract_guard.py")
    readmes = [text(task / "environment/starter/README.md"), text(task / "solution/README.md")]
    disclosures = [instr, *readmes]
    required = ccfg["required_rejected_constructs"]
    needles = ccfg["construct_needles"]
    rejected = syntax.get("rejected_constructs", [])
    nonlocal_ok = (
        all(item in rejected for item in required)
        and all(all(needles.get(item, item) in doc for item in required) for doc in disclosures)
    )
    expected_modules = ["torch", "torch.nn.functional", "math"]
    expected_from = ["numeric_api", "torch.nn"]
    staged_ok = (
        imports.get("allowed_import_modules") == expected_modules
        and all(any(entry.get("module") == module for entry in imports.get("allowed_import_from", []))
                for module in expected_from)
        and "import numpy" in " ".join(imports.get("rejected_examples", []))
    )
    stage_markers = ccfg["staged_markers"]
    marker_ok = stage_markers["instruction"] in instr and all(stage_markers["readme"] in doc for doc in readmes)
    expected_set = "{" + ", ".join('"%s"' % module for module in expected_modules) + "}"
    guard_ok = "ast.Nonlocal" in guard and expected_set in guard
    add(findings, "public_contract_nonlocal", nonlocal_ok,
        "configured rejected constructs are disclosed in instruction, protocol and READMEs",
        "instruction.md; environment/public_eval/protocol.json; starter/solution README")
    add(findings, "public_contract_staged_import", staged_ok and marker_ok,
        "exact staged import whitelist disclosed and public contract mentions staged restrictions",
        "environment/public_eval/protocol.json:/implementation_boundary/staged_import_whitelist")
    add(findings, "guard_unchanged_contract", guard_ok,
        "public contract must match the actual AST/import guard",
        "tests/contract_guard.py")
    add(findings, "task_contract_live_execution", bool(guard.strip()),
        "text-only limits are insufficient; a guard implementation must exist",
        "tests/contract_guard.py")


def oracle_handoff(task: Path, findings: list[dict], cfg: dict) -> None:
    ocfg = cfg["oracle"]
    solution = task / "solution"
    solve = solution / "solve.sh"
    solve_text = text(solve)
    assembler = ocfg.get("assembler")
    if not assembler:
        m = re.search(ocfg["assembler_pattern"], solve_text)
        assembler = m.group(1) if m else ""
    assemble = solution / assembler if assembler else None
    assemble_text = text(assemble) if assemble else ""
    docker_text = text(task / "environment/Dockerfile")
    stage_token = assembler or "assembler"
    stages = bool(assembler) and stage_token in solve_text and "exec bash" in solve_text \
        and solve_text.index(stage_token) < solve_text.index("exec bash")
    submitted_marker = 'exec bash "${SOLUTION_DIR}/' + ocfg["submitted_entry"] + '"'
    submitted = submitted_marker in solve_text
    copy_ok = ocfg["copy_marker"] in assemble_text and all(token in assemble_text for token in ocfg["required_components"])
    private = not any(marker in docker_text for marker in ocfg["private_copy_markers"])
    add(findings, "oracle_handoff_source_before_training", stages and copy_ok and submitted,
        "Oracle stages source, registry and config into SOLUTION_DIR before training; run.sh executes from submitted dir",
        "solution/solve.sh; " + (assembler or "<missing assembler>"))
    add(findings, "oracle_private_reference_not_in_work", private,
        "private Oracle/Reference is not COPY'd into Agent Work image",
        "environment/Dockerfile")


def best_method_adapter(root: Path, task: Path, findings: list[dict], cfg: dict) -> None:
    bcfg = cfg["best_method"]
    paths = cfg["paths"]
    best = p(root, paths["best_method"])
    data = best / "data.py"
    selection = p(root, paths["selection"])
    qa16 = p(root, paths["revalidation"])
    starter = task / "environment/starter/data.py"
    policy = p(root, bcfg["frozen_policy_path"])
    data_raw, starter_raw, policy_raw = text(data), text(starter), text(policy)
    data_sha = sha256_file(data) if data.is_file() else ""
    bad_sha = bcfg.get("bad_data_sha256")
    ast_digest = ast_digest_like_guard(ast.parse(data_raw)) if data_raw else ""
    policy_data = jload(policy) if policy.is_file() else {}
    allowed_ast = policy_data.get("frozen_ast", {}).get("data.py", [])
    if isinstance(allowed_ast, str):
        allowed_ast = [allowed_ast]
    restored = bool(data_raw) and data_raw == starter_raw and (not bad_sha or data_sha != bad_sha)
    add(findings, "best_method_restored_starter_adapter", restored,
        "current best_method/data.py matches the active Starter frozen adapter",
        f"{paths['best_method']}/data.py; environment/starter/data.py")
    add(findings, "best_method_allowed_frozen_ast", ast_digest in allowed_ast,
        "frozen adapter AST matches trusted contract_policy allowed digest",
        f"{paths['best_method']}/data.py; {bcfg['frozen_policy_path']}")
    sel = jload(selection) if selection.is_file() else {}
    qa = jload(qa16) if qa16.is_file() else {}
    synced = (sel.get("method_sha256", {}).get("data.py") == data_sha
              and qa.get("best_method_tree", {}).get("data.py") == data_sha)
    if bcfg.get("require_scope_flags"):
        synced = synced and (sel.get("current_revalidation", {}).get("proves_current_frozen_gate") is False
                             and qa.get("proves_current_frozen_gate") is False)
    add(findings, "best_method_source_binding_synced", bool(sel) and bool(qa) and synced,
        "selection/revalidation hashes synchronized; old PUBLIC_DEV_ONLY evidence cannot prove current frozen gate",
        f"{paths['selection']}; {paths['revalidation']}")
    add(findings, "trusted_policy_not_loosened", bool(policy_raw) and '"frozen_ast"' in policy_raw,
        "trusted frozen policy remains present; repair must not widen it for bad adapter",
        bcfg["frozen_policy_path"])


def provenance(root: Path, findings: list[dict], cfg: dict) -> None:
    pcfg = cfg["provenance"]
    paths = cfg["paths"]
    prov = p(root, paths["provenance"])
    binding = p(root, paths["source_binding"])
    br = p(root, paths["br_results"])
    raw = text(prov)
    required_shas = pcfg.get("required_role_sha256", [])
    files_ok = prov.is_file() and binding.is_file() and br.is_file()
    role_ok = all(sha in raw for sha in required_shas)
    binding_ok = True
    if binding.is_file():
        expected = jload(binding).get("br_results_sha256")
        if expected and br.is_file():
            binding_ok = expected == sha256_file(br)
    no_blanket = pcfg["forbidden_claim"] not in raw
    add(findings, "g03_role_source_binding", files_ok and role_ok and binding_ok and no_blanket,
        "G03 role-specific source identity and raw B/R evidence are present; blanket claim absent",
        f"{paths['provenance']}; {paths['source_binding']}; {paths['br_results']}")


def legacy_conflicts(findings: list[dict], cfg: dict) -> None:
    catalog = jload(REPO / "config/rule_versions.json")
    profile = catalog["profiles"][CURRENT_PROFILE]
    winners = {x["topic"]: x["winner"] for x in profile["conflict_resolution"]}
    expected = cfg["required_conflict_winners"]
    blockers = [topic for topic, winner in expected.items() if winners.get(topic) != winner]
    add(findings, "version_conflict_resolution", not blockers,
        "effective profile resolves -1/-10, docker_image, NOP, final decision and count conflicts",
        "config/rule_versions.json:" + CURRENT_PROFILE)
    add(findings, "platform_runtime_scope", True,
        "Docker/Harbor/Hidden execution and actual GPU/image size are platform_scope; static gate does not claim runtime proof",
        "config/rule_versions.json:platform-0.5.6-current.1-report.verification_scope",
        blocking=False)


def catalog_integrity(findings: list[dict], rule_catalog: Path) -> None:
    data = jload(rule_catalog)
    required = [r["id"] for r in data["rules"]
                if r.get("class") in ("current_mechanical", "current_ablation_only")]
    observed = {f["rule"] for f in findings if f["status"] in ("pass", "fail")}
    missing = [rid for rid in required if rid not in observed]
    add(findings, "catalog_integrity", not missing,
        "all current rule-catalog entries have an executable gate finding",
        "config/rule_catalog.json; missing=" + ",".join(missing))


def main() -> int:
    ap = argparse.ArgumentParser(description="Generic current-standard binary gate")
    ap.add_argument("--root", required=True, help="submission package tree root")
    ap.add_argument("--out", required=True)
    ap.add_argument("--profile", default="default", help="profile name in config/profiles/")
    ap.add_argument("--rule-catalog", default=str(REPO / "config" / "rule_catalog.json"))
    args = ap.parse_args()

    root = Path(args.root).resolve()
    cfg = load_profile(args.profile)
    task = p(root, cfg["paths"]["task"])
    findings: list[dict] = []
    task_config(task, findings, cfg)
    reward_protocol(task, findings, cfg)
    public_contract(task, findings, cfg)
    oracle_handoff(task, findings, cfg)
    best_method_adapter(root, task, findings, cfg)
    provenance(root, findings, cfg)
    legacy_conflicts(findings, cfg)
    catalog_integrity(findings, Path(args.rule_catalog))

    blocking = [f for f in findings if f["status"] == "fail"]
    scope = [f for f in findings if f["status"] == "platform_scope"]
    decision = "FAIL" if blocking else "PASS"
    report = {
        "schema": "current-standard-gate/2",
        "profile": args.profile,
        "effective_profile": CURRENT_PROFILE,
        "root": str(root),
        "decision": decision,
        "final_decision_is_binary": True,
        "summary": {
            "pass": sum(f["status"] == "pass" for f in findings),
            "fail": len(blocking),
            "platform_scope": len(scope),
        },
        "platform_scope_note": "PASS is static source/evidence only; it is not Docker/Harbor/Hidden runtime approval.",
        "findings": findings,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    jwrite(out, report)
    print(json.dumps({"decision": decision, "summary": report["summary"],
                      "fail_rules": [f["rule"] for f in blocking]}, ensure_ascii=False, indent=2))
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
