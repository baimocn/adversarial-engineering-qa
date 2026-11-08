# Baseline 合理性检查

总评：**在已提供材料范围内合理**。本次只读审查，不执行提交代码，不加载权重，不独立复现。

角色：Starter 为两层 GCN 在冻结损坏训练标签上做交叉熵训练；正式 Baseline 为该方法的三 seed 独立训练结果；主评分 B 为 Hidden 两图宏平均聚合 61.883333。没有另设更弱的评分锚点。clean-label oracle 用于 U，额外使用了干净训练标签，不能当作同输入权限的普通竞争基线。

| 对照条件 | Baseline | Reference |
|---|---|---|
| 源码/入口 | `workspace/harbor_task/environment/starter/train.py`、`predictor/GCN_Predictor.py` | `workspace/reference/train.py`、`predictor/DREAM_Predictor.py` |
| 实际方法 | 噪声训练标签 CE，plain GCN | 训练标签双路结构/特征 kNN 传播推断锚点，同质性重加权与图增强对比目标 |
| 固定条件 | 两图、冻结 uniform@0.3 标签和划分；GCN hidden64/2层/dropout.5；Adam .01/.0005 | 同左；EmbedGCN 为同一骨干族并返回中间表示，没有额外预测层 |
| 日程/实际训练 | 每图 200 epoch、200 optimizer updates，全部完成 | 每图 500 epoch、500 updates，全部完成 |
| 共同预算 | 两图训练 7200 秒；日程为允许研究变量 | 同左 |
| 实测两图训练耗时 | 58.86 / 58.11 / 55.77 秒 | 425.85 / 493.55 / 486.17 秒 |
| 选择/停止 | 验证准确率选点；epoch_budget_exhausted；无早停/异常 | 同左 |
| seed | 3000 / 3001 / 3002；冻结损坏实现不随训练 seed 改变 | 同集合、逐项配对 |
| 模型/评分产物 | 各 seed 两模型、artifact.json、原日志、训练曲线、reload.log | 同左；12 个正式 checkpoint 字节哈希均吻合清单 |

主张 → 证据 → 条件 → 结论：B 并非未训练占位。12 份逐图 `training.jsonl` 的 epoch/updates 连续，全部配置轮数完成；B 的最终 train loss 低，后期 val 低于早期选点，不能据早期 checkpoint 推断训练被截短。B 的 Cora 选点为 8/7/6，CiteSeer 为 39/4/5；Reference 为 401/377/499、296/487/245。两侧均按相同验证准则选点并独立重载。当前明确允许训练日程变化，所以 200/500 的差别不构成固定协议违规；本报告只支持整体方法方案比较，不声称隔离出某一损失组件的贡献。

| 项目 | 状态 | 证据与理由 | 最小修复/补证及复验条件 |
|---|---|---|---|
| B01 代表性 | 通过 | `instruction.md` §2、专家说明 §3、Starter GCN 源码明确该朴素对照的角色与选择。未发现包内同权限、同预算的常见更强锚点证明该选择失当；不以年代或分差要求 SOTA。 | 无阻断修改。 |
| B02 实现与训练健全 | 通过 | `Base_Predictor.py` 的 CE、backward、Adam.step、验证与 checkpoint 恢复路径可定位；6 份 B 图训练完成 200 次更新，无报错。完整曲线不是一直改善却被截断的证据。 | 本次未加载权重；已有独立重载记录内部一致。 |
| B03 公平预算 | 通过 | `instruction.md` §4、`repair/protocol_decisions.json`、各正式 result/log：同一 CPU、数据、评价与 7200 秒上限，epoch 为可研究日程；双方均远低于上限。 | 不要求把允许变量强制相等；平台运行另验。 |
| B04 配置与搜索公平 | 通过 | GCN/DREAM YAML 均固定 backbone/Adam；B200/R500 默认日程和参数披露。公开 val 选点，无只给 B 异常学习率或不合理早停的反证。 | 不替专家进行新调参；无已证不公平。 |
| B05 随机性公平 | 通过 | `train.py` 调用 `setup_seed`；三个 seed 均有独立训练日志，12 个模型 hash 与清单匹配且各 seed 不同。正式候选为各自固定方法/配置，不把 Seed best 的固定内部集成 seed 重复当正式独立训练。 | 无。 |
| B06 基本锚点 | 通过 | 两轨第 1 轮 Starter Dev59.7，与 B seed3000 的公开 val59.7 一致。没有随机/常数对照分数可供额外比较；不编造此类分数。oracle 有额外干净训练标签，不是同权限普通 sanity 方法。 | 无；没有额外锚点本身不失败。 |
| B07 改进归因 | 通过 | Reference `_prepare_pseudo_labels` 只播种 train noisy labels；验证仅评价/选点。旧 v7 使用验证标签的 Reference 已放入 `historical_v7_invalid_reference/`，没有用于现有正式 B/R。 | 只支持联合方法收益；若另作单项贡献主张，应有相应消融，本轮未提出该主张。 |
| B08 选择披露 | 通过 | `optimization_evidence/训练证据说明.md`、专家说明 §3–4、comparison/protocol_decisions：角色、日程、共同预算、seed、选点、旧失败和上界变更均披露。 | 保留 U 事后变更说明，不能改称预注册。 |

正式 Hidden 配对复算：seed3000 B60.05/R70.25/Δ10.20；3001 B62.60/R71.40/Δ8.80；3002 B63.00/R69.95/Δ6.95。B均值61.883333，样本标准差1.600260；R均值70.533333，样本标准差0.765398；Δ8.65，约5.40537σ_B。引用 `formal_test_scoring_declared.json` 的12条逐图 test 值；各 result.metrics 明确是 val，不混用。

生效 U=75.1333 时归一化约0.652830；原定数学上限100时约0.226935，均通过区间门。`repair/protocol_decisions.json` 明确经验 U 是出分后变更，故不称预注册；oracle 三 seed 的原记录及重载另在 `u_anchor_oracle/`。经验 U 的剩余余量4.599967略小于3σ_B≈4.800781，作为研究空间风险保留，不升级为硬门。

关键红旗：未发现正式 Baseline 的直接不公平红旗。历史 v7 Reference 的验证标签泄漏已明确无效，不因返修获得有效分数身份。

专家退回说明：Baseline 专项无阻断返修项；保留全部失败、seed、原始日志与 U 选择披露。当前平台构建、NOP、运行隔离验证和历史时长证明按总报告逐原因处置，不转化为 Baseline 不合理。

边界：只读文本、配置、指标、模型文件大小与 SHA-256；未反序列化模型或资产。文件和已有重载记录内部一致不等于本次独立复现；无完整原 sessions 的行为覆盖有限。
