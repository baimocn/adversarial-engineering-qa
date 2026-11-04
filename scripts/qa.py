#!/usr/bin/env python3
"""qa.py —— 质检流水线的统一入口与状态机。

★ 要解决的痛点

  当前形态是「技能 = 一套提示词 + 一堆脚本」。换个宿主（WorkBuddy / zcode / 你自己敲 /
  CI）就要人肉转述上下文：「上一步做到哪了」「哪个 worklist 还没填」「合并过了吗」。
  转述本身会失真，而且换一次宿主就要重讲一遍。

  工程化的做法：**把会话上下文外化成一份状态文件**。任何宿主都只做两件事——
  读 `state.json` 知道下一步，执行那一步，写回状态。不需要知道对话历史。

★ 工作区布局（一个待检对象一个工作区，可多宿主共享）

  <ws>/
    state.json              唯一真相：各阶段状态、产物路径、下一步
    evidence/               collect_evidence 的产物（manifest / shards / symbols）
    plan.json               分派计划
    worklist/shard-*.json   强制核对清单（**唯一需要模型填的东西**）
    gates/*.json            各单元结果
    coverage/*.json         覆盖率报告
    report.json             合并总判
    handoff.md              给另一个宿主的交接说明（可直接粘贴）

★ 命令

  python scripts/qa.py init    --task-dir <task> --workspace <ws> [--label v25]
  python scripts/qa.py run     --workspace <ws> [--stage evidence|plan|worklist|scripts]
  python scripts/qa.py status  --workspace <ws> [--json]
  python scripts/qa.py pending --workspace <ws> [--json]
  python scripts/qa.py check   --workspace <ws>
  python scripts/qa.py merge   --workspace <ws>
  python scripts/qa.py handoff --workspace <ws> [--out <file>]
  python scripts/qa.py all     --workspace <ws>

退出码：0 正常；1 有阻断（check 不过 / merge FAIL）；2 用法或前置缺失。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import validate_coverage as vc  # noqa: E402

SCHEMA = "qa-state/1"
PY = sys.executable
ENV_NO_PYC = {"PYTHONDONTWRITEBYTECODE": "1"}

STAGES = ["evidence", "plan", "worklist", "scripts", "platform", "check", "merge",
          "official", "review", "integrate"]
NEEDS = {
    "evidence": [],
    "plan": ["evidence"],
    "worklist": ["evidence"],
    "scripts": [],
    "platform": [],
    "check": ["worklist"],
    "merge": ["plan"],
    # 官方标准层：run → review → integrate
    "official": [],
    "review": ["official"],
    "integrate": ["review"],
}


# ────────────────────────── 基础工具 ──────────────────────────

def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def sha256_file(p: Path):
    h = hashlib.sha256()
    try:
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
    except OSError:
        return None
    return h.hexdigest()


def task_identity(task: Path) -> dict:
    """不执行任何代码的身份固定：文件数 + 顶层关键文件的哈希。"""
    files = [p for p in task.rglob("*") if p.is_file()]
    keys = {}
    for name in ("instruction.md", "task.toml"):
        p = task / name
        if p.is_file():
            keys[name] = sha256_file(p)
    rel = sorted(str(p.relative_to(task)).replace("\\", "/") for p in files)
    agg = hashlib.sha256("\n".join(rel).encode("utf-8")).hexdigest()
    return {"task_dir": str(task), "file_count": len(files),
            "path_list_sha256": agg, "key_files": keys}


def load_state(ws: Path) -> dict:
    p = ws / "state.json"
    if not p.is_file():
        raise SystemExit("FATAL: 工作区没有 state.json，先跑 qa.py init（%s）" % ws)
    return json.loads(p.read_text(encoding="utf-8"))


def save_state(ws: Path, st: dict):
    st["updated_at"] = now()
    (ws / "state.json").write_text(
        json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def run_script(name: str, args: list):
    cmd = [PY, "-B", str(HERE / name)] + [str(a) for a in args]
    import os
    env = dict(os.environ, **ENV_NO_PYC)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def mark(st: dict, stage: str, status: str, detail: str = "", rc: int | None = None):
    st.setdefault("stages", {})[stage] = {
        "status": status, "rc": rc, "at": now(), "detail": detail[:500],
    }


# ────────────────────────── 槽位统计 ──────────────────────────

def worklist_files(ws: Path) -> list[Path]:
    d = ws / "worklist"
    return sorted(d.glob("shard-*.json")) if d.is_dir() else []


def slot_summary(wl: dict) -> dict:
    """统计一个清单还剩多少槽没填（只读，不写文件）。"""
    errs_f, errs_d, errs_h, errs_m = [], [], [], []
    f_ok, f_all = vc.check_files(wl, errs_f, None)
    d_ok, d_all = vc.check_decls(wl, errs_d)
    h_ok, h_all = vc.check_hotspots(wl, errs_h)
    m_ok, m_all = vc.check_mirrors(wl, errs_m)
    questions = 0
    for h in wl.get("hotspots") or []:
        if not h.get("same_as"):
            questions += len(h.get("questions") or [])
    return {
        "shard": wl.get("shard"),
        "group": wl.get("group"),
        "files": {"ok": f_ok, "required": f_all},
        "declarations": {"ok": d_ok, "required": d_all},
        "hotspots": {"ok": h_ok, "required": h_all},
        "mirrors": {"ok": m_ok, "required": m_all},
        "questions_to_answer": questions,
        "open_slots": (f_all - f_ok) + (d_all - d_ok) + (h_all - h_ok) + (m_all - m_ok),
        "errors": errs_f + errs_d + errs_h + errs_m,
    }


def all_slots(ws: Path) -> list[dict]:
    return [slot_summary(json.loads(p.read_text(encoding="utf-8")))
            for p in worklist_files(ws)]


# ────────────────────────── 命令实现 ──────────────────────────

def cmd_init(a):
    task = Path(a.task_dir).resolve()
    if not task.is_dir():
        print("FATAL: task-dir 不存在:", task)
        return 2
    ws = Path(a.workspace).resolve()
    ws.mkdir(parents=True, exist_ok=True)
    st = {
        "schema": SCHEMA,
        "label": a.label or task.name,
        "identity": task_identity(task),
        "intensity": a.intensity,
        "baseline": a.baseline,
        "zip": str(Path(a.zip).resolve()) if getattr(a, "zip", None) else None,
        "created_at": now(),
        "stages": {},
        "artifacts": {},
    }
    save_state(ws, st)
    print("workspace:", ws)
    print("identity :", json.dumps(st["identity"], ensure_ascii=False))
    print("state    :", ws / "state.json")
    print("\n下一步: python scripts/qa.py run --workspace \"%s\"" % ws)
    return 0


def _stage_evidence(ws: Path, st: dict):
    task = st["identity"]["task_dir"]
    ev = ws / "evidence"
    rc, out = run_script("collect_evidence.py", ["--root", task, "--out", ev])
    if rc == 0 and (ev / "manifest.json").is_file():
        st["artifacts"]["evidence"] = str(ev)
        mark(st, "evidence", "done", "manifest.json 已生成")
    else:
        mark(st, "evidence", "failed", out, rc)
    return rc, out


def _stage_plan(ws: Path, st: dict):
    task = st["identity"]["task_dir"]
    ev = ws / "evidence"
    plan = ws / "plan.json"
    args = ["--task-dir", task, "--evidence-dir", ev, "--out", plan]
    if st.get("baseline"):
        args += ["--baseline", st["baseline"]]
    rc, out = run_script("plan_gate_dispatch.py", args)
    if rc == 0:
        st["artifacts"]["plan"] = str(plan)
        mark(st, "plan", "done", "plan.json 已生成")
    else:
        mark(st, "plan", "failed", out, rc)
    return rc, out


def _stage_worklist(ws: Path, st: dict):
    task = st["identity"]["task_dir"]
    ev = ws / "evidence"
    out_dir = ws / "worklist"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rc, out = run_script("build_review_worklist.py",
                         ["--evidence-dir", ev, "--task-dir", task, "--all",
                          "--outdir", out_dir, "--intensity", st.get("intensity", "standard")])
    if rc == 0:
        st["artifacts"]["worklist"] = str(out_dir)
        mark(st, "worklist", "done", "清单已生成，等待填写")
    else:
        mark(st, "worklist", "failed", out, rc)
    return rc, out


def _stage_scripts(ws: Path, st: dict):
    """确定性脚本：Gate C-1 静态扫描 + 证据索引自检。"""
    task = st["identity"]["task_dir"]
    gates = ws / "gates"
    gates.mkdir(parents=True, exist_ok=True)
    ex = ws / "execution-path.json"
    rc, out = run_script("check_execution_path.py", ["--root", task, "--out", ex])
    if ex.is_file():
        rep = json.loads(ex.read_text(encoding="utf-8"))
        blocking = [f for f in rep["findings"] if f["severity"] == "blocking"]
        unit = {
            "unit_id": "C1.static", "gate": "C",
            "status": "FAIL" if blocking else "PASS",
            "findings": [{"severity": "blocking", "summary": f["detail"],
                          "evidence": "%s:%d" % (f["file"], f["line"]),
                          "snippet": f["detail"]} for f in blocking],
            "reason": "check_execution_path rc=%d blocking=%d" % (rc, len(blocking)),
        }
        (gates / "C1.static.json").write_text(
            json.dumps(unit, ensure_ascii=False, indent=2), encoding="utf-8")
        st["artifacts"]["gates"] = str(gates)
        mark(st, "scripts", "done" if rc == 0 else "failed",
             "blocking=%d" % len(blocking), rc)
    else:
        mark(st, "scripts", "failed", out, rc)
    return rc, out


def _stage_platform(ws: Path, st: dict):
    """平台源包硬规则（B-C01–B-C04，2026-11 新规）。

    注意：内嵌官方层（0.3.10.5）不含这四条，且其中 B-C02 与旧口径
    「填写 docker_image」正面翻转——本阶段以带日期的新平台规则为准，
    冲突在 review 中显式记录，不静默沿用旧规则。
    """
    task = st["identity"]["task_dir"]
    out = ws / "platform-rules.json"
    rc, txt = run_script("check_platform_rules.py", ["--root", task, "--out", out])
    if out.is_file():
        rep = json.loads(out.read_text(encoding="utf-8"))
        st["artifacts"]["platform_rules"] = str(out)
        fails = rep["summary"].get("fail", 0)
        st["artifacts"]["platform_fail"] = fails
        # 违规是数据不是流水线故障：报告写出即视为阶段完成，让 official/review/integrate
        # 继续跑（「发现 FAIL 不阻止继续完成其余审查」）；总判由合并层取最严格结论。
        mark(st, "platform", "done",
             "B-C01–B-C04: fail=%d needs_manual=%d"
             % (fails, rep["summary"].get("needs_manual", 0)), rc)
        return 0, txt
    mark(st, "platform", "failed", txt, rc)
    return rc, txt


def _stage_check(ws: Path, st: dict):
    cov = ws / "coverage"
    cov.mkdir(parents=True, exist_ok=True)
    bad = 0
    lines = []
    for wl_p in worklist_files(ws):
        out = cov / wl_p.name
        res_p = ws / "gates" / ("B.%s" % wl_p.stem.replace("shard-", "shard-") + ".json")
        args = ["--worklist", wl_p, "--out", out]
        if res_p.is_file():
            args += ["--result", res_p]
        rc, txt = run_script("validate_coverage.py", args)
        bad += (rc != 0)
        lines.append("%s rc=%d" % (wl_p.name, rc))
    st["artifacts"]["coverage"] = str(cov)
    mark(st, "check", "done" if bad == 0 else "incomplete",
         "%d/%d 清单完整" % (len(worklist_files(ws)) - bad, len(worklist_files(ws))),
         0 if bad == 0 else 1)
    return (0 if bad == 0 else 1), "\n".join(lines)


def _stage_merge(ws: Path, st: dict):
    plan = ws / "plan.json"
    out = ws / "report.json"
    rc, txt = run_script("merge_gate_results.py",
                         ["--plan", plan, "--results-dir", ws, "--out", out])
    if out.is_file():
        rep = json.loads(out.read_text(encoding="utf-8"))
        st["artifacts"]["report"] = str(out)
        mark(st, "merge", "done" if rep["decision"] == "PASS" else rep["decision"].lower(),
             "decision=%s missing=%d errors=%d"
             % (rep["decision"], len(rep.get("missing") or []), len(rep.get("errors") or [])),
             rc)
    else:
        mark(st, "merge", "failed", txt, rc)
    return rc, txt


def _stage_official(ws: Path, st: dict):
    """跑官方标准层：audit_standard_with_waivers.py（未填底稿时必然 NOT_FINISHED）。"""
    zip_p = st.get("zip")
    if not zip_p or not Path(zip_p).is_file():
        mark(st, "official", "failed", "state 里没有可用的 zip；init 时用 --zip 指定", 2)
        return 2, "缺 zip"
    rc, out = run_script("qa_official.py", ["run", "--workspace", ws, "--zip", zip_p])
    rep = json.loads((ws / "official" / "report.json").read_text(encoding="utf-8")) \
        if (ws / "official" / "report.json").is_file() else {}
    ok = (ws / "official" / "standard" / "report.json").is_file()
    st["artifacts"]["official"] = str(ws / "official")
    mark(st, "official", "done" if ok else "failed",
         "官方 decision=%s code=%s" % (rep.get("decision"), rep.get("code")), rc)
    return (0 if ok else 2), out


def _stage_review(ws: Path, st: dict):
    rc, out = run_script("qa_official.py", ["review", "--workspace", ws])
    rv = ws / "official" / "review.json"
    if rv.is_file():
        rows = json.loads(rv.read_text(encoding="utf-8")).get("checks") or []
        cnt = {"pass": 0, "fail": 0, "manual": 0}
        for r in rows:
            cnt[r.get("status")] = cnt.get(r.get("status"), 0) + 1
        st["artifacts"]["official_review"] = str(rv)
        mark(st, "review", "done",
             "pass=%d fail=%d manual=%d" % (cnt["pass"], cnt["fail"], cnt["manual"]), rc)
    else:
        mark(st, "review", "failed", out, rc)
    return rc, out


def _stage_integrate(ws: Path, st: dict):
    rc, out = run_script("qa_official.py", ["integrate", "--workspace", ws])
    up = ws / "unified.json"
    if up.is_file():
        u = json.loads(up.read_text(encoding="utf-8"))
        st["artifacts"]["unified"] = str(up)
        mark(st, "integrate", "done" if u.get("overall") != "FAIL" else "fail",
             "overall=%s（对抗层 %s / 官方层 %s）"
             % (u.get("overall"), u["adversarial"]["decision"], u["official"]["decision"]), rc)
    else:
        mark(st, "integrate", "failed", out, rc)
    return rc, out


STAGE_FN = {
    "evidence": _stage_evidence,
    "plan": _stage_plan,
    "worklist": _stage_worklist,
    "scripts": _stage_scripts,
    "platform": _stage_platform,
    "check": _stage_check,
    "merge": _stage_merge,
    "official": _stage_official,
    "review": _stage_review,
    "integrate": _stage_integrate,
}


def cmd_run(a):
    ws = Path(a.workspace).resolve()
    st = load_state(ws)
    stages = [a.stage] if a.stage else [s for s in STAGES if s not in ("check", "merge")]
    rc_all = 0
    for s in stages:
        miss = [d for d in NEEDS[s]
                if st.get("stages", {}).get(d, {}).get("status") != "done"]
        if miss:
            print("[%-9s] SKIP 前置未完成: %s" % (s, ", ".join(miss)))
            rc_all = rc_all or 2
            continue
        rc, out = STAGE_FN[s](ws, st)
        save_state(ws, st)
        status = st["stages"][s]["status"]
        print("[%-9s] %-11s rc=%d  %s" % (s, status, rc, st["stages"][s]["detail"]))
        if rc != 0:
            rc_all = rc_all or rc
            break
    save_state(ws, st)
    return rc_all


def cmd_status(a):
    ws = Path(a.workspace).resolve()
    st = load_state(ws)
    slots = all_slots(ws)
    open_slots = sum(s["open_slots"] for s in slots)
    stages = st.get("stages", {})
    info = {
        "workspace": str(ws),
        "label": st.get("label"),
        "task_dir": st["identity"]["task_dir"],
        "file_count": st["identity"]["file_count"],
        "intensity": st.get("intensity"),
        "stages": {s: stages.get(s, {"status": "pending"}).get("status") for s in STAGES},
        "worklists": slots,
        "open_slots": open_slots,
        "next": _next_action(st, slots, str(ws)),
    }
    if a.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return 0

    print("工作区 : %s" % ws)
    print("对象   : %s  (%d 文件)" % (info["task_dir"], info["file_count"]))
    print("强度   : %s" % info["intensity"])
    print()
    print("%-10s %s" % ("阶段", "状态"))
    for s in STAGES:
        print("  %-8s %s" % (s, info["stages"][s]))
    if slots:
        print()
        print("%-12s %-10s %8s %8s %8s %8s" % ("shard", "group", "文件", "声明", "热点", "待填槽"))
        for s in slots:
            print("  %-10s %-8s %4d/%-3d %4d/%-3d %4d/%-3d %8d"
                  % (s["shard"], s["group"],
                     s["files"]["ok"], s["files"]["required"],
                     s["declarations"]["ok"], s["declarations"]["required"],
                     s["hotspots"]["ok"], s["hotspots"]["required"],
                     s["open_slots"]))
        print("  合计待填槽: %d" % open_slots)
    print()
    print("下一步:", info["next"]["action"])
    for line in info["next"].get("detail") or []:
        print("  " + line)
    if info["next"].get("command"):
        print("  命令:", info["next"]["command"])
    return 0


def _next_action(st: dict, slots: list[dict], ws: str = "<ws>") -> dict:
    stages = st.get("stages", {})
    for s in STAGES:
        if stages.get(s, {}).get("status") in ("done",):
            continue
        if s == "check":
            if any(x["open_slots"] > 0 for x in slots):
                todo = [x["shard"] for x in slots if x["open_slots"] > 0]
                return {
                    "action": "填写核对清单（这是唯一需要模型做的步骤）",
                    "detail": ["待填 shard: %s" % ", ".join(todo),
                               "每个清单的 files/declarations/hotspots/mirror_notes 都要填满",
                               "填完执行: python scripts/qa.py check --workspace \"%s\"" % ws],
                    "command": "qa.py check",
                }
            return {"action": "跑覆盖率校验", "detail": [], "command": "qa.py check"}
        if s == "merge":
            return {"action": "合并出总判", "detail": [], "command": "qa.py merge"}
        return {"action": "跑阶段 %s" % s, "detail": [],
                "command": "qa.py run --stage %s" % s}
    return {"action": "已完成：结论见 report.json",
            "detail": [st.get("artifacts", {}).get("report", "")], "command": ""}


def cmd_pending(a):
    ws = Path(a.workspace).resolve()
    slots = all_slots(ws)
    if a.json:
        print(json.dumps(slots, ensure_ascii=False, indent=2))
        return 0
    total = 0
    for s in slots:
        if s["open_slots"] == 0:
            continue
        total += s["open_slots"]
        print("%s (%s) 待填 %d 槽：文件 %d、声明 %d、热点 %d、副本说明 %d；需答 %d 问"
              % (s["shard"], s["group"], s["open_slots"],
                 s["files"]["required"] - s["files"]["ok"],
                 s["declarations"]["required"] - s["declarations"]["ok"],
                 s["hotspots"]["required"] - s["hotspots"]["ok"],
                 s["mirrors"]["required"] - s["mirrors"]["ok"],
                 s["questions_to_answer"]))
    print("合计待填槽: %d" % total)
    return 0


def cmd_check(a):
    ws = Path(a.workspace).resolve()
    st = load_state(ws)
    rc, txt = _stage_check(ws, st)
    save_state(ws, st)
    print(txt)
    print("覆盖率报告目录:", st["artifacts"].get("coverage"))
    return rc


def cmd_merge(a):
    ws = Path(a.workspace).resolve()
    st = load_state(ws)
    rc, txt = _stage_merge(ws, st)
    save_state(ws, st)
    print(txt.strip()[-800:])
    rep_p = ws / "report.json"
    if rep_p.is_file():
        rep = json.loads(rep_p.read_text(encoding="utf-8"))
        print("\ndecision:", rep["decision"])
        for k, v in sorted(rep["gates"].items()):
            print("  gate %-4s %-14s blocking=%d" % (k, v["status"], v["blocking"]))
        if rep.get("missing"):
            print("  MISSING:", ", ".join(rep["missing"]))
        for e in (rep.get("errors") or [])[:10]:
            print("  ERROR:", e)
    return rc


def cmd_handoff(a):
    """生成一段自包含的交接说明，可直接粘给另一个宿主（zcode / 另一个会话）。"""
    ws = Path(a.workspace).resolve()
    st = load_state(ws)
    slots = all_slots(ws)
    info_next = _next_action(st, slots, str(ws))
    stages = st.get("stages", {})

    L = []
    L.append("# 质检交接单（%s）" % st.get("label"))
    L.append("")
    L.append("> 这份文件由 `qa.py handoff` 生成，**自包含**：接手方不需要任何对话历史。")
    L.append("> 直接整段粘贴给另一个 AI 会话或另一个人即可。")
    L.append("")
    L.append("## 1. 对象与工作区（只认这两个路径，不要另建）")
    L.append("")
    L.append("```")
    L.append("待检对象 : %s" % st["identity"]["task_dir"])
    L.append("文件数   : %d" % st["identity"]["file_count"])
    L.append("工作区   : %s" % ws)
    L.append("强度     : %s" % st.get("intensity"))
    L.append("Python   : %s" % PY)
    L.append("```")
    L.append("")
    L.append("## 2. 已完成 / 待办")
    L.append("")
    L.append("| 阶段 | 状态 |")
    L.append("|---|---|")
    for s in STAGES:
        L.append("| %s | %s |" % (s, stages.get(s, {}).get("status", "pending")))
    L.append("")
    L.append("## 3. 你现在要做的一件事")
    L.append("")
    L.append("**%s**" % info_next["action"])
    L.append("")
    for d in info_next.get("detail") or []:
        L.append("- %s" % d)
    L.append("")
    if slots and any(x["open_slots"] > 0 for x in slots):
        L.append("## 4. 待填清单（路径是绝对的，直接打开填）")
        L.append("")
        L.append("| 清单 | 组 | 文件 | 声明 | 热点 | 待填槽 | 需答问题 |")
        L.append("|---|---|---|---|---|---|---|")
        for s in slots:
            L.append("| `%s` | %s | %d/%d | %d/%d | %d/%d | %d | %d |"
                     % (ws / "worklist" / ("%s.json" % s["shard"]), s["group"],
                        s["files"]["ok"], s["files"]["required"],
                        s["declarations"]["ok"], s["declarations"]["required"],
                        s["hotspots"]["ok"], s["hotspots"]["required"],
                        s["open_slots"], s["questions_to_answer"]))
        L.append("")
    L.append("## 5. 填写规则（原样照做，不许改口径）")
    L.append("")
    L.append("1. `files`：每项填 `disposition`（read / skim / skip）+ `reason`；skim、skip 必须写理由。")
    L.append("2. `declarations`：`must_bind=true` 的填 `bound_to`（`file:line` 或 `no_implementation`）+ `verdict`（holds / violated / unverifiable）；写 `no_implementation` 必须给 `note`。")
    L.append("3. `hotspots`：`same_as` 非空的不用答；其余 `answers` 条数必须与 `questions` 一一对应，不许留空。")
    L.append("4. `mirror_notes`：每组的差异必须说明「是否有意」「会不会被一致性校验误判」。")
    L.append("5. `findings`：每条必须有 `evidence`（`file:line`）+ **原文 snippet**，不接受概括。")
    L.append("6. 拿不准的写 `unverifiable` 并说明缺什么，**不要凑 holds**。")
    L.append("")
    L.append("## 6. 填完之后")
    L.append("")
    L.append("```bash")
    L.append("python scripts/qa.py check --workspace \"%s\"   # 覆盖率不满 100%% 会拒收" % ws)
    L.append("python scripts/qa.py merge --workspace \"%s\"   # 出总判" % ws)
    L.append("```")
    L.append("")
    L.append("## 7. 硬约束（违反即作废）")
    L.append("")
    L.append("- 不得修改「待检对象」目录里的任何文件。")
    L.append("- 不得把 blocking 降级成 major，不得给自己加豁免。")
    L.append("- 缺任一单元 ⇒ 总判 INCOMPLETE，不得当成通过。")
    L.append("- 覆盖率 100% 只说明「该看的都看了」，不说明「看对了」；不得据此推断结论可靠。")

    text = "\n".join(L) + "\n"
    out = Path(a.out) if a.out else (ws / "handoff.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print("written:", out)
    print("（整份粘贴给接手方即可，无需再转述任何上下文）")
    return 0


def cmd_all(a):
    ws = Path(a.workspace).resolve()
    st = load_state(ws)
    for s in ("evidence", "plan", "worklist", "scripts", "platform"):
        miss = [d for d in NEEDS[s] if st.get("stages", {}).get(d, {}).get("status") != "done"]
        if miss:
            print("[%-9s] SKIP 前置未完成: %s" % (s, ", ".join(miss)))
            save_state(ws, st)
            return 2
        rc, _ = STAGE_FN[s](ws, st)
        save_state(ws, st)
        print("[%-9s] %-11s %s" % (s, st["stages"][s]["status"],
                                   st["stages"][s]["detail"]))
        if rc != 0:
            return rc
    print("\n确定性部分已完成。下一步需要人工/模型填写 worklist：")
    print("  python scripts/qa.py pending --workspace \"%s\"" % ws)
    print("  python scripts/qa.py handoff --workspace \"%s\"" % ws)
    return 0


def main():
    ap = argparse.ArgumentParser(description="质检流水线统一入口")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init"); p.add_argument("--task-dir", required=True)
    p.add_argument("--zip", default=None, help="提交包 zip（官方层要它）")
    p.add_argument("--workspace", required=True); p.add_argument("--label", default=None)
    p.add_argument("--intensity", default="standard", choices=["light", "standard", "strict"])
    p.add_argument("--baseline", default=None); p.set_defaults(fn=cmd_init)

    p = sub.add_parser("run"); p.add_argument("--workspace", required=True)
    p.add_argument("--stage", default=None, choices=STAGES); p.set_defaults(fn=cmd_run)

    p = sub.add_parser("status"); p.add_argument("--workspace", required=True)
    p.add_argument("--json", action="store_true"); p.set_defaults(fn=cmd_status)

    p = sub.add_parser("pending"); p.add_argument("--workspace", required=True)
    p.add_argument("--json", action="store_true"); p.set_defaults(fn=cmd_pending)

    p = sub.add_parser("check"); p.add_argument("--workspace", required=True)
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("merge"); p.add_argument("--workspace", required=True)
    p.set_defaults(fn=cmd_merge)

    p = sub.add_parser("handoff"); p.add_argument("--workspace", required=True)
    p.add_argument("--out", default=None); p.set_defaults(fn=cmd_handoff)

    p = sub.add_parser("all"); p.add_argument("--workspace", required=True)
    p.set_defaults(fn=cmd_all)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
