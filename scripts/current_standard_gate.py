#!/usr/bin/env python3
"""Current-standard deterministic gate for the effective 2026-11-14 profile.

This gate implements the latest versioned platform rules without model review.
It takes a package tree root, loads config/rule_versions.json, and emits a
binary external verdict: PASS or FAIL. Internal orchestration may still use
INCOMPLETE/QA_NOT_FINISHED, but that is not an author-facing PASS.

The checks are deliberately small and mechanical. Semantic, dynamic and
platform-runtime questions are recorded as `platform_scope`, never auto-passed
as proof of execution.
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
BAD_BEST_METHOD_DATA_SHA = "0c40b9e73c5e59fdd41b389d818d1e38c7dde95beddb5db62570f35c5bf3a2b8"
ALLOWED_DATA_AST = "9d3b0a20364a29671a7d34997a9487096b21be488643758f0188c7e126a4b7df"


def jload(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def jwrite(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def add(findings: list[dict], rule: str, ok: bool, reason: str, evidence: str, blocking: bool = True) -> None:
    findings.append({
        "rule": rule,
        "status": "pass" if ok else ("fail" if blocking else "platform_scope"),
        "blocking": blocking and not ok,
        "reason": reason,
        "evidence": evidence,
    })


def parse_toml_shallow(raw: str) -> dict:
    """Read only current table / top-level key facts; no third-party TOML needed."""
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
    """Mirror contract_guard.ast_digest canonicalization, without importing task code."""
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


def reward_protocol(task: Path, findings: list[dict]) -> None:
    tests = task / "tests"
    grader = text(tests / "grader.py")
    test_sh = text(tests / "test.sh")
    source = grader + "\n" + test_sh
    json_write = bool(re.search(r"reward\.json", grader, re.I) and re.search(r"_atomic_write|open\(|write_reward|json\.dumps", grader, re.I))
    # A reward.txt mention is a historical cleanup target only if it appears in
    # rm/cleanup context. Publishing/writing it as a formal reward is forbidden.
    txt_publish_lines = []
    for i, line in enumerate(grader.splitlines(), 1):
        low = line.lower()
        if "reward.txt" not in low:
            continue
        cleanup = re.search(r"\brm\s+-f|clean_stale|cleanup|清理|废弃", line, re.I)
        write = re.search(r"_atomic_write|open\(|write_reward|json\.dumps|\bcp\b|\becho\b|>\s*\S", line, re.I)
        if write and not cleanup:
            txt_publish_lines.append((i, line.strip()))
    txt_write = bool(txt_publish_lines)
    stale_cleanup = "clean_stale_rewards" in grader or bool(re.search(r"rm\s+-f[^\n]*reward\.txt[^\n]*reward\.json", test_sh, re.I))
    add(findings, "single_formal_reward", bool(json_write) and not txt_write and stale_cleanup,
        "0.5.0/0.5.6: one formal reward file; stale reward cleanup is explicit",
        "workspace/harbor_task/tests/grader.py; tests/test.sh")
    add(findings, "no_reward_txt_publish", not txt_write,
        "reward.txt must not be published as a second formal reward",
        "workspace/harbor_task/tests/grader.py")

    hard_gate = bool(re.search(r"^HARD_GATE\s*=\s*-10(?:\.0+)?\b", grader, re.M) and "CANDIDATE_REJECT_CODES" in grader)
    trusted_fault = ("TRUSTED_FAULT_CODES" in grader and "GRADER_ERROR" in grader and "NOT_READY" in grader)
    no_zero_on_failure = ("reward\": None" in grader or "reward: None" in grader) and "不写任何 reward" in grader
    add(findings, "hard_gate_minus_10", hard_gate,
        "current standard supersedes -1 with candidate hard gate -10",
        "workspace/harbor_task/tests/grader.py:HARD_GATE/CANDIDATE_REJECT_CODES")
    add(findings, "trusted_fault_no_score", trusted_fault and no_zero_on_failure,
        "credible grader/environment faults must be error/no-score, not ordinary 0 or -10",
        "workspace/harbor_task/tests/grader.py:TRUSTED_FAULT_CODES/NOT_READY")
    add(findings, "no_ordinary_zero_failure", "write_reward(0" not in source.replace(" ", ""),
        "failure paths must not publish ordinary 0.0 as a normal score",
        "workspace/harbor_task/tests/grader.py; tests/test.sh")


def task_config(task: Path, findings: list[dict]) -> None:
    task_toml = task / "task.toml"
    raw = text(task_toml)
    parsed = parse_toml_shallow(raw)
    active_lines = [x for x in parsed["lines"] if not x[4].lstrip().startswith("#")]
    docker_image_lines = [x for x in active_lines if x[2].strip() == "docker_image"]
    add(findings, "canonical_task_toml", task_toml.is_file(),
        "effective profile resolves current task from workspace/harbor_task/task.toml",
        "workspace/harbor_task/task.toml")
    add(findings, "no_expert_docker_image", not docker_image_lines,
        "0.5.6 repair overlay: expert source task.toml has no active docker_image; platform selects/builds image",
        "workspace/harbor_task/task.toml lines " + ",".join(str(x[0]) for x in docker_image_lines))
    add(findings, "separate_verifier", "environment_mode" in raw and "separate" in raw,
        "independent Verifier sandbox remains required",
        "workspace/harbor_task/task.toml:[verifier]")
    add(findings, "artifacts_solution", '"/workspace/solution"' in raw,
        "candidate handoff path must match the current contract",
        "workspace/harbor_task/task.toml:artifacts")


def public_contract(task: Path, findings: list[dict]) -> None:
    instr = text(task / "instruction.md")
    protocol_path = task / "environment/public_eval/protocol.json"
    protocol = jload(protocol_path) if protocol_path.is_file() else {}
    boundary = protocol.get("implementation_boundary", {})
    syntax = boundary.get("static_syntax_restrictions", {})
    imports = boundary.get("staged_import_whitelist", {})
    guard = text(task / "tests/contract_guard.py")
    readmes = [text(task / "environment/starter/README.md"), text(task / "solution/README.md")]
    disclosures = [instr, *readmes]
    staged_ok = (
        imports.get("allowed_import_modules") == ["torch", "torch.nn.functional", "math"]
        and any(item.get("module") == "numeric_api" for item in imports.get("allowed_import_from", []))
        and "import numpy" in " ".join(imports.get("rejected_examples", []))
    )
    guard_ok = "ast.Nonlocal" in guard and 'MODULES = {"torch", "torch.nn.functional", "math"}' in guard
    nonlocal_disclosures = [x for x in disclosures if "nonlocal" in x]
    # The platform requires disclosure in every public surface. Counting a
    # single renamed/deleted surface through a generic "nonlocal" search is not
    # enough; the test mutates instruction.md to remove the first disclosure.
    nonlocal_ok = len(nonlocal_disclosures) == len(disclosures) and "nonlocal" in syntax.get("rejected_constructs", [])
    add(findings, "public_contract_nonlocal", nonlocal_ok,
        "QA05/A03: nonlocal rejection disclosed in instruction, protocol and READMEs",
        "workspace/harbor_task/instruction.md; environment/public_eval/protocol.json; starter/solution README")
    add(findings, "public_contract_staged_import", staged_ok,
        "QA11/A03: exact staged import whitelist disclosed",
        "workspace/harbor_task/environment/public_eval/protocol.json:/implementation_boundary/staged_import_whitelist")
    add(findings, "guard_unchanged_contract", guard_ok,
        "public contract must match the actual AST/import guard",
        "workspace/harbor_task/tests/contract_guard.py")
    add(findings, "task_contract_live_execution", bool(guard.strip()),
        "text-only limits are insufficient; a guard implementation must exist",
        "workspace/harbor_task/tests/contract_guard.py")


def oracle_handoff(task: Path, findings: list[dict]) -> None:
    solve = task / "solution/solve.sh"
    assemble = task / "solution/assemble_dream_solution.sh"
    docker = task / "environment/Dockerfile"
    solve_text, assemble_text, docker_text = text(solve), text(assemble), text(docker)
    stages = "assemble_dream_solution.sh" in solve_text and solve_text.index("assemble_dream_solution.sh") < solve_text.index("exec bash")
    submitted = 'exec bash "${SOLUTION_DIR}/run.sh"' in solve_text
    copy_ok = all(token in assemble_text for token in ("cp -a", "predictor/__init__.py", "config", "train.py", "run.sh"))
    private = "COPY solution/" not in docker_text and "COPY reference/" not in docker_text
    add(findings, "oracle_handoff_source_before_training", stages and copy_ok and submitted,
        "0.5.6 H02: DREAM source, registry and config are staged into SOLUTION_DIR before training; run.sh executes from submitted dir",
        "workspace/harbor_task/solution/solve.sh; assemble_dream_solution.sh")
    add(findings, "oracle_private_reference_not_in_work", private,
        "private Oracle/Reference is not COPY'd into Agent Work image",
        "workspace/harbor_task/environment/Dockerfile")


def best_method_adapter(root: Path, task: Path, findings: list[dict]) -> None:
    best = root / "expert_evidence/best_method"
    data = best / "data.py"
    selection = root / "expert_evidence/best_method_selection.json"
    qa16 = root / "expert_evidence/qa16_best_method_revalidation.json"
    starter = task / "environment/starter/data.py"
    data_raw = text(data)
    starter_raw = text(starter)
    data_sha = sha256_file(data) if data.is_file() else ""
    starter_sha = sha256_file(starter) if starter.is_file() else ""
    ast_digest = ast_digest_like_guard(ast.parse(data_raw)) if data_raw else ""
    add(findings, "best_method_restored_starter_adapter", bool(data_raw) and data_raw == starter_raw and data_sha != BAD_BEST_METHOD_DATA_SHA,
        "0.5.6 H04: current best_method/data.py is byte-identical to active Starter frozen adapter",
        "expert_evidence/best_method/data.py; workspace/harbor_task/environment/starter/data.py")
    add(findings, "best_method_allowed_frozen_ast", ast_digest == ALLOWED_DATA_AST,
        "frozen adapter AST matches trusted contract_policy allowed digest",
        "expert_evidence/best_method/data.py")
    sel = jload(selection) if selection.is_file() else {}
    qa = jload(qa16) if qa16.is_file() else {}
    hashes_synced = sel.get("method_sha256", {}).get("data.py") == data_sha and qa.get("best_method_tree", {}).get("data.py") == data_sha
    scope_ok = sel.get("current_revalidation", {}).get("proves_current_frozen_gate") is False and qa.get("proves_current_frozen_gate") is False
    add(findings, "best_method_source_binding_synced", hashes_synced and scope_ok,
        "selection/revalidation hashes synchronized; old PUBLIC_DEV_ONLY 71.2 cannot prove current frozen gate",
        "expert_evidence/best_method_selection.json; qa16_best_method_revalidation.json")
    policy = task / "tests/contract_policy.json"
    policy_raw = text(policy)
    add(findings, "trusted_policy_not_loosened", bool(policy_raw) and '"frozen_ast"' in policy_raw,
        "trusted frozen policy remains present; repair must not widen it for bad adapter",
        "workspace/harbor_task/tests/contract_policy.json")


def provenance(root: Path, findings: list[dict]) -> None:
    prov = root / "optimization_evidence/EVIDENCE_PROVENANCE.md"
    binding = root / "optimization_evidence/formal_run_source_binding.json"
    br = root / "optimization_evidence/formal_test_scoring/br_results.json"
    raw = text(prov)
    ok = (
        prov.is_file() and binding.is_file() and br.is_file()
        and "bfe9f7fe73ad47365a504576804a5e86244eb74c2afbc547c30c640020325e29" in raw
        and "5c57129bddeb2ef8ff628b60ff42f780f350099cd8978dcf7cb010eff8382f63" in raw
        and "逐字节一致；`data.py`" not in raw
    )
    add(findings, "g03_role_source_binding", ok,
        "0.5.6 G03: role-specific source identity, raw B/R evidence, and withdrawn blanket claim",
        "optimization_evidence/EVIDENCE_PROVENANCE.md; formal_run_source_binding.json; br_results.json")


def legacy_conflicts(root: Path, findings: list[dict]) -> None:
    catalog = jload(REPO / "config/rule_versions.json")
    profile = catalog["profiles"][CURRENT_PROFILE]
    blockers = []
    if not any(x["topic"] == "hard_gate" and x["winner"] == "-10" for x in profile["conflict_resolution"]):
        blockers.append("hard_gate")
    if not any(x["topic"] == "NOP" and x["winner"] == "not restored" for x in profile["conflict_resolution"]):
        blockers.append("NOP")
    if not any(x["topic"] == "final_decision" and x["winner"] == "PASS/FAIL" for x in profile["conflict_resolution"]):
        blockers.append("final_decision")
    add(findings, "version_conflict_resolution", not blockers,
        "effective profile resolves -1/-10, docker_image, NOP, final decision and count conflicts",
        "config/rule_versions.json:" + CURRENT_PROFILE,
        blocking=True)
    add(findings, "platform_runtime_scope", True,
        "Docker/Harbor/Hidden execution and actual GPU/image size are platform_scope; static gate does not claim runtime proof",
        "config/rule_versions.json:platform-0.5.6-current.1-report.verification_scope",
        blocking=False)


def main() -> int:
    ap = argparse.ArgumentParser(description="Current-standard binary gate")
    ap.add_argument("--root", required=True, help="submission package tree root")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    task = root / "workspace/harbor_task"
    findings: list[dict] = []
    task_config(task, findings)
    reward_protocol(task, findings)
    public_contract(task, findings)
    oracle_handoff(task, findings)
    best_method_adapter(root, task, findings)
    provenance(root, findings)
    legacy_conflicts(root, findings)

    blocking = [f for f in findings if f["status"] == "fail"]
    scope = [f for f in findings if f["status"] == "platform_scope"]
    decision = "FAIL" if blocking else "PASS"
    report = {
        "schema": "current-standard-gate/1",
        "profile": CURRENT_PROFILE,
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
