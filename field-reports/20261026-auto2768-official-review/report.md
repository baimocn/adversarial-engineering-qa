# 优化面介绍

固定两张引文图的特征、边、划分和损坏训练标签，在固定GCN/Adam骨架内设计噪声鲁棒训练与图上推断方法。AST守卫开放方法类及数值hooks，非仅常量搜索。

可修改：训练损失及辅助一致性/对比目标；样本/邻居可靠性加权与筛选；train-only标签传播与伪目标；训练日程及支持的分阶段集成；无标签图推断读出。

固定面：Cora/CiteSeer公开资产与划分、uniform 0.3损坏标签(seed 3000)；GCN 64宽2层ReLU dropout0.5，无额外层/归一化；Adam lr0.01 weight_decay0.0005；两图训练7200秒声明预算、私有测试与宏平均指标。

指标与质量门：maximize两图测试准确率百分数宏平均；reward=(x-B)/(U-B)，B=61.8833,U=75.1333；模型可加载且预测非退化，硬门失败-1。资格审查另以100为分母并要求Δ≥3σ_B。

# Baseline 与 Reference 跑分

Baseline 方法：未经改动的朴素GCN，在固定损坏训练标签上作交叉熵训练；每图200次Adam更新，使用验证指标选择checkpoint；Starter、正式B和reward零锚点对应同一方法。

Reference 方法：修复后的DREAM：仅从损坏训练标签以结构/特征kNN双路传播推断同类锚点，语义同质性重加权并加入对比学习；每图500次更新、相同骨干/Adam/资产/预算，val仅评价选点。

主指标：macro_average_hidden_test_accuracy_percent（越高越好）。

| training_seed | Baseline | Reference | 配对改善 | 有效性 |
|---|---:|---:|---:|---|
| 3000 | 60.05 | 70.25 | 10.2 | B:是 / R:是 |
| 3001 | 62.6 | 71.4 | 8.8 | B:是 / R:是 |
| 3002 | 63 | 69.95 | 6.95 | B:是 / R:是 |

汇总：Baseline 均值 61.8833333333，样本标准差 1.60026039548；Reference 均值 70.5333333333，样本标准差 0.765397500214。

改善结论：全部正式seed配对改善10.20/8.80/6.95；均值B61.883333,R70.533333,Δ8.65,σ_B1.600260,Δ/σ_B5.405370；生效U75.1333下0.652832，预声明天花板100下0.226935，均在[0.15,0.8]。专家说明第4节首行Δ误写8.10，保留为当前文字算术错误，不改变原始成绩有效性。

质量门：12个B/R图级运行均记录非退化与独立reload预测相同；12个checkpoint字节SHA与计分登记一致，未反序列化；日志实际200/500轮正常结束。旧v7泄漏Reference单列INVALID且不纳入；新平台实跑未执行。

# 前置内容门槛

| 门槛 | 结论 | 原因 |
|---|---|---|
| G01 方法级优化空间 | 通过 | 方法接口可实现损失/可靠性估计/无标签读出及阶段计划；DREAM有真实方法语义变化，非纯常量搜索。 |
| G02 Baseline 合理性 | 通过 | Baseline在已提供材料范围内合理；实际200更新并按val选点，预算/seed/数据公平；五维详见底稿及baseline-review.md。 |
| G03 Reference 提升充分性 | 通过 | 完整三seed正式改善Δ8.65=5.40537σ_B；生效锚点归一化0.652832、天花板口径0.226935均达标；oracle剩余4.6略低于3σ的4.80078，作为空间风险。 |

G03 复算：Δ=8.65；σ_B（样本标准差）=1.60026039548；U=75.1333；归一化分数=0.652831831023。

# 两条轨迹迭代概况

| Agent 轨迹 | 状态 | 打包轮数 | 声明有效轮数 | 有效时长 | 概况与最终结果 |
|---|---|---:|---:|---:|---|
| codex | 完整 | 193 | 193 | - | GCE/小损失分类配额→邻域平滑/硬投票→裕量与单源支配门控，r183最佳66.7，后续184–193未提升；历史66.7，已有原字节复验66.7；非当前协议Hidden成绩。 |
| seed | 完整 | 53 | 52 | - | small-loss/双路LP→TLP→多阶段共识5成员集成→度数感知硬化，r43最佳71.4；ILC/EMA/SWA等失败或持平完整保留，35与36非两个独立成功试验；历史71.4，原字节复验71.1；迁移当前数值接口后Dev71.2(74.2/68.2)，不是历史71.4复现或正式R。 |

# 轨迹可信性与题包绑定

codex：分数有效性待确认；seed：分数有效性待确认

