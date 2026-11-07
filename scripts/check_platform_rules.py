#!/usr/bin/env python3
"""平台源包硬规则检查（B-C01–B-C04，2026-11 平台新规）。

★ 为什么需要这一层

  内嵌官方层是 `0.3.10-standard-waiver.5`（2026-10-23），而平台在 2026-10-26
  （Harbor 1074 题复盘 rev 1145）与 2026-11-03（返修指南）之后给出了四条**新的**
  源包硬规则。它们不在 QA01–QA21 的任何一项里，且其中一条与内嵌层
  **正面翻转**：旧口径要求 task.toml「填写 docker_image」，新口径**禁止**配置。

  规则来源（引用时必须连版本日期一起引）：
    · B-C01/B-C02 —— 返修指南 §6 条目 1/2；supplement platform-audit B-C01/B-C02
    · B-C03/B-C04 —— 返修指南 §6 条目 3/4；supplement B-C03/B-C04

  四条全部静态可判（mechanical 档）。supplement skill 的案例边界已编码进实现：
    · 注释/说明文字出现字段名不算配置（B-C02）
    · 仅 README 里的 URL 不算「实际生效」的包源（B-C03）
    · `.npmrc` 写了 bnpm 但后续 `npm install --registry=...` 覆盖 ⇒ 不符合（B-C04）
    · 未用 npm 的题目 B-C04 不适用，不强制新增 npm 步骤

用法：
  python scripts/check_platform_rules.py --root <提交包根或任务目录> --out <输出>/platform-rules.json

退出码：0 = 无 fail；1 = 有 fail；2 = 用法错误。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

SKIP_DIRS = {"__pycache__", ".git", ".hg", ".svn", "node_modules",
             ".venv", "venv", ".mypy_cache", ".pytest_cache", ".tox"}

BNPM = "bnpm.byted.org"
CANONICAL = "workspace/harbor_task/task.toml"

# ★ 2026-11-06 规则版本信号：平台 1074 复盘新副本中「npm 必须改 bnpm」一条被划掉
#   （原文 ~~如使用npm包…~~，仅留 npm config set 代码块）。在平台新版 skill 明确前，
#   本检查保留检测但降为 needs_manual（只记录不阻断），避免按已撤回规则误判作者。
#   引用时必须连日期版本一起引；新版 skill 发布后复核本常量。
# ★ 2026-11-07 unified-qa v0.5.0 确认：「C04 实际使用 npm 时生效 registry 为指定
#   bnpm，批准替代源/等效配置可接受，无 npm 不适用」（current-check-map.json:307、
#   standard-coverage.md:57）。划线副本的疑虑解除；但静态无法验证「批准替代」依据，
#   非 bnpm 的 registry 保持 needs_manual（作者声明批准依据可转 pass）。
NPM_RULE_STATUS = "confirmed_with_alternatives"
NPM_RULE_NOTE = ("（v0.5.0 延续本规则；批准替代源/等效配置可接受——静态无法验证"
                 "批准依据，作者声明批准出处可转 pass）")

# ★ 2026-11-07 规则版本信号（第三次反转）：unified-qa v0.5.0 把固定位置/禁
#   docker_image 两条降为「旧规则建议」——
#   "B-C01 定位实际有效任务，不恢复固定 workspace 路径"；
#   "不统一禁止源包 docker_image"、"看实际有效 Runner 选择，不按旧固定位置拒收"。
#   本检查保留检测但降为 needs_manual（只记录不阻断），按实际有效配置判定。
LEGACY_LOCATION_RULE_NOTE = ("（v0.5.0 已将该规则降为建议：定位实际有效任务/Runner "
                             "配置即可，不按旧固定位置拒收；本轮仅记录）")

# 已证实的非官方镜像域（发行版/生态官方源之外）。只在这些域出现在
# 「执行载体」里时才判违规；README/说明文档不扫（说明 ≠ 生效）。
MIRROR_DOMAINS = [
    "pypi.tuna.tsinghua.edu.cn", "mirrors.tuna.tsinghua.edu.cn",
    "pypi.mirrors.ustc.edu.cn", "mirrors.ustc.edu.cn",
    "mirrors.aliyun.com", "mirrors.cloud.aliyuncs.com",
    "pypi.douban.com", "pypi.doubanio.com",
    "mirrors.bfsu.edu.cn", "mirrors.nju.edu.cn", "mirror.nju.edu.cn",
    "mirror.sjtu.edu.cn", "mirrors.sjtug.sjtu.edu.cn",
    "mirrors.huaweicloud.com", "mirrors.cloud.tencent.com", "mirrors.tencent.com",
    "mirrors.pku.edu.cn", "mirrors.zju.edu.cn", "mirrors.hit.edu.cn",
    "mirrors.bit.edu.cn", "pypi.hustunique.com", "mirrors.yun-idc.com",
]

# 「实际生效」的执行载体：会真正驱动安装/构建的文件类型。
CARRIER_SUFFIXES = {".sh", ".bash", ".toml", ".cfg", ".ini", ".conf", ".list",
                    ".yaml", ".yml", ".txt", ".env", ".py", ".bat", ".ps1"}
# 专属包管理配置：这些文件里出现镜像域即算生效，无需行内再找关键字。
PKG_CONFIG_NAMES = {"pip.conf", "pip.ini", ".condarc", "uv.toml",
                    "sources.list", "apt.conf", "apt.conf.d"}
# 行级上下文标记：通用载体文件里，镜像域必须与这些标记同行才算「安装指令」。
INSTALL_MARKERS = re.compile(
    r"(pip|index-url|PIP_INDEX_URL|PIP_EXTRA_INDEX_URL|apt-get|apt|conda|uv\s+|cran|CRAN|"
    r"gem\s+install|bundle|repo\.anaconda|download\.pytorch)", re.I)


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


# ────────────────────────── B-C01 ──────────────────────────

def check_c01(root: Path):
    """项目中只保留一份 task.toml，位置 workspace/harbor_task/task.toml。"""
    hits = [p for p in iter_files(root) if p.name == "task.toml"]
    findings = []
    canonical = (root / CANONICAL).resolve()
    task_dir_mode = False
    if not hits:
        findings.append({"severity": "blocking", "file": CANONICAL, "line": 0,
                         "detail": "B-C01：提交包内没有任何 task.toml（缺失任务配置——"
                                   "v0.5.0 下有效任务配置仍是 L0 必需）"})
        status = "fail"
    elif len(hits) > 1:
        paths = ", ".join(rel(root, p) for p in hits)
        findings.append({"severity": "needs_manual", "file": rel(root, hits[0]), "line": 0,
                         "detail": "B-C01：发现 %d 份 task.toml（%s）；v0.5.0 要求定位"
                                   "实际有效任务配置（不按旧固定位置拒收），但多份并存"
                                   "仍须指明实际生效的一份与归档处置" % (len(hits), paths)
                                   + LEGACY_LOCATION_RULE_NOTE})
        status = "needs_manual"
    else:
        only = hits[0].resolve()
        if only == canonical:
            status = "pass"
        elif only == (root / "task.toml").resolve() \
                and (root / "instruction.md").is_file():
            # 传入的是 harbor_task 目录本身而非提交包根：位置校验无从谈起
            status = "pass"
            task_dir_mode = True
            findings.append({"severity": "informational", "file": "task.toml", "line": 0,
                             "detail": "B-C01：传入的是任务目录（含 instruction.md），"
                                       "唯一 task.toml 位于根；提交包根级位置校验"
                                       "（%s）需以提交包根重跑确认" % CANONICAL})
        else:
            status = "needs_manual"
            findings.append({"severity": "needs_manual", "file": rel(root, hits[0]), "line": 0,
                             "detail": "B-C01：唯一 task.toml 位于 %s（旧口径要求 %s）"
                                       % (rel(root, hits[0]), CANONICAL)
                                       + LEGACY_LOCATION_RULE_NOTE})
    # 下游 B-C02 仍需要一个确定性的检查对象：多份时优先规范路径（不随机挑选），
    # 只保证「检查对象确定」，不改变 B-C01 本身的 fail 结论。
    primary = None
    if canonical in [h.resolve() for h in hits]:
        primary = next(h for h in hits if h.resolve() == canonical)
    elif len(hits) == 1:
        primary = hits[0]
    return status, findings, primary, task_dir_mode


# ────────────────────────── B-C02 ──────────────────────────

def _strip_inline_comment(line: str) -> str:
    """去掉 # 后的注释（不考虑引号内的 #——task.toml 实践中足够）。"""
    idx = line.find("#")
    return line if idx < 0 else line[:idx]


