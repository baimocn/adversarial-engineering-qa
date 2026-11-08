# 优化面介绍

Hopper-Hop在线模型化RL，允许重新设计训练期critic目标、价值锚定、专家数据使用和actor/critic模块；实际执行固定use_expert=false的可编程更新函数，并非仅搜索常量。

可修改：_update_vanilla/_td_target_vanilla的损失、目标与数据策略；actor/critic模块及专家数据混合。

固定面：hopper-hop奖励/环境与30回合eval_mode=True评测；plan/_estimate_value_iq与分支开关；数据内容及可信评分文件。

指标与质量门：episode_reward maximize；score=(x-B)/(489.3319-B)，无clip；正式seeds=1/2/3，100000步、30回合；数值要求Δ≥3σ_B和归一化[0.15,0.8]，但健康Baseline质量门当前失败。

# Baseline 与 Reference 跑分

Baseline 方法：Starter原样，中性TD目标r+γQ_target，reward-free世界模型，标量Q集成和symlog回归；100000步在线训练，不使用已加载专家样本。当前零初始化与预测端symlog组合仍阻断Q梯度，故不是健康正式锚点。

Reference 方法：IQ式隐式奖励Q−γV，专家/在线样本混合、软Q目标、χ²正则与初态价值锚定；同100000步及seeds=1/2/3，官方eval_agent重载30回合。

主指标：episode_reward（越高越好）。

| training_seed | Baseline | Reference | 配对改善 | 有效性 |
|---|---:|---:|---:|---|
| 1 | 0.329945773795 | 367.139142703 | 366.809196929 | B:否 / R:是 |
| 2 | 0.0715772312407 | 397.443946274 | 397.372369043 | B:否 / R:是 |
| 3 | 0.00952719380057 | 321.168146531 | 321.158619337 | B:否 / R:是 |

汇总：Baseline 均值 0.137016732946，样本标准差 0.16993752643；Reference 均值 361.917078503，样本标准差 38.4051021674。

改善结论：原始记录Δ=361.780061770，3σ_B=0.509812579，归一化=0.739541794；算术在门槛内，但Baseline实现故障，不能认证真实方法改善。

质量门：记录均COMPLETE且模型文件SHA一致；Baseline健康质量门失败，因此baseline_valid=false；Reference原始实测值保留，不伪称全部正式对照有效。旧comparison_summary已明示作废，不与新值混用。

# 前置内容门槛

| 门槛 | 结论 | 原因 |
|---|---|---|
| G01 方法级优化空间 | 通过 | 可执行的训练损失、目标和模块设计空间开放；Reference改变数据混合和目标形式，超出常量调参。 |
| G02 Baseline 合理性 | 不通过 | Q头末层权重和偏置均为0；soft_ce_scalar对预测值应用sign×log(1+abs)，零点计算图梯度为0，Q无法启动学习。真实Ensemble消融fixed仍q_grad=0；随机线性头控制不能排除此故障。 |
| G03 Reference 提升充分性 | 不通过 | 全部成对数值算术达标，但正式Baseline存在Q零梯度静态故障，三组B均不能作健康对照；大幅提升不能消除此质量门失败。；重算核验：质量门有效性未满足；seed 1 的 baseline_valid 为 false；seed 2 的 baseline_valid 为 false；seed 3 的 baseline_valid 为 false |

G03 复算：Δ=361.78006177；σ_B（样本标准差）=0.16993752643；U=489.3319；归一化分数=0.739541794373。

# 两条轨迹迭代概况

