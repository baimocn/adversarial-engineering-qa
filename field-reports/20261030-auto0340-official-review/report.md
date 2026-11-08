# 优化面介绍

Hopper-Hop 在线模型化强化学习，利用公开专家离线轨迹研究训练期 critic 目标和价值锚定；实际接口开放函数实现，并非只提交常量。

可修改：critic 目标/更新与价值锚定；专家数据混合和利用；actor/critic 模块与允许的规划超参。

固定面：act/plan/_estimate_value_iq 的实现；envs 奖励与任务；Hidden 评分协议 15000 步、30 回合；评分冻结面与数据集。

指标与质量门：episode_reward 越大越好；(x-B)/(U-B) 连续不裁剪；随机正式 seeds 1/2/3；Δ≥3σ_B；参考归一化 [0.15,0.8]。

# Baseline 与 Reference 跑分

Baseline 方法：正式 B 为 vanilla TD critic（不使用专家辅助），reward-free 世界模型；标量 Q 用 (pred-symlog(target))²，零初始化具非零目标梯度通路。每 seed 15000 步独立训练，最后 checkpoint 30 回合评估。

Reference 方法：专家/在线 batch 混合，IQ 隐式奖励 Q-γV 回归及 χ² 正则、v0 锚定；同模型、同训练步数、相同 seed 全集。方法源码的 docstring/装饰器迁移与数值差异分别核查。

主指标：episode_reward（越高越好）。

| training_seed | Baseline | Reference | 配对改善 | 有效性 |
|---|---:|---:|---:|---|
| 1 | 0.124508950991 | 114.672748386 | 114.548239435 | B:是 / R:是 |
| 2 | 0.00068930118808 | 124.697696745 | 124.697007443 | B:是 / R:是 |
| 3 | 0.0345584972706 | 127.691767678 | 127.65720918 | B:是 / R:是 |

汇总：Baseline 均值 0.0532522498167，样本标准差 0.0639915518452；Reference 均值 122.354070936，样本标准差 6.81858873077。

改善结论：历史正式15k证据：Δ=122.300818686111；σ_B=0.063991551845；归一化0.249961487689。全部三对同向改善；当前评分器的两个静态故障另行阻断，不把历史值说成本版实跑。

质量门：六份正式 result COMPLETE、协议一致、六权重 SHA256 实算一致且不同，已有结构重载记录。日志到15000步。现行评分链不可直接正常复用这些成绩证明可运行。

# 前置内容门槛

| 门槛 | 结论 | 原因 |
|---|---|---|
| G01 方法级优化空间 | 通过 | 真实接口允许重写训练期目标、更新、模块及数据利用；starter提供vanilla与可实现IQ骨架，非纯常量搜索。 |
| G02 Baseline 合理性 | 通过 | 现行15k正式Baseline为健康标量TD路径；日志达到共同预算，无直接不公平或故障反证。仅以已交材料范围评价，旧故障批与原Agent分已排除。 |
| G03 Reference 提升充分性 | 通过 | 历史现行15k正式三对重算Δ=122.3008186861、σ_B=0.063991551845、归一化0.249961487689达标。upper来自事前专家均值，不是倒推。当前Verifier实错另记QA05/06和H04，不冒充本版复跑。 |

G03 复算：Δ=122.300818686；σ_B（样本标准差）=0.0639915518452；U=489.3319；归一化分数=0.249961487689。

# 两条轨迹迭代概况

| Agent 轨迹 | 状态 | 打包轮数 | 声明有效轮数 | 有效时长 | 概况与最终结果 |
|---|---|---:|---:|---:|---|
| Codex + GPT-5.6 Sol | 完整 | 8 | 8 | - | 8轮，7次出分、1次失败；依次探索 continuation/support、counterfactual、planner residual、support kernel、ORRA-IQ、potential、失败residual及RACR；第2轮85.168为最佳。 申报36644/40158秒来自首末轮跨度，无法据此确定净有效时长；历史最佳85.168；干净Dev补跑56.405；独立旧入口54.305，协议不同不直接比较。 |
| Codex + Seed 2.1 Turbo | 完整 | 16 | 16 | - | 16轮，4次出分、12次失败；完整保留重启重复时间戳及无代码变更；RTG、latent rollout、V bootstrap、BC、distributional Q、CQL、全回合RTG；第14轮12.2079最佳（旧局部r4-scored）。 申报36644/40158秒来自首末轮跨度，无法据此确定净有效时长；历史最佳12.2079原轮权重已缺；同方法补跑27.5285和14.5289均非原轮，不补造原权重。 |

