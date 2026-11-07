#!/usr/bin/env python3
"""交付契约机械检查（D-C01–D-C04，v2.5）。

★ 来源与版本

  D-C01/D-C02（2026-11-06 引入）：Harbor 1074 题复盘——评分文件缺失 72 题、
  评分资产/锚点不一致 2 题。2604/1841 实测精确复现。

  D-C03/D-C04（2026-11-07 引入）：unified-qa v0.5.0「所有题统一四项协议」中
  可静态判定的两项——
  D-C03 reward 二选一：同次正式评分只输出 reward.json 或 reward.txt 一种
        （"不拼不同 Trial/seed 制造双文件冲突"）。同一评分链同时写两种
        正式 reward 文件 = 违反 L0 协议。诊断文件（result.json/日志）不算。
  D-C04 Oracle 规范入口：harbor_task/solution/solve.sh 必须存在
        （容器侧 /solution/solve.sh），调用 solution/ 内参考实现生成提交物；
        Oracle 材料不得被 COPY 进 Agent 可见镜像（私有边界）。

  其余两项协议（依赖锁定、hard gate −10）需语义/运行判断，不在本脚本。

用法：
  python scripts/check_delivery_contract.py --root <提交包根> --out <out>/delivery-contract.json

退出码：0 = 无 blocking；1 = 有 blocking；2 = 用法错误。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

SKIP_DIRS = {"__pycache__", ".git", ".hg", ".svn", "node_modules",
             ".venv", "venv", ".mypy_cache", ".pytest_cache", ".tox"}
SHA_RE = re.compile(r"^[0-9a-fA-F]{64}$")
PATHISH_RE = re.compile(r"(/|\\|\.[A-Za-z0-9]{1,8}$)")
REWARD_LIKE = re.compile(r"(/|\\|\b)[A-Za-z0-9_./\\-]*(reward|verifier)[A-Za-z0-9_./\\-]*")
# ★ 2026-11-07 误报修正（qa_batch_v2 交叉审计发现）：清单里的 revision_log/history
#   区块保存的是"实名刷新记录"（old_declared/old_actual/previous 等），其键形如
#   tests/grader.py 且带旧哈希——把它们当"当前声明"采进来会产生假失配。
#   这些键名命中历史模式时整棵子树跳过。
HISTORY_KEY_RE = re.compile(
    r"revision_log|revision_history|history|old_declared|old_actual|old_value|"
    r"previous|legacy|archived|superseded|_old$|_prev$", re.I)


def iter_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            yield Path(dirpath) / fn


def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def rel(root: Path, p: Path) -> str:
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(p)


def find_task_toml(root: Path):
    best = None
    for p in iter_files(root):
        if p.name == "task.toml":
            if best is None or len(p.parts) < len(best.parts):
                best = p
    return best


def parse_toml(text: str):
    try:
        import tomllib
        return tomllib.loads(text)
    except Exception:
        return None


# ────────────────────────── D-C01：reward 落点 ──────────────────────────

def check_reward_path(root: Path, task_toml: Path | None):
    """task.toml 声明的 reward_file 必须能在 tests/ 的写入链里找到。"""
    findings = []
    if task_toml is None:
        return "needs_manual", [{"severity": "needs_manual", "file": "workspace/harbor_task/task.toml",
                                 "line": 0, "detail": "D-C01：无 task.toml 可查（前置缺失）"}]
    text = read_text(task_toml)
    declared = None
    data = parse_toml(text)
    if isinstance(data, dict):
        v = data.get("reward_file")
        if v is None and isinstance(data.get("verifier"), dict):
            v = data["verifier"].get("reward_file")
        if isinstance(v, str) and v.strip():
            declared = v.strip()
    if declared is None:
        m = re.search(r"^\s*reward_file\s*=\s*['\"]([^'\"]+)['\"]", text, re.M)
        if m:
            declared = m.group(1).strip()
    if not declared:
        return "not_applicable", [{"severity": "informational", "file": rel(root, task_toml),
                                   "line": 0, "detail": "D-C01：task.toml 未声明 reward_file——"
                                                         "按平台默认语义处理，本项不适用"}]

    # 在 tests/ 的文本里找声明路径（含目录拼接写法，如 $REWARD_DIR/reward.txt）
    tests_dir = task_toml.parent / "tests"
    scan_files = [p for p in iter_files(tests_dir)] if tests_dir.is_dir() else []
    referenced = []
    referenced_dir = []
    reward_like = []
    declared_dir = str(Path(declared.replace("\\", "/")).parent).replace("\\", "/")
    for p in scan_files:
        if p.suffix.lower() not in (".sh", ".py", ".bash", ".txt", ".yaml", ".yml", ".toml"):
            continue
        t = read_text(p)
        if declared in t:
            referenced.append((rel(root, p), t[:t.find(declared)].count("\n") + 1))
        elif declared_dir and declared_dir != "/" and declared_dir in t:
            referenced_dir.append((rel(root, p), t[:t.find(declared_dir)].count("\n") + 1))
        for m in REWARD_LIKE.finditer(t):
            s = m.group(0).strip()
            if s and s not in (declared,):
                reward_like.append((rel(root, p), t[:m.start()].count("\n") + 1, s))

    if referenced:
        f, line = referenced[0]
        return "pass", [{"severity": "informational", "file": f, "line": line,
                         "detail": "D-C01：声明路径 %s 在 tests/ 中被引用（写入链存在）" % declared}]
    if referenced_dir:
        f, line = referenced_dir[0]
        return "pass", [{"severity": "informational", "file": f, "line": line,
                         "detail": "D-C01：声明路径的目录 %s 在 tests/ 中被引用"
                                   "（拼接写入，如 $REWARD_DIR/reward.txt）" % declared_dir}]

    # 声明路径在 tests/ 零出现：列出实际 reward 类写入目标作为对照
    uniq = []
    seen = set()
    for f, line, s in reward_like:
        key = (f, s)
        if key in seen:
            continue
        seen.add(key)
        uniq.append((f, line, s))
    detail = ("D-C01：task.toml 声明的 reward_file=%s 在 tests/ 全目录零出现——"
              "Verifier 实际写入目标是 %s；平台按字面读取声明路径时每次试验都取不到分数"
              % (declared, ", ".join("%s(%s)" % (s, f) for f, _, s in uniq[:4]) or "未找到 reward 类写入路径"))
    findings.append({"severity": "blocking", "file": rel(root, task_toml), "line": 0,
                     "detail": detail})
    return "fail", findings


# ────────────────────────── D-C02：清单哈希全量复算 ──────────────────────────

MANIFEST_NAME_HINTS = ("manifest", "hashes", "trusted", "frozen", "calibration",
                       "env_hashes", "anchor")


def _looks_like_path(v: str) -> bool:
    return isinstance(v, str) and 0 < len(v) < 300 and bool(PATHISH_RE.search(v)) and "\n" not in v


def extract_declarations(node, out, path=""):
    """递归抽取 (path, sha256, size) 当前声明；跳过历史记录区块（revision_log 等）。"""
    if isinstance(node, dict):
        for k, v in node.items():
            if HISTORY_KEY_RE.search(str(k)):
                continue  # 历史记录区块：旧值是实名记录的一部分，不是当前声明
            extract_declarations(v, out, path + "/" + str(k))
        # 形态 A：同一 dict 内 {path|file: ..., sha256: ...}
        path_v = None
        for k in ("path", "file", "rel_path", "relative_path", "filename", "name"):
            v = node.get(k)
            if isinstance(v, str) and _looks_like_path(v):
                path_v = v
                break
        sha_v = None
        for k in ("sha256", "hash", "sha", "digest"):
            v = node.get(k)
            if isinstance(v, str) and SHA_RE.match(v):
                sha_v = v
                break
        if path_v and sha_v:
            size_v = node.get("size") or node.get("size_bytes") or node.get("bytes")
            out.append((path_v, sha_v.lower(), int(size_v) if isinstance(size_v, int) else None))
        # 形态 B：{相对路径: {sha256, size}}
        for k, v in node.items():
            if HISTORY_KEY_RE.search(str(k)):
                continue
            if isinstance(k, str) and _looks_like_path(k) and isinstance(v, dict):
                sha_v = None
                for kk in ("sha256", "hash", "sha", "digest"):
                    vv = v.get(kk)
                    if isinstance(vv, str) and SHA_RE.match(vv):
                        sha_v = vv
                        break
                if sha_v:
                    size_v = v.get("size") or v.get("size_bytes") or v.get("bytes")
                    out.append((k, sha_v.lower(), int(size_v) if isinstance(size_v, int) else None))
    elif isinstance(node, list):
        for v in node:
            extract_declarations(v, out, path)


def resolve_declared(root: Path, manifest: Path, rel_path: str):
    cands = [root / rel_path,
             manifest.parent / rel_path,
             root / "workspace" / "harbor_task" / rel_path,
             root / "harbor_task" / rel_path]
    for c in cands:
        try:
            if c.is_file():
                return c
        except OSError:
            continue
    return None


def _manifest_scope(manifest: Path) -> str:
    """评分合同清单（tests//harbor_task/environment/ 下）vs 专家证据清单。

    只有评分合同的不一致才阻断（D-C02 的复盘来源是「评分资产/锚点不一致」）；
    专家证据（expert_evidence/ 下的 provenance、NOP 树哈希等）的不一致记
    needs_manual——是诚信记录问题，不是提交阻断项。
    """
    parts = set(manifest.parts)
    if "tests" in parts or "harbor_task" in parts or "environment" in parts:
        return "scoring"
    return "evidence"


def check_manifest_hashes(root: Path):
    findings = []
    decls = []
    scanned = []
    for p in iter_files(root):
        low = p.name.lower()
        if p.suffix.lower() != ".json" or not any(h in low for h in MANIFEST_NAME_HINTS):
            continue
        try:
            if p.stat().st_size > 2 * 1024 * 1024:
                continue
        except OSError:
            continue
        try:
            data = json.loads(read_text(p))
        except ValueError:
            findings.append({"severity": "needs_manual", "file": rel(root, p), "line": 0,
                             "detail": "D-C02：清单 JSON 无法解析，无法复算声明哈希"})
            continue
        scanned.append(rel(root, p))
        out = []
        extract_declarations(data, out)
        seen = set()
        for path_v, sha, size in out:
            key = (path_v, sha)
            if key in seen:
                continue
            seen.add(key)
            decls.append((p, path_v, sha, size, _manifest_scope(p)))

    if not scanned:
        return "not_applicable", [{"severity": "informational", "file": "", "line": 0,
                                   "detail": "D-C02：包内未发现含哈希声明的清单文件，本项不适用"}]
    if not decls:
        return "pass", [{"severity": "informational", "file": scanned[0], "line": 0,
                         "detail": "D-C02：清单存在但未抽取到 (path, sha256) 声明"}]

    ok = 0
    mismatched = []
    missing = []
    for manifest, path_v, sha, size, scope in decls[:2000]:
        target = resolve_declared(root, manifest, path_v)
        if target is None:
            missing.append((manifest, path_v, sha, scope))
            continue
        try:
            h = hashlib.sha256(target.read_bytes()).hexdigest()
        except OSError:
            missing.append((manifest, path_v, sha, scope))
            continue
        size_ok = size is None or target.stat().st_size == size
        if h == sha and size_ok:
            ok += 1
        else:
            mismatched.append((manifest, path_v, sha, h, size, target.stat().st_size, scope))

    scoring_bad = [m for m in mismatched if m[6] == "scoring"]
    evidence_bad = [m for m in mismatched if m[6] == "evidence"]

    if scoring_bad:
        m, path_v, sha, h, size, real_size, _ = scoring_bad[0]
        findings.append({
            "severity": "blocking", "file": rel(root, m), "line": 0,
            "detail": "D-C02：评分合同清单声明与实物不符 %d 项（首例 %s：声明 %s%s，"
                      "实物 %s/%dB）——指纹合同失效：要么刷新清单并实名记录变更，要么还原实物"
                      % (len(scoring_bad), path_v, sha[:12],
                         ("/%dB" % size) if size is not None else "", h[:12], real_size)})
        for m2, pv, s2, h2, sz2, rs2, _ in scoring_bad[1:5]:
            findings.append({"severity": "blocking", "file": rel(root, m2), "line": 0,
                             "detail": "D-C02：%s 声明 %s… 实物 %s…" % (pv, s2[:12], h2[:12])})
        return "fail", findings

    if evidence_bad:
        m, path_v, sha, h, size, real_size, _ = evidence_bad[0]
        findings.append({"severity": "needs_manual", "file": rel(root, m), "line": 0,
                         "detail": "D-C02：专家证据清单与实物不符 %d 项（首例 %s）——"
                                   "非评分合同、不阻断提交，但清单需刷新或说明；"
                                   "评审中如实记录为证据侧不一致" % (len(evidence_bad), path_v)})
        return "needs_manual", findings

    if missing:
        m, path_v, sha, scope = missing[0]
        findings.append({"severity": "needs_manual", "file": rel(root, m),
                         "line": 0,
                         "detail": "D-C02：%d 项声明指向包内不存在的文件（首例 %s）——"
                                   "若为包外来源需给出出处与获取方式，不能默认通过"
                                   % (len(missing), path_v)})
        return "needs_manual", findings

    return "pass", [{"severity": "informational", "file": scanned[0], "line": 0,
                     "detail": "D-C02：%d 项声明哈希/尺寸与实物全部一致（扫描清单：%s）"
                               % (ok, ", ".join(scanned[:3]))}]


# ────────────────────────── D-C03：reward 二选一 ──────────────────────────

def check_reward_single_file(root: Path, task_toml: Path | None):
    """同一评分链同时写 reward.json 与 reward.txt = 违反 v0.5.0 L0 协议。

    只认 test.sh/grader 里的写入证据（echo/重定向/open/原子写）；诊断文件
    （result.json、reward_detail、日志）不算正式 reward。
    """
    findings = []
    if task_toml is None:
        return "needs_manual", [{"severity": "needs_manual", "file": "workspace/harbor_task/task.toml",
                                 "line": 0, "detail": "D-C03：无 task.toml 可查（前置缺失）"}]
    tests_dir = task_toml.parent / "tests"
    if not tests_dir.is_dir():
        return "needs_manual", [{"severity": "needs_manual", "file": rel(root, tests_dir),
                                 "line": 0, "detail": "D-C03：tests/ 目录不存在，无法核对写入链"}]
    CLEANUP_RE = re.compile(r"rm\s+-f|clean_stale|预清理|卫生清理|clean_stale_rewards", re.I)
    ASSIGN_JSON = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*=\s*[\"'][^\n]*reward\.json")
    ASSIGN_TXT = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*=\s*[\"'][^\n]*reward\.txt")
    LOOP_BOTH = re.compile(r"for\s+\w+\s+in\s+[^\n]*reward\.txt[^\n]*reward\.json", re.I)
    json_writes, txt_writes = [], []
    indirect_files = []
    for p in iter_files(tests_dir):
        if p.suffix.lower() not in (".sh", ".py", ".bash"):
            continue
        t = read_text(p)
        lines = t.splitlines()
        f_json_nc, f_txt_nc = [], []   # 非清理、非注释行的两种字面量
        json_assign = txt_assign = loop_both = False
        has_call = any(k in t.lower() for k in ("atomic_write", "os.replace", "open(", "dump", "cp ", "echo"))
        for i, line in enumerate(lines, 1):
            low = line.lower()
            # 排除纯诊断/明细文件
            if "reward_detail" in low or "result.json" in low:
                continue
            is_regex_line = 're.compile' in line or 're.search' in line
            is_json = 'reward.json' in low and not is_regex_line
            is_txt = (re.search(r'reward\.txt', low) is not None) and not is_regex_line
            is_cleanup = bool(CLEANUP_RE.search(line))
            is_write = any(k in low for k in (">", "open(", "write", "replace", "echo", "dump", "save"))
            stripped = line.strip()
            is_comment = stripped.startswith("#")
            if is_cleanup:
                continue
            if is_json:
                if is_write:
                    json_writes.append((rel(root, p), i, line.strip()[:120]))
                elif not is_comment:
                    f_json_nc.append(i)
                if ASSIGN_JSON.match(line):
                    json_assign = True
            elif is_txt:
                if is_write:
                    txt_writes.append((rel(root, p), i, line.strip()[:120]))
                elif not is_comment:
                    f_txt_nc.append(i)
                if ASSIGN_TXT.match(line):
                    txt_assign = True
            if LOOP_BOTH.search(line) and "detail.json" not in line:
                loop_both = True
        # ★ v2.5.1 误报修正（2604 r2 交叉审计）：变量间接双写——赋值行
        #   REWARD_TXT=…/reward.txt + REWARD_JSON=…/reward.json + 循环镜像 publish，
        #   行级写入标记扫描抓不到。强特征（两次赋值成对，或 for-in 双扩展循环）
        #   才升 needs_manual；泛共现（注释/正则扫描行）不升。
        if f_json_nc and f_txt_nc and has_call:
            indirect_files.append((rel(root, p), f_json_nc[0], f_txt_nc[0], "weak"))
        if (json_assign and txt_assign) or loop_both:
            indirect_files.append((rel(root, p), 0, 0, "strong"))
    strong = [x for x in indirect_files if x[3] == "strong"]
    if json_writes and txt_writes:
        jf, jl, jl_ = json_writes[0]
        tf, tl, tl_ = txt_writes[0]
        findings.append({"severity": "blocking", "file": jf, "line": jl,
                         "detail": "D-C03：同一评分链同时写 reward.json 与 reward.txt——"
                                   "违反 v0.5.0「正式 reward 二选一」L0 协议"
                                   "（JSON 侧 %s:%d %s；TXT 侧 %s:%d %s）。"
                                   "保留一种为正式 reward，另一种内容移入 result.json 或日志"
                                   % (jf, jl, jl_, tf, tl, tl_)})
        for f, i, s in (json_writes + txt_writes)[1:4]:
            findings.append({"severity": "blocking", "file": f, "line": i,
                             "detail": "D-C03：%s" % s})
        return "fail", findings
    if strong and not (json_writes and txt_writes):
        f, jl, tl, _ = strong[0]
        return "needs_manual", [{"severity": "needs_manual", "file": f, "line": jl,
                                 "detail": "D-C03：疑似变量间接双写（强特征：成对赋值或 "
                                           "for-in 双扩展循环）——同一评分链内 "
                                           "reward.json 与 reward.txt 共存且有写调用"
                                           "（2604 r2 实测形态：赋值+循环镜像）。"
                                           "需人工确认实际落点是否只发布一种"}]
    weak = [x for x in indirect_files if x[3] == "weak"]
    if weak and not (json_writes and txt_writes):
        f, jl, tl = weak[0][:3]
        return "needs_manual", [{"severity": "needs_manual", "file": f, "line": jl,
                                 "detail": "D-C03：疑似变量间接双写——同一评分链内 "
                                           "reward.json（行 %d）与 reward.txt（行 %d）字面量共存"
                                           "且有写调用（2604 r2 实测形态：赋值+循环镜像）。"
                                           "需人工确认实际落点是否只发布一种" % (jl, tl)}]
    if json_writes or txt_writes:
        kind = "reward.json" if json_writes else "reward.txt"
        f, i, s = (json_writes or txt_writes)[0]
        return "pass", [{"severity": "informational", "file": f, "line": i,
                         "detail": "D-C03：正式 reward 单一（%s）——符合二选一协议" % kind}]
    return "not_applicable", [{"severity": "informational", "file": rel(root, tests_dir),
                               "line": 0,
                               "detail": "D-C03：tests/ 内未发现 reward.json/reward.txt "
                                         "写入证据（可能由外部协议生成）——按实际链路核对"}]


# ────────────────────────── D-C04：Oracle 规范入口 ──────────────────────────

def check_oracle_entry(root: Path, task_toml: Path | None):
    """harbor_task/solution/solve.sh 必须存在（v0.5.0 Oracle 规范入口）；
    solution/ 私有材料不得被 COPY 进 Agent 可见镜像。"""
    findings = []
    if task_toml is None:
        return "needs_manual", [{"severity": "needs_manual", "file": "workspace/harbor_task/task.toml",
                                 "line": 0, "detail": "D-C04：无 task.toml 可查（前置缺失）"}]
    task_root = task_toml.parent
    solve = task_root / "solution" / "solve.sh"
    if not solve.is_file():
        findings.append({"severity": "blocking", "file": rel(root, solve), "line": 0,
                         "detail": "D-C04：缺少 Oracle 规范入口 solution/solve.sh——"
                                   "v0.5.0 四项统一协议之一（容器侧 /solution/solve.sh，"
                                   "调用 solution/ 内参考实现生成正常提交物后独立评分）；"
                                   "已有参考实现补交付结构与入口接线即可，不需要重做算法"})
        return "fail", findings
    findings.append({"severity": "informational", "file": rel(root, solve), "line": 0,
                     "detail": "D-C04：solution/solve.sh 在位（Oracle 入口）；调用链与"
                               "输出路径的语义核对留 review"})
    # 私有边界：environment/（Agent 镜像）不得 COPY solution/
    agent_df = task_root / "environment" / "Dockerfile"
    if agent_df.is_file():
        t = read_text(agent_df)
        for i, line in enumerate(t.splitlines(), 1):
            if re.search(r"\bCOPY\b|\bADD\b", line, re.I) and re.search(r"\bsolution\b", line):
                findings.append({"severity": "blocking", "file": rel(root, agent_df),
                                 "line": i,
                                 "detail": "D-C04：Agent 镜像 COPY 了 solution/——Oracle 私有"
                                           "参考解暴露给被测 Agent（%s）" % line.strip()[:100]})
    status = "fail" if any(f["severity"] == "blocking" for f in findings) else "pass"
    return status, findings


# ────────────────────────── 汇总 ──────────────────────────

def main():
    ap = argparse.ArgumentParser(description="交付契约机械检查（D-C01/D-C02）")
    ap.add_argument("--root", required=True, help="提交包根或 harbor_task 目录")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print("FATAL: root not found: %s" % root)
        return 2

    task_toml = find_task_toml(root)
    d01_status, d01_findings = check_reward_path(root, task_toml)
    d02_status, d02_findings = check_manifest_hashes(root)
    d03_status, d03_findings = check_reward_single_file(root, task_toml)
    d04_status, d04_findings = check_oracle_entry(root, task_toml)

    checks = [
        {"id": "D-C01", "title": "声明的 reward_file 必须存在于 Verifier 写入链",
         "status": d01_status, "findings": d01_findings},
        {"id": "D-C02", "title": "包内清单声明的哈希/尺寸必须与实物一致",
         "status": d02_status, "findings": d02_findings},
        {"id": "D-C03", "title": "正式 reward 二选一（json/txt 不得同时写）",
         "status": d03_status, "findings": d03_findings},
        {"id": "D-C04", "title": "Oracle 规范入口 solution/solve.sh 在位且不暴露给 Agent",
         "status": d04_status, "findings": d04_findings},
    ]
    counts = {}
    for c in checks:
        counts[c["status"]] = counts.get(c["status"], 0) + 1

    report = {
        "gate": "delivery_contract",
        "root": str(root),
        "task_toml": str(task_toml) if task_toml else None,
        "summary": counts,
        "checks": checks,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    for c in checks:
        print("  [%-4s] %s  %s" % (c["status"], c["id"], c["title"]))
        for f in c["findings"]:
            if f["severity"] != "informational":
                print("         %s %s:%s  %s" % (f["severity"].upper(), f["file"],
                                                 f["line"], f["detail"][:160]))
    print("summary:", json.dumps(counts, ensure_ascii=False))
    print("written:", out)
    return 1 if counts.get("fail") else 0


if __name__ == "__main__":
    sys.exit(main())
