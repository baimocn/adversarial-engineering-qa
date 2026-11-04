#!/usr/bin/env python3
"""把「读一遍」变成「逐条回答」：生成强制核对清单。

★ 要解决的问题

  让模型串行读 140 个文件，结果取决于它「恰好注意到什么」。注意力在长上下文里
  必然稀释，模型会挑看起来像 bug 的行，漏掉真正致命的**两行接口错配**
  （0340 的 QA05/QA06 就是这么漏的）。

  能机械保证的不是「理解正确」，而是**程序完整性**：
    · 每个文件都有处置（read / skim / skip + 理由）
    · 每条高风险声明都有实现绑定（bound_to 或 no_implementation + 理由）
    · 每个热点函数都有固定问题的答案
    · 每组同源副本的差异都有说明
  程序完整性不能证明结论对，但能消灭「压根没看」这一类漏检。

★ 四类抓手

  1. 文件处置槽 —— 来自 manifest，一个文件一个槽。
  2. 声明绑定槽 —— 来自 shard 的 declarations，按风险打分，高风险强制绑定。
  3. 热点问答槽 —— 来自 symbols.json，按函数体哈希**全局去重**（同一份代码
     在 starter / solution / trusted_env 各有一份，只问一遍）。
  4. 副本对账槽 —— 同一相对路径在多棵树下各有一份时成组；
     **内容不同即必须解释**。0340 的 QA05（docstring 进了 co_consts 导致
     诚实候选被判篡改）只有这条路径能发现。

用法：
  python scripts/build_review_worklist.py --evidence-dir <ev> --task-dir <task> --all \
      --outdir <outdir>/worklist
  python scripts/build_review_worklist.py --evidence-dir <ev> --task-dir <task> \
      --shard shard-0001 --out <outdir>/worklist/shard-0001.json

退出码：0 正常；2 输入缺失。
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

SCHEMA = "review-worklist/1"

RISK_PATTERNS = [
    (re.compile(r"(不可|无法|不能|必须|仅|只|不会|一律|绝不|禁止|强制)"), 3, "绝对声明"),
    (re.compile(r"\d+\s*(秒|s\b|分钟|min|小时|h\b|GB|MB|KB|核|卡|gpu|cpu)", re.I), 3,
     "数量声明"),
    (re.compile(r"(隔离|只读|隐藏|不可见|沙箱|权限|降权|root|suid|提权)", re.I), 3, "安全边界"),
    (re.compile(r"(超时|timeout|重试|retry|失败|异常|error|崩溃)"), 2, "失败路径"),
    (re.compile(r"(指纹|hash|sha256|校验|验证|verify|check)", re.I), 2, "校验口径"),
    (re.compile(r"(评分|reward|score|分数|奖励)"), 2, "评分链"),
    # 2026-11 迁移规则：作者校准义务不得写成 Solver 完成/选优/延长运行条件。
    # ★ 裸 3σ/三标准差不打本标签——题目算法自身合理使用 3σ（异常检测、统计规则）
    #   按返修指南保留；只有「3σ 出现在完成/选优/继续运行语境」才算作者义务。
    (re.compile(r"(3σ|3σ_B|三倍标准差|三标准差)[^。\n]{0,24}"
                r"(才|才算|才完成|否则|继续运行|完成条件|选优|延长)"
                r"|(达到|未达|未达到|不少于|不低于|跑满)[^。\n]{0,16}"
                r"(3σ|σ_B|三倍标准差|三标准差|作者|校准)"
                r"|(作者|专家)校准|校准区间|与作者研究(一致|同时长)|不劣于作者", re.I),
     3, "作者校准义务（2026-11 迁移规则）"),
]

# 高危函数名：出错代价最高的一批
HOT_CRITICAL = {
    "act", "plan", "load", "save", "evaluate", "eval", "verify", "check", "guard",
    "score", "grade", "compute", "estimate", "main", "run", "train", "update",
    "deserialize", "serialize", "forward",
}
# 低危（环境包装器样板，通常与上游 vendored 代码一致）
HOT_LOW = {"step", "reset", "close", "render", "seed", "obs_spec", "action_spec"}
HOT_CLASS = re.compile(r"(Wrapper|Evaluator|Verifier|Grader|Scorer|Policy)$")

QUESTIONS_FUNC = [
    "返回值形状/元数是什么？所有调用点是否按同样元数解包？",
    "可能抛哪些异常？被谁捕获？未捕获时归因给谁（候选还是基础设施）？",
    "读写哪些外部状态（文件/网络/全局/self 属性）？失败时是否留下半成品？",
]
QUESTIONS_CLASS = [
    "被谁实例化？构造参数来自候选可控的地方还是可信侧？",
    "是否覆写 dunder（__new__/__getattr__/__eq__ 等）或继承外部基类？",
    "实例化后是否有属性被外部改写？改写点在哪？",
]

QUESTIONS_LOW = [
    "参数与返回值形状是否与调用方一致？有无 dtype / device 转换？",
]

# 强度档：控制「问多少」。默认 standard —— 高危函数问全，环境样板只问形状。
INTENSITY = {
    "light": {"include_low": False, "critical_q": 2, "must_bind_min": 4, "max_bind": 15},
    "standard": {"include_low": True, "critical_q": 3, "must_bind_min": 3, "max_bind": 40},
    "strict": {"include_low": True, "critical_q": 3, "must_bind_min": 2, "max_bind": 200},
}


# 路径 → 它服务的官方 QA 项。让质检员知道「答这一槽是为了判哪一项」。
SERVES = [
    ("instruction.md", ["QA01", "QA05", "QA07", "QA08", "QA11", "QA14", "QA20"]),
    ("frozen_manifest.json", ["QA10", "QA14", "QA21"]),
    ("task.toml", ["QA15", "QA17", "QA20"]),
    ("tests/grader.py", ["QA02", "QA06", "QA10", "QA21"]),
    ("tests/test.sh", ["QA06", "QA09", "QA21"]),
    ("tests/model.py", ["QA10"]),
    ("tests/Dockerfile", ["QA05", "QA06"]),
    ("tests/hidden_assets/anchors.json", ["QA02", "QA04", "QA19"]),
    ("environment/Dockerfile", ["QA05", "QA20"]),
    ("environment/starter/", ["QA14", "QA20"]),
    ("environment/public_eval/", ["QA02", "QA06"]),
    ("environment/reference/", ["QA03", "QA13"]),
    ("optimization_evidence/", ["QA03", "QA13", "QA19"]),
]


def serves_for(path: str):
    hits = []
    for pat, ids in SERVES:
        if path == pat or path.startswith(pat):
            for i in ids:
                if i not in hits:
                    hits.append(i)
    return hits

BLINDSPOT_BY_GROUP = {
    "tests": [
        "评分链的类型流向：numpy↔tensor、float32↔float64、device 是否一致",
        "返回值元数：定义处与每个调用点是否一致（3 返 2 收是最常见形态）",
        "失败归因：题面说属基础设施的错误，实现里是否真的不计候选",
        "指纹/校验口径：被比对的两份副本在「被忽略的字段」上是否真的一致",
    ],
    "environment": [
        "Dockerfile 注释里的声明（版本、超时、体积）与指令是否一致",
        "依赖版本锁定方式；离线/无网时是否仍可构建",
        "启动命令与工作目录是否与 task.toml / 题面一致",
    ],
    "solution": [
        "入口契约：命令行参数、默认值、必填项是否与题面一致",
        "配置读取：候选是否可覆盖协议键（action_dim / mpc / episode_length）",
        "错误处理：异常是否被吞掉、是否静默降级",
    ],
    "root": [
        "task.toml 的资源与时长声明是否有实现约束（不只是写在字段里）",
        "instruction.md 的绝对声明逐条绑定实现位置",
        "题面承诺的错误分类与评分实现是否一致",
        "题面中的作者校准义务（3σ/校准区间/跑满作者时长）是否被写成 Solver 完成、"
        "选优或延长运行条件——2026-11 迁移规则要求迁出；题目算法自身合理使用 3σ 除外",
        "源包是否只保留一份 task.toml 于 workspace/harbor_task/，且无 docker_image"
        "（2026-11 平台硬规则 B-C01/B-C02，check_platform_rules.py 机械核对）",
    ],
}
BLINDSPOT_DEFAULT = ["入口与出口契约", "失败路径与归因", "外部输入的类型与边界"]


def score_decl(text: str):
    hits, score = [], 0
    for pat, w, label in RISK_PATTERNS:
        if pat.search(text):
            score += w
            hits.append(label)
    return score, hits


def body_fp(task_root: Path | None, rel_path: str, line: int):
    if task_root is None:
        return None
    p = task_root / rel_path
    if not p.is_file():
        return None
    try:
        src = p.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src)
    except (OSError, SyntaxError, ValueError):
        return None
    target = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                and getattr(node, "lineno", -1) == line:
            target = node
            break
    if target is None:
        return None
    seg = ast.get_source_segment(src, target) or ""
    norm = re.sub(r"\s+", " ", seg).strip()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def hotspot_priority(path: str, short: str) -> int:
    p = 0
    if path.startswith("tests/") or "/" not in path:
        p += 10
    if short in HOT_CRITICAL:
        p += 6
    elif short in HOT_LOW:
        p += 0
    elif HOT_CLASS.search(short):
        p += 4
    return p


def build_mirror_sets(manifest: dict) -> list[dict]:
    """同源副本：同一相对路径（末两段）在多棵树下各有一份。"""
    groups: dict[str, list[dict]] = {}
    for f in manifest.get("files") or []:
        parts = str(f.get("path", "")).split("/")
        if len(parts) < 2:
            continue
        groups.setdefault("/".join(parts[-2:]), []).append({
            "path": f["path"], "sha256": f.get("sha256"),
            "size_bytes": f.get("size_bytes", 0),
        })
    out = []
    for key, items in sorted(groups.items()):
        if len(items) < 2:
            continue
        shas = {i["sha256"] for i in items}
        out.append({
            "key": key,
            "identical": len(shas) == 1,
            "count": len(items),
            "members": items,
            "must_explain": len(shas) > 1,
            "question": ("这些副本内容不同。差异是否都是**有意**的？逐条列出差异点，"
                         "并判断是否会被任何『内容一致性校验』当成篡改/漂移。"),
        })
    return out


def scan_symbols(shards_data: list[tuple[str, Path]], symbols: list[dict],
                 task_root: Path | None, include_low: bool):
    """预扫：给每个热点算 body_fp，按**负载均衡**指定唯一作答方。

    ★ 为什么均衡：0340 里 starter / solution / trusted_env 三份副本函数体完全相同，
      若按「谁的路径字典序靠前谁答」，environment 片会独扛 54 个热点（162 问），
      而 solution 片只剩 1 个。按当前负载取最小者，能把三片压到相近。

    返回 {(path,line,qualname): (fp, owner_sid, owner_label)}
    """
    occ: list[tuple[str, dict, str | None]] = []
    for sid, spath in shards_data:
        sh = json.loads(spath.read_text(encoding="utf-8"))
        paths = {f["path"] for f in sh.get("files", [])}
        for s in symbols:
            if s.get("path") not in paths:
                continue
            q = s.get("qualname", "")
            short = q.rsplit(".", 1)[-1]
            is_cls = s.get("kind") == "class"
            if not (short in HOT_CRITICAL
                    or (include_low and short in HOT_LOW)
                    or (is_cls and HOT_CLASS.search(short))):
                continue
            occ.append((sid, s, body_fp(task_root, s["path"], s.get("line", 0))))

    by_fp: dict[str, list[tuple[str, dict]]] = {}
    for sid, s, fp in occ:
        key = fp if fp else "_nofp:%s:%s" % (s["path"], s.get("line"))
        by_fp.setdefault(key, []).append((sid, s))

    load: dict[str, int] = {}
    info: dict[tuple, tuple] = {}
    # 先认领「只有一份实现」的，再认领多副本的，避免均衡时把稀缺资源挪走
    for key, items in sorted(by_fp.items(), key=lambda kv: len(kv[1])):
        cands = sorted({sid for sid, _ in items})
        owner = min(cands, key=lambda x: (load.get(x, 0), x))
        sid0, s0 = items[0]
        label = "%s:%s:%s" % (owner, s0["path"], s0.get("line"))
        load[owner] = load.get(owner, 0) + 1
        for sid, s in items:
            info[(s["path"], s.get("line", 0), s.get("qualname", ""))] = (
                None if key.startswith("_nofp:") else key, owner, label)
    return info



def build_shard(shard_path: Path, sid: str, symbols: list[dict], fp_info: dict,
                must_bind_min: int, max_bind: int, mirrors: list[dict],
                owner_map: dict[str, str], intensity: dict):
    sh = json.loads(shard_path.read_text(encoding="utf-8"))
    group = sh.get("group", "?")
    files, decls, hot = [], [], []

    for f in sh.get("files", []):
        files.append({
            "path": f["path"], "size_bytes": f.get("size_bytes", 0),
            "serves": serves_for(f["path"]),
            "disposition": None, "reason": None,
        })
    scope_paths = {f["path"] for f in files}

    # ① 声明槽
    scored = []
    for f in sh.get("files", []):
        for d in f.get("declarations") or []:
            s, hits = score_decl(d.get("text", ""))
            scored.append((s, hits, d))
    scored.sort(key=lambda x: -x[0])
    for i, (s, hits, d) in enumerate(scored, 1):
        decls.append({
            "id": "D%04d" % i,
            "path": d.get("path"), "line": d.get("line"),
            "text": (d.get("text") or "")[:300],
            "risk": s, "risk_tags": hits,
            "serves": serves_for(d.get("path") or ""),
            "must_bind": s >= must_bind_min and i <= max_bind,
            "bound_to": None, "verdict": None, "note": None,
        })

    # ② 热点槽（全局去重）
    seen = set()
    for s in symbols:
        if s.get("path") not in scope_paths:
            continue
        q = s.get("qualname", "")
        short = q.rsplit(".", 1)[-1]
        is_cls = s.get("kind") == "class"
        if not (short in HOT_CRITICAL
                or (intensity["include_low"] and short in HOT_LOW)
                or (is_cls and HOT_CLASS.search(short))):
            continue
        key = (s["path"], s.get("line", 0), q)
        if key in seen:
            continue
        seen.add(key)
        fp, owner_sid, owner_label = fp_info.get(
            (s["path"], s.get("line", 0), q), (None, None, None))
        mine = owner_sid in (None, sid)
        hid = "H%04d" % len(hot)
        if is_cls:
            qs = QUESTIONS_CLASS
        elif short in HOT_LOW:
            qs = QUESTIONS_LOW
        else:
            qs = QUESTIONS_FUNC[:intensity["critical_q"]]
        hot.append({
            "id": hid,
            "path": s["path"], "line": s.get("line"), "kind": s.get("kind"),
            "qualname": q,
            "priority": hotspot_priority(s["path"], short),
            "serves": serves_for(s["path"]),
            "body_fp": (fp[:16] if fp else None),
            "same_as": None if mine else owner_label,
            "questions": qs if mine else [],
            # 复用项 questions 为空，answers 也必须为空，否则长度校验永远不过
            "answers": None if mine else [],
            "auto_note": None if mine else "同一份代码由 %s 作答，本处不重复" % owner_label,
        })
    hot.sort(key=lambda h: (-h["priority"], h["path"], h["line"] or 0))
    for i, h in enumerate(hot):
        h["rank"] = i + 1

    # ③ 副本对账槽：只归 owner（路径字典序最靠前成员所在的 shard），避免重复劳动
    ms = []
    for g in mirrors:
        if g["key"] not in owner_map or owner_map[g["key"]] != sid:
            continue
        if not any(m["path"] in scope_paths for m in g["members"]):
            continue
        ms.append(g)

    return {
        "schema": SCHEMA,
        "shard": sid,
        "group": group,
        "files": files,
        "declarations": decls,
        "hotspots": hot,
        "mirror_sets": ms,
        "mirror_notes": {g["key"]: None for g in ms if g["must_explain"]},
        "blindspot_checklist": BLINDSPOT_BY_GROUP.get(group, BLINDSPOT_DEFAULT),
        "rules": [
            "files 每项必须填 disposition（read/skim/skip）与 reason；空着即 INCOMPLETE",
            "must_bind=true 的声明必须填 bound_to 与 verdict；无实现写 no_implementation + note",
            "hotspots 中 same_as 非空者已自动答复；其余 answers 必须与 questions 一一对应",
            "mirror_notes 里每一项都必须说明差异是否有意、是否会被一致性校验误判",
            "证据一律写 file:line + 原文 snippet，不接受「见上文」",
        ],
    }


def main():
    ap = argparse.ArgumentParser(description="生成强制核对清单")
    ap.add_argument("--evidence-dir", required=True)
    ap.add_argument("--task-dir", default=None, help="待检目录（用于函数体去重与副本对账）")
    ap.add_argument("--shard", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--must-bind-min", type=int, default=None,
                    help="风险分 ≥ 该值才强制绑定（默认按 intensity）")
    ap.add_argument("--max-bind", type=int, default=None,
                    help="每个 shard 最多强制绑定多少条声明（默认按 intensity）")
    ap.add_argument("--intensity", choices=sorted(INTENSITY), default="standard",
                    help="light=只问高危；standard=高危全问+样板只问形状；strict=全问")
    args = ap.parse_args()

    cfg = dict(INTENSITY[args.intensity])
    if args.must_bind_min is not None:
        cfg["must_bind_min"] = args.must_bind_min
    if args.max_bind is not None:
        cfg["max_bind"] = args.max_bind

    ev = Path(args.evidence_dir)
    man_p = ev / "manifest.json"
    if not man_p.is_file():
        print("FATAL: 找不到", man_p)
        return 2
    manifest = json.loads(man_p.read_text(encoding="utf-8"))
    symbols = []
    if (ev / "symbols.json").is_file():
        symbols = json.loads((ev / "symbols.json").read_text(encoding="utf-8"))

    shards = manifest.get("shards") or []
    targets = []
    if args.shard:
        targets = [s for s in shards if s.get("id") == args.shard]
        if not targets:
            print("FATAL: 找不到 shard", args.shard)
            return 2
    elif args.all:
        targets = shards
    else:
        print("FATAL: 需要 --shard 或 --all")
        return 2

    task_root = Path(args.task_dir).resolve() if args.task_dir else None
    mirrors = build_mirror_sets(manifest)
    # 副本组归 owner：成员路径字典序最靠前的那个 shard
    owner_map = {}
    for g in mirrors:
        first = sorted(m["path"] for m in g["members"])[0]
        for sh in shards:
            sp = ev / sh["path"]
            if not sp.is_file():
                continue
            paths = {f["path"] for f in json.loads(sp.read_text(encoding="utf-8")).get("files", [])}
            if first in paths:
                owner_map[g["key"]] = sh["id"]
                break

    shards_data = [(s["id"], ev / s["path"]) for s in shards if (ev / s["path"]).is_file()]
    fp_info = scan_symbols(shards_data, symbols, task_root, cfg["include_low"])

    total = {"files": 0, "declarations": 0, "must_bind": 0, "hotspots": 0,
             "hotspots_deduped": 0, "mirror_sets": 0, "mirror_diff": 0}
    for t in targets:
        w = build_shard(ev / t["path"], t["id"], symbols, fp_info,
                        cfg["must_bind_min"], cfg["max_bind"], mirrors, owner_map, cfg)
        total["files"] += len(w["files"])
        total["declarations"] += len(w["declarations"])
        total["must_bind"] += sum(1 for d in w["declarations"] if d["must_bind"])
        total["hotspots"] += len(w["hotspots"])
        total["hotspots_deduped"] += sum(1 for h in w["hotspots"] if h["same_as"])
        total["mirror_sets"] += len(w["mirror_sets"])
        total["mirror_diff"] += sum(1 for g in w["mirror_sets"] if g["must_explain"])
        if args.all:
            outdir = Path(args.outdir or ".")
            outdir.mkdir(parents=True, exist_ok=True)
            p = outdir / ("%s.json" % w["shard"])
        else:
            p = Path(args.out)
            p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(w, ensure_ascii=False, indent=2), encoding="utf-8")
        print("%-12s files=%-3d decls=%-3d must_bind=%-3d hotspots=%-3d(复用 %d) "
              "mirrors=%-2d(差异 %d) -> %s"
              % (w["shard"], len(w["files"]), len(w["declarations"]),
                 sum(1 for d in w["declarations"] if d["must_bind"]),
                 len(w["hotspots"]), sum(1 for h in w["hotspots"] if h["same_as"]),
                 len(w["mirror_sets"]),
                 sum(1 for g in w["mirror_sets"] if g["must_explain"]), p))
    print("TOTAL:", json.dumps(total, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
