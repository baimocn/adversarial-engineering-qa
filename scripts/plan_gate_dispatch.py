#!/usr/bin/env python3
"""闸门并行分派：把一次质检拆成可独立认领的单元，供主模型分给子代理。

★ 为什么需要（2026-10-30）：
  实测三个确定性脚本的耗时是 collect_evidence 1.4s / check_execution_path 1.6s /
  check_honest_candidate 18.6s —— **脚本不是瓶颈**。
  慢在「主模型串行读 140 个文件 + 串行推理」，那是小时级。

  所以并行要并的不是脚本，是**阅读与推理面**：按证据索引已有的 shard 切成独立单元，
  每个子代理只对自己那片负责，主模型只做分派、合并与裁定。

核心设计约束：
  1. **切分必须来自 manifest**，不靠模型临时决定 —— 否则各子代理覆盖范围重叠或漏读。
  2. **每个单元有唯一输出路径 + 固定 schema** —— 合并方能机器校验「有没有漏跑」。
  3. **漏跑不得被当成通过** —— 缺单元一律 INCOMPLETE，见 merge_gate_results.py。
  4. **分派只是并行化，不减少总工作量** —— 墙钟变短，token 总量通常上升。

用法：
  python scripts/plan_gate_dispatch.py \
      --task-dir <待检目录> --evidence-dir <evidence-index 输出目录> \
      --out <输出目录>/plan.json [--max-units 8] [--baseline <基线目录或 git ref>]

输出 plan.json 后，主模型按 `units[*].parallel_group` 分组派发；同组可并发，
组号小的先跑。`depends_on` 非空的单元必须等依赖单元出结果。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCHEMA = "gate-dispatch-plan/1"

# 单元接受标准：写进 plan 里，子代理必须逐条满足，否则该单元判 INCOMPLETE
ACCEPT_REVIEW = [
    "先跑 build_review_worklist.py 生成本片清单，再逐条填满；coverage_pct 必须 100%",
    "shard 内每个文件都要有明确结论（已读/略读/跳过并说明原因），不得只读模型偶然看到的文件",
    "每条 finding 必须给 file:line + **原文 snippet**（不接受概括），证据类型标明静态读码/脚本输出/运行结果",
    "must_bind 声明必须绑定到实现位置；无实现的写 no_implementation 并说明理由",
    "hotspots 的固定问题逐条作答，不得留空",
    "不得把「属于其他 shard」作为不看的理由；跨 shard 疑点写入 cross_refs",
]
ACCEPT_SCRIPT = [
    "必须实际执行脚本，记录 rc 与输出 JSON 路径",
    "blocking 计数不得被改写或忽略",
]


def load_manifest(ev_dir: Path) -> dict:
    p = ev_dir / "manifest.json"
    if not p.is_file():
        raise SystemExit("FATAL: 找不到 %s（先跑 collect_evidence.py）" % p)
    return json.loads(p.read_text(encoding="utf-8"))


def build_units(manifest: dict, ev_dir: Path, baseline: str | None) -> list[dict]:
    units: list[dict] = []

    # ── Gate A：变更面回归 ──
    units.append({
        "id": "A.regression",
        "gate": "A",
        "kind": "diff_regression",
        "parallel_group": 1,
        "depends_on": [],
        "inputs": {"baseline": baseline},
        "output": "gates/A.regression.json",
        "acceptance": [
            "列出实际 diff、允许变更面、非预期变化、既有修复回归",
            "「逐字节不变」只能证明没漂移，不能证明基线正确",
            "无基线且本轮不作回归声明时记 not_applicable 并说明原因",
        ],
        "status_if_no_baseline": "not_applicable" if not baseline else None,
    })

    # ── Gate B：按证据索引的 shard 切分 ──
    for sh in manifest.get("shards") or []:
        sid = sh.get("id", "shard")
        group = sh.get("group", "?")
        units.append({
            "id": "B.%s" % sid,
            "gate": "B",
            "kind": "code_review",
            "parallel_group": 2,
            "depends_on": [],
            "inputs": {"shard": sh.get("path"), "group": group,
                       "file_count": sh.get("file_count")},
            "output": "gates/B.%s.json" % sid,
            "worklist": {
                "build": "scripts/build_review_worklist.py --shard %s" % sid,
                "path": "worklist/%s.json" % sid,
                "validate": "scripts/validate_coverage.py",
                "coverage_required_pct": 100.0,
            },
            "acceptance": ACCEPT_REVIEW,
            "status_if_no_baseline": None,
        })

    # ── Gate C-1：确定性静态扫描（脚本快，主模型可自己跑）──
    units.append({
        "id": "C1.static",
        "gate": "C",
        "kind": "script",
        "parallel_group": 1,
        "depends_on": [],
        "inputs": {"script": "scripts/check_execution_path.py",
                   "args": ["--root", "<task-dir>", "--out", "<outdir>/execution-path.json"]},
        "output": "gates/C1.static.json",
        "acceptance": ACCEPT_SCRIPT,
        "status_if_no_baseline": None,
    })

    # ── Gate C-2：诚实候选冒烟（最慢，单独一个单元）──
    units.append({
        "id": "C2.honest",
        "gate": "C",
        "kind": "script",
        "parallel_group": 1,
        "depends_on": [],
        "inputs": {"script": "scripts/check_honest_candidate.py",
                   "candidates": ["reference", "starter", "solution"],
                   "note": "reference 与 starter 都要跑；只跑一个会假绿"},
        "output": "gates/C2.honest.json",
        "acceptance": ACCEPT_SCRIPT + ["每个候选各出一份结果，缺候选记 needs_manual"],
        "status_if_no_baseline": None,
    })

    # ── 合并 ──
    units.append({
        "id": "MERGE",
        "gate": "META",
        "kind": "merge",
        "parallel_group": 9,
        "depends_on": [u["id"] for u in units],
        "inputs": {"script": "scripts/merge_gate_results.py"},
        "output": "gates/merged.json",
        "acceptance": [
            "所有单元都有结果文件；缺任一单元 ⇒ INCOMPLETE",
            "任一 gate FAIL ⇒ 总判 FAIL",
            "Gate C blocking 不可豁免，不得降级为 manual",
        ],
        "status_if_no_baseline": None,
    })
    return units


def main():
    ap = argparse.ArgumentParser(description="闸门并行分派计划器")
    ap.add_argument("--task-dir", required=True)
    ap.add_argument("--evidence-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--baseline", default=None)
    ap.add_argument("--max-units", type=int, default=8,
                    help="并发上限提示（写入 plan，供主模型控制同时派发数）")
    args = ap.parse_args()

    task = Path(args.task_dir).resolve()
    ev = Path(args.evidence_dir).resolve()
    if not task.is_dir():
        print("FATAL: task-dir 不存在:", task)
        return 2
    manifest = load_manifest(ev)

    units = build_units(manifest, ev, args.baseline)
    groups = {}
    for u in units:
        groups.setdefault(u["parallel_group"], []).append(u["id"])

    plan = {
        "schema": SCHEMA,
        "task_dir": str(task),
        "evidence_dir": str(ev),
        "source_digest": manifest.get("source_digest"),
        "files_total": manifest.get("files_total"),
        "python_files_indexed": manifest.get("python_files_indexed"),
        "baseline": args.baseline,
        "max_concurrent": args.max_units,
        "parallel_groups": {str(k): v for k, v in sorted(groups.items())},
        "units": units,
        "cost_note": "并行只缩短墙钟，不减少总工作量；总 token 通常高于串行。",
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    print("schema:", SCHEMA)
    print("units:", len(units))
    for g, ids in sorted(groups.items()):
        print("  group %d (%d): %s" % (g, len(ids), ", ".join(ids)))
    print("max_concurrent:", args.max_units)
    print("written:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
