# v2.6 深度审计报告（2026-11-13）

- 审计对象：`baimocn/adversarial-engineering-qa`，`main@a01bca6`（v2.6 合并后）
- 审计分支：`audit-v2.6`
- 方法：逐文件人工审阅 + 定向回归测试 + Mimosa deep scan + v27 实跑
- 结论：**发现 3 个需要修的问题（1 high、1 medium、1 low），已修复；2 条官方 kernel advisory 接受并记录；Mimosa 深度扫描为 inconclusive/partial，不宣称项目安全。**

## 一、发现与处置

### F1（HIGH，已修）分解命令可执行任意代码

- 位置：`scripts/run_decomposition_checks.py` 的 `ALLOWED_COMMANDS`
- 问题：原白名单包含 `bash`、`sh`、`node`，且 `python` 允许 `-c`；拆题由模型生成，恶意或错误的 spec 可以执行任意 shell/JS/Python 代码，绕过“只跑题包检查”的边界。
- 修复：
  - 白名单收窄为 `python` / `python3` / `pytest`；
  - `python` 的第一个参数必须是 task root 下的 `.py` 文件；拒绝 `-c`、`-m`、stdin、绝对路径和 `..`；
  - `pytest` 的非 flag 参数必须落在 task root 内；
  - `validate_decomposition.py` 做同样的前置校验，runner 再做一次运行前校验。
- 回归：`tests/test_decomposition.py` 新增 `python -c`、`bash` 两个用例；`tests/test_strict_orchestration.py` 新增 `python -c`、`bash` 两个 runner 用例。

### F2（MEDIUM，已修）静态检查/证据可读超大文件

- 位置：`scripts/run_decomposition_checks.py`、`scripts/validate_decomposition.py`、`scripts/panel_lib.py`
- 问题：`file_contains` / `json_value` / `regex` / 行证据会整文件读入内存；模型可指向 70MB 资产或构造超大文件，造成内存压力。
- 修复：统一 8,000,000 B 上限；超限直接 fail/拒绝，不做读取。
- 回归：`tests/test_strict_orchestration.py::test_large_file_rejected`（8,000,001 B）。

### F3（LOW，已修）SKILL.md 版本头滞后

- 位置：`SKILL.md` 顶部 `**版本**`
- 问题：README 已到 v2.6，SKILL.md 仍写 v2.5。
- 修复：改为 `v2.6（2026-11-13）`。

### F4（ADVISORY，接受，不修）官方 kernel 的 `audit_task.py:1988`

- Mimosa deep scan 报 2 条 high advisory，分别在：
  - `official/autoresearch-task-qa-legacy-waiver/scripts/audit_task.py:1988`
  - `official/autoresearch-unified-qa/scripts/audit_task.py:1988`
- 人工数据流复核：
  - `main(argv=None)` 的 `argv = sys.argv[1:]` 只在显式 argv 缺失时使用；
  - `parse_args(argv)` 得到 `args.source`，`source = args.source.expanduser().resolve()`；
  - `inspect_source_kind(source)` 只做 `stat` / `os.scandir` / `open`，路径来自 CLI 调用者；
  - 本仓库的 `qa_official.py` / `qa_unified.py` 只传入本地可信题包路径，不把远端输入交给它。
- 结论：advisory 成立但不可在本仓库的调用链上利用；官方包只读，不修改。`verdictEffect: none`。

### F5（覆盖缺口，接受）Mimosa 扫描为 inconclusive/partial

- Scan ID `scan-2026-11-13T16-10-32.275Z-2d119ce2066b`，seal `sha256:f3766185…`。
- 131 文件选中/解析，0 读取失败、0 解析失败；`threatModel` / `findingDiscovery` partial，`validation` / `pathAnalysis` / `reporting` completed。
- 本报告的人工审阅覆盖新增 strict 层、官方层接入点、workflow 与测试；**没有**逐行审阅 vendored 0.3.10/0.5.0 官方包的全部实现。不能把本报告当作“官方包无问题”的证明。

## 二、验证

- 全仓测试：**129/129 OK**（1 skipped）。
- v27 实跑（`strict_verify.py --package-zip`）：
  - `decision=INCOMPLETE`；
  - `verified=1`（instruction 披露 256 文件上限）；
  - `open_ids=[official-0.3.10:auditor, official-0.5.0:auditor]`（官方底稿未填）；
  - `fail_ids=[]`（旧版本地预填的布局误报没有进入 verified fail）。
- 定向安全用例：`python -c` / `bash` / 超 8MB 文件均被拒绝。

## 三、残余风险（如实）

1. **进程级沙箱**：独立 temp dir + 解释器 + 超时 + 最小环境；不是容器级网络/内存/只读隔离。
2. **`python <script>` 仍会执行题包内代码**：这是“CPU 真跑”的设计目标；脚本被限制在 task root 内，但脚本自身的行为不做沙箱。
3. **证据引用可以很短**：`panel_lib` 只校验 quote 是该行子串，不判断语义充分性；短引用可能弱化双评审。
4. **官方层底稿仍需填**：0.3.10 的 21 项与 0.5.0 的 90 项未填时，strict 只能是 INCOMPLETE；这是 fail-closed，不是缺陷。
5. **官方 advisory 仍在**：两条 `audit_task.py:1988` 保持只读，未打补丁。
