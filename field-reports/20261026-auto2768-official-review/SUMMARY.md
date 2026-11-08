# auto2768 · 平台官方质检三轮实录（FAIL → FAIL → PASS_WITH_WAIVERS）

**这是 field-reports 的第一批样本**，来自飞书平台对同一题包（auto2768，图标签噪声鲁棒学习）的三轮官方质检。方向与误报申诉相反。平台判据层层加码，题包三轮修复，最后才拿到 PASS_WITH_WAIVERS。想理解本 skill 判据从哪来，这三轮是原始素材。

## 三轮概览

| 轮次 | 目录 | 日期 | decision | 21 项结果 | 关键 fail |
|---|---|---|---|---|---|
| 1 | `20261025-auto2768-official-review/` | 2026-10-25 | **FAIL** | 14 pass / 3 waivers / **4 fail** | QA05 约束执行实现、QA08 参考解信息泄露、QA11 instruction 八项内容、QA17 Harbor Harness 兼容性 |
| 2 | `20261026-auto2768-official-review/` | 2026-10-26 | **FAIL** | 15 pass / 5 waivers / **1 fail** | QA13 Baseline 与参考解提升（seed3000 配对表 Δ 误写 +8.10，应为 +10.20） |
| 3 | `20261027-auto2768-official-review/` | 2026-10-27 | **PASS_WITH_WAIVERS** | 16 pass / 5 waivers / 0 fail | 无 fail。遗留 5 项豁免（时长核算证据、禁网迁移缺口、Harbor H03/H05/H06） |

## 每轮抓到了什么（standard_findings 摘录）

- **第 1 轮**。单轮 7200 秒仅声明未执行、模型加载质量门未实施；题面第 69 行披露 Reference 用 500 epochs（n_epochs 本身是研究变量，属可变配置泄露）；Dev 输出路径与默认身份权限不一致。
- **第 2 轮**。删禁网字段后没有联网查原始干净标签的执行防护；专家说明 §4 的 seed3000 表格 Δ 算错（70.25−60.05 误写 +8.10）；Harbor H02/H03/H05/H06 未通过。
- **第 3 轮**。守卫/加载门/timeout 均已实现且与题面一致；遗留豁免集中在"时长核算证据缺失"与"禁网字段删除未形成可信网络执行"两族；H03/H05/H06 仍挂账。

## 从这三轮长出的 skill 判据

本 skill 的多个机制直接由这三轮驱动。

- **QA05 到 Gate C 执行层门禁**。第 1 轮的"约束仅声明未执行"催生了 `check_execution_path.py` 对"守卫是否真实接线"的静态检查（timeout_attribution_mismatch、landlock_dependency 等 10 条规则）。
- **QA08 到题面泄露扫描**。第 1 轮的 500 epochs 泄露进入判据反推记录，"参考解可变配置不得进题面"成为 QA08 的机械核对口径。
- **QA13 到 D-C02 哈希复算**。第 2 轮的数值一致性错误展示了"声明与实物必须逐字节对账"的必要性，后来固化为 `check_delivery_contract.py` 的 D-C02。
- **QA17/H06 到平台挂账纪律**。Harbor 兼容性与 NOP 复跑这两类本机永远验不了的项目，在本 skill 里强制记 `platform_scope`，不判 FAIL 也不包装成 PASS。

## 怎么读这批文件

每个目录结构相同。

- `report.json` / `report.md`，官方主报告（21 项 QA + Harbor 六项 + content gates + 豁免逐条理由）。
- `standard-waiver/`（若在）与 `waiver_report.md`，标准层底稿与豁免明细。
- `return_to_expert.txt`，平台回传给专家的整改要求原文。
- `manifest.json`，包哈希与 skill 版本标识（`skills_sha256`），可对齐判据版本。
- `baseline-review.md` / `skills-revision.json`，Baseline 侧复核与 skill 修订记录。

## 已做脱敏

原 zip 含平台表 ID、记录 ID 与提交事件号，属平台内部标识，已在 `manifest.json` 中原样保留，仅含 ID，不含个人与本机路径。全部文件经扫描确认无机器路径与个人信息。题包内容仅以 finding 中的「文件与行号」引用形式出现。
