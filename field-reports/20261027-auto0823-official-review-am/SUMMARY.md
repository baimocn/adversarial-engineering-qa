# auto0823 · 平台官方质检两轮实录（同日两轮，均 FAIL，唯一 fail 均为 QA21）

**平台来源**。飞书「三期专家自行选题表」（`tblZRCgkFlAMaUBy`）的 `质检附件` 字段，官方 skill `standard_review_with_waivers` 阶段出品，非我方复核。两轮同日（2026-10-27），以 UTC 时间区分，上午轮 14 时 25 分（`-am` 目录），晚间轮 22 时 35 分（`-pm` 目录）。

## 两轮概览

| 轮次 | 目录 | generated (UTC) | decision | 21 项结果 | fail |
|---|---|---|---|---|---|
| 上午 | `../20261027-auto0823-official-review-am/` | 2026-10-27 14 时 25 分（UTC） | **FAIL** | 15 pass / 5 waivers / **1 fail** | QA21 |
| 晚间 | `../20261027-auto0823-official-review-pm/` | 2026-10-27 22 时 35 分（UTC） | **FAIL** | 15 pass / 5 waivers / **1 fail** | QA21 |

两轮 21 项结构完全相同（15/5/1），但 findings 内容不同，晚间轮比上午轮多 1 条（14 条变 15 条），判据在当天内发生了加码。

## 判据要点（standard_findings 摘录）

- **两轮共同**。禁网迁移缺口（TOML 已移除不支持的禁网字段，`HF_HUB_OFFLINE` 与读出 seccomp 不等于整个 Agent 禁网，按已批准白名单处理）；时长核算证据缺失；Harbor H02/H03/H05/H06 未通过；Seed 多成员旧分无完整权重、已撤回得分主张仅作研究记录。
- **上午轮独有**。best_method 说明两处实质错误，gpt56 的 README 把 Seed 的 5 成员仅存 1 个写成本目录限制；专家表把 winner 隐藏 reward 写 1.3179，与 83.96 及现 B/U 应得的 1.307072 不符。
- **晚间轮独有**。best_method 训练输出未生成 `inference.json`，`run.sh` 直接调用当前 Dev 合同，实际回放缺省单视图恒等读出，与所称 18 视图仿射方法不符。这是上午轮没有的新发现，且直指"声明的方法与实际回放路径不一致"。

## 驱动了哪些判据

- **两轮的 QA21 到 D-C01/D-C02 的"声明与实物对账"强化**。说明文档数值与 JSON 复算不符（1.3179 对 1.307072）、训练输出缺 `inference.json`，都是"包内声明必须能被机械复核"的案例。
- **晚间轮的读出回放缺口**，指向 Gate C 对"声明方法是否真在评分链上执行"的检查方向。方法文件存在不等于回放时真的被调用。
- **禁网迁移两轮连续出现**，对应 `platform_scope` 与白名单口径。平台已批准的 `unsupported_network_policy` 豁免在报告里如何表述，成为本 skill 处理同类挂账的参照。

## 脱敏

manifest 保留平台表 ID、记录 ID、run_id（仅 ID）。全部文件经扫描确认无本机路径与个人信息。
