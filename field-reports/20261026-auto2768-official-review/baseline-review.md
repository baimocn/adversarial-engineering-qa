# Baseline 合理性检查

总评：**在已提供材料范围内合理**。采用用户指定的 autoresearch-baseline-quality，完成 B01–B08 只读核查。未执行提交代码、训练、模型重载或私有评分，未反序列化权重。

角色：Starter 为 plain GCN + corrupted-label cross entropy；正式 Baseline 为该起点的三 seed 独立训练；reward 的 B 为该正式 Baseline 的隐藏测试宏平均 61.8833。Reference 是修复验证标签隔离后的 DREAM。clean-label oracle 只用于 U，不是正常任务可用的训练数据或竞争候选。

| 对照条件 | Baseline | Reference |
|---|---|---|
| 来源与源码 | `workspace/harbor_task/environment/starter/predictor/GCN_Predictor.py`；正式记录为 gcn | `workspace/reference/predictor/DREAM_Predictor.py`；正式记录为 dream |
| 固定条件 | 两图固定特征/边/划分与 uniform@0.3 损坏训练标签；GCN 64宽2层、dropout0.5；Adam lr0.01、weight_decay0.0005 | 同左；标签可靠性、辅助对比目标及日程为研究变量 |
| 数据边界 | train-only noisy_label 监督；干净 val 仅评价与 checkpoint 选择 | 同类锚点从损坏 train 标签经结构/特征双路 LP 推断；val 不进入训练或读出 |
| 实际训练 | 每图200 epoch、200 optimizer updates；六个图级日志全部正常预算结束 | 每图500 epoch、500 updates；六个图级日志全部正常预算结束 |
| 选中 epoch（seed 3000/3001/3002） | Cora 8/7/6；CiteSeer 39/4/5 | Cora 401/377/499；CiteSeer 296/487/245 |
| 共同预算与实际成本 | 两图训练上限7200秒；记录55.77–58.86秒，CPU | 同一上限；425.85–493.55秒，CPU；不宣称等耗时单因素比较 |
| 模型与重载 | 6个 checkpoint 存在且字节哈希匹配计分登记；每个图独立重载记录与预测一致声明 | 同左；没有用同一权重冒充全部训练 seed |

| seed | B Cora/CiteSeer 选点 | R Cora/CiteSeer 选点 | 测试宏平均 B → R | 改善 |
|---|---|---|---|---|
| 3000 | 8 / 39 | 401 / 296 | 60.05 → 70.25 | 10.20 |
| 3001 | 7 / 4 | 377 / 487 | 62.60 → 71.40 | 8.80 |
| 3002 | 6 / 5 | 499 / 245 | 63.00 → 69.95 | 6.95 |

复算：B 均值61.883333、样本标准差1.600260；R 均值70.533333、样本标准差0.765398；Δ=8.65=5.405370σ_B。U=75.1333 下归一化0.652832，数学上限100下0.226935。U 是出分后替换的实证锚点，不能称为预注册；两口径均达标。来源为 `optimization_evidence/formal_test_scoring_declared.json`、`comparison_summary.json`、`expert_evidence/repair/protocol_decisions.json` 及全部 `baseline_runs/seed_*/result.json`、`reference_runs/seed_*/result.json`。

| 项目 | 状态 | 主张 → 证据 → 比较条件 → 结论 | 最小修复/补证及复验条件 |
|---|---|---|---|
| B01 代表性 | 通过 | 题面明确以 plain GCN+CE 为合理朴素起点；GCN 方法与固定骨架下的噪声鲁棒研究匹配。`instruction.md` §2/4、`GCN_Predictor.py`、专家说明§3支持此角色；没有用年代、低分或R增益推断不合理。 | 无需换成SOTA或新增外部锚点。 |
| B02 实现与训练健全 | 通过 | `Base_Predictor.py` 的 train-only 损失、zero_grad/backward/step、val选点及严格reload链可定位；流式读取12份逐epoch日志，B全200更新、R全500更新。B末期训练loss降至约0.010–0.024，val低于选中早期最佳，未见故障初始化或无依据截断。 | 无需因B训练轮数较少而补训；结果不等于独立动态复现。 |
| B03 公平预算 | 通过 | `instruction.md` §4、`protocol_decisions.json` 明确epoch日程可变且共有7200秒上限；全部正式B/R同CPU、同图/切分/指标/seed。R成本较高但均在共同上限内，结论限定整体方案改善。 | 不要求相同epoch；若改称等耗时单因素贡献，应另提供相应已有控制。 |
| B04 配置与搜索公平 | 通过 | GCN固定0.01/0.0005等正常配置，B200/R500为披露默认值；val统一选点，失败开发尝试完整保留于`historical_development_attempts/`。未见只对B设置失真参数或测试集选checkpoint。 | 无直接异常，无需替专家重做最优调参。 |
| B05 随机性公平 | 通过 | 三seed3000/3001/3002逐项配对；`utils/tools.py` setup_seed进入Python/NumPy/Torch；12个正式权重字节哈希互异并与计分索引一致。staged最佳方法内部15个seed与正式B/R重复训练明确分开。 | 不把同一checkpoint复评分或内部集成成员算作正式重复；现有材料支持未出现该错误。 |
| B06 基本锚点 | 通过 | 正式B就是未经修改可运行Starter；两轨首轮公开Dev59.7与B seed3000公开val59.7对应。U是专家侧clean-label oracle，数据权限更强，不应作为普通公平Baseline要求。没有编造随机/常数成绩。 | 无需新增随机锚点或借oracle削弱B。 |
| B07 改进归因 | 通过 | 新DREAM双路LP监督只来自train labels；val只评价选点，固定资产/切分/骨架/预算。旧v7验证标签泄漏Reference明确单列INVALID，未纳入当前三seed。`DREAM_Predictor.py`、`data.py`、`reload.py`与新正式记录一致支持整体方法改进。 | 不将历史污染分数作为正证；无须凭旧泄漏推定新正式结果一律无效。 |
| B08 选择披露 | 通过 | 专家说明、训练说明、protocol_decisions说明B来源、200/500日程、选择规则及U后选；正式结果和失败历史保留。当前专家说明seed3000的Δ=8.10是可定位的文档算术错误，需更正为10.20，但不构成Baseline被削弱的证据。 | 更正文档首行Δ，与原始计分记录一致；不改原模型或重训。该当前错误由总审查保留未豁免。 |

关键红旗：未发现直接弱化 Baseline、挑最差 seed、复制同一模型冒充独立重训或验证标签监督新正式 Reference 的证据。未独立验证未知权重内容或所有历史进程行为。

专家退回说明：Baseline 合理性专项通过；总审查中的当前文档算术问题仍需修正。请将专家说明§4 seed3000的增量由+8.10更正为+10.20，验收只需与两图宏平均及现有正式JSON一致，不要求重训、新跑Agent或补平台NOP。

边界：静态源码、日志、原始指标和哈希内部一致，不等于本次独立复现。CPU记录未冒充H20/L20实测；平台镜像准备、当前Trial与物理隔离属平台后续事项，未当成Baseline不合理的依据。逐运行提取与哈希观察保存在工作目录 `static-observations.json`。
