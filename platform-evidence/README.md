# platform-evidence · 平台经验文档证据库

这里收**平台/项目组在群聊中分享的方法论、失败案例、返修指南与问题汇总**。它们是判据来源与版本演化证据，不是对某一题包的最终合规结论。

入库原则：

1. 原文本地副本按飞书 `docs +fetch --doc-format markdown` / `sheets +table-get` 导出；表格分流数据保留为结构化 JSON。
2. 公共仓库副本必须脱敏：移除一次性登录参数、内部 URL 的敏感 query、个人姓名、内部日志链接、token 型附件地址；保留文档标题、token、来源时间和可复核判据。
3. 不改写原文的判据含义；脱敏只替换定位符/身份信息。
4. 每条材料在 `manifest.json` 中记录 source_doc、type、source_group、share_time、message_id、sha256、status。
5. 当前 gate 只消费 `current_mechanical` / `current_ablation_only` 条目；`platform_scope` 和 `legacy_archived` 不自动判作者失败。

## 四类整合状态

| 类别 | 含义 | 当前处理 |
|---|---|---|
| `current_mechanical` | 最新标准中可静态/机械验证 | 进入当前 gate，必须配 bad/good 消融 |
| `current_ablation_only` | 最新标准相关，但以具体题包回归样本证明 | 保留为 ablation case，不写死通用执行器 |
| `platform_scope` | 只能平台实跑或动态验证 | 只记录 scope，不由本地静态检查判 PASS/FAIL |
| `legacy_archived` | 旧 0.3.10/V4 口径，已被最新标准取代 | 归档参考，不参与当前 gate |

统计见 `integration_matrix.json`；逐篇精读见 `DEEP_READ.md`；规则覆盖差异见 `coverage_matrix.json`。