# 轨迹可信性与题包绑定

Codex + GPT-5.6 Sol：分数无效；Codex + Seed 2.1 Turbo：分数无效

| 轨迹 | 所交内容审查 | 分数与当前包对应 | 审查范围 | run_summary 哈希 |
|---|---|---|---|---|
| Codex + GPT-5.6 Sol | 不通过 | 无效 | 仅审查已交轮次/方法摘要；未提供工具调用或sessions，结论限于这些材料。 | run_summary 的四项题包哈希与当前包一致。 |
| Codex + Seed 2.1 Turbo | 不通过 | 无效 | 仅审查已交轮次/方法摘要；未提供工具调用或sessions，结论限于这些材料。 | run_summary 的四项题包哈希与当前包一致。 |

- Codex + GPT-5.6 Sol：存在泄漏 / 已确认：两轨使用旧100条公开数据，包含后续Hidden34条，历史Dev分受污染；系历史作者数据边界缺陷，不推定Agent主观作弊。；受影响分数无效；影响轮次 [1, 2, 3, 4, 5, 6, 7, 8]；证据 expert_evidence/trajectory_codex.json；expert_evidence/两轨可比性对照表_20261027.md；expert_evidence/专家作业说明文档.md；expert_evidence/best_method/REPRODUCIBILITY_STATUS.md
  修复：保留无效历史分与适用范围；当前已重切公开/私有集，不将旧Dev作为正式B/R证据。；验收：现有切分说明、历史轨迹与现行正式结果的独立用途记录。

- Codex + Seed 2.1 Turbo：存在泄漏 / 已确认：两轨使用旧100条公开数据，包含后续Hidden34条，历史Dev分受污染；系历史作者数据边界缺陷，不推定Agent主观作弊。；受影响分数无效；影响轮次 [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]；证据 expert_evidence/trajectory_seed.json；expert_evidence/两轨可比性对照表_20261027.md；expert_evidence/专家作业说明文档.md；expert_evidence/best_method/REPRODUCIBILITY_STATUS.md
  修复：保留无效历史分与适用范围；当前已重切公开/私有集，不将旧Dev作为正式B/R证据。；验收：现有切分说明、历史轨迹与现行正式结果的独立用途记录。

# QA15 资源证据

缺少：当前成绩的硬件归属/换卡影响尚未确认

| 运行 | 计时范围 | 记录耗时（秒） | GPU 数量/型号 | 分配 CPU 核 |
|---|---|---:|---|---:|

资源需求估算：完整一轮约 6500 秒，1 张 GPU，16 核 CPU；旧RTX4080SUPER同协议全臂最坏5837.9s；小模型规划/环境CPU较重，按约11%余量估6500s。包内跨卡1.0225仅历史vGPU/4080对比，不能当H20保证。

计时口径：完整单seed15000步训练、checkpoint重载、30回合评分和收尾；非整条研究跨度。

# 目标部署能力

配置范围：innerfield-maso-v1

当前交付符合内场能力检查；Solver/Verifier 仍须不同 sandbox。

任务硬件与成绩对应：gpu / unverified；当前成绩的硬件归属/换卡影响尚未确认
证据：workspace/harbor_task/task.toml；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；expert_evidence/专家作业说明文档.md

# 格式对齐建议

三目录职责可识别；正式result使用等价扁平字段、train.log及集中reload.log/manifest；并非缺正式结果/模型。多份历史与修订附件保留，未用文件数量代替内容。八字段ok状态/时间及版本迁移另记具体缺口。

