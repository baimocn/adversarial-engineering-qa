# field-reports · 平台质检报告收集处

这里收**平台侧（官方 skill / 官方质检链路）对题包出的质检报告**。平台出的 FAIL、豁免和覆盖声明，是本 skill 判据反推的原始素材。我们自己的复核报告不入库，自己人写的报告证明不了判据，平台出的结论才可以。

## 已入库样本

| 目录 | 内容 |
|---|---|
| `20261024-auto0340-official-review/` | auto0340 第 1 轮，FAIL，6 项 fail（QA05/QA10/QA11/QA13/QA15/QA17），含 SUMMARY |
| `20261030-auto0340-official-review/` | auto0340 第 2 轮，FAIL，4 项 fail（QA05/QA06/QA11/QA17），含 SUMMARY |
| `20261024-auto2001-official-review/` | auto2001 第 1 轮，FAIL，7 项 fail（QA02/QA03/QA04/QA13/QA17/QA18/QA21），含 SUMMARY |
| `20261029-auto2001-official-review/` | auto2001 第 2 轮，FAIL，4 项 fail（QA05/QA06/QA11/QA17），含 SUMMARY |
| `20261027-auto0823-official-review-am/` | auto0823 同日上午轮，FAIL，1 项 fail（QA21），含 SUMMARY |
| `20261027-auto0823-official-review-pm/` | auto0823 同日晚间轮，FAIL，1 项 fail（QA21，晚间新增读出回放缺口），含 SUMMARY |
| `20261025-auto2768-official-review/` | auto2768 第 1 轮，FAIL，4 项 fail（QA05/QA08/QA11/QA17），含 SUMMARY |
| `20261026-auto2768-official-review/` | auto2768 第 2 轮，FAIL，1 项 fail（QA13 数值一致性），含 SUMMARY |
| `20261027-auto2768-official-review/` | auto2768 第 3 轮，PASS_WITH_WAIVERS（0 fail，5 项豁免），含 SUMMARY |

九轮来自四个题包（auto0340、auto2001、auto0823、auto2768）的同一条官方链路（`standard_review_with_waivers` 阶段），全部从飞书平台两张表的附件字段下载（三期领题表与三期专家自行选题表），是判据反推的原始素材，读法见各自 SUMMARY。fail 分布有明确共性，QA05 在 0340/2001/2768 三个包的第一轮全部命中，QA17 紧随其后；这正是 `check_execution_path.py` 十条规则的选题依据。

## 你可以交什么

- 平台官方质检报告，任意轮次、任意判定。FAIL、PASS_WITH_WAIVERS、PASS 都收，PASS_WITH_WAIVERS 里的豁免理由同样是判据素材。
- 平台终检 / 审计链路的报告（A/B 两段类）。
- 平台返修指南、复盘副本、规则更新通知的原文。判据反推不只需要报告。

**不收**你自己用本 skill 或其他工具跑出的复核报告。发现检查器误报或漏报请走 issue 加 PR 路线，见主 README「欢迎提 PR」一节。

## 提交前先看

1. **脱敏**。报告里的包路径、本机目录改成 `<package-root>` 这样的占位符；个人账号、邮箱、内部链接一律移除。题包内容只保留触发判据的最小片段，不要整包上传。
2. **一份报告一个目录**，命名 `YYYYMMDD-<题号或别名>-<链路>/`，例如 `20261108-auto1234-official-review/`。目录里放平台原始文件（保持原文件名），外加一个 `SUMMARY.md` 说明来源链路、判定结果与判据要点。
3. **SUMMARY 写四件事**。① 报告出自哪条链路（阶段名/审计入口）；② decision 与关键 fail/豁免清单；③ 你认为哪些条目驱动了或应该驱动判据变化；④ 脱敏了哪些字段。
4. **不要改报告原文**。平台报告按原样入库，改写过的报告没有证据价值。

## 我们怎么用这些报告

- 新判据线索 → 与 `references/platform-criteria-inference.md` 的反转记录对照，必要时开 issue 讨论，对齐后进检查器。
- 规则反转佐证 → 记入判据反推文档的版本历史。
- 与已有样本同链路的 → 并入对照序列（比如同一题包的新一轮）。

收到的报告默认按 CC BY 4.0 与仓库同许可处理；不同意请在 SUMMARY 里注明。