| 轨迹 | 所交内容审查 | 分数与当前包对应 | 审查范围 | run_summary 哈希 |
|---|---|---|---|---|
| codex | 待补充核验 | 分数有效性待确认 | 仅审查已交轮次/方法摘要；未提供工具调用或sessions，结论限于这些材料。 | run_summary 的四项题包哈希与当前包一致。 |
| seed | 待补充核验 | 分数有效性待确认 | 仅审查已交轮次/方法摘要；未提供工具调用或sessions，结论限于这些材料。 | run_summary 的四项题包哈希与当前包一致。 |

# QA15 资源证据

16CPU/0GPU，完整一轮保守估3600秒，包括训练、重载及评分；纯CPU不需要换H20/L20。当前源码重验runtime与历史Docker环境分别保留。

| 运行 | 计时范围 | 记录耗时（秒） | GPU 数量/型号 | 分配 CPU 核 |
|---|---|---:|---|---:|

资源需求估算：完整一轮约 3600 秒，0 张 GPU，16 核 CPU；正式最慢两图493.55秒；更重3阶段×5成员×200epoch当前复验已完成。预留约1小时覆盖进程启动、独立reload和私有评分，非内场实测或任意候选上界证明。

计时口径：完整一轮训练+独立重载+评分；非10h研究时间，排队安装不计。

# 目标部署能力

配置范围：innerfield-maso-v1

当前交付符合内场能力检查；Solver/Verifier 仍须不同 sandbox。

任务硬件与成绩对应：cpu / same_hardware；B/R同一声明Docker环境均CPU；后续Python3.10主机Dev重验不是正式B/R迁到新卡成绩。交付两侧0GPU；无证据确认正式B/R跨卡不公平。
证据：optimization_evidence/baseline_runs/seed_3000/result.json；optimization_evidence/baseline_runs/seed_3001/result.json；optimization_evidence/baseline_runs/seed_3002/result.json；optimization_evidence/reference_runs/seed_3000/result.json；optimization_evidence/reference_runs/seed_3001/result.json；optimization_evidence/reference_runs/seed_3002/result.json；workspace/harbor_task/task.toml；expert_evidence/repair/current_source_revalidation/runtime.json

# 格式对齐建议

三目录职责明确；正式seed聚合目录下含两图模型/曲线/重载，为等价布局；旧开发/污染记录为留档不计分，不能因多交扣错。原始time为历史记录，未回填新字段。

- `optimization_evidence/_layout_migrated.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/_layout_v2.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_3000/curve.csv`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_3000/model/citeseer/metrics.json`（可合并）：指标通常可并入同目录的 result.json。
- `optimization_evidence/baseline_runs/seed_3000/model/cora/metrics.json`（可合并）：指标通常可并入同目录的 result.json。
- `optimization_evidence/baseline_runs/seed_3001/curve.csv`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_3001/model/citeseer/metrics.json`（可合并）：指标通常可并入同目录的 result.json。
- `optimization_evidence/baseline_runs/seed_3001/model/cora/metrics.json`（可合并）：指标通常可并入同目录的 result.json。
- `optimization_evidence/baseline_runs/seed_3002/curve.csv`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_3002/model/citeseer/metrics.json`（可合并）：指标通常可并入同目录的 result.json。
- `optimization_evidence/baseline_runs/seed_3002/model/cora/metrics.json`（可合并）：指标通常可并入同目录的 result.json。
- `optimization_evidence/formal_test_scoring_declared.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/historical_development_attempts`（可保留的额外项）：保留失败开发记录，继续与正式结果分开标识。
- `optimization_evidence/historical_v7_invalid_reference`（可保留的额外项）：保留验证标签泄漏旧Reference为INVALID，勿纳入正式改善。
- `optimization_evidence/public_dev_qualification.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/README.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_3000/curve.csv`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_3000/model/citeseer/metrics.json`（可合并）：指标通常可并入同目录的 result.json。
- `optimization_evidence/reference_runs/seed_3000/model/cora/metrics.json`（可合并）：指标通常可并入同目录的 result.json。
- `optimization_evidence/reference_runs/seed_3001/curve.csv`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_3001/model/citeseer/metrics.json`（可合并）：指标通常可并入同目录的 result.json。
- `optimization_evidence/reference_runs/seed_3001/model/cora/metrics.json`（可合并）：指标通常可并入同目录的 result.json。
- `optimization_evidence/reference_runs/seed_3002/curve.csv`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_3002/model/citeseer/metrics.json`（可合并）：指标通常可并入同目录的 result.json。
- `optimization_evidence/reference_runs/seed_3002/model/cora/metrics.json`（可合并）：指标通常可并入同目录的 result.json。
- `optimization_evidence/u_anchor_oracle`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `expert_evidence/repair`（可合并）：可为多轮迁移说明增加当前事实索引，历史证据保持原样。

说明：额外材料仅作精简或归位建议，不因多交而单独判错。

# 质检结论：不通过

