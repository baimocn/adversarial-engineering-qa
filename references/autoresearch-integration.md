# AutoResearch / Harbor 官方分级调用与 v4 全覆盖

## 1. 四层职责与唯一权威

处理 AutoResearch / Harbor 题包时，必须依次完成以下四层；不得用其中一层替代另一层。

1. **官方领域层**：`autoresearch-task-qa-legacy-waiver`，负责原 v0.3.10 的 G01–G03、QA01–QA21、H01–H06、F01–F07、NOP、轨迹、资源、指纹、原标准和历史豁免。
2. **Baseline 专项层**：`autoresearch-baseline-quality`，负责 B01–B08；官方 `research-quality.md` 规定的最低核对表只在专项 Skill 不可用时作为明确降级的 fallback。
3. **原 v4 工程深挖层**：`references/autoresearch-v4-original.md` 是原提示词的逐字保留版；六道闸门、4.1–4.13、5.1–5.6、十三张命名底稿、最终八步输出和 18 条收尾核验卡均以此原文为操作权威。
4. **新增对抗实现层**：本 Skill 的 Gate A/B、E15–E20、跨文件契约、行为矩阵、有效反例、ablation 和独立红队。它只增加检查，不修改官方规则，不覆盖官方原判。

`references/autoresearch-v4-coverage.json` 是覆盖 ID、官方 18 份 references、交付文件和机器展开规则的唯一清单权威。覆盖校验通过只说明调用、记录和交付完整，不等于机器已经替代人工语义审查。

**平台专项伴随层（2026-11 新增）**：`official/autoresearch-supplement-platform-audit`（1.0.1，只读内嵌副本）提供 A 原版六类增量审计 + B 平台专项（B-C01–B-C04、B-P/B-E/B-S 原因族）。它**不替代**上述四层，也**不改写**官方原判；其 B-C01–B-C04 的机械部分由 `scripts/check_platform_rules.py` 直接执行，语义部分（三判断分离、责任三标记、证据三态、处理清单）按其原文执行。同一根因在多层出现时共用一个 finding 编号，不重复制造返修项。

## 2. 先探测官方 Skill，再开始题包判断

官方 Skill 已内嵌到本 Skill 根目录 `official/`（只读副本），默认以相对路径解析：

- `official/autoresearch-task-qa-legacy-waiver`
- `official/autoresearch-baseline-quality`

优先使用用户显式 `--official-skill` 指定的路径；显式路径失败即失败，不静默回退。否则依次解析环境变量 `AUTORESEARCH_QA_SKILL`，最后落到内嵌 `official/` 相对路径。不得凭记忆假定官方 Skill 存在，也不得默认依赖外部绝对路径。

```bash
python scripts/check_autoresearch_integration.py contract \
  --out "<输出目录>/official-contract.json"
```

该命令必须核实：

- 官方名称和版本 `0.3.10-standard-waiver.5`；
- 18 份官方 references 与四个核心脚本；
- 内嵌 `official/autoresearch-baseline-quality`；
- `audit_standard_with_waivers.py --help` 真实可运行，且暴露 `source`、`--standard-review`、`--review`、`--out-dir`；
- 上述官方文件的合同 SHA-256。

缺官方 Skill、版本不符、Baseline 专项缺失或 CLI 探测失败时，整题最高 `INCOMPLETE`。不得用本 Skill 内摘要冒充官方领域层。官方 Skill 本体始终只读。

### 2.1 官方热更新只允许显式同步

官方 Skill 可能热更新。质检过程中不得自动同步、不得修改 `official/` 内嵌副本。需要更新时由用户显式执行：

```bash
python scripts/sync_official_skills.py --check   # 只比较，不写入
python scripts/sync_official_skills.py --apply   # staging 校验后原子替换
```

同步后必须重新运行 `contract` 探测并人工复核兼容合同；官方规则/版本变化不得静默接受。

## 3. 官方领域层：必须真实执行完整入口

### 3.1 先读规则并收集，不把初稿当终稿

按官方 `SKILL.md` 读取 18 份 references。先形成闸门 1 清单，再运行完整入口生成收集初稿和内部模板：

```bash
python "official/autoresearch-task-qa-legacy-waiver/scripts/audit_standard_with_waivers.py" "<待检 ZIP 或目录>" \
  --out-dir "<输出目录>/collection"
```

无 review 的运行只是收集/模板阶段。`collection/report.json` 不得作为最终结论；`audit_collection.py`、`audit_format_repair.py` 和 F01–F07 也都不能替代完整审查。

### 3.2 分级完成 Baseline 与官方语义底稿

在安全清点和任务根定位后，按 `autoresearch-baseline-quality` 完成 B01–B08，将结论放在优化面之后、Reference 提升结论之前。只有该 Skill 确实不可用时，才使用官方 `research-quality.md` 最低核对表，并把降级列为覆盖缺口。

将收集阶段生成的模板复制到输出终稿目录之外的 `worksheets/`：

