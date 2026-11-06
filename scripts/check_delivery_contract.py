#!/usr/bin/env python3
"""交付契约机械检查（D-C01 / D-C02，v2.4.1）。

★ 为什么需要这一层（来源：Harbor 1074 题复盘 2026-10-26 / 2026-11-06 副本）

  复盘里有两类问题此前只能靠 agent 语义发现，但其实是纯机械的：

  D-C01 评分文件缺失（74 题评分失败中 72 题为 RewardFileNotFoundError）：
        task.toml 声明的 reward_file 从未被 Verifier 写入。
        2604 实测：声明 /logs/verifier/reward.txt，全链只写 /workspace/.verifier/*，
        全树 /logs 唯一出现即声明自身 ⇒ 每次试验缺 reward。
        同口径反例（work_2768）：test.sh 用 REWARD_DIR=/logs/verifier 写盘且平台
        实跑成功读回 ⇒ 平台按字面读取声明路径，落点不符即缺分。

  D-C02 评分资产/锚点不一致（2 题）+ 1841 实测指纹合同失效（26 项中 5 项失配）：
        包内清单（frozen_manifest / TRUSTED_HASHES / env_hashes / calibration 等）
        声明的 sha256/size 与实物不符。哈希复算是纯机械的，不该等 agent 读码。

  纪律：只报可静态确定的（声明路径是否存在/是否被写入、声明哈希是否等于实物）；
  动态可达性（平台是否真按字面读取）不在这里断言，由 review 绑定证据。

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


def extract_declarations(node, out):
    """递归抽取 (path, sha256, size) 声明，兼容三种常见形态。"""
    if isinstance(node, dict):
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
        for v in node.values():
            extract_declarations(v, out)
    elif isinstance(node, list):
        for v in node:
            extract_declarations(v, out)


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

    checks = [
        {"id": "D-C01", "title": "声明的 reward_file 必须存在于 Verifier 写入链",
         "status": d01_status, "findings": d01_findings},
        {"id": "D-C02", "title": "包内清单声明的哈希/尺寸必须与实物一致",
         "status": d02_status, "findings": d02_findings},
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
