# 平台经验整合状态（2026-11-14）

本表回答「官方提供的方法论和失败案例是否都整合了」。结论不是简单的是/否，而是按四类边界列出。

## 材料层：已完整入库

- 全量群消息：通知群 272 条、讨论群 403 条，均 `has_more=false`
- 分享链接与附件：23 个唯一 URL、多个官方 skill 包/QA 文本
- 精读材料：9 份平台经验/方法论/返修文档
- 官方反馈报告：4 轮 FAIL→FAIL→FAIL→PASS 已在 PR #4 原样入库
- 本公共副本：9 份正文 + 精读索引 + 覆盖矩阵 + manifest + 四类整合矩阵

## 规则层：按四类整合

| 类别 | 数量 | 含义 | 例子 |
|---|---:|---|---|
| `current_mechanical` | 12 | 最新标准下可静态/机械验证，已进当前 gate 并有 bad/good 消融 | `-10` hard gate、单一 reward、公开合同 nonlocal/staged 白名单、Oracle handoff、best_method frozen adapter |
| `current_ablation_only` | 1 | 最新标准相关，但只作为具体题包回归样本，不写死通用执行器 | G03 角色源码绑定（auto2768 v28/v29/v30 消融） |
| `platform_scope` | 2 | 只能平台实跑或动态验证，不由本地静态检查判作者 FAIL | Docker/Harbor/Hidden、GPU 实卡、Verifier 预算、终检五类 advisory |
| `legacy_archived` | 4 | 旧 0.3.10/V4 口径，被最新标准取代 | `-1`、NOP 每次补交、PASS_WITH_WAIVERS、两轨 10h/八字段硬门 |

详见 `integration_matrix.json` 和 `coverage_matrix.json`。

## 未转成自动 FAIL 的经验

这些经验已精读并保留在证据库/覆盖矩阵，但**故意不转成当前自动 FAIL**：

- 难度过低 / 难度过高 / 无高分合法解
- Verifier 并行化与预算适配
- GPU H20/L20 实际运行、旧卡结果冒充目标卡
- 公开数据可重建 Hidden
- 超时收尾余量
- 共享 UID + NPROC 进程上限冲突
- 模型/分词器/训练资产完整性
- `MUJOCO_LOG.TXT` / `__pycache__` 具体污染
- Judge 吞异常、CPU 计时沿用旧卡、题面未公开特定限制

原因：这些需要语义判断、受控运行探针或平台执行证据；静态文本匹配会制造误判，且平台当前报告未把它们作为所有题统一 L0。

## 对抗性审查结论

1. **版本轴优先**：0.3.10/V4、0.5.0-current.1、0.5.6-current.1 不能同时激活。冲突由 `config/rule_versions.json` 裁决。
2. **证据与执行分离**：`platform-evidence/` 只证明平台说过什么；`config/rule_catalog.json` 决定什么规则当前生效；`scripts/current_standard_gate.py` 只执行可机械验证的规则。
3. **核心机制消融**：每条 current_mechanical 规则必须有 good PASS / bad FAIL；公共 CI 中若无本地 good_root，会显式记录 skipped，不假装跑过完整包消融。
4. **奥卡姆剃刀**：不构造「所有历史经验都硬编码」的万能 checker。归档、消融、平台 scope、legacy 分层即可。
5. **低耦合**：题包特例放 `config/profiles/auto2768-v30.json` 与 `config/ablation_cases.json`；通用执行器只读 profile。

## 仍需注意

- PR #5 的 CI 在 GitHub 上无本地 v30_tree，会跑单元测试、规则目录校验，并把完整包消融显式标 skipped；本地已跑完整 11 个 bad/good case。
- Mimosa deep 扫描为 `inconclusive / partial`，不宣称项目完全安全。
- 平台后续发布 0.5.7+ 时，先更新版本目录和整合矩阵，再改 gate；不得把旧文档直接回灌成硬规则。