产物：evidence-input｜通过 15 项｜不通过 2 项｜未完成 4 项｜跳过/不适用 0 项

前置三门：通过 3 项｜不通过 0 项｜待核验 0 项；全部复核完成：否。

口径：只读检查及已有证据复核；QA07/08 查 instruction；QA18 审所交轨迹及提供的 sessions，QA21 单独核对 run_summary 的四项题包哈希；QA15 允许根据日志、轨迹和B/R实现估算资源。QA16 两条各至少 10h；仅无训练且单轮很短、例外证据完整时可各至少 7h。排队、安装与故障不计有效迭代时长。未执行提交代码、未独立复跑或反序列化模型。

Harbor 格式/接口：未完成；已提交 NOP 的运行或任务版本关联待核实。

| 检查项 | 是否通过 | 原因 |
|---|---|---|
| QA01 八章节与题面信息泄露 | 通过 | 题面八节有实质目标/环境/评分/范围/边界/提交/流程/完成条件；未给参考论文、仓库或方法答案。 |
| QA02 评分公式与 0/1 锚点 | 通过 | verifier-owned calibration B61.8833 U75.1333；normalize_score为未裁剪线性(x-B)/(U-B)，B→0,U→1。 |
| QA03 参考解分数与复现材料 | 通过 | Reference源码/入口、三seed×两图非空原始日志、逐epoch曲线、模型及独立reload齐全；归一化0.652832。 |
| QA04 波动指标的 3σ 可分辨性 | 通过 | 固定候选按3000/3001/3002独立重训，setup_seed进入Python/NumPy/Torch；σ_B按n-1复算，改善≥5σ。staged内成员seed不冒充正式重复。 |
| QA05 约束执行实现 | 不通过 | 源码守卫、模型加载门及run.sh每图3600秒训练timeout存在；但删禁网字段后没有联网查原始干净标签的执行防护，此具体迁移缺口按白名单处理。 |
| QA06 Verifier 入口、分数与错误处理 | 通过 | bash /tests/test.sh用隔离Python进入可信grader；成功写有限主reward，两类错误保留分类，未处理异常也落reward。 |
| QA07 instruction 中的 Hidden 信息泄露 | 通过 | 仅审instruction，未披露隐藏测试节点标签、答案或可恢复样本。 |
| QA08 instruction 中的参考解信息泄露 | 通过 | 仅审instruction，已去除B/R具体epoch与耗时提示；未泄露Reference代码、配置或原始分数。 |
| QA09 结果清理与原子写入 | 通过 | main先clean_stale_rewards删除txt/json，再同目录.tmp经os.replace原子替换，优先json一致写同值。 |
| QA10 冻结面保护或恢复实现 | 通过 | Agent以非root身份，data/starter/public_eval只读；Verifier私有policy/calibration/labels独立预置，候选源码不导入，AST固定scaffold校验；不声称完整物理隔离认证。 |
| QA11 instruction 八项内容 | 通过 | 八部分输入输出/范围/资源/评分互相吻合；训练预算明确不含独立reload，Dev --out统一solution可写路径；run.sh旧注释含reload属陈旧注释，以实际调用与题面明确范围为准。 |
| QA12 Git 清理 | 通过 | 完整清点未发现.git目录。 |
| QA13 Baseline 与参考解提升 | 不通过 | 正式配对原值与改善有效；但当前专家说明§4 seed3000表格将70.25-60.05误写+8.10，应+10.20，与formal_test_scoring_declared一致性错误未豁免。 |
| QA14 合法改进空间 | 通过 | 合法方法空间包含图一致性目标、样本可靠性与读出组合；Reference未饱和，oracle headroom4.6略低3σ为风险而非硬失败，数学天花板余量29.4667。 |
| QA15 评分资源需求估算 | 通过 | 16CPU/0GPU，完整一轮保守估3600秒，包括训练、重载及评分；纯CPU不需要换H20/L20。当前源码重验runtime与历史Docker环境分别保留。 |
| QA16 轨迹实际迭代时长 | 待补充核验 | codex缺少有效时长或排除排队/安装/故障的核算证据；seed缺少有效时长或排除排队/安装/故障的核算证据 |
| QA17 Harbor Harness 兼容性 | 待补充核验 | Harbor 子项未通过：H02 版本与配置；H03 环境与运行路径；H05 Job/Trial 调用配置；H06 NOP 自检记录；详细原因与证据保留在 report.json。 |
| QA18 轨迹、日志与分析 | 待补充核验 | 两条193/53轮均属本题、不同模型独立探索；已读全部轮次及映射。启动最高档/空输出/历史Prompt全量等证明不足；未见已确认两轨任务条件实质差异，不能声称已证实相同。 |
| QA19 seed 与有效提升阈值 | 通过 | 题面§7公开冻结corruption seed及训练seed集合，说明Δ>0、≥3样本σ和[0.15,0.8]资格阈值，区分候选单份评分。 |
| QA20 修改范围、网络与工具策略 | 通过 | 题面§4/5明确修改范围、禁止外部干净标签查表、网络现状与平台默认工具策略。 |
| QA21 三个 JSON 的填写内容 | 待补充核验 | trajectory/annotation/summary可解析，246轮八字段齐全、best对应；当前四项hash可重算，但当前指纹不能倒推绑定历史dream-v1运行，按迁移缺口处理。 |