def check_c02(root: Path, task_toml: Path | None):
    """镜像/构建来源核对。v0.5.0：不统一禁止源包 docker_image（降为建议），
    核对实际镜像/构建与私有资产；Dockerfile 缺失按「镜像来源二选一」记 manual。"""
    findings = []
    if task_toml is None:
        return "needs_manual", [{"severity": "needs_manual", "file": CANONICAL, "line": 0,
                                 "detail": "B-C02：无 task.toml 可查（前置 B-C01 已失败）"}]
    text = read_text(task_toml)
    configured = None       # (line, value)
    comment_only = 0
    for i, raw in enumerate(text.splitlines(), 1):
        if "docker_image" not in raw:
            continue
        code = _strip_inline_comment(raw)
        m = re.match(r"\s*docker_image\s*=\s*(.+?)\s*$", code)
        if m:
            val = m.group(1).strip().strip("'\"")
            if val:
                configured = (i, val)
            else:
                findings.append({"severity": "informational", "file": rel(root, task_toml),
                                 "line": i, "detail": "B-C02：docker_image 为空串，"
                                 "不构成有效配置，但建议直接删除该字段"})
        else:
            comment_only += 1
    status = "pass"
    if configured:
        i, val = configured
        findings.append({"severity": "needs_manual", "file": rel(root, task_toml), "line": i,
                         "detail": "B-C02：专家源 task.toml 配置了 docker_image=%r——"
                                   "2026-10-26 旧口径禁止；v0.5.0 不统一禁止，改为核对"
                                   "实际镜像/构建与私有资产（镜像可访问性属平台侧）" % val
                                   + LEGACY_LOCATION_RULE_NOTE})
        status = "needs_manual"
    elif comment_only:
        findings.append({"severity": "informational", "file": rel(root, task_toml),
                         "line": 0, "detail": "B-C02：docker_image 仅出现在注释/说明中，"
                         "不构成有效配置（不计违规）"})

    # environment/Dockerfile：镜像来源二选一（Dockerfile 或 docker_image），
    # 两者皆无才阻断；有 Dockerfile 时仍核 COPY 来源（确定性构建失败）
    task_root = task_toml.parent
    env_df = task_root / "environment" / "Dockerfile"
    if not env_df.is_file():
        if configured:
            findings.append({"severity": "informational", "file": rel(root, env_df), "line": 0,
                             "detail": "B-C02：未交付 environment/Dockerfile，但声明了"
                                       " docker_image——镜像来源二选一成立；平台按声明"
                                       "镜像准备，实际可拉取性属平台侧验证"})
        else:
            findings.append({"severity": "needs_manual", "file": rel(root, env_df), "line": 0,
                             "detail": "B-C02：既无 environment/Dockerfile 也未声明"
                                       " docker_image——镜像来源二选一不成立，"
                                       "平台无法构建" + LEGACY_LOCATION_RULE_NOTE})
            status = "needs_manual"
    else:
        findings.extend(check_copy_sources(root, env_df))
        for f in findings:
            if f["severity"] == "blocking" and f["file"] != rel(root, task_toml):
                status = "fail"
        tests_df = task_root / "tests" / "Dockerfile"
        if tests_df.is_file():
            findings.extend(check_copy_sources(root, tests_df))
            for f in findings:
                if f["severity"] == "blocking" and f["file"] != rel(root, task_toml):
                    status = "fail"
    return status, findings


