#!/usr/bin/env python3
"""闸门结果合并：把各子代理产出的单元结果合成一份可校验的总判。

★ 设计原则（与 SKILL.md「不得静默降级」一致）：

  1. **缺单元 = INCOMPLETE，绝不当通过。** 子代理跑失败、超时、忘写文件，
     在这层必须显形，而不是被「其他单元都 PASS」淹没。
  2. **Gate C 的 blocking 不可豁免。** 检测到 blocking 却报 PASS 的单元，
     本身判为 INVALID（自相矛盾），并入 errors。
  3. **`not_applicable` 只在有理由时成立。** 无理由的 not_applicable 降为 INCOMPLETE。
  4. **不认计划外的单元。** 防止子代理自己加一个宽松的单元来稀释结论。

用法：
  python scripts/merge_gate_results.py \
      --plan <outdir>/plan.json --results-dir <outdir> \
      --out <outdir>/gates/merged.json

单元结果约定文件名：plan.units[i].output 的路径（相对 results-dir）。
单元结果最小 schema：
  {"unit_id":"B.shard-0001","gate":"B","status":"PASS|FAIL|INCOMPLETE|not_applicable",
   "findings":[{"severity":"blocking|major|minor|info","summary":"...","evidence":"..."}],
   "reason":"..."}

退出码：0 = 总判 PASS 或 PASS_WITH_WAIVERS；1 = FAIL；2 = INCOMPLETE。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VALID_STATUS = {"PASS", "FAIL", "INCOMPLETE", "not_applicable"}
ORDER = {"FAIL": 3, "INCOMPLETE": 2, "PASS": 1, "not_applicable": 0}


def load_unit(res_dir: Path, rel: str) -> tuple[dict | None, str | None]:
    p = res_dir / rel
    if not p.is_file():
        return None, "结果文件缺失：%s" % rel
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return None, "结果文件无法解析：%s（%s）" % (rel, e)
    if not isinstance(d, dict):
        return None, "结果不是对象：%s" % rel
    return d, None


def main():
    ap = argparse.ArgumentParser(description="闸门结果合并")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--results-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    plan_p = Path(args.plan)
    res_dir = Path(args.results_dir)
    if not plan_p.is_file():
        print("FATAL: plan 不存在:", plan_p)
        return 2
    plan = json.loads(plan_p.read_text(encoding="utf-8"))
    planned = {u["id"]: u for u in plan.get("units", [])}

    errors: list[str] = []
    unit_rows: list[dict] = []
    seen: set[str] = set()

    for uid, u in planned.items():
        if u.get("kind") == "merge":
            continue  # 合并单元就是本脚本自己
        d, err = load_unit(res_dir, u["output"])
        if err:
            errors.append(err)
            unit_rows.append({"unit_id": uid, "gate": u["gate"],
                              "status": "INCOMPLETE", "reason": err,
                              "findings": []})
            continue
        got_id = d.get("unit_id")
        if got_id != uid:
            errors.append("单元 id 不匹配：计划 %s，结果自称 %r" % (uid, got_id))
        status = d.get("status")
        if status not in VALID_STATUS:
            errors.append("%s 的 status 非法：%r" % (uid, status))
            status = "INCOMPLETE"
        findings = d.get("findings") or []
        blocking = [f for f in findings if str(f.get("severity")) == "blocking"]
        # ★ 自相矛盾检查：有 blocking 却报 PASS
        if blocking and status == "PASS":
            errors.append("%s 声明 blocking=%d 却报 PASS（自相矛盾，按 FAIL 计）"
                          % (uid, len(blocking)))
            status = "FAIL"
        # ★ not_applicable 必须有理由
        if status == "not_applicable" and not (d.get("reason") or "").strip():
            errors.append("%s 报 not_applicable 但没给理由，降为 INCOMPLETE" % uid)
            status = "INCOMPLETE"
        # ★ 覆盖率：单元声明了 coverage 就必须 100%，否则即使 PASS 也降为 INCOMPLETE。
        cov = d.get("coverage")
        if isinstance(cov, dict):
            pct = cov.get("coverage_pct")
            if not isinstance(pct, (int, float)) or pct < 100.0:
                errors.append("%s 覆盖率不足：%r（要求 100%%）" % (uid, pct))
                if status == "PASS":
                    status = "INCOMPLETE"
            if cov.get("complete") is False:
                errors.append("%s 的 coverage.complete=false" % uid)
                if status == "PASS":
                    status = "INCOMPLETE"
        seen.add(uid)
        unit_rows.append({
            "unit_id": uid,
            "gate": u["gate"],
            "status": status,
            "reason": d.get("reason", ""),
            "findings": findings,
            "blocking": len(blocking),
            "output": u["output"],
        })

    # 计划外单元
    extra = []
    for p in res_dir.rglob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(d, dict) and d.get("unit_id") and d["unit_id"] not in planned:
            extra.append(d["unit_id"])
    if extra:
        errors.append("发现计划外单元（不予采纳）：%s" % ", ".join(sorted(set(extra))))

    # 按 gate 合并
    gates: dict[str, dict] = {}
    for row in unit_rows:
        g = gates.setdefault(row["gate"], {"units": [], "status": None, "blocking": 0})
        g["units"].append(row["unit_id"])
        g["blocking"] += row.get("blocking", 0)
        # ★ 从 None 起算，不能从 PASS 起算：否则一个只有 not_applicable 单元的门
        #   会被显示成 PASS（"没基线没验" 被读成 "回归通过"），就是假绿。
        cur = row["status"]
        if g["status"] is None or ORDER.get(cur, 2) > ORDER.get(g["status"], 1):
            g["status"] = cur

    # 总判：FAIL > INCOMPLETE > PASS；not_applicable 不阻断，但也不等于通过
    gate_statuses = [g["status"] for g in gates.values()]
    if any(s == "FAIL" for s in gate_statuses):
        decision = "FAIL"
    elif any(s == "INCOMPLETE" for s in gate_statuses):
        decision = "INCOMPLETE"
    elif any(s == "PASS" for s in gate_statuses):
        decision = "PASS"
    else:
        decision = "INCOMPLETE"   # 全部门都是 not_applicable：什么都没验，不能算通过
    na_gates = sorted(k for k, v in gates.items() if v["status"] == "not_applicable")

    merged = {
        "schema": "gate-merge/1",
        "task_dir": plan.get("task_dir"),
        "source_digest": plan.get("source_digest"),
        "decision": decision,
        "gates": {k: {"status": v["status"], "units": v["units"],
                      "blocking": v["blocking"]} for k, v in sorted(gates.items())},
        "units": unit_rows,
        "not_applicable_gates": na_gates,
        "missing": [u for u in planned if u not in seen and planned[u].get("kind") != "merge"],
        "errors": errors,
        "note": "缺单元一律 INCOMPLETE；Gate C blocking 不可豁免。",
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    print("decision:", decision)
    for k, v in sorted(gates.items()):
        print("  gate %-4s %-14s units=%d blocking=%d"
              % (k, v["status"], len(v["units"]), v["blocking"]))
    if merged["missing"]:
        print("  MISSING:", ", ".join(merged["missing"]))
    for e in errors:
        print("  ERROR:", e)
    print("written:", out)
    return {"PASS": 0, "FAIL": 1}.get(decision, 2)


if __name__ == "__main__":
    sys.exit(main())