- `optimization_evidence/ast_equivalence_check.py`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/ast_equivalence_result.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/README.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_1/eval.csv`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_1/train.log`（可合并）：训练输出通常可统一为同轮 run.log。
- `optimization_evidence/baseline_runs/seed_2/eval.csv`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_2/train.log`（可合并）：训练输出通常可统一为同轮 run.log。
- `optimization_evidence/baseline_runs/seed_3/eval.csv`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_3/train.log`（可合并）：训练输出通常可统一为同轮 run.log。
- `optimization_evidence/baseline_runs_100k_superseded`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/DELIVERY_STATE.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/gate_matrix_20261030`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/hidden_20261022`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/public_crosscheck`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/README.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/README.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_1/eval.csv`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_1/train.log`（可合并）：训练输出通常可统一为同轮 run.log。
- `optimization_evidence/reference_runs/seed_2/eval.csv`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_2/train.log`（可合并）：训练输出通常可统一为同轮 run.log。
- `optimization_evidence/reference_runs/seed_3/eval.csv`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_3/train.log`（可合并）：训练输出通常可统一为同轮 run.log。
- `optimization_evidence/reference_runs_100k_superseded`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reload.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reload_aggregate.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reload_manifest.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/rerun_15k_20261025`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/run15k_raw_20261025`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/selfcheck_20261030`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/upper_anchor_recompute.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/v13修订说明_20261027.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/v17修订说明_20261028.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/v18修订说明_20261028.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/v19修订说明_20261028.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/v20修订说明_20261028.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/v21修订说明_20261028.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/v22修订说明_20261029.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/v22验收_20261029.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/v23修订说明_20261029.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/v23验收_20261029.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/v24修订说明_20261029.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/v24验收_20261029.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/v2553修订说明_20261030.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/v2554修订说明_20261030.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/v25修订说明_20261029.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/v25验收_20261029.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/五份报告逐条复核裁定_20261029.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/优化面证明_0340_20261005.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/自检checklist_col33_20261006.txt`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `修复记录_第三次质检_20261026.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/`（可合并）：大量逐版说明可做索引并归档，保留原始结果与作废范围。
- `expert_evidence/repair/qa03_rescore/`（可保留的额外项）：保留复评诊断，但不与正式15k原始结果混算。
- `optimization_evidence/baseline_runs_100k_superseded/`（可保留的额外项）：保留已作废标记，仅追溯。

说明：额外材料仅作精简或归位建议，不因多交而单独判错。

# 质检结论：不通过

产物：evidence-input｜通过 13 项｜不通过 5 项｜未完成 3 项｜跳过/不适用 0 项

前置三门：通过 3 项｜不通过 0 项｜待核验 0 项；全部复核完成：否。

口径：只读检查及已有证据复核；QA07/08 查 instruction；QA18 审所交轨迹及提供的 sessions，QA21 单独核对 run_summary 的四项题包哈希；QA15 允许根据日志、轨迹和B/R实现估算资源。QA16 两条各至少 10h；仅无训练且单轮很短、例外证据完整时可各至少 7h。排队、安装与故障不计有效迭代时长。未执行提交代码、未独立复跑或反序列化模型。

Harbor 格式/接口：不通过；已提交自检记录不满足 NOP 运行要求。

| 检查项 | 是否通过 | 原因 |
|---|---|---|
| QA01 八章节与题面信息泄露 | 通过 | 八部分覆盖任务、环境、评分、边界、提交、流程与完成条件；未直接给出参考论文标题/编号或参考方法。 |
| QA02 评分公式与 0/1 锚点 | 通过 | 实际 (mean_r-B)/(U-B) 无clip，B=0.0532522498、U=489.3319，B映射0、U映射1，正斜率约0.002044。 |
| QA03 参考解分数与复现材料 | 通过 | 正式R三seed result、非空train.log、真实checkpoint和结构重载记录可追溯；历史归一化0.249961达标。未声称本版评分链已成功运行。 |
| QA04 波动指标的 3σ 可分辨性 | 通过 | 随机评估；train入口set_seed(cfg.seed)、环境cfg.seed生效。完整1/2/3逐seed同向，σ_B按n−1，Δ/σ_B=1911.2026。固定方法、独立权重非复制。 |
| QA05 约束执行实现 | 不通过 | 静态 G6 剥离 docstring，但运行时 _code_fp 将 co_consts 中的 docstring 纳入指纹；当前 Starter 的 _estimate_value_iq 说明字符串与可信副本不同，实际方法体相同也会被 _guard 误判篡改。Reference 的说明字符串亦不同。 |
| QA06 Verifier 入口、分数与错误处理 | 不通过 | 评分父进程将动作构造成 np.ndarray 后传入 TensorWrapper.step；该包装器调用 action.numpy()，ndarray 无此方法，正常动作在首步即抛 AttributeError，并被当作候选侧失败计 -1。 |
| QA07 instruction 中的 Hidden 信息泄露 | 通过 | 仅审instruction：描述Hidden存在、隔离及标量upper，未交付Hidden样本、标签或可恢复答案；物理隔离另审H01/H03。 |
| QA08 instruction 中的参考解信息泄露 | 通过 | 仅审instruction：未给参考代码、具体参考配置/结果或论文线索；目标与接口说明不等于解法。 |
| QA09 结果清理与原子写入 | 通过 | 入口预清理reward及诊断；正常评分由同目录临时文件+os.replace写JSON与TXT。该写入实现存在，不等于本版正常评分已跑通。 |
| QA10 冻结面保护或恢复实现 | 通过 | 可信/tests root属主去写权限，候选降权；冻结面评分前后校验，reward目录root拥有。父进程持环境与累加回报；同进程方法守卫有限，不把它认证为完整安全边界。 |
| QA11 instruction 八项内容 | 不通过 | 八项实质内容齐，但题面将超时列为基础设施错误；当前评测超时 eval_timeout_* 被默认归候选并计-1，实际错误归因与题面矛盾。 |
| QA12 Git 清理 | 通过 | 完整清单未发现提交包内.git（含remotes/tags/reflog）；不把报告工作目录的系统.git算入题包。 |
| QA13 Baseline 与参考解提升 | 通过 | 已读六份Hidden及六份Public交叉运行；现行健康基线与IQ参考共同15k/30回合、1/2/3全集，正式Hidden各对改善且汇总通过。历史已作废100k与Agent Dev分不计入。 |
| QA14 合法改进空间 | 通过 | 开放critic目标/数据利用/模块设计；Reference为IQ目标，合法额外方向可研究多步目标或分布稳健锚定，不需质检训练新解。R距U仍约366.978，未饱和。 |
| QA15 评分资源需求估算 | 待补充核验 | 缺少：当前成绩的硬件归属/换卡影响尚未确认 |
| QA16 轨迹实际迭代时长 | 待补充核验 | Codex + GPT-5.6 Sol缺少有效时长或排除排队/安装/故障的核算证据；Codex + Seed 2.1 Turbo缺少有效时长或排除排队/安装/故障的核算证据 |
| QA17 Harbor Harness 兼容性 | 不通过 | Harbor 子项未通过：H03 环境与运行路径；H04 测试入口与 reward；H06 NOP 自检记录；详细原因与证据保留在 report.json。 |
| QA18 轨迹、日志与分析 | 不通过 | 两轨全部24轮及最终方法/补跑/失败已审；历史旧公开100条含Hidden34条，受影响Dev分invalid，不作正式B/R正证。实际最高档/启动及部分历史条件证据有限，未查实两轨有实质条件差异。 |
| QA19 seed 与有效提升阈值 | 通过 | 题面说明随机性、正式种子口径与Δ≥3σ_B；不额外要求题面说明replicate数。 |
| QA20 修改范围、网络与工具策略 | 通过 | 题面明确可改/冻结范围、禁止取外部模型/数据/答案，引用平台默认工具策略；无需要额外环境的任务运行调用。 |
| QA21 三个 JSON 的填写内容 | 待补充核验 | 两轨JSON八字段均解析、失败null与原因及best相符，annotation/run_summary属本题；实算四项95文件指纹匹配。声明hash是当前迁移包身份，不证明历史字节；旧status=ok与历史版本绑定按迁移缺口单列。 |

# 退回专家说明

QA05 约束执行实现（不通过）：静态 G6 剥离 docstring，但运行时 _code_fp 将 co_consts 中的 docstring 纳入指纹；当前 Starter 的 _estimate_value_iq 说明字符串与可信副本不同，实际方法体相同也会被 _guard 误判篡改。Reference 的说明字符串亦不同。
证据：workspace/harbor_task/tests/evaluate_verify.py:720-740；workspace/harbor_task/tests/evaluate_verify.py:805-831；workspace/harbor_task/tests/evaluate_verify.py:927-945；workspace/harbor_task/tests/hard_gate.py:603-632；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:146-168；workspace/harbor_task/tests/trusted_env/trusted_tdmpc2.py
请修改/补充：统一静态与运行时冻结比较的语义范围，排除仅 docstring 差异；保留对可执行代码变化的拒绝。
复检验收材料：提交修正后的真实源码；复验时用原样 Starter 和 Reference 各走正常动作的完整入口，确认冻结检查通过、环境至少完成一个完整回合并产出真实 reward；另确认实际改写冻结代码仍拒绝。本次不执行候选或 Verifier，也不要求重做历史两轨。

QA06 Verifier 入口、分数与错误处理（不通过）：评分父进程将动作构造成 np.ndarray 后传入 TensorWrapper.step；该包装器调用 action.numpy()，ndarray 无此方法，正常动作在首步即抛 AttributeError，并被当作候选侧失败计 -1。
证据：workspace/harbor_task/tests/evaluate_verify.py:590-599；workspace/harbor_task/tests/trusted_env/envs/__init__.py:80-83；workspace/harbor_task/tests/trusted_env/envs/wrappers/tensor.py:36-40；workspace/harbor_task/tests/test.sh
请修改/补充：统一父进程动作与 TensorWrapper 接口，例如校验后转 CPU float32 Tensor 再 step；将评测器自身接口异常与候选违规分开归因。
复检验收材料：提交修正后的真实源码；复验时用原样 Starter 和 Reference 各走正常动作的完整入口，确认冻结检查通过、环境至少完成一个完整回合并产出真实 reward；另确认实际改写冻结代码仍拒绝。本次不执行候选或 Verifier，也不要求重做历史两轨。

QA11 instruction 八项内容（不通过）：八项实质内容齐，但题面将超时列为基础设施错误；当前评测超时 eval_timeout_* 被默认归候选并计-1，实际错误归因与题面矛盾。
证据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/evaluate_verify.py:555-578；workspace/harbor_task/tests/evaluate_verify.py:1280-1305；workspace/harbor_task/tests/evaluate_verify.py:1447-1462；workspace/harbor_task/tests/evaluate_verify.py:1695-1709
请修改/补充：统一题面和实际错误归因；当前评测器故障须修正，历史缺口另列。
复检验收材料：提交修正后的真实源码；复验时用原样 Starter 和 Reference 各走正常动作的完整入口，确认冻结检查通过、环境至少完成一个完整回合并产出真实 reward；另确认实际改写冻结代码仍拒绝。本次不执行候选或 Verifier，也不要求重做历史两轨。

QA15 评分资源需求估算（待补充核验）：缺少：当前成绩的硬件归属/换卡影响尚未确认
证据：workspace/harbor_task/task.toml；optimization_evidence/public_crosscheck/reference/seed_1/result.json；expert_evidence/专家作业说明文档.md；optimization_evidence/训练证据说明.md；workspace/harbor_task/tests/test.sh；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json
请修改/补充：按任务性质核对当前Solver/Verifier资源。换卡只复核受影响的成绩或耗时，并引用已有配置、说明或运行记录；旧测量保留原硬件标签。
复检验收材料：CPU题不申请GPU；GPU题的实际目标卡型为H20/L20；受影响正式分数有目标硬件对应依据，不能只改型号沿用旧分。

QA16 轨迹实际迭代时长（待补充核验）：Codex + GPT-5.6 Sol缺少有效时长或排除排队/安装/故障的核算证据；Codex + Seed 2.1 Turbo缺少有效时长或排除排队/安装/故障的核算证据
证据：expert_evidence/trajectory_codex.json；expert_evidence/run_summary.json；expert_evidence/trajectory_seed.json
请修改/补充：为Codex + GPT-5.6 Sol、Codex + Seed 2.1 Turbo补一张时长表：研究起止、排队/安装/API失联/故障区间、仍正常运行的训练重叠及有效秒数。可引用已交轨迹和日志片段；不强制提交完整timer或sessions。
复检验收材料：可复算的两轨起止/扣除表，与轨迹时间相符；默认每轨≥36000有效秒。最终复验、收集和明确故障不计，健康训练并发只计一次。

QA17 Harbor Harness 兼容性（不通过）：Harbor 子项未通过：H03 环境与运行路径；H04 测试入口与 reward；H06 NOP 自检记录；详细原因与证据保留在 report.json。
证据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/hidden_assets/README.md；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/evaluate_verify.py:590-599；workspace/harbor_task/tests/trusted_env/envs/__init__.py:80-83；workspace/harbor_task/tests/trusted_env/envs/wrappers/tensor.py:36-40；workspace/harbor_task/tests/evaluate_verify.py:720-740；workspace/harbor_task/tests/evaluate_verify.py:805-831；workspace/harbor_task/tests/evaluate_verify.py:927-945；workspace/harbor_task/tests/hard_gate.py:603-632；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:146-168；workspace/harbor_task/tests/trusted_env/trusted_tdmpc2.py；expert_evidence/nop_trial/config.json；expert_evidence/nop_trial/reproduce_nop_full.sh；expert_evidence/nop_trial/trial.log；expert_evidence/nop_trial/result.json；expert_evidence/nop_trial/verifier/reward.json；expert_evidence/nop_trial/verifier/reward.txt
请修改/补充：统一题面和实际错误归因；当前评测器故障须修正，历史缺口另列。
复检验收材料：提交修正后的真实源码；复验时用原样 Starter 和 Reference 各走正常动作的完整入口，确认冻结检查通过、环境至少完成一个完整回合并产出真实 reward；另确认实际改写冻结代码仍拒绝。本次不执行候选或 Verifier，也不要求重做历史两轨。

QA18 轨迹、日志与分析（不通过）：两轨全部24轮及最终方法/补跑/失败已审；历史旧公开100条含Hidden34条，受影响Dev分invalid，不作正式B/R正证。实际最高档/启动及部分历史条件证据有限，未查实两轨有实质条件差异。
证据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/两轨可比性对照表_20261027.md；expert_evidence/best_method/REPRODUCIBILITY_STATUS.md；expert_evidence/专家作业说明文档.md
请修改/补充：统一题面和实际错误归因；当前评测器故障须修正，历史缺口另列。
复检验收材料：提交修正后的真实源码；复验时用原样 Starter 和 Reference 各走正常动作的完整入口，确认冻结检查通过、环境至少完成一个完整回合并产出真实 reward；另确认实际改写冻结代码仍拒绝。本次不执行候选或 Verifier，也不要求重做历史两轨。

QA21 三个 JSON 的填写内容（待补充核验）：两轨JSON八字段均解析、失败null与原因及best相符，annotation/run_summary属本题；实算四项95文件指纹匹配。声明hash是当前迁移包身份，不证明历史字节；旧status=ok与历史版本绑定按迁移缺口单列。
证据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/expert_annotation.json；expert_evidence/run_summary.json
请修改/补充：按本项已读事实处理具体历史证明缺口，保留旧成绩原硬件/时长口径，不新增重跑义务。
复检验收材料：本项已有材料及本轮历史豁免依据；不补造时长/运行或改写旧记录。