def check_copy_sources(root: Path, dockerfile: Path):
    """Dockerfile COPY/ADD 的字面来源在 context 中必须真实存在（B-P12 静态形态）。

    ★ 只报可静态确定的：字面路径（无 $VAR、非 --from=、非 URL）在 context 展开
      后零命中 ⇒ 构建必然失败。通配符展开零命中同理。动态路径跳过，不猜。
    """
    findings = []
    context = dockerfile.parent
    text = read_text(dockerfile)
    lines = text.replace("\\\n", " ").splitlines()
    for i, ln in enumerate(lines, 1):
        m = re.match(r"\s*(COPY|ADD)\s+(.+?)\s*$", ln, re.I)
        if not m:
            continue
        tokens = m.group(2).split()
        if any(t.startswith("--from=") for t in tokens):
            continue  # 多阶段构建，来源在别的 stage，静态无法解析
        srcs = [t for t in tokens if not t.startswith("--")]
        for s in srcs[:-1]:  # 最后一个 token 是目的路径
            if "$" in s or "{" in s:
                continue
            if s.lower().startswith(("http://", "https://")):
                continue  # ADD 的 URL 形式
            if any(ch in s for ch in "*?["):
                hit = bool(list(context.glob(s)))
            elif s.endswith("/") or s == ".":
                hit = (context / s).is_dir()
            else:
                hit = (context / s).exists()
            if not hit:
                findings.append({
                    "severity": "blocking",
                    "file": rel(root, dockerfile), "line": i,
                    "detail": "B-C02/B-P12：COPY/ADD 来源 %r 在构建上下文 %s 中不存在"
                              "（检查 .dockerignore 与资产交付，不得建空资产应付）"
                              % (s, rel(root, context))})
    return findings