| Agent 轨迹 | 状态 | 打包轮数 | 声明有效轮数 | 有效时长 | 概况与最终结果 |
|---|---|---:|---:|---:|---|
| Codex + GPT-5.6 Sol | 完整 | 8 | 8 | - | 8轮依次尝试continuation支持、反事实校准、planner残差、支持核、IQ目标、势函数、残差校准、保守间隔；R7评分失败，其余7轮出分；真实最佳R2；历史Dev最佳R2=85.168；不作为当前新切分Hidden泛化或作者正式B/R证据。 |
| Codex + Seed 2.1 Turbo | 完整 | 16 | 7 | - | 16条跨4次编排：早期RTG/latent rollout与expectile方向失败或无代码改动；R12首次出分；R14分布式Q+RTG+BC最佳，R15 CQL与R16全回合RTG均未超过。4轮出分、12失败；旧声明7有效轮不等于7成功轮；历史Dev最佳R14=12.2079；不作为当前新切分Hidden泛化或作者正式B/R证据。 |

# 轨迹可信性与题包绑定

Codex + GPT-5.6 Sol：分数无效；Codex + Seed 2.1 Turbo：分数无效

| 轨迹 | 所交内容审查 | 分数与当前包对应 | 审查范围 | run_summary 哈希 |
|---|---|---|---|---|
| Codex + GPT-5.6 Sol | 不通过 | 无效 | 仅审查已交轮次/方法摘要；未提供工具调用或sessions，结论限于这些材料。 | run_summary 的四项题包哈希与当前包一致。 |
| Codex + Seed 2.1 Turbo | 不通过 | 无效 | 仅审查已交轮次/方法摘要；未提供工具调用或sessions，结论限于这些材料。 | run_summary 的四项题包哈希与当前包一致。 |

- Codex + GPT-5.6 Sol：存在泄漏 / 已确认：历史研究时公开100条数据含34条Hidden（已由重切报告确认）；这属于旧题公开集污染，不推断Agent主动越权；原Dev数值留档，不能支持当前未见Hidden。；受影响分数无效；影响轮次 [1, 2, 3, 4, 5, 6, 7, 8]；证据 expert_evidence/repair/dataset_resplit_20261021/resplit_report.json；expert_evidence/专家作业说明文档.md；expert_evidence/trajectory_codex.json
  修复：仅保留历史成绩及原适用范围，排除其作为当前正式B/R正证。；验收：当前已重切数据与重新采集正式结果来源区分清楚，不要求历史Agent重跑。

- Codex + Seed 2.1 Turbo：存在泄漏 / 已确认：历史研究时公开100条数据含34条Hidden（已由重切报告确认）；这属于旧题公开集污染，不推断Agent主动越权；原Dev数值留档，不能支持当前未见Hidden。；受影响分数无效；影响轮次 [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]；证据 expert_evidence/repair/dataset_resplit_20261021/resplit_report.json；expert_evidence/专家作业说明文档.md；expert_evidence/trajectory_seed.json
  修复：仅保留历史成绩及原适用范围，排除其作为当前正式B/R正证。；验收：当前已重切数据与重新采集正式结果来源区分清楚，不要求历史Agent重跑。

# QA15 资源证据

reference_hidden_seed1 完整单次评分 25334.899999999998s 超过7200s；reference_hidden_seed2 完整单次评分 25309.4s 超过7200s；reference_hidden_seed3 完整单次评分 25337.7s 超过7200s；reference_public_seed1 完整单次评分 24776.100000000002s 超过7200s；reference_public_seed2 完整单次评分 24811.5s 超过7200s；reference_public_seed3 完整单次评分 24760.600000000002s 超过7200s；starter_hidden_seed1 完整单次评分 16839.7s 超过7200s；starter_hidden_seed2 完整单次评分 16948.9s 超过7200s；starter_hidden_seed3 完整单次评分 16934.5s 超过7200s；starter_public_seed1 完整单次评分 16647.2s 超过7200s；starter_public_seed2 完整单次评分 16639.7s 超过7200s；starter_public_seed3 完整单次评分 16757.2s 超过7200s；估算完整一轮评分耗时 39600 超过上限7200

