#!/usr/bin/env python3
"""执行层门禁（Gate C · 诚实候选冒烟）：把候选原样跑一遍，必须能出分。

★ 为什么这条最重要（2026-10-30，从 11 份官方报告反推）：

  平台 `0.3.10-standard-waiver.5-toolfix.2` 抓出的 0340 三条剩余 fail，
  **全部是「诚实候选拿不到分」**，没有一条是「候选能作弊」：

    QA05  静态 G6 剥了 docstring，运行时指纹没剥
          ⇒ starter 与可信副本方法体一字不差，却被判「篡改」⇒ −1
    QA06  父进程把动作构造成 np.ndarray 传给 TensorWrapper.step，
          包装器第一行是 action.numpy() ⇒ 首步 AttributeError ⇒ −1
    QA11  题面说超时属基础设施，实现里 timeout 不在 infra 前缀表 ⇒ 归候选 −1

  而我方 8 轮迭代、五路对抗复核，查的全是「候选怎么作弊」。
  这一类缺陷的共同特征是：**只有真跑一遍才会暴露，静态查「安全检查够不够严」永远查不到**。

  所以这道门禁的判据只有一句话：
    **拿题目自带的 starter / reference 原样当候选，跑一遍，必须拿到分。**

用法（两种）：

  1) 显式命令（推荐，可移植到任何任务）：
     python scripts/check_honest_candidate.py \
       --task-dir <harbor_task> --candidate <candidate_dir> \
       --cmd "{py} -B {entry} --solution_dir {candidate} --out {out}" \
       --out execution-honest.json

     占位符：{py} {entry} {candidate} {task_dir} {out} {ckpt}
     `{entry}` 自动取 tests/ 下第一个含 --solution_dir 的脚本。

  2) 自动探测：省略 --cmd，脚本会找 tests/ 下的评测入口并尝试 --episodes 1。
     探测失败会明确报 needs_manual，不假装通过。

退出码：0 = 未见崩溃且拿到分；1 = blocking；2 = 无法执行（needs_manual）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

# 崩溃签名 → 归因。顺序即优先级（越具体的越前）。
CRASH_SIGNATURES = [
    (re.compile(r"frozen_method_tampered|frozen method tampered", re.I),
     "fingerprint_false_positive",
     "冻结面指纹把诚实候选判成篡改（QA05 形态：docstring/常量口径不一致）"),
    (re.compile(r"'numpy\.ndarray' object has no attribute '(numpy|detach|cpu|to)'", re.I),
     "tensor_api_mismatch",
     "numpy 数组被当作张量使用（QA06 形态：包装器调 action.numpy()）"),
    (re.compile(r"too many values to unpack|not enough values to unpack|"
                r"cannot unpack non-iterable", re.I),
     "return_contract_mismatch",
     "返回值元数与调用方解包不一致（2001 形态：3 返 2 收）"),
    (re.compile(r"act_exception", re.I),
     "policy_chain_exception",
     "动作通道抛异常（评分链对诚实候选不可用）"),
    (re.compile(r"mat1 and mat2 must have the same dtype|"
                r"expected scalar type .* but found", re.I),
     "dtype_mismatch",
     "张量 dtype 不一致（权重 float32 vs 输入 float64）"),
    (re.compile(r"ModuleNotFoundError|ImportError: cannot import name", re.I),
     "import_error",
     "导入失败（环境/依赖与题面声明不符）"),
]

GENERIC_TRACEBACK = re.compile(r"Traceback \(most recent call last\)")


def find_entry(task_dir: Path) -> Path | None:
    """在 tests/ 下找带 --solution_dir 的评测脚本。"""
    tests = task_dir / "tests"
    if not tests.is_dir():
        return None
    cands = []
    for p in sorted(tests.glob("*.py")):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "--solution_dir" in text and "argparse" in text:
            # 优先名字里带 evaluate / verify 的
            score = 0 if re.search(r"(evaluate|verify|grade|score)", p.name, re.I) else 1
            cands.append((score, p))
    if not cands:
        return None
    cands.sort(key=lambda x: (x[0], x[1].name))
    return cands[0][1]


def classify(text: str):
    for pat, kind, desc in CRASH_SIGNATURES:
        m = pat.search(text)
        if m:
            line = text[:m.start()].count("\n") + 1
            return {"type": kind, "detail": desc, "matched": m.group(0)[:160]}
    if GENERIC_TRACEBACK.search(text):
        return {"type": "unclassified_crash",
                "detail": "出现未归类的 Traceback（需人工看堆栈）",
                "matched": "Traceback"}
    return None


def parse_score(out_path: Path):
    """从评测产物里尽力取分。取不到就返回 None（不臆造）。"""
    if not out_path.is_file():
        return None
    try:
        d = json.loads(out_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(d, dict):
        return None
    # 常见字段名，按优先级
    for k in ("episode_reward_mean", "score", "mean_reward", "reward_mean",
              "final_score", "total_reward"):
        v = d.get(k)
        if isinstance(v, (int, float)):
            return {"field": k, "value": float(v)}
    # 嵌一层
    for k in ("result", "metrics", "eval"):
        sub = d.get(k)
        if isinstance(sub, dict):
            for kk in ("episode_reward_mean", "score", "mean_reward"):
                v = sub.get(kk)
                if isinstance(v, (int, float)):
                    return {"field": "%s.%s" % (k, kk), "value": float(v)}
    return None


def pick_candidate(task_dir: Path, explicit: str | None) -> tuple[Path | None, str]:
    if explicit:
        p = Path(explicit).resolve()
        return (p, "explicit") if p.is_dir() else (None, "explicit-missing")
    for name in ("reference", "solution"):
        p = task_dir / name
        if p.is_dir():
            return p, name
    return None, "not-found"


def main():
    ap = argparse.ArgumentParser(description="Gate C · 诚实候选冒烟")
    ap.add_argument("--task-dir", required=True, help="harbor_task 根目录")
    ap.add_argument("--candidate", default=None,
                    help="候选目录（默认 reference → solution）")
    ap.add_argument("--cmd", default=None,
                    help="命令模板，占位符 {py} {entry} {candidate} {task_dir} {out} {ckpt}")
    ap.add_argument("--ckpt", default=None, help="可选权重路径，供 {ckpt} 占位符")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--stdin-file", default=None,
                    help="协议型评测器：把该文件内容喂给 stdin（如 policy_only 的 init/obs/bye 序列）")
    ap.add_argument("--out", required=True, help="JSON 报告输出路径")
    ap.add_argument("--allow-missing-score", action="store_true",
                    help="只要不崩就算过（默认要求拿到分）")
    args = ap.parse_args()

    task_dir = Path(args.task_dir).resolve()
    report = {
        "gate": "honest_candidate",
        "task_dir": str(task_dir),
        "candidate": None,
        "command": None,
        "elapsed_sec": None,
        "returncode": None,
        "crash": None,
        "score": None,
        "verdict": None,
        "reason": None,
    }

    if not task_dir.is_dir():
        report.update(verdict="needs_manual", reason="task-dir 不存在")
        _write(args.out, report)
        print("FATAL: task-dir not found:", task_dir)
        return 2

    cand, how = pick_candidate(task_dir, args.candidate)
    if cand is None:
        report.update(verdict="needs_manual",
                      reason="找不到候选目录（%s）；请用 --candidate 指定" % how)
        _write(args.out, report)
        print("NEEDS_MANUAL:", report["reason"])
        return 2
    report["candidate"] = str(cand)
    report["candidate_origin"] = how

    entry = find_entry(task_dir)
    out_json = Path(args.out).resolve().parent / "_honest_out.json"

    if args.cmd:
        tmpl = args.cmd
        cmd = tmpl.format(py=sys.executable,
                          entry=str(entry) if entry else "",
                          candidate=str(cand),
                          task_dir=str(task_dir),
                          out=str(out_json),
                          ckpt=args.ckpt or "")
    else:
        if entry is None:
            report.update(verdict="needs_manual",
                          reason="未找到评测入口（tests/ 下无 --solution_dir 脚本）；请用 --cmd 指定")
            _write(args.out, report)
            print("NEEDS_MANUAL:", report["reason"])
            return 2
        cmd = [sys.executable, "-B", str(entry),
               "--solution_dir", str(cand), "--out", str(out_json)]
        if args.ckpt:
            cmd += ["--ckpt", args.ckpt]
        # 未知任务可能还缺必填参数，跑失败会落在 needs_manual
    if isinstance(cmd, str):
        cmd = shlex.split(cmd, posix=(os.name != "nt"))
    report["command"] = cmd

    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    stdin_payload = None
    if args.stdin_file:
        sf = Path(args.stdin_file)
        if not sf.is_file():
            report.update(verdict="needs_manual", reason="stdin-file 不存在：%s" % sf)
            _write(args.out, report)
            print("NEEDS_MANUAL:", report["reason"])
            return 2
        stdin_payload = sf.read_text(encoding="utf-8", errors="replace")
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=str(task_dir), input=stdin_payload,
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           timeout=args.timeout, env=env)
        elapsed = time.time() - t0
        text = (r.stdout or "") + "\n" + (r.stderr or "")
        report.update(elapsed_sec=round(elapsed, 1), returncode=r.returncode)
        crash = classify(text)
        report["crash"] = crash
        report["score"] = parse_score(out_json)

        if crash:
            report.update(verdict="blocking",
                          reason="诚实候选在评分链上崩溃：%s（%s）"
                                 % (crash["type"], crash["detail"]))
        elif report["score"] is None and not args.allow_missing_score:
            report.update(verdict="needs_manual",
                          reason="未见崩溃，但也没解析到分数（需人工确认产物字段）")
        else:
            report.update(verdict="pass", reason="诚实候选跑通并出分")
    except subprocess.TimeoutExpired:
        report.update(elapsed_sec=args.timeout, verdict="blocking",
                      reason="诚实候选超过 %ds 未完成（疑似死锁或复杂度失控）"
                             % args.timeout)
    except OSError as e:
        report.update(verdict="needs_manual", reason="无法执行命令：%s" % e)

    _write(args.out, report)
    print("candidate:", report["candidate"], "(%s)" % report.get("candidate_origin"))
    print("command:", " ".join(shlex.quote(c) for c in report["command"])[:300])
    print("rc=%s elapsed=%ss" % (report["returncode"], report["elapsed_sec"]))
    if report["crash"]:
        print("  CRASH [%s] %s" % (report["crash"]["type"], report["crash"]["detail"]))
        print("  matched:", report["crash"]["matched"])
    if report["score"]:
        print("  score: %s = %s" % (report["score"]["field"], report["score"]["value"]))
    print("verdict: %s — %s" % (report["verdict"], report["reason"]))
    print("written:", args.out)
    return {"pass": 0, "blocking": 1, "needs_manual": 2}[report["verdict"]]


def _write(path, report):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
