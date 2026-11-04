#!/usr/bin/env python3
"""执行层门禁（Gate C）：静态扫出「评分链会让诚实候选崩溃」的已知形态。

★ 为什么需要这一层（2026-10-30，从 11 份官方质检报告反推）：

  平台 `0.3.10-standard-waiver.5-toolfix.2` 的 QA06 判据，已从
  「入口在不在 / 退出码分不分类 / reward 落不落地」（结构层）
  改成「按真实调用链走一遍，看类型/数量对不对」（执行层）。

  证据：QA06 在 `.5` 和 `.5-toolfix.1` 下对 4 个任务全 pass，
  在 `.5-toolfix.2` 下对 2 个任务全 fail，根因分别是：
    · 0340：父进程把动作构造成 np.ndarray 传给 TensorWrapper.step，
            而包装器第一行是 self.env.step(action.numpy()) ⇒ AttributeError
    · 2001：超时分支 return 三元组，调用方按二元组解包 ⇒ ValueError

  这两类都不是「安全检查」能发现的，是「跑一遍」才能发现的。
  本脚本用静态启发式把它们提前到提交前。

用法：
  python scripts/check_execution_path.py --root <待检目录> --out <输出>/execution-path.json

退出码：0 = 无 blocking；1 = 有 blocking；2 = 用法错误。
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path

SKIP_DIRS = {"__pycache__", ".git", "node_modules", ".mypy_cache", ".pytest_cache"}
NP_CONSTRUCTORS = {"asarray", "array", "zeros", "ones", "empty", "full"}
TENSOR_METHODS = {"numpy", "detach", "cpu", "to", "float", "double"}


def iter_py(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            if fn.endswith(".py"):
                yield Path(dirpath) / fn


def parse(path: Path):
    try:
        return ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return None


def call_name(node: ast.Call) -> str:
    f = node.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return ""


def is_numpy_expr(node, aliases):
    """判断表达式是否在构造 numpy 数组。"""
    if isinstance(node, ast.Call) and call_name(node) in NP_CONSTRUCTORS:
        f = node.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            return f.value.id in aliases
        return call_name(node) == "array"
    return False


def collect_numpy_aliases(trees):
    aliases = {"np", "numpy"}
    for t in trees:
        for node in ast.walk(t):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name in ("numpy",):
                        aliases.add(a.asname or "numpy")
    return aliases


def _is_wrapper_step(fn, pname):
    """是否是「把 .numpy() 结果转发给内层 env.step」的包装器方法。

    ★ 只认这一种形态，否则会把 dm_control 自己的 step(np.array) 全判成问题
      （本机首版就是这么误报 24 条的）。
      形态：def step(self, action): self.env.step(action.numpy())
    """
    calls_numpy = False
    calls_inner = False
    for sub in ast.walk(fn):
        if not isinstance(sub, ast.Call) or not isinstance(sub.func, ast.Attribute):
            continue
        if (sub.func.attr == "numpy" and isinstance(sub.func.value, ast.Name)
                and sub.func.value.id == pname):
            calls_numpy = True
        if (sub.func.attr == "step" and isinstance(sub.func.value, ast.Attribute)
                and sub.func.value.attr in ("env", "inner", "wrapper", "_env")):
            calls_inner = True
    return calls_numpy and calls_inner


def rule_tensor_api(trees, aliases):
    """规则 EX-01：把 numpy 数组传给一个「内部把参数 .numpy() 转发给 env」的包装器。

    形态（0340 实测）：
        act = np.asarray(resp["action"], ...)
        env.step(act)                      # env 是 TensorWrapper
        # 而 TensorWrapper.step 里： self.env.step(action.numpy())
    """
    out = []
    # 只收集「包装器转发」型的方法名
    wants_tensor = {}
    for path, tree in trees.items():
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.args.args:
                continue
            for pname in [a.arg for a in node.args.args[1:]]:
                if _is_wrapper_step(node, pname):
                    wants_tensor.setdefault(node.name, set()).add((pname, path))

    # 再找把 numpy 数组喂给同名方法的调用点
    # ★ 只扫「评测入口层」：排除环境实现目录（envs / tasks / wrappers）。
    #   理由：`.step()` 在环境内部被大量合法调用（dm_control 的 step 本身就吃 numpy），
    #   静态无法判定接收者类型。0340 的真实故障点在评测器的 eval loop（tests/evaluate_verify.py），
    #   不在环境实现里。首版不排除会误报 20+ 条。
    SKIP_PARTS = {"envs", "tasks", "wrappers", "starter"}
    for path, tree in trees.items():
        if tree is None:
            continue
        if SKIP_PARTS & set(path.parts):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in wants_tensor or not node.args:
                continue
            arg = node.args[0]
            # ★ 只报「跨文件」：包装器定义在 A、调用在 B。
            #   同文件内的 .step(numpy) 多是环境自身实现（dm_control 的 step 接受 numpy），
            #   首版不加这条会误报 24 条。
            cross = any(def_path != path for _, def_path in wants_tensor[node.func.attr])
            if not cross:
                continue
            if is_numpy_expr(arg, aliases) or (
                    isinstance(arg, ast.Name) and _assigned_from_numpy(tree, arg.id, aliases)):
                out.append({
                    "rule": "tensor_api_mismatch",
                    "severity": "blocking",
                    "file": str(path.relative_to(ROOT)),
                    "line": node.lineno,
                    "detail": "把 numpy 数组传给 .%s()；该方法内部对参数调用 .numpy()（numpy 数组无此方法）"
                              % node.func.attr,
                })
    return out


def _assigned_from_numpy(tree, name, aliases):
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and is_numpy_expr(node.value, aliases):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    return True
    return False


def rule_timeout_attribution(trees, instr_text):
    """规则 EX-03：题面把超时归基础设施，代码把 timeout 归候选。

    形态（0340 实测）：
        instruction.md： 「超时属于基础设施错误」
        evaluate_verify.py： _INFRA_FAULT_PREFIXES = ("privilege_drop_", "eval_env_failed")
                             "eval_timeout_%ds" 不在其中 ⇒ 归候选 −1
    """
    out = []
    if not instr_text:
        return out
    if not re.search(r"(超时|timeout)[^。\n]{0,60}(基础设施|infra|infrastructure|单独报告|非候选|与候选无关)",
                     instr_text, re.I):
        return out
    for path, tree in trees.items():
        if tree is None:
            continue
        for node in ast.walk(tree):
            # 只认 `_INFRA...` 变量名的赋值（首版按"含 privilege 的字符串元组"匹配，
            # 会误命中普通错误消息元组，v25.5.5 上误报 2 条）
            if not isinstance(node, ast.Assign):
                continue
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if not any("INFRA" in n.upper() for n in names):
                continue
            val = node.value
            if not isinstance(val, (ast.Tuple, ast.List)):
                continue
            vals = [e.value for e in val.elts
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            if not any("timeout" in v.lower() for v in vals):
                out.append({
                    "rule": "timeout_attribution_mismatch",
                    "severity": "needs_manual",
                    "file": str(path.relative_to(ROOT)),
                    "line": node.lineno,
                    "detail": "题面声明超时属基础设施，但 %s 不含 timeout（成员：%s）"
                              % ("/".join(names), ", ".join(vals) or "空"),
                })
    return out


def rule_absolute_claims(trees, instr_text):
    """规则 EX-02：题面「绝对声明」清单（供人工/报告逐条对账）。

    不自动判 fail——只把声明挖出来，强制 review.json 逐条绑定证据。
    0340 的 QA05/QA11 都是「题面写了、实现没做」。
    """
    out = []
    if not instr_text:
        return out
    pat = re.compile(r"[^\n。]{0,30}(不可|无法|不能|必须|仅|只|不会|一律)[^\n。]{0,40}")
    seen = set()
    for m in pat.finditer(instr_text):
        s = m.group(0).strip()
        if len(s) < 12 or s in seen:
            continue
        seen.add(s)
        if len(seen) > 40:
            break
        out.append({
            "rule": "absolute_claim",
            "severity": "informational",
            "file": "instruction.md",
            "line": instr_text[:m.start()].count("\n") + 1,
            "detail": "绝对声明：%s" % s,
        })
    return out


def _tuple_arity(node):
    """`return a, b, c` → 3；`return (a, b)` → 2；其余 → None。"""
    if isinstance(node, ast.Tuple):
        return len(node.elts)
    return None


def rule_return_arity(trees):
    """规则 EX-04：返回值元数与调用方解包个数不一致。

    形态（2001 实测，活到 v37）：
        def run(...):
            ...
            return 3, 0.0, "timeout"      # 三元组
        total, score = run(...)           # 二元组解包 ⇒ ValueError
      `.5` / `toolfix.1` 查「退出码分不分类」全 pass；`toolfix.2` 走真实调用链才炸。

    ★ 只在「同一文件内定义、且所有 return 元数一致」时才判，
      避免把 `return x, y` / `return None` 混写的函数误报。
    """
    out = []
    for path, tree in trees.items():
        if tree is None:
            continue
        defs = {}
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            arities = set()
            for sub in ast.walk(node):
                if isinstance(sub, ast.Return) and sub.value is not None:
                    a = _tuple_arity(sub.value)
                    if a is not None:
                        arities.add(a)
            if len(arities) == 1:
                defs[node.name] = (arities.pop(), node.lineno)
        if not defs:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if not isinstance(node.value, ast.Call):
                continue
            # ★ 只认裸函数调用（`run(...)`），不认 `self.env.step(...)`。
            #   理由：同名方法在不同类里语义完全不同——dm_control 的 `self._env.step()`
            #   返回单个 TimeStep 对象，会被误判成「4 元组按 1 个解包」（实测误报 9 条）。
            if not isinstance(node.value.func, ast.Name):
                continue
            name = call_name(node.value)
            if name not in defs:
                continue
            arity, def_line = defs[name]
            n_targets = 0
            for t in node.targets:
                if isinstance(t, ast.Tuple):
                    n_targets = len(t.elts)
                elif isinstance(t, ast.Name):
                    n_targets = 1
            if n_targets and n_targets != arity:
                out.append({
                    "rule": "return_arity_mismatch",
                    "severity": "blocking",
                    "file": str(path.relative_to(ROOT)),
                    "line": node.lineno,
                    "detail": "%s() 在 :%d 一律返回 %d 元组，此处按 %d 个解包 ⇒ ValueError"
                              % (name, def_line, arity, n_targets),
                })
    return out


# ────────────────────────── 2026-11 新增：执行环境类规则 ──────────────────────────
# 以下规则的错误类定义（4.13 纪律）：凡「运行环境/移交/评分链在诚实路径上必然
# 出错」的形态，无论出现在哪个文件都算。来源：平台 1074 题复盘 rev 1145 与
# 2026-11-03 返修指南的八类已确认运行缺陷，全部为真实打回，不是假设攻防。

def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def find_dockerfiles(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            if fn == "Dockerfile" or fn.startswith("Dockerfile."):
                yield Path(dirpath) / fn


def find_task_toml(root: Path):
    best = None
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        if "task.toml" in filenames:
            p = Path(dirpath) / "task.toml"
            if best is None or len(p.parts) < len(best.parts):
                best = p
    return best


def rule_landlock_dependency(trees):
    """EX-05：无条件 import landlock —— 平台环境不可用 ⇒ 训练/评分未开始即退出。

    形态（复盘八类之一）：可信入口 `import landlock` / `from pylandlock import ...`
    无 try/except 保护。有 ImportError 守护的只记 informational。
    """
    out = []
    targets = ("landlock", "pylandlock")
    for path, tree in trees.items():
        if tree is None:
            continue
        import_nodes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.split(".")[0] in targets:
                        import_nodes.append((node, a.name))
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").split(".")[0] in targets:
                    import_nodes.append((node, node.module))
        for node, mod in import_nodes:
            guarded = False
            for t in ast.walk(tree):
                if isinstance(t, ast.Try) and node in t.body:
                    names = {h.type.id for h in t.handlers
                             if isinstance(h.type, ast.Name)}
                    if names & {"ImportError", "Exception", "BaseException", "OSError", "ModuleNotFoundError"}:
                        guarded = True
                    break
            out.append({
                "rule": "landlock_dependency",
                "severity": "informational" if guarded else "blocking",
                "file": str(path.relative_to(ROOT)),
                "line": node.lineno,
                "detail": ("%simport %s；平台环境 Landlock 不可用——%s"
                           % ("有 ImportError 守护的" if guarded else "无条件",
                              mod,
                              "仍须确认降级后保护语义" if guarded
                              else "训练/评分入口会在启动即崩溃，移除强依赖并保留边界检查")),
            })
    return out


SERVICE_HINT = re.compile(
    r"(uvicorn|gunicorn|nginx|serve|server|service|jupyter|socat|sshd|"
    r"http\.server|flask|start\.sh|entrypoint)", re.I)


def rule_entrypoint_only_init(dockerfiles, root):
    """EX-06：服务/资产准备只出现在镜像 ENTRYPOINT/CMD（informational，强制绑定）。

    平台直接执行约定命令时不隐式触发 ENTRYPOINT（复盘八类之一）。
    静态无法判定平台实际调用方式，只挖出声明位置强制 review 绑定。
    """
    out = []
    for p in dockerfiles:
        text = _read_text(p)
        for i, raw in enumerate(text.replace("\\\n", " ").splitlines(), 1):
            m = re.match(r"\s*(ENTRYPOINT|CMD)\s+(.+)", raw, re.I)
            if m and SERVICE_HINT.search(m.group(2)):
                out.append({
                    "rule": "entrypoint_only_init",
                    "severity": "informational",
                    "file": str(p.relative_to(root)),
                    "line": i,
                    "detail": "服务/准备指令出现在镜像 %s——平台按约定命令直接执行时"
                              "不会隐式触发；须在正式入口显式接入准备与就绪检查" % m.group(1).upper(),
                })
    return out


ROOT_LITERAL = re.compile(r"[\"'](/root/[^\"']*)[\"']")


def rule_home_writability(dockerfiles, trees, text_files, root):
    """EX-07：非 root USER 运行时代码硬编码 /root/ —— HOME/临时目录不可写类缺陷。

    复盘八类之一：HOME/缓存/日志目录按实际运行 UID 初始化。镜像声明了非 root
    USER 而 .py/.sh 硬编码 /root/ 字面量 ⇒ 确定性失败；无 USER 声明时 UID 未知
    ⇒ needs_manual，不猜。
    """
    user_non_root = False
    for p in dockerfiles:
        for raw in _read_text(p).splitlines():
            m = re.match(r"\s*USER\s+(\S+)", raw, re.I)
            if m and m.group(1).strip("'\"") not in ("root", "0"):
                user_non_root = True
    out = []
    hits = []
    for p in text_files:
        if p.suffix.lower() not in (".py", ".sh", ".bash"):
            continue
        for i, line in enumerate(_read_text(p).splitlines(), 1):
            m = ROOT_LITERAL.search(line)
            if m:
                hits.append((p, i, m.group(1)))
    for p, i, lit in hits:
        out.append({
            "rule": "home_writability",
            "severity": "blocking" if user_non_root else "needs_manual",
            "file": str(p.relative_to(root)),
            "line": i,
            "detail": ("硬编码 /root/ 路径 %r" % lit
                       + ("——镜像声明了非 root USER，运行时必然 Permission denied"
                          if user_non_root
                          else "——镜像未声明 USER，实际运行 UID 未知，须按平台运行身份核对")),
        })
    return out


def rule_artifacts_handoff(task_toml, instr_text, trees, root):
    """EX-08：artifacts 移交声明与题面提交路径/评分读取路径不一致。

    复盘八类之一：「Agent 有候选，Verifier 却收到空目录」。确定性形态：
    题面声明的提交路径与 task.toml artifacts 不一致 ⇒ blocking；
    artifacts 声明后 tests/ 与题面均无引用 ⇒ needs_manual。
    """
    out = []
    if task_toml is None:
        return out
    text = _read_text(task_toml)
    artifacts = []
    try:
        import tomllib
        data = tomllib.loads(text)
        v = data.get("artifacts")
        if isinstance(v, list):
            artifacts = [str(x) for x in v]
    except Exception:
        m = re.search(r"artifacts\s*=\s*\[([^\]]*)\]", text, re.S)
        if m:
            artifacts = re.findall(r"[\"']([^\"']+)[\"']", m.group(1))
    if not artifacts:
        out.append({
            "rule": "artifacts_handoff_mismatch",
            "severity": "needs_manual",
            "file": str(task_toml.relative_to(root)),
            "line": text[:text.find("artifacts")].count("\n") + 1 if "artifacts" in text else 0,
            "detail": "task.toml 未声明 artifacts——候选移交契约无从核对，"
                      "按平台执行器要求补齐声明",
        })
        return out

    # ① 题面提交路径 vs artifacts
    instr_paths = set(re.findall(r"/workspace/[A-Za-z0-9_./-]+", instr_text or ""))
    submit_paths = set()
    for m in re.finditer(r"[^\n]*(提交|submit|solution|移交|写入)[^\n]*", instr_text or "", re.I):
        submit_paths.update(re.findall(r"/workspace/[A-Za-z0-9_./-]+", m.group(0)))
    norm_art = {a.rstrip("/") for a in artifacts}
    conflict = [s for s in submit_paths if s.rstrip("/") not in norm_art]
    if conflict:
        out.append({
            "rule": "artifacts_handoff_mismatch",
            "severity": "blocking",
            "file": "instruction.md",
            "line": 0,
            "detail": "题面提交路径 %s 与 task.toml artifacts %s 不一致——"
                      "初始化、题面、artifacts 声明、平台移交和评分读取位置必须统一"
                      % (sorted(conflict)[:3], artifacts),
        })
    # ② artifacts 路径是否被 tests/ 或题面引用
    referenced = False
    for a in artifacts:
        base = a.rstrip("/")
        if base in instr_paths or base in (s.rstrip("/") for s in submit_paths):
            referenced = True
            break
        for path, tree in trees.items():
            src = _read_text(path)
            if base in src or base.split("/")[-1] in src:
                referenced = True
                break
        if referenced:
            break
    if not referenced:
        out.append({
            "rule": "artifacts_handoff_mismatch",
            "severity": "needs_manual",
            "file": str(task_toml.relative_to(root)),
            "line": 0,
            "detail": "artifacts 声明 %s 未被 tests/ 或题面任何文件引用——"
                      "核对 Verifier 实际读取路径与移交声明是否同一次运行" % artifacts,
        })
    return out


WRITE_FUNCS = {"write", "save", "savefig", "dump", "to_csv", "to_json",
               "to_parquet", "savetxt", "makedirs", "mkdir", "touch"}


def rule_submission_pollution(trees, artifacts, root):
    """EX-09：公开评测向提交目录写入缓存/日志——污染严格提交白名单。

    复盘八类之一：可信评估的缓存/日志须放评估输出位置。只报字面量写目标
    命中 artifacts 路径的调用，动态拼接记覆盖限制。
    """
    out = []
    if not artifacts:
        return out
    for path, tree in trees.items():
        if tree is None:
            continue
        src = _read_text(path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fname = call_name(node)
            is_write_open = (fname == "open" and len(node.args) >= 2
                             and isinstance(node.args[1], ast.Constant)
                             and isinstance(node.args[1].value, str)
                             and node.args[1].value in ("w", "a", "x", "w+", "a+"))
            if not (is_write_open or fname in WRITE_FUNCS):
                continue
            lits = [n.value for n in ast.walk(node)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str)]
            for lit in lits:
                for a in artifacts:
                    if str(lit).startswith(a.rstrip("/")):
                        out.append({
                            "rule": "submission_dir_pollution",
                            "severity": "blocking",
                            "file": str(path.relative_to(root)),
                            "line": node.lineno,
                            "detail": "写操作目标 %r 落在提交目录 %s——缓存/日志须移到"
                                      "评估输出位置，公开评测不得污染提交白名单"
                                      % (lit, a),
                        })
                        break
                else:
                    continue
                break
    return out


def rule_atomic_replace_race(trees, root):
    """EX-10：同文件同时出现原子替换与链接数检查——两者存在已证实竞态。

    复盘八类之一：os.replace 与单链接（st_nlink）检查需要有界重开约定。
    静态只能证明「两者同文件共存」，竞态判定与修复方式须人工读码 ⇒ needs_manual。
    """
    out = []
    for path, tree in trees.items():
        if tree is None:
            continue
        has_replace = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if (node.func.attr in ("replace", "rename")
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "os"):
                    has_replace = True
                    break
        if not has_replace:
            continue
        src = _read_text(path)
        if "st_nlink" in src or "nlink" in src.lower():
            out.append({
                "rule": "atomic_replace_race",
                "severity": "needs_manual",
                "file": str(path.relative_to(root)),
                "line": 0,
                "detail": "同文件同时使用 os.replace/os.rename 与 st_nlink 链接数检查——"
                          "平台已证实原子替换与单链接检查存在竞态；发布/读取约定须兼容"
                          "瞬态（有界重开），不得删安全检查或无限重试",
            })
    return out


ROOT = Path(".")


def main():
    global ROOT
    ap = argparse.ArgumentParser(description="执行层门禁（Gate C）")
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--instruction", default=None,
                    help="instruction.md 路径（默认在 root 下自动找）")
    args = ap.parse_args()

    ROOT = Path(args.root).resolve()
    if not ROOT.is_dir():
        print("FATAL: root not found: %s" % ROOT)
        return 2

    trees = {}
    for p in iter_py(ROOT):
        trees[p] = parse(p)
    aliases = collect_numpy_aliases([t for t in trees.values() if t])

    instr_path = Path(args.instruction) if args.instruction else None
    if instr_path is None:
        cand = list(ROOT.rglob("instruction.md"))
        instr_path = cand[0] if cand else None
    instr = instr_path.read_text(encoding="utf-8", errors="replace") if instr_path and instr_path.is_file() else ""

    # 2026-11 新增规则的材料：Dockerfile、task.toml、文本文件、artifacts 声明
    dockerfiles = list(find_dockerfiles(ROOT))
    task_toml = find_task_toml(ROOT)
    text_files = [p for p in ROOT.rglob("*")
                  if p.is_file() and p.suffix.lower() in (".py", ".sh", ".bash")
                  and not (SKIP_DIRS & set(p.parts))]
    artifacts = []
    if task_toml is not None:
        tt_text = _read_text(task_toml)
        try:
            import tomllib
            v = tomllib.loads(tt_text).get("artifacts")
            if isinstance(v, list):
                artifacts = [str(x) for x in v]
        except Exception:
            m = re.search(r"artifacts\s*=\s*\[([^\]]*)\]", tt_text, re.S)
            if m:
                artifacts = re.findall(r"[\"']([^\"']+)[\"']", m.group(1))

    findings = []
    findings += rule_tensor_api(trees, aliases)
    findings += rule_return_arity(trees)
    findings += rule_timeout_attribution(trees, instr)
    findings += rule_absolute_claims(trees, instr)
    findings += rule_landlock_dependency(trees)
    findings += rule_entrypoint_only_init(dockerfiles, ROOT)
    findings += rule_home_writability(dockerfiles, trees, text_files, ROOT)
    findings += rule_artifacts_handoff(task_toml, instr, trees, ROOT)
    findings += rule_submission_pollution(trees, artifacts, ROOT)
    findings += rule_atomic_replace_race(trees, ROOT)

    for i, f in enumerate(findings, 1):
        f["id"] = "EX-%02d" % i

    blocking = [f for f in findings if f["severity"] == "blocking"]
    manual = [f for f in findings if f["severity"] == "needs_manual"]
    report = {
        "gate": "execution_path",
        "root": str(ROOT),
        "files_scanned": len(trees),
        "instruction": str(instr_path) if instr_path else None,
        "summary": {"blocking": len(blocking), "needs_manual": len(manual),
                    "informational": len(findings) - len(blocking) - len(manual)},
        "findings": findings,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("scanned %d py files, instruction=%s" % (len(trees), bool(instr)))
    for f in findings:
        if f["severity"] != "informational":
            print("  [%s] %s %s:%d  %s" % (f["severity"].upper(), f["id"],
                                           f["file"], f["line"], f["detail"][:120]))
    print("summary: %s" % json.dumps(report["summary"]))
    print("written:", out)
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