| 运行 | 计时范围 | 记录耗时（秒） | GPU 数量/型号 | 分配 CPU 核 |
|---|---|---:|---|---:|
| reference_hidden_seed1 | score | 25334.9 | 1 / NVIDIA vGPU-32GB | 4 |
| reference_hidden_seed2 | score | 25309.4 | 1 / NVIDIA vGPU-32GB | 4 |
| reference_hidden_seed3 | score | 25337.7 | 1 / NVIDIA vGPU-32GB | 4 |
| reference_public_seed1 | score | 24776.1 | 1 / RTX 4080 SUPER | 4 |
| reference_public_seed2 | score | 24811.5 | 1 / RTX 4080 SUPER | 4 |
| reference_public_seed3 | score | 24760.6 | 1 / RTX 4080 SUPER | 4 |
| starter_hidden_seed1 | score | 16839.7 | 1 / NVIDIA vGPU-32GB | 4 |
| starter_hidden_seed2 | score | 16948.9 | 1 / NVIDIA vGPU-32GB | 4 |
| starter_hidden_seed3 | score | 16934.5 | 1 / NVIDIA vGPU-32GB | 4 |
| starter_public_seed1 | score | 16647.2 | 1 / RTX 4080 SUPER | 4 |
| starter_public_seed2 | score | 16639.7 | 1 / RTX 4080 SUPER | 4 |
| starter_public_seed3 | score | 16757.2 | 1 / RTX 4080 SUPER | 4 |

资源需求估算：完整一轮约 39600 秒，1 张 GPU，16 核 CPU；源日志最长单seed训练+重载评估25337.7s，配置保守预算39600s。GPU显存整卡峰值4821MiB，小模型；目标卡为推断、非实测。当前Verifier实际0GPU是独立静态错误。

计时口径：涵盖完整100000步训练、checkpoint加载和30回合评估；正式三seed当前顺序执行时需求约3倍，估算39600只是单seed预算下界，已经超限。

# 目标部署能力

配置范围：innerfield-maso-v1

当前交付符合内场能力检查；Solver/Verifier 仍须不同 sandbox。

任务硬件与成绩对应：gpu / unverified；当前成绩的硬件归属/换卡影响尚未确认
证据：optimization_evidence/hidden_20261022/README.md；workspace/harbor_task/task.toml；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json

# 格式对齐建议

三目录职责可定位；baseline/reference_runs已补为10-22当前结果且有真实模型，hidden_20261022为12运行等价原始补充。旧comparison_summary/reload_manifest明确作废留档；.jsonl旧字段映射到实际.json。推荐精简但不因多交失败。

