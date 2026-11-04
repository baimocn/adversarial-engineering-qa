# 审查与报告契约

## 1. 两个门禁不可合并

### Gate A：变更面回归

回答“本轮改动是否引入漂移、是否破坏既有修复”。证据来自基线身份、diff、允许变更范围和回归用例。

### Gate B：当前实现正确性

回答“当前产物本身是否满足声明”。即使文件与旧版逐字节相同，也必须重新检查接口、分支、约束和攻击面。

最终判定取更严格结果。Gate A 的 PASS 不能补偿 Gate B 的 FAIL 或证据不足。

## 2. 证据等级

| 等级 | 含义 | 能支持什么 |
|---|---|---|
| EV0 | 作者 README、自证、旧报告、其他模型转述 | 只能作为待检声明，不能独立支持 PASS |
| EV1 | 文件/字段存在，静态位置已打开核对 | 存在性、格式或局部静态结论 |
| EV2 | 确定性静态推导、复算、路径/契约证明 | 静态 FAIL；有限的静态 PASS |
| EV3 | 本轮在记录环境下直接运行到目标行为 | 已覆盖行为的动态 PASS/FAIL |
| EV4 | 目标可达 + 有效对照 + 核心机制 ablation/独立复现 | 强对抗结论，不自动外推到未测攻击面 |

“有证据”不等于“证据足以支持该结论”。PASS 必须匹配声明所需等级。

## 3. 状态和终判

检查项状态使用 `pass / fail / manual / pass_with_waivers`。Gate A 额外允许有依据的 `not_applicable`。

- 缺实现证据、缺必要动态验证或工具不可用：`manual`。
- 已定位当前实现与声明冲突：`fail`，不因整体不错而降级。
- 原标准层只允许 `PASS / FAIL / INCOMPLETE`。
- 豁免层单独记录 `PASS_WITH_WAIVERS / FAIL / ERROR`；不得覆盖原标准结果。
- 工具找不到原命令时，先区分“声明接口不存在”与“审查环境缺工具”。前者可判 FAIL，后者是 INCOMPLETE。

## 4. review.json 的结构权威

`report-schema.json` 定义字段、必填项、枚举和类型。`validate_review.py` 负责严格 JSON 解析、重复键拒绝和跨字段语义规则。不要在另一份文档复制一套不同字段结构。

最小内容：

- `artifact`：当前对象身份；
- `mode` 与 `scope`：静态/动态、授权、包含和排除范围；
- `change_regression`、`current_correctness`：两个独立门禁；
- `claims`：声明—实现—证据—覆盖；
- `behavior_coverage`：正常和失败分支覆盖；
- `adversarial_cases`：到达目标、对照、ablation 和 oracle；
- `findings`：确认问题及其对门禁/检查项的影响；
- `standard_decision`、`waiver_review`：原判与豁免分层；
- `coverage_statement`、`weakest_link`：实际覆盖分母和最薄弱环节；
- （v1.1）`platform_checks`：B-C01–B-C04 平台硬规则逐项结论，每条带证据三态
  （verified / materials_missing / not_run），不设全局「待核验」；
- （v1.1）`three_judgements`：运行链路情况 / 成绩可信性 / 作者是否需要返修，三个判断分开写；
- （v1.1）finding 可选 `responsible`（author / platform / unresolved）与 `action`
  （author_fix / platform_fix / record_only），两者不得互相矛盾。

## 5. 发现必须进入判级

每个 `finding` 至少关联一个 claim 或 gate。声称“无门槛影响”时写出逐条依据；仅把错误列进报告而所有项照旧 PASS，属于落锤—判级断链。

多个 finding 可指向同一检查项；一个 finding 也可影响多个检查项。不得为让终稿好看而删除已确认 finding。

## 6. 覆盖和否定结论

分别记录：

- 文件总数、索引数、排除数；
- 机器扫描条数；
- 人工逐条判读条数；
- 行为分支总数、实际运行数、未测分支；
- 攻击用例总数、到达目标数、有效对照数。

“未发现 X”只在声明范围内成立。机器扫描 1000 条、人工判读 20 条时，不得写成“全量 1000 条均无问题”。

## 7. 最薄弱环节

必须指出一个最不确定或覆盖最弱的环节，优先从未核对类别、动态未验证声明、静态关联推断和独立红队缺口中选择。不得回答“没有薄弱环节”。

## 8. 报告一致性

`review.json` 是机器权威；`report.md` 至少复述当前对象哈希、模式、两个门禁、确认 finding、覆盖限制、最薄弱环节和终判。任何一边修改结论，另一边必须同步并重新运行校验器。

## 9. AutoResearch 分层报告例外

AutoResearch / Harbor 审查中，官方逐项底稿沿用原 v4 文件名 `review.json`；本节约定的对抗报告命名为 `adversarial_review.json`，并设置 `domain="autoresearch_harbor"`。官方 `standard_review/` 与 `waiver_review/` 保持原样，最终 `report.json` 另外合并官方原标准、官方豁免、对抗实现和覆盖四层 decision。不得为了让通用字段一致而改写官方报告。完整规则见 `autoresearch-integration.md`。