# ────────────────────────── B-C03 ──────────────────────────

def _is_pkg_config(name: str) -> bool:
    low = name.lower()
    return low in PKG_CONFIG_NAMES or low.startswith("sources.list")


def _is_carrier(p: Path) -> bool:
    low = p.name.lower()
    if low in PKG_CONFIG_NAMES or low.startswith("dockerfile"):
        return True
    return p.suffix.lower() in CARRIER_SUFFIXES


def check_c03(root: Path):
    """依赖下载使用发行版/生态官方源；只扫执行载体，不扫说明文档。"""
    findings = []
    status = "pass"
    for p in iter_files(root):
        if not _is_carrier(p):
            continue  # .md / 说明文档里的 URL 不判违规（PLATFORM 案例：说明 ≠ 生效）
        try:
            if p.stat().st_size > 4 * 1024 * 1024:
                continue
        except OSError:
            continue
        text = read_text(p)
        dedicated = _is_pkg_config(p.name) or p.name.lower().startswith("dockerfile")
        for i, line in enumerate(text.splitlines(), 1):
            domain = next((d for d in MIRROR_DOMAINS if d in line.lower()), None)
            if not domain:
                continue
            if dedicated or INSTALL_MARKERS.search(line):
                findings.append({
                    "severity": "blocking",
                    "file": rel(root, p), "line": i,
                    "detail": "B-C03：实际生效的依赖源使用了非官方镜像 %s——"
                              "改为发行版/对应生态官方源；保留版本、哈希与签名校验，"
                              "不得以换源名义删除校验" % domain})
                status = "fail"
            else:
                findings.append({
                    "severity": "needs_manual",
                    "file": rel(root, p), "line": i,
                    "detail": "B-C03：执行载体 %s 出现镜像域 %s，但行内无安装指令标记——"
                              "需读上下文确认是否实际生效（变量拼接/间接调用）"
                              % (rel(root, p), domain)})
                if status == "pass":
                    status = "needs_manual"
    return status, findings


# ────────────────────────── B-C04 ──────────────────────────

NPM_USE = re.compile(r"npm\s+(install|ci|run|config|exec|publish)", re.I)
REG_FLAG = re.compile(r"--registry[=\s](\S+)", re.I)
REG_CONFIG = re.compile(r"npm\s+config\s+set\s+registry\s+(\S+)", re.I)
REG_ENV = re.compile(r"npm_config_registry[=:](\S+)", re.I)
NPMRC_REG = re.compile(r"^\s*registry\s*=\s*(\S+)", re.M)


def _norm(url: str) -> str:
    u = url.strip().strip("'\"")
    u = re.sub(r"^https?://", "", u, flags=re.I)
    return u.rstrip("/").lower()


