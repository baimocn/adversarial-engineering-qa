"""Read-only checks for the current delivery standard, without executing task code.

The optional review object is an INTERNAL reviewer worksheet: it points at existing
materials, not a new author submission format. Facts are read from those sources;
no field named ``pass``/``status`` can replace an observed contradictory fact.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import harbor_review

CHECKS = (
    ("CS03", "正式reward输出兼容读取"),
    ("CS04", "正式主分数可识别"),
    ("CS05", "指定退出场景Solver主Agent响应超过50轮"),
)
CHECK_TITLES = dict(CHECKS)
EXCLUDED_PARTS = {".git", "__pycache__", "history", "historical", "archive", "archives", "docs", "reports", "report", "expert_evidence", "evidence"}
AUTOMATIC_EXIT = {"auto_submit", "auto-submission", "automatic_submission", "automatic_submit", "timeout", "timed_out", "time_limit", "time_limit_exceeded", "超时", "自动交卷"}
NORMAL_EXIT = {"completed", "complete", "success", "normal", "manual_submit", "agent_done", "finished", "正常结束", "主动交卷"}
MAIN_AGENTS = {"main", "main_agent", "primary", "root"}
QA_AGENTS = {"qa", "qaagent", "qualityassurance", "qualityassuranceagent"}
TOOL_EVENTS = {"tool", "tool_result", "tool_call", "function_call", "function_call_output", "tool_use"}
MAX_TEXT_BYTES = 32 * 1024 * 1024


def template():
    return {
        "reward_runs": [],
        "agent_runs": [],
        "note": "内部底稿；按现有文件实际结构填来源路径和JSON路径，不要求专家新增同名文件，不接受手填pass。",
    }


def _finite(value):
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def _path(root, relative):
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError("source path must be a non-empty relative path")
    ref = Path(relative)
    if ref.is_absolute() or ".." in ref.parts:
        raise ValueError("source path must stay within the inspected root")
    result = (root / ref).resolve()
    if not result.is_relative_to(root.resolve()) or not result.is_file():
        raise ValueError(f"source file missing or outside root: {relative}")
    return result


def _read(root, relative):
    path = _path(root, relative)
    if path.stat().st_size > MAX_TEXT_BYTES:
        raise ValueError(f"source exceeds {MAX_TEXT_BYTES} bytes; inspect with a streaming source adapter: {relative}")
    return path.read_text(encoding="utf-8")


def _json(root, relative):
    return json.loads(_read(root, relative))


def _at(value, pointer):
    if pointer is None:
        return value
    if not isinstance(pointer, list):
        raise ValueError("JSON source selectors must be lists of existing object keys / array indices")
    for key in pointer:
        if isinstance(value, list) and isinstance(key, int) and not isinstance(key, bool):
            value = value[key]
        elif isinstance(value, dict) and isinstance(key, str):
            value = value[key]
        else:
            raise ValueError("JSON selector does not address an existing value")
    return value


def _item(code, title):
    return {"id": code, "title": title, "status": "review", "problems": [], "limitations": [], "evidence": [], "observations": [], "responsibility": "reviewer", "required_for_static_completion": True, "applicability": "current_materials"}


def _done(item, *, applicable=True):
    item["evidence"] = sorted(set(item["evidence"]))
    item["status"] = "fail" if item["problems"] else "review" if item["limitations"] else "pass" if applicable else "not_applicable"
    return item


def _source_files(root, files):
    relative = files if files is not None else [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and not p.is_symlink()]
    return sorted(set(str(f) for f in relative if isinstance(f, (str, Path))))


def _is_current(path):
    return not EXCLUDED_PARTS.intersection(part.lower() for part in Path(path).parts)


def _reward_files(root, review, stage):
    rows = review.get("reward_runs", [])
    if not isinstance(rows, list):
        return [], ["reward_runs内部底稿必须为数组"]
    parsed, errors = [], []
    for row in rows:
        try:
            if not isinstance(row, dict):
                raise ValueError("reward_runs条目须指向已有评分记录")
            paths = row.get("files", [])
            if not isinstance(paths, list) or not paths:
                raise ValueError("reward_runs须指出同次评分已有输出文件")
            for ref in paths:
                _path(root, ref)
            parents = {str(Path(ref).parent) for ref in paths}
            if len(parents) != 1:
                raise ValueError("同次reward文件须在同一评分输出目录；不能把不同Trial拼为双文件")
            historical = row.get("historical", stage == "history")
            if not isinstance(historical, bool):
                raise ValueError("historical需为布尔值，不能以字符串false伪装历史范围")
            parsed.append({**row, "history": historical})
        except (ValueError, TypeError, OSError) as exc:
            errors.append(str(exc))
    return parsed, errors


def _reward_checks(root, files, config, review, stage):
    contract, score = _item("CS03", CHECK_TITLES["CS03"]), _item("CS04", CHECK_TITLES["CS04"])
    runs, errors = _reward_files(root, review, stage)
    contract["limitations"].extend(errors); score["limitations"].extend(errors)
    for row in runs:
        refs = row["files"]
        names = {Path(ref).name for ref in refs}
        double = {"reward.txt", "reward.json"}.issubset(names)
        for item in (contract, score):
            item["evidence"].extend(refs)
            item["observations"].append({"run": row.get("run_id"), "files": refs, "historical": row["history"]})
        if double:
            contract["observations"].append({"dual_output": refs, "selected_file": "reward.json", "policy": "当前及历史均兼容双文件，JSON优先；不因双文件本身要求重跑"})
        if not ({"reward.txt", "reward.json"} & names):
            contract["problems" if not row["history"] else "limitations"].append("所选记录没有原生reward.txt或reward.json；核对实际正式输出/adapter")
        contract_result = harbor_review.current_reward_contract(
            output_paths=[_path(root, ref) for ref in refs],
            stage="history" if row["history"] else "runtime",
        )
        contract["observations"].append({"native_contract": contract_result})
        for finding in contract_result["findings"]:
            target = score if finding["code"] in ("main_reward_unresolved", "reward_output_invalid") else contract
            if finding["status"] == "fail":
                target["problems" if not row["history"] else "limitations"].append(finding["message"])
            elif finding["status"] == "manual" and finding["code"] != "main_reward_unresolved":
                target["limitations"].append(finding["message"])
        for ref in refs:
            if double and Path(ref).name != "reward.json":
                continue
            try:
                if Path(ref).name == "reward.txt":
                    value = float(_read(root, ref).strip())
                    if not math.isfinite(value):
                        raise ValueError("reward.txt不是有限数值主分")
                elif Path(ref).name == "reward.json":
                    data = _json(root, ref)
                    if not isinstance(data, dict):
                        raise ValueError("reward.json不是JSON对象")
                    if "reward" in data:
                        if not _finite(data["reward"]):
                            raise ValueError("reward字段不是有限数值")
                    else:
                        numeric = {key: val for key, val in data.items() if _finite(val)}
                        mapping = row.get("score_mapping")
                        if len(numeric) == 1:
                            score["observations"].append({"path": ref, "identifiable_main_score": next(iter(numeric)), "policy": "当前及历史唯一有限指标按原读取规则兼容，不要求新增reward键或读取凭据"})
                        elif isinstance(mapping, dict):
                            key = mapping.get("key")
                            reader = mapping.get("reader_source")
                            reader_text = _read(root, reader)
                            evidence = mapping.get("runtime_evidence")
                            if key not in numeric or not re.search(r"['\"]" + re.escape(str(key)) + r"['\"]", reader_text):
                                raise ValueError("主分映射与已有输出或读取实现不对应")
                            score["evidence"].append(reader)
                            # Existing source or log chains are enough; this is
                            # not a requirement for a newly shaped JSON receipt.
                            bound = Path(ref).name in reader_text
                            refs = [evidence] if isinstance(evidence, str) else evidence or []
                            if not isinstance(refs, list):
                                raise ValueError("已有读取依据须为来源路径或路径数组")
                            for evidence_ref in refs:
                                evidence_text = _read(root, evidence_ref)
                                score["evidence"].append(evidence_ref)
                                try:
                                    receipt = json.loads(evidence_text)
                                except ValueError:
                                    receipt = None
                                if isinstance(receipt, dict) and {"source_reward", "score_key", "reward"} <= receipt.keys():
                                    if (receipt["source_reward"] != ref or receipt["score_key"] != key
                                            or not _finite(receipt["reward"]) or receipt["reward"] != numeric[key]):
                                        raise ValueError("既有实际读取记录与主分映射不一致")
                                    bound = True
                                elif Path(ref).name in evidence_text and str(key) in evidence_text:
                                    bound = True
                            if not bound:
                                score["limitations"].append(f"{ref}: 已定位{key}读取实现；尚需结合既有调用链确认实际使用，不接受手填adapter通过")
                                if stage == "source":
                                    score.setdefault("platform_pending_limitations", []).append(score["limitations"][-1])
                                    score["required_for_static_completion"] = False
                                    score["responsibility"] = "platform"
                                    score["applicability"] = "source_score_mapping_runtime_binding_pending"
                            else:
                                score["observations"].append({"path": ref, "identifiable_main_score": key,
                                    "policy": "已有读取源码/日志对应选定reward及指标；不要求新增固定JSON回执"})
                        elif numeric:
                            score["limitations"].append(f"{ref}: 多指标尚未明确主分及实际adapter读取对应，需读现有链路后判断")
                        else:
                            raise ValueError("输出无可识别有限数值主分")
            except (ValueError, OSError, TypeError, UnicodeError) as exc:
                score["problems" if not row["history"] else "limitations"].append(f"{ref}: {exc}")
    if not runs:
        # Source occurrences are not proof of same-execution writes: rm -f both is normal.
        writers = []
        for ref in files:
            if not _is_current(ref) or Path(ref).suffix not in (".py", ".sh"):
                continue
            try:
                text = _read(root, ref)
            except (ValueError, OSError, UnicodeError):
                continue
            output_names = sorted(set(re.findall(r"(?:[>]|write_text\s*\(|open\s*\()[^\n]{0,180}?(reward\.(?:json|txt))", text)))
            if output_names:
                writers.append({"path": ref, "possible_outputs": output_names})
        contract["observations"].extend(writers)
        contract["limitations"].append("静态检查尚无同次正式输出；源码仅提到两个文件不能证明同时写入，清理旧文件也不是违规")
        score["limitations"].append("尚无选定当前正式reward或实际读取链，不能以任意数值JSON自动宣称主分通过")
    if runs and stage == "source" and any(message not in score.get("platform_pending_limitations", []) for message in score["limitations"]):
        score["required_for_static_completion"] = True
        score["responsibility"] = "reviewer"
        score["applicability"] = "provided_materials_require_review"
    if not runs and not errors and stage == "source":
        for item in (contract, score):
            item["required_for_static_completion"] = False
            item["applicability"] = "runtime_output_not_yet_available"
    return _done(contract), _done(score)


def _session_data(root, relative):
    if Path(relative).suffix.lower() not in (".jsonl", ".ndjson"):
        return _json(root, relative)
    responses, metadata, complete, unknown_response_events = [], {}, False, False
    with _path(root, relative).open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError(f"会话JSONL第{number}行不是对象")
            kind = event.get("type")
            payload = event.get("payload", event)
            if not isinstance(payload, dict):
                continue
            if kind in ("session_meta", "session_start"):
                metadata.update({key: payload[key] for key in ("agent_role", "agent_type", "agent_id", "agent_name") if key in payload})
            elif kind in ("llm_response", "model_response"):
                if str(payload.get("type", "")).lower() in TOOL_EVENTS:
                    unknown_response_events = True
                else:
                    responses.append({**payload, "type": kind})
            elif kind in ("session_end", "session_complete") and payload.get("complete") is True:
                complete = True
            elif kind in ("response_item", "assistant_message"):
                # Native event blocks need response grouping; do not count calls/messages as separate LLM completions.
                unknown_response_events = True
    return {**metadata, "responses": responses,
            "complete": complete and not unknown_response_events,
            "parser_note": "JSONL只计一次一条的llm_response/model_response事件，原生块需保留实际response分组"}


def _exit_reason(data):
    if isinstance(data, dict):
        for key in ("exit_reason", "termination_reason", "stop_reason"):
            if isinstance(data.get(key), str):
                return data[key].strip().lower()
        if str(data.get("status", "")).lower() in AUTOMATIC_EXIT:
            return str(data["status"]).lower()
    return None


def _is_qa_agent(data):
    """Use explicit existing scope metadata; QA review traces are not Solver runs."""
    if not isinstance(data, dict):
        return False
    return any(re.sub(r"[\s_-]+", "", str(data.get(key, "")).lower()) in QA_AGENTS
               for key in ("agent_role", "agent_type", "agent_name", "agent_id"))


def _selected_qa_scope(data, pointer):
    """A selector cannot discard an explicit QA scope on any parent object."""
    if _is_qa_agent(data):
        return True
    if pointer is None:
        return False
    if not isinstance(pointer, list):
        raise ValueError("JSON source selectors must be lists of existing object keys / array indices")
    for key in pointer:
        data = _at(data, [key])
        if _is_qa_agent(data):
            return True
    return False


def _response_count(data, *, selected_main=False):
    """Known response/message exports only; experiment rounds and tool counters are never counted."""
    container = data
    if isinstance(data, dict):
        if _is_qa_agent(data):
            raise ValueError("选中的会话声明为QA-Agent，不能作为Solver主Agent响应记录")
        explicit_agent = data.get("agent_role", data.get("agent_type"))
        main_identity = data.get("agent_id")
        if explicit_agent is not None and str(explicit_agent).lower() not in MAIN_AGENTS:
            raise ValueError("选中的会话声明为子Agent，不能作为主Agent轮数")
        selected_main = selected_main or str(explicit_agent).lower() in MAIN_AGENTS or str(main_identity).lower() in MAIN_AGENTS
        if isinstance(data.get("responses"), list):
            container = data["responses"]
            kind = "responses"
        elif isinstance(data.get("messages"), list):
            container = data["messages"]
            kind = "messages"
        else:
            raise ValueError("会话不是已识别的responses/messages记录；不能用rounds或tool_calls替代")
    else:
        kind = "messages"
        main_identity = None
    if not selected_main:
        raise ValueError("尚未由会话元数据或现有主会话对应依据确认main范围")
    if not isinstance(container, list):
        raise ValueError("会话记录不是数组")
    count, seen = 0, set()
    for message in container:
        if not isinstance(message, dict):
            raise ValueError("会话记录含非对象条目")
        if _is_qa_agent(message):
            continue
        role_scope = message.get("agent_role", message.get("agent_type"))
        identity = message.get("agent_id")
        if role_scope is not None and str(role_scope).lower() not in MAIN_AGENTS:
            continue
        if identity is not None and str(identity).lower() not in MAIN_AGENTS and identity != main_identity:
            continue
        role = str(message.get("role", "")).lower()
        if role in {"tool", "function", "user", "system", "developer"} or str(message.get("type", "")).lower() in TOOL_EVENTS:
            continue
        if kind == "responses":
            recognized = (role == "assistant" or message.get("type") in ("llm_response", "model_response", "response")
                          or isinstance(message.get("choices"), list) or isinstance(message.get("output"), list))
            if not recognized:
                raise ValueError("responses数组条目不是可识别的模型响应，不能按数组长度计数")
        elif role != "assistant":
            continue
        response_id = message.get("response_id")
        if response_id is None:
            response_id = message.get("completion_id")
        if response_id is None:
            # Native full completion exports use id (Responses/Chat Completions).
            response_id = message.get("id")
        if response_id is not None:
            if not isinstance(response_id, (str, int)) or isinstance(response_id, bool):
                raise ValueError("response identity不是可识别的字符串或整数，需按现有记录核对分组")
            if response_id in seen:
                continue
            seen.add(response_id)
        count += 1
    return count


def _turns(root, review, stage, files):
    item = _item("CS05", CHECK_TITLES["CS05"])
    runs = list(review.get("agent_runs", [])) if isinstance(review.get("agent_runs", []), list) else None
    invalid_run_list = runs is None
    if not isinstance(runs, list):
        item["limitations"].append("agent_runs内部底稿必须为数组"); runs = []
    known = {r.get("result_source") for r in runs if isinstance(r, dict)}
    detected = []
    for ref in files:
        name = Path(ref).name.lower()
        if Path(ref).suffix != ".json" or not (name.startswith(("trajectory", "session")) or name in ("agent_result.json", "result.json")):
            continue
        try:
            document = _json(root, ref)
            path = []
            agent_result = document
            if name == "result.json":
                if not isinstance(document, dict) or not isinstance(document.get("agent_result"), dict):
                    continue
                agent_result = document["agent_result"]; path = ["agent_result"]
            reason = _exit_reason(agent_result)
            if reason is None or ref in known or _is_qa_agent(document) or _is_qa_agent(agent_result):
                continue
            detected.append({"result_source": ref, "result_path": path,
                             "session_source": agent_result.get("main_session_source") if isinstance(agent_result, dict) else None})
        except (ValueError, OSError, UnicodeError, TypeError):
            continue  # Existing core QA owns unrelated JSON validity; never infer a model run from its name.
    runs.extend(detected)
    applicable = False
    if not runs:
        item["limitations"].append("未定位适用的退出原因及主Agent实际会话；不新增专家轨迹字段要求，不能以实验轮数代替")
    for row in runs:
        try:
            result_ref = row["result_source"]
            result_document = _json(root, result_ref)
            if _selected_qa_scope(result_document, row.get("result_path", [])):
                raise ValueError("已有结果属于QA-Agent审阅，不能作为Solver退出/响应记录")
            result = _at(result_document, row.get("result_path", []))
            reason = _exit_reason(result)
            item["evidence"].append(result_ref)
            if reason is None:
                raise ValueError("现有结果未识别退出原因；不能用手填场景覆盖来源")
            if reason in NORMAL_EXIT:
                item["observations"].append({"run": row.get("run_id"), "exit_reason": reason, "applicable": False})
                continue
            if reason not in AUTOMATIC_EXIT:
                raise ValueError(f"退出场景{reason!r}不明确，需按现有日志核对是否自动交卷/超时")
            applicable = True
            session_ref = row["session_source"]
            session_document = _session_data(root, session_ref)
            if _selected_qa_scope(session_document, row.get("session_path", [])):
                raise ValueError("选中的会话属于QA-Agent，不能作为Solver主Agent响应记录")
            session = _at(session_document, row.get("session_path", []))
            selected_main = False
            if row.get("main_scope_source"):
                scope_ref = row["main_scope_source"]
                scope_document = _json(root, scope_ref)
                scope = _at(scope_document, row.get("main_scope_path", []))
                if not isinstance(scope, dict) or _selected_qa_scope(scope_document, row.get("main_scope_path", [])) or scope.get("session_source") != session_ref or str(scope.get("agent_role", "")).lower() not in MAIN_AGENTS:
                    raise ValueError("现有主会话映射与所选session不符")
                item["evidence"].append(scope_ref); selected_main = True
            count = _response_count(session, selected_main=selected_main)
            item["evidence"].append(session_ref)
            item["observations"].append({"run": row.get("run_id"), "exit_reason": reason, "main_llm_responses": count, "applicable": True})
            complete = isinstance(session, dict) and session.get("complete") is True
            complete = complete or (isinstance(result, dict) and result.get("main_session_complete") is True)
            if count <= 50 and complete:
                item["problems"].append(f"{row.get('run_id', session_ref)}: {reason}场景完整主会话LLM responses={count}，未超过50")
            elif count <= 50:
                item["limitations"].append(f"{session_ref}: 已读{count}次响应但会话完整性尚未确认，不据片段断言未超过50，也不自动通过")
        except (KeyError, IndexError, TypeError, ValueError, OSError, UnicodeError) as exc:
            item["limitations"].append(str(exc))
    if not runs and not invalid_run_list and stage == "source":
        item["required_for_static_completion"] = False
        item["responsibility"] = "platform"
        item["applicability"] = "no_current_agent_run_in_source_delivery"
    elif not applicable and not item["limitations"]:
        item["applicability"] = "not_automatic_submission_or_timeout"
    return _done(item, applicable=applicable)


def collect(root, files=None, config=None, stage="source"):
    root = Path(root).resolve()
    if stage not in ("source", "runtime", "history"):
        raise ValueError("stage must be source/runtime/history")
    return {"root": str(root), "files": _source_files(root, files), "config": config or {}, "stage": stage}


def apply_review(current, review=None, root=None, validate_evidence=None):
    """The extra validate_evidence argument is accepted for compatibility with old helpers."""
    data = review if isinstance(review, dict) else {}
    inspected_root = Path(root or current["root"]).resolve()
    config, files, stage = current["config"], current["files"], current["stage"]
    rows = list(_reward_checks(inspected_root, files, config, data, stage))
    rows.append(_turns(inspected_root, data, stage, files))
    status = "fail" if any(r["status"] == "fail" for r in rows) else "review" if any(r["status"] == "review" for r in rows) else "pass"
    return {"status": status, "stage": stage, "checks": rows, "summary": "只读来源核对；review表示检查范围限制，不能直接换算为fail或已实跑通过。", "executed_task": False}


def audit(root, files=None, config=None, review=None, stage="source"):
    return apply_review(collect(root, files, config, stage), review)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--config", type=Path, help="optional already-parsed task config JSON; task code is never imported")
    parser.add_argument("--stage", choices=("source", "runtime", "history"), default="source")
    args = parser.parse_args()
    review = json.loads(args.review.read_text()) if args.review else None
    config = json.loads(args.config.read_text()) if args.config else None
    result = audit(args.root, config=config, review=review, stage=args.stage)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
