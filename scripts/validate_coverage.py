#!/usr/bin/env python3
"""核对清单完整性校验：把「读了没」从自述变成机器可判。

★ 它**不判断结论对不对**，只判断「该看的都看了、该绑的都绑了」。
  这是能机械保证的部分；剩下的语义正确性靠抽检与第二路独立红队。

检查项（任一不满足即 rc=1）：
  1. files：每项都要有 disposition ∈ {read, skim, skip}；
     skim / skip 必须给 reason（略读/跳过要说明依据，不能静默）。
  2. declarations：must_bind=true 的必须有 bound_to 与 verdict；
     bound_to="no_implementation" 时必须给 note 说明为什么题面/注释里的声明没有实现。
  3. hotspots：answers 条数必须与 questions 一致，且每条非空。
  4. result.json（若提供）：每条 finding 必须有 file:line 形式的 evidence 与 snippet。

用法：
  python scripts/validate_coverage.py --worklist <filled.json> \
      [--result <unit result.json>] --out <coverage-report.json>

退出码：0 = 完整；1 = 有缺口；2 = 用法错误。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DISP_OK = {"read", "skim", "skip"}
VERDICT_OK = {"holds", "violated", "unverifiable"}
LINE_REF = re.compile(r"^[\w./\\-]+:\d+$")


def _split_refs(ev: str) -> list[str]:
    """evidence 允许一条 finding 引用多处：`a.py:1, b.py:2` 或换行分隔。"""
    parts = re.split(r"[,;\s]+", ev.strip())
    return [p for p in parts if p]


def _all_refs_ok(ev: str) -> bool:
    refs = _split_refs(ev)
    return bool(refs) and all(LINE_REF.match(r) for r in refs)



def check_files(w, errs, gaps):
    n_ok = 0
    for f in w.get("files") or []:
        d = f.get("disposition")
        if d not in DISP_OK:
            errs.append("文件未处置：%s（disposition=%r）" % (f.get("path"), d))
            continue
        if d in ("skim", "skip") and not (f.get("reason") or "").strip():
            errs.append("文件 %s 标记 %s 但没给 reason" % (f.get("path"), d))
            continue
        n_ok += 1
    return n_ok, len(w.get("files") or [])


def check_decls(w, errs):
    n_ok = n_req = 0
    for d in w.get("declarations") or []:
        if not d.get("must_bind"):
            continue
        n_req += 1
        b = d.get("bound_to")
        v = d.get("verdict")
        if not b:
            errs.append("声明 %s 必须绑定但 bound_to 为空（%s:%s）"
                        % (d.get("id"), d.get("path"), d.get("line")))
            continue
        if b != "no_implementation" and not LINE_REF.match(str(b)):
            errs.append("声明 %s 的 bound_to 不是 file:line 形式：%r" % (d.get("id"), b))
            continue
        if b == "no_implementation" and not (d.get("note") or "").strip():
            errs.append("声明 %s 标了 no_implementation 但没写 note" % d.get("id"))
            continue
        if v not in VERDICT_OK:
            errs.append("声明 %s 的 verdict 非法：%r" % (d.get("id"), v))
            continue
        n_ok += 1
    return n_ok, n_req


def check_hotspots(w, errs):
    n_ok = 0
    hs = w.get("hotspots") or []
    for h in hs:
        qs = h.get("questions") or []
        ans = h.get("answers")
        if not isinstance(ans, list) or len(ans) != len(qs):
            errs.append("热点 %s(%s:%s) answers 条数应为 %d，实际 %r"
                        % (h.get("id"), h.get("path"), h.get("line"), len(qs),
                           len(ans) if isinstance(ans, list) else ans))
            continue
        if any(not str(a).strip() for a in ans):
            errs.append("热点 %s 有空答案" % h.get("id"))
            continue
        n_ok += 1
    return n_ok, len(hs)


def check_result(result, errs):
    n_ok = 0
    fs = result.get("findings") or []
    for i, f in enumerate(fs):
        ev = str(f.get("evidence") or "")
        if not _all_refs_ok(ev):
            errs.append("finding[%d] 的 evidence 不是 file:line 列表：%r" % (i, ev[:80]))
            continue
        if not str(f.get("snippet") or "").strip():
            errs.append("finding[%d] 缺 snippet（必须贴原文，不允许概括）" % i)
            continue
        n_ok += 1
    return n_ok, len(fs)


def check_mirrors(w, errs):
    """同源副本差异必须有说明：这是 0340 QA05 的唯一发现路径。"""
    notes = w.get("mirror_notes")
    if not isinstance(notes, dict):
        return 0, 0
    ok = 0
    for key, val in notes.items():
        if not str(val or "").strip():
            errs.append("同源副本组 %s 内容不同但 mirror_notes 为空（必须逐条说明差异是否有意）"
                        % key)
        else:
            ok += 1
    return ok, len(notes)


def main():
    ap = argparse.ArgumentParser(description="核对清单完整性校验")
    ap.add_argument("--worklist", required=True)
    ap.add_argument("--result", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    p = Path(args.worklist)
    if not p.is_file():
        print("FATAL: worklist 不存在:", p)
        return 2
    w = json.loads(p.read_text(encoding="utf-8"))
    errs: list[str] = []

    f_ok, f_all = check_files(w, errs, None)
    d_ok, d_all = check_decls(w, errs)
    h_ok, h_all = check_hotspots(w, errs)
    m_ok, m_all = check_mirrors(w, errs)

    r_ok = r_all = 0
    if args.result:
        rp = Path(args.result)
        if not rp.is_file():
            errs.append("指定了 --result 但文件不存在：%s" % rp)
        else:
            r_ok, r_all = check_result(json.loads(rp.read_text(encoding="utf-8")), errs)

    total_req = f_all + d_all + h_all + r_all + m_all
    total_ok = f_ok + d_ok + h_ok + r_ok + m_ok
    cov = (100.0 * total_ok / total_req) if total_req else 100.0
    report = {
        "schema": "coverage-report/1",
        "worklist": str(p),
        "shard": w.get("shard"),
        "group": w.get("group"),
        "counts": {
            "files": {"ok": f_ok, "required": f_all},
            "declarations_must_bind": {"ok": d_ok, "required": d_all},
            "hotspots": {"ok": h_ok, "required": h_all},
            "mirror_sets": {"ok": m_ok, "required": m_all},
            "findings": {"ok": r_ok, "required": r_all} if args.result else None,
        },
        "coverage_pct": round(cov, 1),
        "complete": not errs,
        "errors": errs,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("shard=%s group=%s" % (w.get("shard"), w.get("group")))
    print("  files      %d/%d" % (f_ok, f_all))
    print("  decls      %d/%d (must_bind)" % (d_ok, d_all))
    print("  hotspots   %d/%d" % (h_ok, h_all))
    print("  mirrors    %d/%d" % (m_ok, m_all))
    if args.result:
        print("  findings   %d/%d" % (r_ok, r_all))
    print("  coverage   %.1f%%   complete=%s" % (cov, report["complete"]))
    for e in errs[:20]:
        print("  GAP:", e)
    if len(errs) > 20:
        print("  ... 另有 %d 条" % (len(errs) - 20))
    print("written:", out)
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
