#!/usr/bin/env python3
"""官方标准层（QA01–QA21 + G01–G03 + Harbor 六项）的编排与底稿生成。

★ 为什么必须单列一层

  本 skill 原有的 Gate A/B/C 是「对抗层」：查的是候选能不能作弊、诚实候选能不能跑通。
  官方 skill 的 21 项是「标准层」：查的是题包作为**交付物**是否合格（题面信息、
  评分公式、锚点可分辨性、NOP、指纹、资源时长、轨迹）。两层编号互不相通。

  实测代价（AutoRe1841）：只跑对抗层时，「NOP 记录早于题包最后两次修改」这类
  结构性问题完全看不见 —— 因为对抗层根本不看 NOP 与指纹。

★ 三层判定，不许混

  mechanical  规则可判（数值/布尔/文件存在），脚本给结论 + 证据
  manual      需要读语义，脚本只**预填证据**并写明还缺什么，status 留 manual
  blocked     前置缺失（如官方报告没跑），不猜

  **manual 不许自动转成 pass。** 官方脚本明写 STANDARD_MANUAL_REVIEW_NOT_FINISHED：
  「原 manual 仍需质检员审明，不能自动转为作者失败」——同样也不能自动转成通过。

用法：
  python scripts/qa_official.py run       --workspace <ws> --task-dir <task> --zip <submission.zip>
  python scripts/qa_official.py review    --workspace <ws>
  python scripts/qa_official.py integrate --workspace <ws>
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent
OFFICIAL_SKILL = SKILL_ROOT / "official" / "autoresearch-task-qa-legacy-waiver"
AUDITOR = OFFICIAL_SKILL / "scripts" / "audit_standard_with_waivers.py"
PY = sys.executable


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def read_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


# ───────────────────────── 事实采集 ─────────────────────────


class Pack:
    """提交包读取器：优先磁盘，回落 zip；路径前缀多候选。

    实测坑：
      · 只解出 workspace/harbor_task 时，optimization_evidence/ 与 expert_evidence/
        并不在 task 旁边 —— 必须回落 zip，否则 QA13/QA17 误判「材料缺失」；
      · zip 里证据在根（optimization_evidence/）、题包在 workspace/harbor_task/，
        前缀不能只按 task.toml 推断。
    """

    def __init__(self, task: Path, zip_path: str | None):
        import zipfile
        self.task = task
        self.zf = zipfile.ZipFile(zip_path) if (zip_path and Path(zip_path).is_file()) else None
        self.names = set(self.zf.namelist()) if self.zf else set()
        # 提交包根可能在 task.parent、task.parent.parent
        self.disk_roots = [task.parent, task.parent.parent]
        # zip 内可能的前缀
        self.zip_prefixes = ["", "workspace/", "submission/", "dist/"]

    def _disk(self, rel: str):
        for r in self.disk_roots:
            p = r / rel
            if p.is_file():
                return p
        return None

    def _zip_key(self, rel: str):
        for pre in self.zip_prefixes:
            k = pre + rel
            if k in self.names:
                return k
        return None

    def exists(self, rel: str) -> bool:
        return self._disk(rel) is not None or self._zip_key(rel) is not None

    def read_json(self, rel: str, default=None):
        p = self._disk(rel)
        if p:
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except ValueError:
                return default
        k = self._zip_key(rel)
        if k:
            try:
                return json.loads(self.zf.read(k).decode("utf-8"))
            except ValueError:
                return default
        return default

    def glob(self, rel_dir: str, suffix: str) -> list[str]:
        d = rel_dir.rstrip("/") + "/"
        out: list[str] = []
        for r in self.disk_roots:
            dd = r / rel_dir
            if dd.is_dir():
                out += [str(x.relative_to(r)).replace("\\", "/")
                        for x in sorted(dd.glob("*" + suffix))]
            if out:
                return out
        for pre in self.zip_prefixes:
            hit = [k[len(pre):] for k in sorted(self.names)
                   if k.startswith(pre + d) and k.endswith(suffix)]
            if hit:
                return hit
        return out


def gather_facts(task: Path, ws: Path, official: Path, zip_path: str | None) -> dict:
    f: dict = {"task_dir": str(task), "zip": zip_path}

    f["instruction"] = read_text(task / "instruction.md")
    try:
        import tomllib
        with open(task / "task.toml", "rb") as h:
            f["toml"] = tomllib.load(h)
    except Exception:  # noqa: BLE001
        f["toml"] = {}

    f["anchors"] = read_json(task / "tests" / "hidden_assets" / "anchors.json", {}) or {}
    f["grader_src"] = read_text(task / "tests" / "grader.py")
    f["testsh_src"] = read_text(task / "tests" / "test.sh")
    f["tests_docker"] = read_text(task / "tests" / "Dockerfile")
    f["env_docker"] = read_text(task / "environment" / "Dockerfile")
    f["frozen"] = read_json(task / "frozen_manifest.json", {}) or {}

    # 证据目录：磁盘优先，回落 zip
    pack = Pack(task, zip_path)
    f["pack"] = pack
    f["comparison"] = pack.read_json("optimization_evidence/comparison_summary.json", {}) or {}
    f["method_hashes"] = pack.read_json("optimization_evidence/method_hashes.json", {}) or {}

    f["nop"] = {}
    rw = [x for x in pack.glob("expert_evidence/nop_m5_trial", "reward.json")]
    if rw:
        f["nop"] = {"reward_path": rw[0],
                    "reward": (pack.read_json(rw[0], {}) or {}).get("reward")}
        rs = [x for x in pack.glob("expert_evidence/nop_m5_trial", "result.json")]
        if rs:
            d = pack.read_json(rs[0], {}) or {}
            f["nop"].update({"result_path": rs[0],
                             "task_name": d.get("task_name"),
                             "task_checksum": d.get("task_checksum")})

    # 树内是否含 .git
    f["git_dirs"] = [str(p.relative_to(task)) for p in task.rglob(".git") if p.is_dir()]

    # 官方确定性报告
    std = read_json(official / "standard" / "report.json", {}) or {}
    f["fingerprint"] = std.get("task_fingerprint") or {}
    f["resource_review"] = std.get("resource_review") or {}
    f["format_alignment"] = std.get("format_alignment") or {}
    f["harbor_obs"] = (std.get("harbor") or {}).get("observations") or {}

    # 我方两层结果
    f["c1"] = read_json(ws / "execution-path.json", {}) or {}
    f["c2"] = read_json(ws / "gates" / "C2.honest.json", {}) or {}
    return f


# ───────────────────────── 21 项规则 ─────────────────────────
# 每个规则返回 (status, summary, evidence[])
# status ∈ pass | fail | manual

def qa01(f):
    n = len(re.findall(r"^##\s+", f["instruction"], re.M))
    heads = re.findall(r"^##\s+(.+)$", f["instruction"], re.M)
    ev = ["instruction.md（%d 个二级标题）" % n] + heads[:10]
    return "manual", "八章节结构与题面泄露需逐节核对；已抽出二级标题供判", ev


def qa02(f):
    g, a = f["grader_src"], f["anchors"]
    has_norm = "def normalize" in g
    has_scale = "raw_scaled" in g
    has_anch = "baseline_balanced_accuracy" in a and "upper_balanced_accuracy" in a
    ev = ["tests/grader.py: normalize=%s raw_scaled=%s" % (has_norm, has_scale),
          "tests/hidden_assets/anchors.json: B=%s U=%s scale=%s"
          % (a.get("baseline_balanced_accuracy"), a.get("upper_balanced_accuracy"), a.get("scale"))]
    if not (has_norm and has_anch and has_scale):
        return "fail", "评分公式缺 normalize / 锚点 / 量纲换算之一", ev
    # 题面口头声明与实现的差异（实测：instruction 称 reports the raw value，实际是归一化值）
    claim_raw = bool(re.search(r"reports the raw value", f["instruction"], re.I))
    if claim_raw:
        return "fail", ("题面称「grader reports the raw value」，实现返回 (raw×100−B)/(U−B) 的归一化值；"
                        "分数域不是 [0,1]"), ev + ["instruction.md: 声称 reports the raw value"]
    return "pass", "评分公式、锚点与量纲换算一致", ev


def qa03(f):
    c, mh = f["comparison"], f["method_hashes"]
    ok = bool(c.get("reference", {}).get("per_seed")) and bool(mh.get("checkpoints"))
    ev = ["optimization_evidence/comparison_summary.json: reference per_seed=%s"
          % (c.get("reference", {}).get("per_seed")),
          "optimization_evidence/method_hashes.json: checkpoints=%d 个"
          % len(mh.get("checkpoints") or {})]
    if not ok:
        return "manual", "参考解分数或复现材料缺失，需人工核对", ev
    return "manual", "参考解三 seed 与 checkpoint 哈希已就位；「可复现」仍需人判断（本机未重跑）", ev


def qa04(f):
    a = f["anchors"]
    d = a.get("delta_in_sigmas")
    need = a.get("required_sigmas", 3.0)
    ev = ["anchors.json: delta=%.6f sigma_B=%.6f delta_in_sigmas=%.4f required=%.1f"
          % (a.get("delta", 0), a.get("sigma_B", 0), d or 0, need)]
    if d is None:
        return "manual", "anchors 缺 delta_in_sigmas，无法判 3σ 可分辨性", ev
    return ("pass" if d >= need else "fail"), \
           ("提升 %.2fσ ≥ 要求 %.1fσ" % (d, need) if d >= need
            else "提升仅 %.2fσ < 要求 %.1fσ，三 seed 无法分辨" % (d, need)), ev


def qa05(f):
    return "manual", "约束执行需对照 instruction 的 Hard Boundaries 与镜像实现逐条核对", \
           ["instruction.md: Hard Boundaries 段", "tests/Dockerfile", "environment/Dockerfile"]


def qa06(f):
    t, c2 = f["testsh_src"], f["c2"]
    cases = c2.get("cases") or []
    ok_cases = sum(1 for c in cases if c.get("ok"))
    ev = ["tests/test.sh: cd /tests + PYTHONSAFEPATH=%s" % ("PYTHONSAFEPATH" in t),
          "C2 契约用例 %d/%d 通过" % (ok_cases, len(cases))]
    if not cases:
        return "manual", "未执行 C2 契约用例，Verifier 入口与错误处理未验", ev
    if ok_cases < len(cases):
        return "fail", "C2 契约用例有未通过项", ev
    return "manual", ("Verifier 入口与错误分类已由 C2 四个用例验证；"
                      "「分数语义是否与题面一致」需人判断"), ev


def qa07(f):
    txt = f["instruction"]
    hits = re.findall(r"hidden[_a-z]*|hidden test|test\.npz", txt, re.I)
    return "manual", "题面 Hidden 泄露需逐句核对（脚本仅做关键词提示）", \
           ["instruction.md: 命中 %d 处 hidden 相关字样" % len(hits)]


def qa08(f):
    return "manual", "参考解信息泄露需对照 optimization_evidence 与题面", \
           ["instruction.md", "optimization_evidence/comparison_summary.json"]


def qa09(f):
    t = f["testsh_src"]
    rm_old = bool(re.search(r"rm -f", t))
    atomic = "os.replace" in t and "mkstemp" in t
    ev = ["tests/test.sh: 清理旧 reward=%s" % rm_old, "tests/test.sh: 原子写 os.replace+mkstemp=%s" % atomic]
    if rm_old and atomic:
        return "pass", "旧结果已清理，reward.json 走 mkstemp+fsync+os.replace 原子落盘", ev
    return "fail", "结果清理或原子写缺失", ev


def qa10(f):
    g = f["grader_src"]
    frozen = "MODEL_SOURCE" in g and "load_frozen_model" in g
    ev = ["tests/grader.py: 从可信 MODEL_SOURCE 加载冻结模型=%s" % frozen,
          "frozen_manifest.json: frozen/open 分区存在=%s" % bool(f["frozen"].get("frozen"))]
    if not frozen:
        return "fail", "grader 未从可信副本加载模型，冻结面不受保护", ev
    return "manual", "冻结面加载路径已确认；「候选改动会被丢弃」需在容器层核实", ev


def qa11(f):
    return "manual", "题面八项内容需逐项核对", ["instruction.md"]


def qa12(f):
    if f["git_dirs"]:
        return "fail", "题包内存在 .git 目录：%s" % ", ".join(f["git_dirs"][:3]), f["git_dirs"][:3]
    return "pass", "题包内无 .git 目录", ["task 树扫描：0 个 .git"]


def qa13(f):
    c = f["comparison"]
    b, r = c.get("baseline", {}), c.get("reference", {})
    bm, rm_ = b.get("mean"), r.get("mean")
    ev = ["comparison_summary.json: B mean=%.6f R mean=%.6f" % (bm or 0, rm_ or 0)]
    if bm is None or rm_ is None:
        return "manual", "缺 B/R 均值，无法判提升", ev
    return ("pass" if rm_ > bm else "fail"), \
           ("R %.4f > B %.4f，提升 %.4f" % (rm_, bm, rm_ - bm) if rm_ > bm
            else "R 未超过 B"), ev


def qa14(f):
    fr = f["frozen"]
    return "manual", "合法改进空间需对照 frozen/open 分区与题面 Allowed Scope", \
           ["frozen_manifest.json: open 项 %d 条" % (len(fr.get("open") or {})
                                                     if isinstance(fr.get("open"), (dict, list)) else 0)]


def qa15(f):
    tm = f["toml"]
    lim = f["resource_review"].get("limits") or {}
    env = (tm.get("environment") or {})
    ver = (tm.get("verifier") or {}).get("environment") or {}
    t_lim = (tm.get("task") or {}).get("time_limit_seconds")
    gpus = env.get("gpus")
    cpus = env.get("cpus")
    gtypes = env.get("gpu_types") or []
    over = []
    if t_lim and lim.get("score_seconds") and t_lim > lim["score_seconds"]:
        over.append("单轮 %ss > 上限 %ss" % (t_lim, lim["score_seconds"]))
    if gpus is not None and lim.get("gpu_count") and gpus > lim["gpu_count"]:
        over.append("GPU %s > 上限 %s" % (gpus, lim["gpu_count"]))
    if cpus is not None and lim.get("cpu_cores") and cpus > lim["cpu_cores"]:
        over.append("CPU %s > 上限 %s" % (cpus, lim["cpu_cores"]))
    allowed_g = set(lim.get("gpu_types") or [])
    bad_types = [g for g in gtypes if allowed_g and g not in allowed_g]
    ev = ["task.toml: time=%ss gpus=%s cpus=%s types=%s" % (t_lim, gpus, cpus, gtypes),
          "官方上限: %s" % json.dumps(lim, ensure_ascii=False)]
    if over or bad_types:
        msg = "；".join(over + (["卡型 %s 不在允许列表" % bad_types] if bad_types else []))
        return "manual", "超限项已如实声明，需平台复核：" + msg, ev
    return "pass", "资源与时长在官方上限内", ev


def qa16(f):
    tj = f["pack"].glob("expert_evidence", "trajectory_*.json") \
        if "pack" in f else []
    if not tj:
        return "manual", "未找到轨迹文件，迭代时长无法核", ["expert_evidence/trajectory_*.json"]
    return "manual", "轨迹时长需逐条读 rounds 时间段（%d 个轨迹文件）" % len(tj), tj[:5]


def qa17(f):
    nop, fp = f["nop"], f["fingerprint"]
    ev = []
    if not nop.get("reward_path"):
        return "fail", "包内无 NOP 产物（reward.json 缺失），H06/QA17 不通过", ["expert_evidence/nop_m5_trial"]
    ev.append("NOP: %s reward=%s" % (nop["reward_path"], nop.get("reward")))
    if fp.get("task_content_sha256"):
        ev.append("当前 task_content_sha256=%s…" % fp["task_content_sha256"][:16])
    if nop.get("task_checksum"):
        ev.append("NOP task_checksum=%s…（Harbor 自有口径，与上面不是同一算法）"
                  % str(nop["task_checksum"])[:16])
    ev.append("NOP 目录时间=%s" % nop.get("mtime"))
    return "manual", ("NOP 产物存在且 reward 有限；但**其与当前题包的版本绑定需质检员给出语义映射证据**"
                      "（harbor_review 要求 trial_task_binding.summary + evidence，不接受按日志猜测）。"
                      "若题包自 NOP 后被改动过，须重跑 NOP 或提供改名/变更映射"), ev


def qa18(f):
    return "manual", "轨迹、日志与分析需人读（rounds、失败重试、是否到达目标）", \
           ["expert_evidence/trajectory_*.json"]


def qa19(f):
    a, c = f["anchors"], f["comparison"]
    seeds = c.get("seeds") or a.get("seeds") or []
    d = a.get("delta_in_sigmas")
    ok = len(seeds) >= 3 and (d or 0) >= (a.get("required_sigmas", 3.0))
    ev = ["seeds=%s" % seeds, "delta_in_sigmas=%s" % d]
    return ("pass" if ok else "fail"), \
           ("三个 seed + 提升 %.2fσ，超过有效阈值" % d if ok else "seed 数或提升幅度不足"), ev


def qa20(f):
    return "manual", "修改范围、网络与工具策略需对照 instruction 的 Allowed Scope / Hard Boundaries", \
           ["instruction.md: Allowed Scope / Hard Boundaries"]


def qa21(f):
    c2 = f["c2"]
    cases = c2.get("cases") or []
    names = [c.get("case") for c in cases]
    ev = ["C2 用例：%s" % ", ".join(names), "tests/grader.py REQUIRED_FIELDS 校验存在"]
    if "missing_submission_json" in names and "path_escape" in names:
        return "manual", ("三个 JSON 的字段校验与路径逃逸已由 C2 验证；"
                          "「声明值是否属实」按题面为 honor-system，需人判断"), ev
    return "manual", "未跑 C2 契约用例，三个 JSON 的校验未验", ev


RULES = {
    "QA01": qa01, "QA02": qa02, "QA03": qa03, "QA04": qa04, "QA05": qa05,
    "QA06": qa06, "QA07": qa07, "QA08": qa08, "QA09": qa09, "QA10": qa10,
    "QA11": qa11, "QA12": qa12, "QA13": qa13, "QA14": qa14, "QA15": qa15,
    "QA16": qa16, "QA17": qa17, "QA18": qa18, "QA19": qa19, "QA20": qa20,
    "QA21": qa21,
}


# ───────────────────────── 子命令 ─────────────────────────

def cmd_run(a):
    ws = Path(a.workspace).resolve()
    official = ws / "official"
    official.mkdir(parents=True, exist_ok=True)
    if not AUDITOR.is_file():
        print("FATAL: 找不到官方审计入口", AUDITOR)
        return 2
    cmd = [PY, "-B", str(AUDITOR), str(Path(a.zip).resolve()),
           "--out-dir", str(official)]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    out = (r.stdout or "") + (r.stderr or "")
    print(out.strip()[-400:])
    rep = read_json(official / "report.json", {}) or {}
    print("官方层 decision=%s code=%s" % (rep.get("decision"), rep.get("code")))
    print("（未填底稿时必然 ERROR/REVIEW_NOT_FINISHED，这是设计如此）")
    return 0


def cmd_review(a):
    ws = Path(a.workspace).resolve()
    st = read_json(ws / "state.json", {}) or {}
    task = Path(st.get("identity", {}).get("task_dir", a.task_dir or "")).resolve()
    if not task.is_dir():
        print("FATAL: task 目录不可用，先跑 qa.py init")
        return 2
    official = ws / "official"
    facts = gather_facts(task, ws, official, st.get("zip"))

    tpl = read_json(official / "standard_review_template.json")
    if tpl is None:
        print("FATAL: 缺 standard_review_template.json，先跑 qa_official.py run")
        return 2

    stats = {"pass": 0, "fail": 0, "manual": 0}
    for row in tpl.get("checks", []):
        qid = row.get("id")
        fn = RULES.get(qid)
        if fn is None:
            row["status"] = "manual"
            row["summary"] = "无对应规则，需人工审阅"
            continue
        try:
            status, summary, ev = fn(facts)
        except Exception as exc:  # noqa: BLE001
            status, summary, ev = "manual", "规则执行异常：%s" % exc, []
        row["status"] = status
        row["summary"] = summary
        row["evidence"] = ev
        stats[status] = stats.get(status, 0) + 1

    # 质检员逐项结论（覆盖规则给出的 manual），必须是人工判断，不许脚本生成
    fills_p = Path(a.fills) if getattr(a, "fills", None) else (official / "manual_fills.json")
    fills = read_json(fills_p, {}) if fills_p.is_file() else {}
    filled = 0
    for row in tpl.get("checks", []):
        qid = row.get("id")
        if qid in fills:
            f0 = fills[qid]
            if f0.get("status") not in ("pass", "fail", "manual"):
                continue
            row["status"] = f0["status"]
            row["summary"] = f0.get("summary", row.get("summary", ""))
            row["evidence"] = f0.get("evidence", row.get("evidence", []))
            filled += 1
    if fills:
        print("叠加质检员结论：%d 项（来源 %s）" % (filled, fills_p.name))
        stats = {"pass": 0, "fail": 0, "manual": 0}
        for row in tpl.get("checks", []):
            stats[row["status"]] = stats.get(row["status"], 0) + 1

    # 内容门 G01–G03 留给人工（需读方法面）
    cg = tpl.get("content_gates") or {}
    for row in cg.get("checks", []) if isinstance(cg, dict) else []:
        row["status"] = "manual"
        row["summary"] = row.get("summary") or "需读 B/R 方法面后判定"

    out = official / "review.json"
    out.write_text(json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")
    print("21 项判定：pass=%d fail=%d manual=%d" % (stats["pass"], stats["fail"], stats["manual"]))
    print("written:", out)
    print("\nFAIL 项：")
    for row in tpl.get("checks", []):
        if row["status"] == "fail":
            print("  %s %s | %s" % (row["id"], row["title"], row["summary"][:90]))
    return 0


def cmd_integrate(a):
    """把官方层结论并进我方总判，输出统一视图。"""
    ws = Path(a.workspace).resolve()
    review = read_json(ws / "official" / "review.json", {}) or {}
    mine = read_json(ws / "report.json", {}) or {}
    rows = review.get("checks") or []
    off_fail = [r for r in rows if r.get("status") == "fail"]
    off_manual = [r for r in rows if r.get("status") == "manual"]
    off_pass = [r for r in rows if r.get("status") == "pass"]

    if off_fail:
        decision = "FAIL"
    elif off_manual:
        decision = "INCOMPLETE"
    elif rows:
        decision = "PASS"
    else:
        decision = "INCOMPLETE"

    merged = {
        "schema": "qa-unified/1",
        "generated_at": now(),
        "adversarial": {"decision": mine.get("decision"),
                        "gates": mine.get("gates"),
                        "blocking": sum(v.get("blocking", 0)
                                        for v in (mine.get("gates") or {}).values())},
        "official": {"decision": decision,
                     "counts": {"pass": len(off_pass), "fail": len(off_fail),
                                "manual": len(off_manual)},
                     "fail_items": [{"id": r["id"], "title": r["title"],
                                     "summary": r["summary"]} for r in off_fail],
                     "manual_items": [r["id"] for r in off_manual]},
        "overall": "FAIL" if (mine.get("decision") == "FAIL" or decision == "FAIL")
                   else "INCOMPLETE" if "INCOMPLETE" in (mine.get("decision"), decision)
                   else "PASS",
    }
    out = ws / "unified.json"
    out.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    print("对抗层 : %s" % merged["adversarial"]["decision"])
    print("官方层 : %s  (pass=%d fail=%d manual=%d)"
          % (decision, len(off_pass), len(off_fail), len(off_manual)))
    print("总判   : %s" % merged["overall"])
    if off_fail:
        print("\n官方 FAIL：")
        for r in off_fail:
            print("  %s %s | %s" % (r["id"], r["title"], r["summary"][:100]))
    if off_manual:
        print("\n仍待人工（%d 项）：%s" % (len(off_manual), ", ".join(r["id"] for r in off_manual)))
    print("written:", out)
    return 0 if merged["overall"] != "FAIL" else 1


def main():
    ap = argparse.ArgumentParser(description="官方标准层编排")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run")
    p.add_argument("--workspace", required=True)
    p.add_argument("--zip", required=True)
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("review")
    p.add_argument("--workspace", required=True)
    p.add_argument("--task-dir", default=None)
    p.add_argument("--fills", default=None,
                   help="质检员逐项结论 JSON：{QA01:{status,summary,evidence},...}")
    p.set_defaults(fn=cmd_review)

    p = sub.add_parser("integrate")
    p.add_argument("--workspace", required=True)
    p.set_defaults(fn=cmd_integrate)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
