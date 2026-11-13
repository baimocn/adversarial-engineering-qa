"""Positioned engineering observations and an INTERNAL semantic review worksheet.

No submitted code is executed or imported. Patterns describe reading locations,
never defects. The six groups reuse existing owners; they are not new check IDs
or a new expert delivery schema. Existing runtime evidence is optional at source
stage, but evidence actually cited by a completed review must be readable.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import unquote

import docker_paths
import evidence_refs
import harbor_review
try:
    import tomllib
except ImportError:
    tomllib = None

GROUPS = {
    "score_paths": ("H04",), "timeout_budget": ("H04",),
    "resource_alignment": ("QA15",), "controls_logs": ("QA05",),
    "score_scope": ("H04",), "delivery_lineage": ("QA21",),
}
RELATED = {"score_paths": ["QA06", "QA09", "F07", "B-S01", "B-S03"],
           "timeout_budget": ["QA15"], "resource_alignment": ["H03", "F06", "B-GPU"],
           "controls_logs": ["H03", "QA20"], "score_scope": ["CS04"], "delivery_lineage": ["T01", "T02"]}
BRANCHES = ("valid_candidate", "candidate_rejected", "trusted_failure", "interrupted")
EXCLUDED = {".git", "__pycache__", "node_modules", ".venv", "venv", "history", "historical",
            "archive", "archives", "docs", "reports", "report", "old", "backup"}
SOURCE_LIMIT = 512 * 1024
LOG_LIMIT = 256 * 1024
EVIDENCE_LIMIT = 4 * 1024 * 1024
TOTAL_LIMIT = 8 * 1024 * 1024
FILE_LIMIT = 2048
SCOPE_KEYS = {"scope", "eligibility", "eligible", "formal_adoption", "formally_eligible",
              "score_valid", "valid_for", "qc_coverage", "evaluation_scope", "formal_gate_eligible"}
LINEAGE_KEYS = {"trial_id", "selected_trial", "formal_trial", "qc_trial_id", "archive_sha256",
                "package_sha256", "candidate_sha256", "source_record_id", "superseded_by"}
TIMEOUT_KEYS = {"timeout", "timeout_sec", "timeout_seconds", "verifier_timeout_sec", "timeout_multiplier",
                "verifier_timeout_multiplier", "override_verifier_timeout_sec", "max_timeout_sec",
                "max_verifier_timeout_sec", "deadline", "kill_grace_seconds", "grace_period"}
RESOURCE_KEYS = {"gpus", "gpu_types", "gpu_type", "cpus", "device", "device_type", "docker_image",
                 "selected_type", "actual_type", "gpu_route", "cuda_visible_devices"}
GENERIC = {"pass", "passed", "ok", "reviewed", "complete", "completed", "通过", "无问题",
           "已检查", "不适用", "n/a", "not applicable", "none"}


def _safe(root, ref):
    path = Path(ref)
    if path.is_absolute():
        raise ValueError("reference must be relative to the inspected bundle")
    target = (root / path).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise ValueError("reference is not a file within the inspected bundle")
    return target


def _text(path, limit):
    # Bound reads even when stat races with a growing log. Never follow a FIFO.
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError(f"file exceeds the {limit}-byte read limit")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError(f"file exceeds the {limit}-byte read limit")
    return raw.decode("utf-8")


def _specific(value):
    return isinstance(value, str) and bool(value.strip()) and value.strip().lower().rstrip(".。") not in GENERIC


class _JSONLocator:
    """Locate a field in a large JSON stream without retaining unrelated values.

    This checks the selected location, not whole-file JSON validity or semantic
    support; the review's actual reader remains authoritative for those facts.
    """
    def __init__(self, stream):
        self.stream, self.buffer, self.index = stream, "", 0

    def peek(self):
        if self.index == len(self.buffer):
            self.buffer, self.index = self.stream.read(65536), 0
        return self.buffer[self.index:self.index + 1]

    def pop(self):
        value = self.peek()
        self.index += bool(value)
        return value

    def space(self):
        while self.peek() and self.peek().isspace():
            self.pop()

    def string(self, capture=False):
        if self.pop() != '"':
            raise ValueError("JSON object key is not a string")
        parts, escaped, oversized = ['"'], False, False
        while True:
            char = self.pop()
            if not char:
                raise ValueError("unterminated JSON string at evidence location")
            if capture and len(parts) < 65536:
                parts.append(char)
            elif capture:
                oversized = True
            if char == '"' and not escaped:
                break
            escaped = char == "\\" and not escaped
        return json.loads("".join(parts)) if capture and not oversized else None

    def skip(self):
        self.space()
        char = self.peek()
        if char == '"':
            self.string()
        elif char in ("{", "["):
            depth = 0
            while True:
                char = self.peek()
                if not char:
                    raise ValueError("unterminated JSON container before evidence location")
                if char == '"':
                    self.string()
                    continue
                self.pop()
                depth += int(char in "{[") - int(char in "}]")
                if depth == 0:
                    return
        else:
            while self.peek() and self.peek() not in ",]} \r\n\t":
                self.pop()

    def locate(self, tokens):
        self.space()
        if not tokens:
            return bool(self.peek())
        char = self.pop()
        if char == "{":
            self.space()
            if self.peek() == "}":
                return False
            while True:
                self.space()
                key = self.string(capture=True)
                self.space()
                if self.pop() != ":":
                    raise ValueError("missing JSON colon before evidence location")
                if key == tokens[0]:
                    return self.locate(tokens[1:])
                self.skip()
                self.space()
                delimiter = self.pop()
                if delimiter == "}":
                    return False
                if delimiter != ",":
                    raise ValueError("invalid JSON object before evidence location")
        elif char == "[" and re.fullmatch(r"0|[1-9]\d*", str(tokens[0])):
            wanted, index = int(tokens[0]), 0
            while True:
                self.space()
                if self.peek() == "]":
                    return False
                if index == wanted:
                    return self.locate(tokens[1:])
                self.skip()
                self.space()
                delimiter = self.pop()
                if delimiter == "]":
                    return False
                if delimiter != ",":
                    raise ValueError("invalid JSON array before evidence location")
                index += 1
        return False


def _resolve_evidence(root, ref):
    """Use the existing resolver, with bounded streaming for large locations."""
    try:
        return evidence_refs.resolve_ref(root, ref)
    except ValueError as exc:
        if "4 MiB inspection limit" not in str(exc):
            raise
    name, _, fragment = ref.partition("#")
    suffix = re.search(r":(-?\d+(?:--?\d+)?)$", name)
    line_fragment = suffix[1] if suffix else fragment if fragment.startswith("L") else None
    path = _safe(root, name[:suffix.start()] if suffix else name)
    if line_fragment is not None:
        location = re.fullmatch(r"L?(-?\d+)(?:-L?(-?\d+))?", line_fragment)
        if not location:
            raise ValueError("invalid evidence line location")
        start, end = int(location[1]), int(location[2] or location[1])
        if not 1 <= start <= end:
            raise ValueError("evidence line location out of bounds")
        lines, any_text, last = 0, False, ""
        with path.open(encoding="utf-8") as stream:
            while True:
                chunk = stream.read(65536)
                if not chunk:
                    break
                any_text, last = True, chunk[-1]
                lines += chunk.count("\n")
                if lines >= end:
                    return path
        if lines + int(any_text and last != "\n") < end:
            raise ValueError("evidence line location out of bounds")
        return path
    if fragment.startswith("/"):
        decoded = unquote(fragment)
        if re.search(r"~(?![01])", decoded):
            raise ValueError("invalid JSON Pointer escape")
        tokens = [token.replace("~1", "/").replace("~0", "~") for token in decoded[1:].split("/")]
    else:
        field = fragment[6:] if fragment.startswith("field=") else fragment[2:] if fragment.startswith("$.") else fragment
        tokens = evidence_refs._field_tokens(field)
    with path.open(encoding="utf-8") as stream:
        if not _JSONLocator(stream).locate(tokens):
            raise ValueError("JSON field location does not exist")
    return path


def _roles(config):
    cfg = config if isinstance(config, dict) else {}
    agent = cfg.get("environment", {})
    agent = agent if isinstance(agent, dict) else {}
    verifier = cfg.get("verifier", {})
    verifier = verifier if isinstance(verifier, dict) else {}
    venv = verifier.get("environment")
    return {"agent": agent, "verifier": venv if isinstance(venv, dict) else agent}


def _classify(path):
    name, suffix = path.name.lower(), path.suffix.lower()
    if suffix in {".py", ".sh", ".bash", ".toml", ".yaml", ".yml"} or name == "dockerfile":
        return "source"
    if suffix in {".log", ".txt"} and (suffix == ".log" or any(s in name for s in ("stdout", "stderr", "trial"))):
        return "log"
    if suffix == ".json" and any(s in name for s in ("receipt", "summary", "result", "run", "config", "qc", "lineage", "delivery")):
        return "metadata"
    return None


def _call_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _call_name(node.value) + "." + node.attr
    return "<expression>"


def _collect(root, task, config):
    observations, errors, cached = [], [], {}
    seen, total = 0, 0
    cfg_path = task / "task.toml"
    cfg_ref = cfg_path.relative_to(root).as_posix() if cfg_path.is_file() else None
    if cfg_ref:
        try:
            cached[cfg_ref] = _text(_safe(root, cfg_ref), SOURCE_LIMIT)
            total += len(cached[cfg_ref].encode("utf-8"))
            if config is None and tomllib:
                config = tomllib.loads(cached[cfg_ref])
            elif config is None:
                errors.append({"group": "resource_alignment", "path": cfg_ref, "error": "TOML parser unavailable; effective roles need review", "required": True})
        except (OSError, ValueError, UnicodeError) as exc:
            errors.append({"group": "score_paths", "path": cfg_ref, "error": str(exc),
                           "required": "read limit" not in str(exc), "observation_only": "read limit" in str(exc)})
    selection = docker_paths.image_selection(task, config)

    def add(kind, group, ref, line=None, excerpt="", **details):
        observations.append({"kind": kind, "group": group, "path": ref, "line": line,
                             "ref": f"{ref}:{line}" if line else ref,
                             "excerpt": excerpt[:360], "details": details})

    for role, env in _roles(config).items():
        add("selected_role_environment", "resource_alignment", cfg_ref, role=role,
            provenance="trusted supplied/parsed effective config; file reference is source context",
            environment=copy.deepcopy(env), image_selection=copy.deepcopy(selection) if role == "verifier" else
            {"source": "agent_image" if env.get("docker_image") else "agent_build", "image": env.get("docker_image")})

    for base, dirs, names in os.walk(task, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d.lower() not in EXCLUDED and not (Path(base) / d).is_symlink())
        for name in sorted(names):
            path = Path(base) / name
            kind = _classify(path)
            if not kind:
                continue
            relative = path.relative_to(root).as_posix()
            local = path.relative_to(task).as_posix()
            # A selected prebuilt image does not select a dormant Dockerfile.
            if (local == "environment/Dockerfile" and _roles(config)["agent"].get("docker_image")
                    or local == "tests/Dockerfile" and selection["source"] != "tests_dockerfile"):
                continue
            seen += 1
            if seen > FILE_LIMIT or total >= TOTAL_LIMIT:
                errors.append({"group": "score_paths", "path": relative, "error": "automatic observation budget reached; review the selected remaining sources", "required": False, "observation_only": True})
                return observations, errors, cached
            group = "controls_logs" if kind == "log" else "score_scope" if kind == "metadata" else "score_paths"
            try:
                target = _safe(root, relative)
                if relative in cached:
                    raw = cached[relative]
                else:
                    raw = _text(target, min(LOG_LIMIT if kind == "log" else SOURCE_LIMIT, TOTAL_LIMIT - total))
                    cached[relative] = raw
                    total += len(raw.encode("utf-8"))
            except (OSError, ValueError, UnicodeError) as exc:
                if kind == "metadata" and any(s in path.name.lower() for s in ("qc", "lineage", "delivery")):
                    group = "delivery_lineage"
                observational = kind == "metadata" or "read limit" in str(exc)
                errors.append({"group": group, "path": relative, "error": str(exc),
                               "required": not observational, "observation_only": observational,
                               "review_needed": True})
                continue
            lines = raw.splitlines()
            for number, line in enumerate(lines, 1):
                if kind == "source":
                    if re.search(r"reward\.(?:txt|json)", line) and re.search(r">|\bopen\s*\(|write|dump|replace|rename|unlink|\brm\b", line):
                        add("formal_reward_operation", "score_paths", relative, number, line,
                            note="Confirm formal versus temporary output, ordering and whether an interrupted run can be consumed.")
                    if re.search(r"timeout|setitimer|alarm\s*\(|kill-after|grace|deadline", line, re.I):
                        add("timeout_expression", "timeout_budget", relative, number, line,
                            note="Literal or expression only; effective override, timer scope and total wall-clock budget need semantic review.")
                    if re.search(r"\bgpus?\b|gpu_types|\bcpus\b|docker_image|^\s*FROM\b|cuda|nvidia|\.to\(['\"]|\.cuda\(", line, re.I):
                        add("resource_or_device_reference", "resource_alignment", relative, number, line)
                    if re.search(r"chmod\b.*?/dev/(?:nvidia|dri)|CUDA_VISIBLE_DEVICES|set\s+-[^\n]*e\b|\btrap\b", line):
                        add("control_or_cleanup", "controls_logs", relative, number, line,
                            note="A warning or a device keyword does not establish control failure or score invalidity.")
                elif kind == "log" and re.search(r"warn|error|fail|timeout|read.only|permission|denied|cuda|nvidia|reward|score|fallback|recover", line, re.I):
                    add("existing_log_event", "controls_logs", relative, number, line)
                if kind == "log" and re.search(r"\bgpu\b|\bdevice\b|\bH20\b|\bL20\b|cuda|nvidia", line, re.I):
                    add("existing_route_or_device_event", "resource_alignment", relative, number, line)
            if kind == "source" and path.suffix.lower() == ".py":
                try:
                    tree = ast.parse(raw, filename=relative)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.Try, getattr(ast, "TryStar", ast.Try))):
                            for handler in node.handlers:
                                names = {_call_name(n) for n in ast.walk(handler.type)} if handler.type else set()
                                if handler.type is None or names.intersection({"Exception", "BaseException", "builtins.Exception", "builtins.BaseException"}):
                                    calls = [{"call": _call_name(n.func), "ref": f"{relative}:{n.lineno}"}
                                             for child in node.body for n in ast.walk(child) if isinstance(n, ast.Call)][:40]
                                    add("broad_exception_region", "score_paths", relative, handler.lineno,
                                        lines[handler.lineno - 1], try_line=node.lineno,
                                        try_end_line=node.body[-1].end_lineno, calls=calls,
                                        note="Check candidate/trusted provenance; broad catch syntax itself is allowed.")
                except (SyntaxError, RecursionError, ValueError) as exc:
                    add("source_parse_limit", "score_paths", relative, excerpt=str(exc), note="Review raw source; parser failure is not a task defect.")
            if kind == "metadata":
                try:
                    data = json.loads(raw)
                except (ValueError, RecursionError) as exc:
                    if any(s in path.name.lower() for s in ("receipt", "qc", "lineage", "delivery")):
                        errors.append({"group": "delivery_lineage" if any(s in path.name.lower() for s in ("qc", "lineage", "delivery")) else "score_scope",
                                       "path": relative, "error": "automatically discovered metadata is not readable JSON: " + str(exc),
                                       "required": False, "observation_only": True, "review_needed": True})
                    continue  # The collector does not certify arbitrary runtime JSON.
                stack = [(data, "")]
                visited = 0
                while stack and visited < 5000:
                    node, pointer = stack.pop()
                    visited += 1
                    if isinstance(node, dict):
                        for key, value in node.items():
                            location = pointer + "/" + str(key).replace("~", "~0").replace("/", "~1")
                            group = ("score_scope" if key in SCOPE_KEYS else "delivery_lineage" if key in LINEAGE_KEYS else
                                     "timeout_budget" if key in TIMEOUT_KEYS else "resource_alignment" if key in RESOURCE_KEYS else None)
                            if group:
                                add({"score_scope": "existing_scope_field", "delivery_lineage": "existing_lineage_field",
                                     "timeout_budget": "existing_timeout_field", "resource_alignment": "existing_resource_field"}[group], group,
                                    relative, excerpt=str(value)[:300], pointer=location, value=value if not isinstance(value, (dict, list)) else "<container>")
                                observations[-1]["ref"] = relative + "#" + location
                            if isinstance(value, (dict, list)):
                                stack.append((value, location))
                    elif isinstance(node, list):
                        stack.extend((value, pointer + "/" + str(i)) for i, value in enumerate(node) if isinstance(value, (dict, list)))
    return observations, errors, cached


def collect(root, *, task_root=None, config=None):
    """Collect all six groups once, with bounded reads and exact source positions."""
    root = Path(root).resolve()
    task = root if task_root in (None, "", ".") else (root / task_root).resolve()
    if not task.is_relative_to(root) or not task.is_dir():
        raise ValueError("task_root must select a directory within the inspected bundle")
    observations, errors, _ = _collect(root, task, config)
    return {"observations": observations, "errors": [e for e in errors if not e.get("observation_only")],
            "collection_limitations": [e for e in errors if e.get("observation_only")], "executed_task": False}


def normalize_reward_run(root, row, *, stage="source"):
    """Reuse current AND historical native JSON-first reward reading; no penalty rule."""
    root = Path(root).resolve()
    if not isinstance(row, dict):
        raise ValueError("each reward run must be an internal reviewer object")
    refs = row.get("files", [])
    if not isinstance(refs, list) or not refs:
        raise ValueError("reward run must reference existing reward files")
    paths = [_safe(root, ref) for ref in refs]
    parents = {path.parent for path in paths if path.name in {"reward.json", "reward.txt"}}
    if len(parents) != 1:
        raise ValueError("one reward run must reference one execution output directory")
    # Explicit files are existing outputs even when auditing a source package.
    result = harbor_review.current_reward_contract(output_paths=paths,
        stage="history" if row.get("historical") else "runtime", main_score_key=row.get("main_score_key"))
    selected = Path(result["selected_file"]).relative_to(root).as_posix() if result.get("selected_file") else None
    findings = [{**f, "status": "unreviewed" if f["status"] == "manual" else f["status"],
                 "evidence": [Path(ref).relative_to(root).as_posix() for ref in f.get("evidence", [])]} for f in result["findings"]]
    return {**result, "status": "unreviewed" if result["status"] == "manual" else result["status"],
            "selected_file": selected, "selected_path": selected, "findings": findings, "audit_stage": stage}


def template():
    """Internal notes only: summaries may cite existing source, logs or metadata."""
    result = {name: {"summary": "", "evidence": [], "details": ""} for name in GROUPS}
    result["score_paths"]["branches"] = {name: {"summary": "", "evidence": [], "outcome": ""} for name in BRANCHES}
    result["score_scope"]["note"] = "Existing scope evidence only; absent receipt is nonblocking. has_score, score_valid and formal_adoption are separate claims."
    result["delivery_lineage"]["note"] = "Optional batch/ledger/QC binding; choose the formal Trial explicitly, not necessarily the newest."
    return result


def audit(root, review=None, *, task_root=None, config=None, stage="source"):
    root = Path(root).resolve()
    task = root if task_root in (None, "", ".") else (root / task_root).resolve()
    if not task.is_relative_to(root) or not task.is_dir():
        raise ValueError("task_root must select a directory within the inspected bundle")
    observations, errors, cache = _collect(root, task, config)
    checks = []
    claims = {"has_score": None, "score_valid": None, "formal_adoption": None, "qc_coverage": None,
              "reward_runs": [], "limitations": [], "delivery_affects_historical_score": False}
    if review is not None and not isinstance(review, dict):
        errors.append({"group": "score_paths", "error": "engineering_review must be an internal reviewer object", "required": True})
        review = None
    review = review or {}
    groups = review.get("groups", review)
    if not isinstance(groups, dict):
        groups = {}
        errors.append({"group": "score_paths", "error": "groups must be an object", "required": True})

    def refs(value, label):
        if not isinstance(value, list) or not value:
            raise ValueError(label + " needs existing evidence references")
        for ref in value:
            path = _resolve_evidence(root, ref)
            relative = path.relative_to(root).as_posix()
            if relative not in cache:
                # A size-limited automatic collector is not a claim that an
                # author artifact is missing. Completed semantic review cites
                # its existing reader; only explicit locations are checked here.
                cache[relative] = _text(path, EVIDENCE_LIMIT) if path.stat().st_size <= EVIDENCE_LIMIT else None
        return list(dict.fromkeys(value))

    for name, owners in GROUPS.items():
        local = [o for o in observations if o["group"] == name]
        row = {"name": name, "status": "unreviewed", "owner_ids": list(owners), "summary": "Await semantic review of existing materials.",
               "owner_id": owners[0], "related_checks": RELATED[name], "evidence": [], "problems": [],
               "advisories": [], "limitations": [], "observations": local,
               "affects_score_validity": name not in {"delivery_lineage"},
               "delivery_notes_only": name == "delivery_lineage",
               "review_complete": False,
               "required_for_static_completion": name not in {"score_scope", "delivery_lineage"} or bool(local) and name == "score_scope"}
        supplied = groups.get(name)
        existing_unobserved = any(e.get("group") == name and e.get("review_needed") for e in errors)
        if existing_unobserved and name == "score_scope":
            row["required_for_static_completion"] = True
        if supplied is None and name in {"score_scope", "delivery_lineage"} and not local and not existing_unobserved:
            row.update(status="not_applicable", review_complete=True, summary="No existing scope/lineage material selected; no new receipt or external ledger required.")
        elif supplied is not None:
            try:
                if not isinstance(supplied, dict):
                    raise ValueError(name + " must be an object")
                if not _specific(supplied.get("summary")):
                    raise ValueError(name + " needs an actual review summary, not a generic pass")
                row["summary"] = supplied["summary"]
                if supplied.get("status") in {"manual", "unreviewed", "review", "incomplete"}:
                    raise ValueError(name + " is explicitly unreviewed")
                if supplied.get("status") not in {None, "pass", "fail", "not_applicable", "evidence_limited", "advisory", "warn"}:
                    raise ValueError(name + " has an unsupported internal review status")
                optional_absent = name in {"score_scope", "delivery_lineage"} and not local and supplied.get("status") == "not_applicable"
                row["evidence"] = refs(supplied.get("evidence"), name) if not optional_absent or supplied.get("evidence") else []
                row["details"] = copy.deepcopy(supplied.get("details", ""))
                if name == "score_paths":
                    branches = supplied.get("branches", {})
                    if not isinstance(branches, dict):
                        raise ValueError("score_paths.branches must be an object")
                    # A completed PASS covers all four outcomes. A reviewer who
                    # has read the available source may instead document that
                    # the selected entry/wrapper is missing; this is a material
                    # limitation, not an unfilled internal worksheet.
                    needed = BRANCHES if supplied.get("status") != "evidence_limited" or branches else ()
                    for branch in needed:
                        actual = branches.get(branch)
                        if (not isinstance(actual, dict) or not _specific(actual.get("summary"))
                                or not isinstance(actual.get("outcome"), (str, dict)) or not actual["outcome"]):
                            raise ValueError("score_paths requires actual summary/evidence/outcome for " + branch)
                        row["evidence"].extend(refs(actual.get("evidence"), "score_paths." + branch))
                    row["branches"] = copy.deepcopy(branches)
                findings = supplied.get("findings", [])
                if not isinstance(findings, list):
                    raise ValueError(name + ".findings must be an array")
                for finding in findings:
                    if (not isinstance(finding, dict) or not _specific(finding.get("reason"))
                            or not _specific(finding.get("remediation")) or finding.get("owner_id") not in owners):
                        raise ValueError(name + " findings need a precise reason, remediation and an existing group owner_id")
                    evidence = refs(finding.get("evidence"), name + ".finding")
                    if not all(re.search(r"(?::\d+(?:-\d+)?|#(?:L\d|/|field=|\$\.))", ref) for ref in evidence):
                        raise ValueError(name + " findings require positioned evidence, not a bare filename")
                    digest = hashlib.sha256(json.dumps([name, finding["reason"], evidence], ensure_ascii=False).encode()).hexdigest()[:12]
                    supplied_code = finding.get("code", finding.get("key"))
                    normalized = {**finding, "code": supplied_code if isinstance(supplied_code, str) and supplied_code.strip() else f"engineering.{name}.{digest}",
                                  "evidence": evidence, "owner_id": owners[0], "related_checks": RELATED[name]}
                    advisory = (finding.get("blocking") is False or supplied.get("status") in {"advisory", "warn"}
                                or finding.get("severity") in {"advisory", "nonblocking", "info", "warn"})
                    if name == "delivery_lineage":
                        advisory = True  # Batch/QC bookkeeping never negates an existing Harbor score.
                    normalized["blocking"] = not advisory
                    row["advisories" if advisory else "problems"].append(normalized)
                if supplied.get("status") == "fail" and not row["problems"] and not row["advisories"]:
                    raise ValueError(name + " cannot fail without an evidenced concrete finding")
                row["status"] = ("fail" if row["problems"] else "not_applicable" if optional_absent else
                                 "evidence_limited" if supplied.get("status") == "evidence_limited" else "pass")
                row["review_complete"] = True
                row["evidence"] = list(dict.fromkeys(row["evidence"]))
                if name == "score_scope":
                    for key in ("score_valid", "formal_adoption", "qc_coverage"):
                        if key in supplied:
                            if key != "qc_coverage" and supplied[key] is not None and not isinstance(supplied[key], bool):
                                raise ValueError("score_scope." + key + " must be boolean or unknown")
                            claims[key] = supplied[key]
                if name == "delivery_lineage":
                    claims["delivery_lineage"] = {"status": row["status"], "summary": row["summary"], "details": row["details"]}
            except (OSError, ValueError, UnicodeError, TypeError) as exc:
                row["status"] = "fail" if row["problems"] else "unreviewed"
                row["review_complete"] = False
                row["limitations"].append(str(exc))
                errors.append({"group": name, "error": str(exc), "required": True})
        for error in errors:
            if error.get("group") == name:
                row["limitations"].append(error.get("path", "") + ": " + error["error"])
                if error.get("required"):
                    row["status"] = "fail" if row["problems"] else "unreviewed"
                    row["review_complete"] = False
                    if name != "delivery_lineage":
                        row["required_for_static_completion"] = True
        row["limitations"] = list(dict.fromkeys(row["limitations"]))
        if name == "score_scope" and not row["review_complete"]:
            claims.update(score_valid=None, formal_adoption=None, qc_coverage=None)
        if name == "delivery_lineage" and "delivery_lineage" in claims:
            claims["delivery_lineage"]["status"] = row["status"]
        checks.append(row)

    runs = review.get("reward_runs", groups.get("score_scope", {}).get("reward_runs", []) if isinstance(groups.get("score_scope"), dict) else [])
    run_errors = []
    if isinstance(runs, list):
        for index, run in enumerate(runs):
            try:
                claims["reward_runs"].append(normalize_reward_run(root, run, stage=stage))
            except (OSError, ValueError, TypeError, UnicodeError) as exc:
                run_errors.append(f"reward_runs[{index}]: {exc}")
        if runs and not run_errors:
            claims["has_score"] = any(r.get("main_score") is not None for r in claims["reward_runs"])
    else:
        run_errors.append("reward_runs must be an array of existing outputs")
    if (runs and not run_errors and claims['has_score'] is False
            and (claims['score_valid'] is True or claims['formal_adoption'] is True)):
        run_errors.append('Explicitly selected outputs have no parseable main score; score_valid/formal_adoption cannot be asserted true')
    if run_errors:
        # A broken internal selection cannot establish that a task had no score.
        # Retain readable run facts while withholding aggregate scope claims.
        claims.update(has_score=None, score_valid=None, formal_adoption=None, qc_coverage=None)
        claims["limitations"].extend(run_errors)
        score_scope = next(row for row in checks if row["name"] == "score_scope")
        score_scope.update(status="fail" if score_scope["problems"] else "unreviewed",
                           review_complete=False, required_for_static_completion=True)
        score_scope["limitations"].extend(run_errors)
        errors.extend({"group": "score_scope", "error": message, "required": True,
                       "kind": "internal_review_selection"} for message in run_errors)
    return {"executed_task": False, "stage": stage, "observations": observations, "checks": checks,
            "template": template(), "errors": [e for e in errors if not e.get("observation_only")],
            "collection_limitations": [e for e in errors if e.get("observation_only")], "claims": claims}