# 退回专家说明

QA05 约束执行实现（不通过）：源码守卫、模型加载门及run.sh每图3600秒训练timeout存在；但删禁网字段后没有联网查原始干净标签的执行防护，此具体迁移缺口按白名单处理。
证据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/contract_guard.py；workspace/harbor_task/tests/grader.py；workspace/harbor_task/environment/starter/run.sh；workspace/harbor_task/task.toml
请修改/补充：保留真实历史状态；本轮不要求新证明或补跑，由豁免层逐原因处置。
复检验收材料：依据现有材料与对应历史豁免政策复核，不把未运行写成成功。

QA13 Baseline 与参考解提升（不通过）：正式配对原值与改善有效；但当前专家说明§4 seed3000表格将70.25-60.05误写+8.10，应+10.20，与formal_test_scoring_declared一致性错误未豁免。
证据：expert_evidence/专家作业说明文档.md；optimization_evidence/formal_test_scoring_declared.json；optimization_evidence/comparison_summary.json
请修改/补充：仅更正专家说明§4 seed3000的Δ为+10.20；保留正式原始记录和历史失败记录。
复检验收材料：文档表格由两图宏平均复算，与formal_test_scoring_declared逐seed一致；无需重训或新跑Agent。

QA16 轨迹实际迭代时长（待补充核验）：codex缺少有效时长或排除排队/安装/故障的核算证据；seed缺少有效时长或排除排队/安装/故障的核算证据
证据：expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/timing_codex.tsv；expert_evidence/run_summary.json；expert_evidence/timing_seed.tsv
请修改/补充：为codex、seed补一张时长表：研究起止、排队/安装/API失联/故障区间、仍正常运行的训练重叠及有效秒数。可引用已交轨迹和日志片段；不强制提交完整timer或sessions。
复检验收材料：可复算的两轨起止/扣除表，与轨迹时间相符；默认每轨≥36000有效秒。最终复验、收集和明确故障不计，健康训练并发只计一次。

QA17 Harbor Harness 兼容性（待补充核验）：Harbor 子项未通过：H02 版本与配置；H03 环境与运行路径；H05 Job/Trial 调用配置；H06 NOP 自检记录；详细原因与证据保留在 report.json。
证据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/private/cora_test.npz；workspace/harbor_task/tests/private/citeseer_test.npz；workspace/harbor_task/instruction.md；expert_evidence/repair/harbor/schema_validation.json；workspace/harbor_task/tests/test.sh；workspace/harbor_task/environment/starter/run.sh；expert_evidence/repair/harbor/native_nop_trial/native_trial/config.json；expert_evidence/repair/harbor/native_nop_trial/native_trial/result.json；expert_evidence/repair/harbor/native_nop_trial/VERSION_BINDING.md；expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/reward.json；expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/reward.txt；expert_evidence/repair/harbor/native_nop_trial/native_trial/trial.log；expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/test-stdout.txt
请修改/补充：保留真实历史状态；本轮不要求新证明或补跑，由豁免层逐原因处置。
复检验收材料：依据现有材料与对应历史豁免政策复核，不把未运行写成成功。

QA18 轨迹、日志与分析（待补充核验）：两条193/53轮均属本题、不同模型独立探索；已读全部轮次及映射。启动最高档/空输出/历史Prompt全量等证明不足；未见已确认两轨任务条件实质差异，不能声称已证实相同。
证据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/best_method_selection.json；expert_evidence/qa16_best_method_revalidation.json；expert_evidence/run_summary.json#task_binding
请修改/补充：保留真实历史状态；本轮不要求新证明或补跑，由豁免层逐原因处置。
复检验收材料：依据现有材料与对应历史豁免政策复核，不把未运行写成成功。

QA21 三个 JSON 的填写内容（待补充核验）：trajectory/annotation/summary可解析，246轮八字段齐全、best对应；当前四项hash可重算，但当前指纹不能倒推绑定历史dream-v1运行，按迁移缺口处理。
证据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/expert_annotation.json；expert_evidence/best_method_selection.json
请修改/补充：保留真实历史状态；本轮不要求新证明或补跑，由豁免层逐原因处置。
复检验收材料：依据现有材料与对应历史豁免政策复核，不把未运行写成成功。