- `optimization_evidence/baseline_runs/README.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_1/eval.csv`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_2/eval.csv`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_3/eval.csv`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/DELIVERY_STATE.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/hidden_20261022`（可保留的额外项）：保留12运行原始日志和双切分结果，与正式Hidden六组映射清楚。
- `optimization_evidence/README.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/README.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_1/eval.csv`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_2/eval.csv`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_3/eval.csv`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reload_aggregate.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reload_manifest.json`（旧布局/打包杂项）：旧逐回合数组全零而均值非零，已被作废记录覆盖；不得作为当前重载正证。
- `optimization_evidence/优化面证明_0340_20261005.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/自检checklist_col33_20261006.txt`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/comparison_summary.json`（可合并）：保留作废标记并归历史资料，避免旧均值与当前锚点混用。
- `expert_evidence/best_method/box1_GPT-5.6_Sol`（旧布局/打包杂项）：存在旧代码/权重导出副本，明确以box1及rerun_src映射为准。

说明：额外材料仅作精简或归位建议，不因多交而单独判错。

# 质检结论：不通过

产物：evidence-input｜通过 11 项｜不通过 7 项｜未完成 3 项｜跳过/不适用 0 项

前置三门：通过 1 项｜不通过 2 项｜待核验 0 项；全部复核完成：否。

口径：只读检查及已有证据复核；QA07/08 查 instruction；QA18 审所交轨迹及提供的 sessions，QA21 单独核对 run_summary 的四项题包哈希；QA15 允许根据日志、轨迹和B/R实现估算资源。QA16 两条各至少 10h；仅无训练且单轮很短、例外证据完整时可各至少 7h。排队、安装与故障不计有效迭代时长。未执行提交代码、未独立复跑或反序列化模型。

Harbor 格式/接口：不通过；已提交 NOP 的运行或任务版本关联待核实。

| 检查项 | 是否通过 | 原因 |
|---|---|---|
| QA01 八章节与题面信息泄露 | 通过 | 八章节有实质内容；仅通用TD-MPC2风格和必要接口说明，无参考论文标题、arXiv或参考解配置。 |
| QA02 评分公式与 0/1 锚点 | 通过 | 归一化为(mean_r-B)/(U-B)，方向连续单调且无clip；B/upper采用当前Hidden锚点；Baseline健康性独立在G02/G03失败。 |
| QA03 参考解分数与复现材料 | 待补充核验 | Reference三seed正式结果和非空日志、模型SHA齐全，原始归一化约0.73954；新增独立reload标NOT_RUN，但当次run_one已有训练后eval_agent加载，不伪造补验。 |
| QA04 波动指标的 3σ 可分辨性 | 通过 | 训练seed通过set_seed进入random/numpy/torch及环境；两臂固定候选，完整1/2/3配对。样本σ_B=.169937526、Δ=361.780061770，算术超过3σ；故障锚点效力另列G02/G03。 |
| QA05 约束执行实现 | 不通过 | 环境文件有hash门禁，但题面固定的plan/_estimate_value_iq与config分支未恢复或校验；build_eval_cfg直接读取候选config并导入候选TDMPC2，固定评测边界可被改动。 |
| QA06 Verifier 入口、分数与错误处理 | 通过 | 单入口test.sh调用评分器；成功输出非空有限数值reward.json并写reward.txt；基础设施失败退出，降级有detail记录。 |
| QA07 instruction 中的 Hidden 信息泄露 | 通过 | 题面只描述Hidden规模/统计量/注入路径及禁令，未公开样本、标签或可恢复答案。 |
| QA08 instruction 中的参考解信息泄露 | 通过 | 题面未给参考代码、参考具体损失或参考分数；允许空间说明和朴素TD介绍不等同答案。 |
| QA09 结果清理与原子写入 | 通过 | 入口先清reward及预写结果，正常结果使用同目录临时文件和os.replace原子替换。 |
| QA10 冻结面保护或恢复实现 | 不通过 | 训练子进程虽降权，eval_agent在test.sh的root评分父进程中import候选tdmpc2/common并调用构造、load和act；候选代码因此取得可信文件属主权限，a-w不能保护冻结面。 |
| QA11 instruction 八项内容 | 不通过 | 题面称评测固定30回合，默认Dev入口实际10回合/30000步并自称与Hidden同协议；正式run_one的eval seed_offset=1000，而正式评分1000+seed，协议说明应区分。 |
| QA12 Git 清理 | 通过 | 清点提交数据无.git目录；当前审查工作区自身.git不属于提交材料，不混用。 |
| QA13 Baseline 与参考解提升 | 不通过 | 六组正式Hidden原值、训练及模型均存在，但Baseline仍有零梯度故障；不能用当前B证明健康方法差异，旧被作废数字不参与。 |
| QA14 合法改进空间 | 通过 | 可研究时间限RTG校正、支持域/反事实价值目标等合法方向；Reference约0.7395仍有约127.4原始回报headroom，非饱和。 |
| QA15 评分资源需求估算 | 不通过 | reference_hidden_seed1 完整单次评分 25334.899999999998s 超过7200s；reference_hidden_seed2 完整单次评分 25309.4s 超过7200s；reference_hidden_seed3 完整单次评分 25337.7s 超过7200s；reference_public_seed1 完整单次评分 24776.100000000002s 超过7200s；reference_ |
| QA16 轨迹实际迭代时长 | 待补充核验 | Codex + GPT-5.6 Sol缺少有效时长或排除排队/安装/故障的核算证据；Codex + Seed 2.1 Turbo缺少有效时长或排除排队/安装/故障的核算证据 |
| QA17 Harbor Harness 兼容性 | 不通过 | Harbor 子项未通过：H03 环境与运行路径；H05 Job/Trial 调用配置；H06 NOP 自检记录；详细原因与证据保留在 report.json。 |
| QA18 轨迹、日志与分析 | 不通过 | 已读Sol8轮、Seed16轮和best源码/产物；旧公开集含全部Hidden，历史分数不作新Hidden正证；无sessions不扩称行为全覆盖；六维条件对比未见确认的实质差异，历史证明缺口单列。 |
| QA19 seed 与有效提升阈值 | 通过 | 题面明确训练与评估随机性和Δ≥3σ_B有效提升阈值，固定seed不当作确定性。 |
| QA20 修改范围、网络与工具策略 | 通过 | 有实质可改/禁改范围，禁止外部数据模型答案，允许本地工具且引用平台默认策略；不依赖禁网生效。 |
| QA21 三个 JSON 的填写内容 | 待补充核验 | 两轨八字段完整，当前四项89文件指纹与run_summary一致；旧runs中的.jsonl命名可映射实际.json，但当前hash不能追溯证明10月历史任务版本。 |

# 退回专家说明

G02 Baseline 合理性（不通过）：Q头末层权重和偏置均为0；soft_ce_scalar对预测值应用sign×log(1+abs)，零点计算图梯度为0，Q无法启动学习。真实Ensemble消融fixed仍q_grad=0；随机线性头控制不能排除此故障。
证据：workspace/harbor_task/environment/starter/tdmpc2/common/math.py:5-29；workspace/harbor_task/environment/starter/tdmpc2/common/math.py:71-77；workspace/harbor_task/environment/starter/tdmpc2/common/world_model.py:30-34；workspace/harbor_task/environment/starter/tdmpc2/common/init.py:4-22；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:293-312；expert_evidence/repair/value_loss_ablation/README.md；expert_evidence/repair/value_loss_ablation/ablation_fixed.json
请修改/补充：修复标量价值回归在真实零初始化Q头的梯度通路（例如直接对Q回归变换后的目标，或使用零点梯度正确的实现），保留健康朴素Starter及共同预算；撤回故障Baseline支持的改善主张。
复检验收材料：真实WorldModel零初始化、非零TD目标下的Q参数梯度及一次更新差异；同协议健康B/R完整seed结果与对应源码/模型。无需为历史轨迹重新roll。

G03 Reference 提升充分性（不通过）：全部成对数值算术达标，但正式Baseline存在Q零梯度静态故障，三组B均不能作健康对照；大幅提升不能消除此质量门失败。；重算核验：质量门有效性未满足；seed 1 的 baseline_valid 为 false；seed 2 的 baseline_valid 为 false；seed 3 的 baseline_valid 为 false
证据：optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；workspace/harbor_task/environment/starter/tdmpc2/common/math.py:5-29；workspace/harbor_task/environment/starter/tdmpc2/common/math.py:71-77；workspace/harbor_task/environment/starter/tdmpc2/common/world_model.py:30-34；workspace/harbor_task/environment/starter/tdmpc2/common/init.py:4-22；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:293-312；expert_evidence/repair/value_loss_ablation/README.md；expert_evidence/repair/value_loss_ablation/ablation_fixed.json
请修改/补充：修复标量价值回归在真实零初始化Q头的梯度通路（例如直接对Q回归变换后的目标，或使用零点梯度正确的实现），保留健康朴素Starter及共同预算；撤回故障Baseline支持的改善主张。；按相同数据、评测及预算协议提交两组通过质量门的正式结果；修复该轮质量门失败原因后按正式协议重新运行并保留原始失败记录
复检验收材料：真实WorldModel零初始化、非零TD目标下的Q参数梯度及一次更新差异；同协议健康B/R完整seed结果与对应源码/模型。无需为历史轨迹重新roll。

QA03 参考解分数与复现材料（待补充核验）：Reference三seed正式结果和非空日志、模型SHA齐全，原始归一化约0.73954；新增独立reload标NOT_RUN，但当次run_one已有训练后eval_agent加载，不伪造补验。
证据：optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；workspace/reference/tdmpc2/tdmpc2.py；expert_evidence/repair/rerun_20261021/run_one.py:291-306；optimization_evidence/reference_runs/seed_1/model/reload.log
请修改/补充：保留当次重载依据和当前未额外复验状态。
复检验收材料：已有模型哈希及当次eval_agent的来源关联。

QA05 约束执行实现（不通过）：环境文件有hash门禁，但题面固定的plan/_estimate_value_iq与config分支未恢复或校验；build_eval_cfg直接读取候选config并导入候选TDMPC2，固定评测边界可被改动。
证据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/hard_gate.py；workspace/harbor_task/tests/evaluate_verify.py:173-245
请修改/补充：将固定planner/分支配置从可信副本调用或做实际校验，开放方法接口仅用于允许研究面。
复检验收材料：干净候选通过；改固定planner/分支配置被拒或不生效；整个评测时限含训练和评估。

QA10 冻结面保护或恢复实现（不通过）：训练子进程虽降权，eval_agent在test.sh的root评分父进程中import候选tdmpc2/common并调用构造、load和act；候选代码因此取得可信文件属主权限，a-w不能保护冻结面。
证据：workspace/harbor_task/tests/evaluate_verify.py:205-245；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh
请修改/补充：将候选模型加载/推理也放入受限进程，可信环境、锚点和reward写入进程独立；拒绝降权失败时回退root。
复检验收材料：完整调用链无高权限导入候选代码；候选不能修改原始环境/锚点/评分器，可信侧独立统计指标。

QA11 instruction 八项内容（不通过）：题面称评测固定30回合，默认Dev入口实际10回合/30000步并自称与Hidden同协议；正式run_one的eval seed_offset=1000，而正式评分1000+seed，协议说明应区分。
证据：workspace/harbor_task/instruction.md；workspace/harbor_task/environment/public_eval/eval_dev.py:5-14；workspace/harbor_task/environment/public_eval/eval_dev.py:67-99；expert_evidence/repair/rerun_20261021/run_one.py:296-306；workspace/harbor_task/tests/evaluate_verify.py:384-391
请修改/补充：明确Dev与正式评分各自步数/回合/seed协议；统一需要一致的评测种子与正式锚点口径。
复检验收材料：题面、公开入口、正式评分和锚点生成参数逐项一致或清楚披露合法差别。

QA13 Baseline 与参考解提升（不通过）：六组正式Hidden原值、训练及模型均存在，但Baseline仍有零梯度故障；不能用当前B证明健康方法差异，旧被作废数字不参与。
证据：optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；workspace/harbor_task/environment/starter/tdmpc2/common/math.py:5-29；workspace/harbor_task/environment/starter/tdmpc2/common/math.py:71-77；workspace/harbor_task/environment/starter/tdmpc2/common/world_model.py:30-34；workspace/harbor_task/environment/starter/tdmpc2/common/init.py:4-22；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:293-312；expert_evidence/repair/value_loss_ablation/README.md；expert_evidence/repair/value_loss_ablation/ablation_fixed.json
请修改/补充：修复标量价值回归在真实零初始化Q头的梯度通路（例如直接对Q回归变换后的目标，或使用零点梯度正确的实现），保留健康朴素Starter及共同预算；撤回故障Baseline支持的改善主张。
复检验收材料：真实WorldModel零初始化、非零TD目标下的Q参数梯度及一次更新差异；同协议健康B/R完整seed结果与对应源码/模型。无需为历史轨迹重新roll。

QA15 评分资源需求估算（不通过）：reference_hidden_seed1 完整单次评分 25334.899999999998s 超过7200s；reference_hidden_seed2 完整单次评分 25309.4s 超过7200s；reference_hidden_seed3 完整单次评分 25337.7s 超过7200s；reference_public_seed1 完整单次评分 24776.100000000002s 超过7200s；reference_
证据：workspace/harbor_task/task.toml；optimization_evidence/hidden_20261022/README.md；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed3/train.log
请修改/补充：按任务性质核对当前Solver/Verifier资源。换卡只复核受影响的成绩或耗时，并引用已有配置、说明或运行记录；旧测量保留原硬件标签。
复检验收材料：CPU题不申请GPU；GPU题的实际目标卡型为H20/L20；受影响正式分数有目标硬件对应依据，不能只改型号沿用旧分。

QA16 轨迹实际迭代时长（待补充核验）：Codex + GPT-5.6 Sol缺少有效时长或排除排队/安装/故障的核算证据；Codex + Seed 2.1 Turbo缺少有效时长或排除排队/安装/故障的核算证据
证据：expert_evidence/trajectory_codex.json；expert_evidence/run_summary.json；expert_evidence/trajectory_seed.json
请修改/补充：为Codex + GPT-5.6 Sol、Codex + Seed 2.1 Turbo补一张时长表：研究起止、排队/安装/API失联/故障区间、仍正常运行的训练重叠及有效秒数。可引用已交轨迹和日志片段；不强制提交完整timer或sessions。
复检验收材料：可复算的两轨起止/扣除表，与轨迹时间相符；默认每轨≥36000有效秒。最终复验、收集和明确故障不计，健康训练并发只计一次。

QA17 Harbor Harness 兼容性（不通过）：Harbor 子项未通过：H03 环境与运行路径；H05 Job/Trial 调用配置；H06 NOP 自检记录；详细原因与证据保留在 report.json。
证据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/hidden_assets/README.md；expert_evidence/hidden_set/README.md；expert_evidence/hidden_set/hidden_expert.dat；expert_evidence/nop_trial/trial.log；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/environment/starter/tdmpc2/train.py；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/evaluate_verify.py:537-557；expert_evidence/nop_trial/config.json；expert_evidence/nop_trial/nop_trial.sh；expert_evidence/nop_trial/README.md；expert_evidence/nop_trial/result.json；expert_evidence/nop_trial/verifier/reward.txt；expert_evidence/nop_trial/verifier/test-stdout.txt；expert_evidence/nop_trial/verifier/reward_full.json
请修改/补充：修复H03当前资源及权限边界；平台准备镜像/当前Trial事项不混为作者静态缺陷。
复检验收材料：H03静态调用和有效配置闭合，其他H项按逐原因结果汇总。

QA18 轨迹、日志与分析（不通过）：已读Sol8轮、Seed16轮和best源码/产物；旧公开集含全部Hidden，历史分数不作新Hidden正证；无sessions不扩称行为全覆盖；六维条件对比未见确认的实质差异，历史证明缺口单列。
证据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md；expert_evidence/run_summary.json；expert_evidence/repair/dataset_resplit_20261021/resplit_report.json；expert_evidence/best_method/box1/artifact.json；expert_evidence/best_method/box2/artifact.json
请修改/补充：保留历史分数适用范围与已批准证明差异，不能把污染分数用于正式B/R。
复检验收材料：两轨内容、最佳候选和分数采用范围明确；不要求历史重跑。

QA21 三个 JSON 的填写内容（待补充核验）：两轨八字段完整，当前四项89文件指纹与run_summary一致；旧runs中的.jsonl命名可映射实际.json，但当前hash不能追溯证明10月历史任务版本。
证据：expert_evidence/run_summary.json；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/expert_annotation.json
请修改/补充：保持当前哈希与历史版本分开，记录旧字段映射。
复检验收材料：本批仅豁免旧研究绑定迁移，不改写历史。
