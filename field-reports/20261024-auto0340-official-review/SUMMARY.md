# auto0340 · 平台官方质检两轮实录（FAIL → FAIL）

**平台来源**。飞书题包表 `质检附件` 字段，官方 skill `standard_review_with_waivers` 阶段出品，非我方复核。

## 两轮概览

| 轮次 | 目录 | 日期 | decision | 21 项结果 | 关键 fail |
|---|---|---|---|---|---|
| 1 | `../20261024-auto0340-official-review/` | 2026-10-24 | **FAIL** | 11 pass / 4 waivers / **6 fail** | QA05、QA10、QA11、QA13、QA15、QA17 |
| 2 | `../20261030-auto0340-official-review/` | 2026-10-30 | **FAIL** | 13 pass / 4 waivers / **4 fail** | QA05、QA06、QA11、QA17 |

## 判据要点（standard_findings 摘录）

- **第 1 轮（32 条 findings）**。Baseline 的 Q 头末层权重与偏置全为 0，`soft_ce_scalar` 在零点的计算图梯度为 0，Q 无法启动学习，三组 B 不能作健康对照；环境文件有 hash 门禁但题面固定的 `plan/_estimate_value_iq` 与 config 分支未校验；评分父进程 import 候选代码，候选拿到可信文件属主权限，`a-w` 保护不住冻结面。
- **第 2 轮（16 条 findings）**。静态 G6 剥离 docstring 但运行时指纹未剥离，starter 与可信副本的说明字符串差异导致失配；评分父进程传 `np.ndarray` 给 `TensorWrapper.step`，正常动作首步抛 `AttributeError`；评测超时被默认归候选计 −1，与题面"超时属基础设施错误"矛盾。

## 驱动了哪些判据

- **QA05/QA10 到 Gate C 的 frozen-surface 家族**。第 1 轮的"边界放错位置"（候选在可信进程里被 import）与第 2 轮的"静态指纹与运行时指纹不一致"是 `check_execution_path.py` 冻结面规则的直接来源。
- **第 2 轮超时归因到 `timeout_attribution_mismatch` 规则**。题面与实现的超时归属矛盾被机械化。
- **第 2 轮 ndarray 崩溃**，`return_arity_mismatch` 与正常路径崩溃类检查的案例来源之一。

## 脱敏

manifest 保留平台表 ID、记录 ID、run_id（仅 ID）。全部文件经扫描确认无本机路径与个人信息。