- `standard_review.json`：原标准内部 review，完整填写 overview、G01–G03、QA01–QA21、H01–H06、轨迹、资源、格式和 NOP；
- `legacy_review.json`：完整逐项内容、两轨可比性、F 项、逐 finding 豁免和 `standard_resolutions`。

逐条打开证据填写。空白模板、收集初稿和未处理的 `standard_findings` 都不能通过。

### 3.3 运行官方原标准 + 豁免最终入口

```bash
python "official/autoresearch-task-qa-legacy-waiver/scripts/audit_standard_with_waivers.py" "<待检 ZIP 或目录>" \
  --standard-review "<工作底稿目录>/standard_review.json" \
  --review "<工作底稿目录>/legacy_review.json" \
  --out-dir "<输出目录>/waiver_review"
```

保留官方退出码和原样输出：

| 退出码 | 官方 waiver decision | 含义 |
|---|---|---|
| 0 | `PASS_WITH_WAIVERS` | 完整审查已完成；不等于没有历史原判 |
| 1 | `FAIL` | 存在未被豁免的实质失败 |
| 2 | `ERROR` | 输入、底稿、审查或豁免 reconcile 未完成 |

将 `waiver_review/standard/` 原样复制为最终交付的 `standard_review/`，不得修改原报告。将填写的 `standard_review.json` 复制为最终交付根目录的 `review.json`，以满足原 v4 的逐项底稿要求；本 Skill 的对抗报告另存为 `adversarial_review.json`。

官方报告必须同时保留 `standard_decision`、原 finding、具体豁免 reason code、豁免后状态及 NOP/资源/轨迹/指纹明细。当前实现缺陷不得通过历史豁免消失。

## 4. 原 v4 工程深挖层：逐闸门执行，不做摘要替代

加载 `references/autoresearch-v4-original.md` 并严格执行：

1. 闸门 1：18 份 references 清单及 QA/H/G/F 路由；
2. 闸门 2：先建 QA01–QA21、H01–H06、G01–G03、F01–F07 空表；
3. 闸门 3：逐项 evidence、定位、归属、口径、自身产物能力链、落锤到判级映射和独立重判；
4. 闸门 4：4.1 有效性字段、4.2 正式值、4.3 绕过面、4.4 资源、4.5 同预算效果、4.6 派生数、4.7 废止、4.8 归属、4.9 口径、4.10 判读队列、4.11 同表横看、4.12 自身产物复现链、4.13 类泛化；
5. 闸门 5：5.1 算术、5.2 三门与 Baseline、5.3 分层 decision、5.4 逐 finding 豁免、5.5 表格口径/归属、5.6 有效时长；
6. 闸门 6：全部交付、唯一最薄弱环节、逐 run 分母、人工判读与机器扫描分母、未核对类别。

4.1 的有效性字段溯源表放在 `formal_value_recompute.json` 的独立 `validity_fields` 部分，避免原文“十三张命名文件”与最终十三类检查之间的命名歧义；其余命名文件不得合并或省略。

生成覆盖工作表：

```bash
python scripts/check_autoresearch_integration.py init-coverage \
  --artifact "<待检包>" --sha256 "<实测 SHA-256>" \
  --out "<输出目录>/autoresearch_coverage.json"
```

该工作表展开原 v4、官方 QA/H/G/F、Baseline B01–B08、E1–E25、18 条核验卡、最终八步输出和独立红队。每项只允许 `pass/fail/manual`；PASS 必须有本轮证据，FAIL 必须关联 finding。某类没有适用对象时，也要核查后写明“不适用事实已确认”的证据，不能留空或直接跳过。

## 5. 新增对抗实现层与错误类台账

在官方和原 v4 检查之外，继续完成主 `SKILL.md` 的 Gate A/B、声明—实现—行为链、返回契约、公开命令原样执行、攻击到达目标、对照/ablation 和独立红队。

E1–E14 按原文保留；新增：

| 编号 | 错误类定义 | 必查动作 |
|---|---|---|
| E15 | 分支返回契约不一致 | 枚举所有返回点与调用点，覆盖超时/异常分支 |
| E16 | 声明接口无法原样执行 | 在声明 cwd、布局、参数和环境中逐字执行；静态未授权时记 manual |
| E17 | 隔离语义夸大 | 分栏检查进程、文件、UID、挂载和网络边界，不互相替代 |
| E18 | 无效负向测试/弱 oracle | 先证明攻击到达目标，再检查目标性质、对照和 ablation |
| E19 | 早退或不变性被误继承为完整覆盖 | 列出 NOP/空数据/缺权重/历史 PASS 实际覆盖和未测分支 |
| E20 | 跨文件 producer/consumer/config/docs 关联丢失 | 建四联单和跨分片笔记，从 consumer 反向追踪 |

2026-11 新增（来源：Harbor 1074 题执行复盘 rev 1145、`autoresearch-supplement-platform-audit` 1.0.1、2026-11-03 返修指南；引用时连版本日期一起引）：