def check_c04(root: Path):
    """npm 必须使用 bnpm.byted.org；以实际生效配置为准（覆盖语义：命令行 > config set > .npmrc）。"""
    flag_regs, config_regs, npmrc_regs = [], [], []
    npm_used = False
    for p in iter_files(root):
        low = p.name.lower()
        if low in ("package.json", "package-lock.json", "npm-shrinkwrap.json"):
            npm_used = True
        if not _is_carrier(p):
            continue
        text = read_text(p)
        if NPM_USE.search(text):
            npm_used = True
        for i, line in enumerate(text.splitlines(), 1):
            if not NPM_USE.search(line) and "registry" not in line.lower():
                continue
            for m in REG_FLAG.finditer(line):
                if "npm" in line.lower():
                    flag_regs.append((rel(root, p), i, m.group(1)))
            for m in REG_CONFIG.finditer(line):
                config_regs.append((rel(root, p), i, m.group(1)))
            for m in REG_ENV.finditer(line):
                config_regs.append((rel(root, p), i, m.group(1)))
        if low == ".npmrc":
            for m in NPMRC_REG.finditer(text):
                npmrc_regs.append((rel(root, p), 0, m.group(1)))

    findings = []
    if not npm_used:
        return "not_applicable", [{"severity": "informational", "file": "", "line": 0,
                                   "detail": "B-C04：题包未使用 npm，本项不适用；"
                                             "不强制新增 npm 步骤"}]
    # ① 命令行 --registry 优先级最高：任一 npm 命令覆盖为非 bnpm ⇒ 违规
    overrides = [(f, i, u) for f, i, u in flag_regs if _norm(u) != BNPM]
    if overrides:
        f, i, u = overrides[0]
        findings.append({"severity": "needs_manual", "file": f, "line": i,
                         "detail": "B-C04：npm 命令行 --registry=%s 覆盖了其他配置"
                                   "（.npmrc 写了 bnpm 也会被它盖掉）——建议改为 bnpm 或删掉覆盖"
                                   % u + NPM_RULE_NOTE})
        return "needs_manual", findings
    if flag_regs:
        return "pass", [{"severity": "informational", "file": flag_regs[0][0],
                         "line": flag_regs[0][1],
                         "detail": "B-C04：npm 安装命令显式使用 %s" % flag_regs[0][2]}]
    # ② 无命令行覆盖：看 config set / 环境变量 / .npmrc
    effective = config_regs + npmrc_regs
    bad = [(f, i, u) for f, i, u in effective if _norm(u) != BNPM]
    if bad:
        f, i, u = bad[0]
        findings.append({"severity": "needs_manual", "file": f, "line": i,
                         "detail": "B-C04：npm registry 实际生效为 %s——"
                                   "按 2026-11 规则应为 https://%s" % (u, BNPM)
                                   + NPM_RULE_NOTE})
        return "needs_manual", findings
    if effective:
        return "pass", [{"severity": "informational", "file": effective[0][0],
                         "line": effective[0][1],
                         "detail": "B-C04：npm registry 配置为 bnpm 且无覆盖"}]
    # ③ npm 已使用但源包内无任何 registry 配置：默认 npmjs 不符合，
    #    但基础镜像可能已配置——静态无法判定
    findings.append({"severity": "needs_manual", "file": "", "line": 0,
                     "detail": "B-C04：npm 已使用但源包内未见任何 registry 配置——"
                               "默认源 registry.npmjs.org 按 2026-11 规则不符合要求；"
                               "若依赖基础镜像预配，须指出该镜像与配置证据" + NPM_RULE_NOTE})
    return "needs_manual", findings


# ────────────────────────── 汇总 ──────────────────────────

def main():
    ap = argparse.ArgumentParser(description="平台源包硬规则检查（B-C01–B-C04）")
    ap.add_argument("--root", required=True, help="提交包根或 harbor_task 目录")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print("FATAL: root not found: %s" % root)
        return 2

    c01_status, c01_findings, task_toml, task_dir_mode = check_c01(root)
    c02_status, c02_findings = check_c02(root, task_toml)
    c03_status, c03_findings = check_c03(root)
    c04_status, c04_findings = check_c04(root)

    checks = [
        {"id": "B-C01", "title": "唯一 task.toml 于 workspace/harbor_task/",
         "status": c01_status, "findings": c01_findings},
        {"id": "B-C02", "title": "源 task.toml 禁配 docker_image；Dockerfile 与上下文完整",
         "status": c02_status, "findings": c02_findings},
        {"id": "B-C03", "title": "依赖使用发行版/生态官方源（实际生效设置）",
         "status": c03_status, "findings": c03_findings},
        {"id": "B-C04", "title": "npm registry 为 bnpm.byted.org（未用 npm 则不适用）",
         "status": c04_status, "findings": c04_findings},
    ]
    counts = {}
    for c in checks:
        counts[c["status"]] = counts.get(c["status"], 0) + 1

    report = {
        "gate": "platform_rules",
        "root": str(root),
        "task_dir_mode": task_dir_mode,
        "rules_version": "返修指南 2026-11-03 / supplement platform-audit 1.0.1 / 复盘 rev 1145",
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
                                                 f["line"], f["detail"][:140]))
    print("summary:", json.dumps(counts, ensure_ascii=False))
    print("written:", out)
    return 1 if counts.get("fail") else 0


if __name__ == "__main__":
    sys.exit(main())