| 编号 | 错误类定义 | 必查动作 |
|---|---|---|
| E21 | 源包配置违规（多份 task.toml、专家源配 docker_image、依赖非官方源、npm 未走 bnpm） | `check_platform_rules.py` 机械核对 B-C01–B-C04；注释/说明中的字段名不算配置；README 里的 URL 不算生效包源 |
| E22 | 运行环境执行缺陷（Landlock 强依赖、非 root USER 硬编码 /root/、服务仅靠镜像 ENTRYPOINT 初始化、HOME/临时目录不可写、原子替换与单链接检查竞态） | Gate C 新规则 `landlock_dependency` / `home_writability` / `entrypoint_only_init` / `atomic_replace_race`；静态判不了的（进程上限、UID 未知）记 needs_manual，不猜 |
| E23 | 资产缺失与移交断链（模型/分词器未交、artifacts 声明与题面提交路径或 Verifier 读取路径不一致、Verifier 收到空目录） | Gate C `artifacts_handoff_mismatch`；仅 MANIFEST 或「运行时挂载」一句话不算交付 |
| E24 | 提交目录污染与评分回传断裂（公开评测缓存/日志写进提交白名单路径；reward 未生成/回传失败/null） | Gate C `submission_dir_pollution`；评分问题核对最终候选→Verifier 输入→原始指标→平台 reward→归档全链；不补造 0 分 |
| E25 | 责任错置（把平台镜像/网络/回传故障归为作者缺陷，或反之；用「没有日志」推出「没有运行」或「运行失败」） | finding 必填 `responsible`（author/platform/unresolved）与 `action`；三个判断分开写：运行链路情况 / 成绩可信性 / 作者是否需要返修；证据三态 verified / materials_missing / not_run，不设全局「待核验」结论 |

`generalization_discipline.json` 必须包含 E1–E25 每类定义、来源、检查位置、本轮是否启用、全包分母、命中数、确认/无法判定分布和判级映射。E15–E25 的可静态定位或可动态复现缺陷属于当前实现问题，不适用历史迁移豁免。

## 6. 最终交付结构

所有输出必须写入 `references/multi-review-workspace.md` 定义的独立会话目录（`reviews/<任务编号>__<包版本>__<模型名>__<会话ID>/`），不得与共用提取树或其他模型/会话的输出混放。结构如下：

```text
<输出目录>/
  report.txt / report.md / report.json
  return_to_expert.txt
  review.json                         # 官方原标准逐项底稿副本
  adversarial_review.json            # 新增双门禁与对抗报告
  autoresearch_coverage.json         # 全量覆盖记录
  constraint_bypass.json
  formal_value_recompute.json        # 含 4.1 validity_fields 与 4.2 正式值
  per_run_compliance.json
  resource_compliance.json
  derived_recompute.json
  deprecation_verification.json
  weakest_link.json
  attribution_review.json
  caliber_review.json
  judgement_queue.json
  table_object_caliber_matrix.json
  reproducibility_chain_review.json
  generalization_discipline.json
  standard_review/                   # 官方原标准报告，不改写
  waiver_review/                     # 官方豁免层完整输出，不改写
```

`report.json` 至少分别包含：

```json
{
  "official_standard_decision": "PASS | FAIL | INCOMPLETE",
  "official_waiver_decision": "PASS_WITH_WAIVERS | FAIL | ERROR",
  "adversarial_decision": "PASS | FAIL | INCOMPLETE",
  "coverage_decision": "PASS | FAIL | INCOMPLETE",
  "decision": "PASS | PASS_WITH_WAIVERS | FAIL | INCOMPLETE"
}
```

合并规则取最严格结果：

- 任一未豁免的官方 FAIL、当前实现 FAIL、覆盖 FAIL 或独立红队确认的当前缺陷 → `FAIL`；
- 无确定 FAIL，但官方 ERROR、任一层 INCOMPLETE、覆盖 manual、官方路径缺失或红队未完成 → `INCOMPLETE`；
- 仅具体历史 finding 按白名单通过，且所有当前检查完成 → `PASS_WITH_WAIVERS`；
- 原标准与当前实现均 PASS、无实际豁免且覆盖完整 → `PASS`。

最终八步输出顺序和 18 条收尾核验卡按原 v4 原文执行。`PASS_WITH_WAIVERS` 只能写“带豁免通过”。

## 7. 机器终检

先校验对抗报告，再校验官方分层、覆盖记录、交付哈希和合并 decision：

```bash
python scripts/validate_review.py --review "<输出目录>/adversarial_review.json"

python scripts/check_autoresearch_integration.py validate \
  --review "<输出目录>/adversarial_review.json" \
  --coverage "<输出目录>/autoresearch_coverage.json" \
  --delivery-dir "<输出目录>" \
  --out "<输出目录>/integration-validation.json"
```

`validate` 默认使用内嵌 `official/` 相对路径核对官方实际调用；显式 `--official-skill` 时以其为准且失败不回退。校验器发现缺项、哈希不符、官方未实际执行、decision 被改写或覆盖未闭环时，不得宣布完成。机器校验不替代对原始证据的语义阅读，也不证明未执行的动态行为已经通过。
