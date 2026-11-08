# 旧题完整质检与逐原因豁免

本轮结论：FAIL
阶段：standard_review_with_waivers
已完成全部内容审阅：是

原 v0.3.10 全部检查及完整内容审阅已完成，包括已有 NOP；仅按具体历史原因豁免。未执行题包代码或新增 Harbor Trial。
平台实跑：not_executed；未执行模型、题目程序、Docker 或 Harbor。

## 方法与正式对照

Hopper-Hop 在线模型化强化学习，利用公开专家离线轨迹研究训练期 critic 目标和价值锚定；实际接口开放函数实现，并非只提交常量。
可修改：critic 目标/更新与价值锚定；专家数据混合和利用；actor/critic 模块与允许的规划超参
冻结面：act/plan/_estimate_value_iq 的实现；envs 奖励与任务；Hidden 评分协议 15000 步、30 回合；评分冻结面与数据集
指标与质量门：episode_reward 越大越好；(x-B)/(U-B) 连续不裁剪；随机正式 seeds 1/2/3；Δ≥3σ_B；参考归一化 [0.15,0.8]。
Baseline：正式 B 为 vanilla TD critic（不使用专家辅助），reward-free 世界模型；标量 Q 用 (pred-symlog(target))²，零初始化具非零目标梯度通路。每 seed 15000 步独立训练，最后 checkpoint 30 回合评估。
Reference：专家/在线 batch 混合，IQ 隐式奖励 Q-γV 回归及 χ² 正则、v0 锚定；同模型、同训练步数、相同 seed 全集。方法源码的 docstring/装饰器迁移与数值差异分别核查。
正式改善：历史正式15k证据：Δ=122.300818686111；σ_B=0.063991551845；归一化0.249961487689。全部三对同向改善；当前评分器的两个静态故障另行阻断，不把历史值说成本版实跑。
质量有效性：六份正式 result COMPLETE、协议一致、六权重 SHA256 实算一致且不同，已有结构重载记录。日志到15000步。现行评分链不可直接正常复用这些成绩证明可运行。
已有原始对照：[{"seed": 1, "baseline": 0.12450895099148813, "reference": 114.67274838561086, "baseline_valid": true, "reference_valid": true}, {"seed": 2, "baseline": 0.0006893011880796015, "reference": 124.6976967446135, "baseline_valid": true, "reference_valid": true}, {"seed": 3, "baseline": 0.03455849727063954, "reference": 127.69176767755877, "baseline_valid": true, "reference_valid": true}]
依据：optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/comparison_summary.json；optimization_evidence/reload.log；optimization_evidence/upper_anchor_recompute.json；optimization_evidence/run15k_raw_20261025/README.md

## 研究三门

### G01 方法级优化空间

观察判定：pass；本轮判定：pass
真实接口允许重写训练期目标、更新、模块及数据利用；starter提供vanilla与可实现IQ骨架，非纯常量搜索。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py；workspace/harbor_task/tests/hard_gate.py

### G02 Baseline 合理性

观察判定：pass；本轮判定：pass
现行15k正式Baseline为健康标量TD路径；日志达到共同预算，无直接不公平或故障反证。仅以已交材料范围评价，旧故障批与原Agent分已排除。
审阅依据：optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；workspace/harbor_task/environment/starter/tdmpc2/common/math.py；expert_evidence/repair/value_loss_ablation/q_grad_probe_result.json；optimization_evidence/训练证据说明.md
训练充分性：两臂各seed达到15000步，原始train.log显示完成及汇总；统一预算下未要求收敛，无凭据认定少训练。
  依据：optimization_evidence/baseline_runs/seed_1/train.log；optimization_evidence/baseline_runs/seed_2/train.log；optimization_evidence/baseline_runs/seed_3/train.log；optimization_evidence/reference_runs/seed_1/train.log；optimization_evidence/reference_runs/seed_2/train.log；optimization_evidence/reference_runs/seed_3/train.log
方法代表性：原始TD朴素对照对应公开起点；Reference引入专家辅助目标是允许研究变量。简单与低分不等于不合理，不以未验证包外SOTA判退。
  依据：workspace/harbor_task/instruction.md；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py；workspace/reference/tdmpc2/iq.py
原协议预算可比性：同Hidden数据、相同15k步骤与30回合，seed全集配对，历史同卡RTX4080SUPER；R多花训练耗时仍在共同2h预算内。
  依据：optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json
实现正确性：标量soft_ce分支target-only symlog，optim/backward/step存在；既有生产Ensemble探针首步非零梯度0.1055259，第二步早层有梯度。历史故障批未采用。
  依据：workspace/harbor_task/environment/starter/tdmpc2/common/math.py；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py；expert_evidence/repair/value_loss_ablation/q_grad_probe_result.json
选择与对照完整性：1/2/3无丢seed，方法代码哈希每臂固定，六模型哈希不同且逐项一致；final选择披露，不将同模型复评冒充独立重训。
  依据：optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/reload_manifest.json；optimization_evidence/run15k_raw_20261025/README.md

### G03 Reference 提升充分性

观察判定：pass；本轮判定：pass
历史现行15k正式三对重算Δ=122.3008186861、σ_B=0.063991551845、归一化0.249961487689达标。upper来自事前专家均值，不是倒推。当前Verifier实错另记QA05/06和H04，不冒充本版复跑。
审阅依据：optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/upper_anchor_recompute.json；workspace/harbor_task/tests/anchors.json
正式复算：{"baseline_mean": 0.05325224981673576, "reference_mean": 122.35407093592771, "baseline_sample_std": 0.06399155184515133, "reference_sample_std": 6.818588730769847, "improvement": 122.30081868611097, "run_count": 3, "sigma_multiplier": 1911.2025753346027, "three_sigma_baseline": 0.191974655535454, "normalized_score": 0.2499614876890265}

## 21 项内容与实现

### QA01 八章节与题面信息泄露

观察判定：pass；本轮判定：pass
八部分覆盖任务、环境、评分、边界、提交、流程与完成条件；未直接给出参考论文标题/编号或参考方法。
审阅依据：workspace/harbor_task/instruction.md

### QA02 评分公式与 0/1 锚点

观察判定：pass；本轮判定：pass
实际 (mean_r-B)/(U-B) 无clip，B=0.0532522498、U=489.3319，B映射0、U映射1，正斜率约0.002044。
审阅依据：workspace/harbor_task/tests/evaluate_verify.py:1841-1861；workspace/harbor_task/tests/anchors.json；optimization_evidence/upper_anchor_recompute.json

### QA03 参考解分数与复现材料

观察判定：pass；本轮判定：pass
正式R三seed result、非空train.log、真实checkpoint和结构重载记录可追溯；历史归一化0.249961达标。未声称本版评分链已成功运行。
审阅依据：optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/reload_manifest.json；optimization_evidence/reload.log；workspace/reference/tdmpc2/tdmpc2.py；expert_evidence/repair/qa03_rescore/rescore_out/qa03_rescore_summary.json；expert_evidence/repair/qa03_rescore/rescore_out/qa03_rescore_summary_official_criteria.json

### QA04 波动指标的 3σ 可分辨性

观察判定：pass；本轮判定：pass
随机评估；train入口set_seed(cfg.seed)、环境cfg.seed生效。完整1/2/3逐seed同向，σ_B按n−1，Δ/σ_B=1911.2026。固定方法、独立权重非复制。
审阅依据：optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；workspace/harbor_task/environment/starter/tdmpc2/train.py；workspace/harbor_task/environment/starter/tdmpc2/common/seed.py；workspace/harbor_task/tests/sigma_b_gate.py

### QA05 约束执行实现

观察判定：fail；本轮判定：fail
静态 G6 剥离 docstring，但运行时 _code_fp 将 co_consts 中的 docstring 纳入指纹；当前 Starter 的 _estimate_value_iq 说明字符串与可信副本不同，实际方法体相同也会被 _guard 误判篡改。Reference 的说明字符串亦不同。
审阅依据：workspace/harbor_task/tests/evaluate_verify.py:720-740；workspace/harbor_task/tests/evaluate_verify.py:805-831；workspace/harbor_task/tests/evaluate_verify.py:927-945；workspace/harbor_task/tests/hard_gate.py:603-632；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:146-168；workspace/harbor_task/tests/trusted_env/trusted_tdmpc2.py
- 静态 G6 剥离 docstring，但运行时 _code_fp 将 co_consts 中的 docstring 纳入指纹；当前 Starter 的 _estimate_value_iq 说明字符串与可信副本不同，实际方法体相同也会被 _guard 误判篡改。Reference 的说明字符串亦不同。；处理：unwaived
  依据：workspace/harbor_task/tests/evaluate_verify.py:720-740；workspace/harbor_task/tests/evaluate_verify.py:805-831；workspace/harbor_task/tests/evaluate_verify.py:927-945；workspace/harbor_task/tests/hard_gate.py:603-632；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:146-168；workspace/harbor_task/tests/trusted_env/trusted_tdmpc2.py
  修改方向：统一静态与运行时冻结比较的语义范围，排除仅 docstring 差异；保留对可执行代码变化的拒绝。
  验收：提交修正后的真实源码；复验时用原样 Starter 和 Reference 各走正常动作的完整入口，确认冻结检查通过、环境至少完成一个完整回合并产出真实 reward；另确认实际改写冻结代码仍拒绝。本次不执行候选或 Verifier，也不要求重做历史两轨。

### QA06 Verifier 入口、分数与错误处理

观察判定：fail；本轮判定：fail
评分父进程将动作构造成 np.ndarray 后传入 TensorWrapper.step；该包装器调用 action.numpy()，ndarray 无此方法，正常动作在首步即抛 AttributeError，并被当作候选侧失败计 -1。
审阅依据：workspace/harbor_task/tests/evaluate_verify.py:590-599；workspace/harbor_task/tests/trusted_env/envs/__init__.py:80-83；workspace/harbor_task/tests/trusted_env/envs/wrappers/tensor.py:36-40；workspace/harbor_task/tests/test.sh
- 评分父进程将动作构造成 np.ndarray 后传入 TensorWrapper.step；该包装器调用 action.numpy()，ndarray 无此方法，正常动作在首步即抛 AttributeError，并被当作候选侧失败计 -1。；处理：unwaived
  依据：workspace/harbor_task/tests/evaluate_verify.py:590-599；workspace/harbor_task/tests/trusted_env/envs/__init__.py:80-83；workspace/harbor_task/tests/trusted_env/envs/wrappers/tensor.py:36-40
  修改方向：统一父进程动作与 TensorWrapper 接口，例如校验后转 CPU float32 Tensor 再 step；将评测器自身接口异常与候选违规分开归因。
  验收：提交修正后的真实源码；复验时用原样 Starter 和 Reference 各走正常动作的完整入口，确认冻结检查通过、环境至少完成一个完整回合并产出真实 reward；另确认实际改写冻结代码仍拒绝。本次不执行候选或 Verifier，也不要求重做历史两轨。

### QA07 instruction 中的 Hidden 信息泄露

观察判定：pass；本轮判定：pass
仅审instruction：描述Hidden存在、隔离及标量upper，未交付Hidden样本、标签或可恢复答案；物理隔离另审H01/H03。
审阅依据：workspace/harbor_task/instruction.md

### QA08 instruction 中的参考解信息泄露

观察判定：pass；本轮判定：pass
仅审instruction：未给参考代码、具体参考配置/结果或论文线索；目标与接口说明不等于解法。
审阅依据：workspace/harbor_task/instruction.md

### QA09 结果清理与原子写入

观察判定：pass；本轮判定：pass
入口预清理reward及诊断；正常评分由同目录临时文件+os.replace写JSON与TXT。该写入实现存在，不等于本版正常评分已跑通。
审阅依据：workspace/harbor_task/tests/test.sh:1-8；workspace/harbor_task/tests/test.sh:148-192；workspace/harbor_task/tests/evaluate_verify.py:83-125

### QA10 冻结面保护或恢复实现

观察判定：pass；本轮判定：pass
可信/tests root属主去写权限，候选降权；冻结面评分前后校验，reward目录root拥有。父进程持环境与累加回报；同进程方法守卫有限，不把它认证为完整安全边界。
审阅依据：workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/tests/hard_gate.py；workspace/harbor_task/tests/trusted_env/envguard.py

### QA11 instruction 八项内容

观察判定：fail；本轮判定：fail
八项实质内容齐，但题面将超时列为基础设施错误；当前评测超时 eval_timeout_* 被默认归候选并计-1，实际错误归因与题面矛盾。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/evaluate_verify.py:555-578；workspace/harbor_task/tests/evaluate_verify.py:1280-1305；workspace/harbor_task/tests/evaluate_verify.py:1447-1462；workspace/harbor_task/tests/evaluate_verify.py:1695-1709
- 题面称超时是基础设施错误，评测器当前把eval_timeout_*归候选并出-1。；处理：unwaived
  依据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/evaluate_verify.py:555-578；workspace/harbor_task/tests/evaluate_verify.py:1280-1305；workspace/harbor_task/tests/evaluate_verify.py:1447-1462；workspace/harbor_task/tests/evaluate_verify.py:1695-1709
  修改方向：修正超时/环境接口故障的责任归因，与题面明确区分候选违规。
  验收：提交修正后的真实源码；复验时用原样 Starter 和 Reference 各走正常动作的完整入口，确认冻结检查通过、环境至少完成一个完整回合并产出真实 reward；另确认实际改写冻结代码仍拒绝。本次不执行候选或 Verifier，也不要求重做历史两轨。

### QA12 Git 清理

观察判定：pass；本轮判定：pass
完整清单未发现提交包内.git（含remotes/tags/reflog）；不把报告工作目录的系统.git算入题包。
审阅依据：@legacy_inventory

### QA13 Baseline 与参考解提升

观察判定：pass；本轮判定：pass
已读六份Hidden及六份Public交叉运行；现行健康基线与IQ参考共同15k/30回合、1/2/3全集，正式Hidden各对改善且汇总通过。历史已作废100k与Agent Dev分不计入。
审阅依据：optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/comparison_summary.json；optimization_evidence/训练证据说明.md

### QA14 合法改进空间

观察判定：pass；本轮判定：pass
开放critic目标/数据利用/模块设计；Reference为IQ目标，合法额外方向可研究多步目标或分布稳健锚定，不需质检训练新解。R距U仍约366.978，未饱和。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py；workspace/reference/tdmpc2/iq.py；workspace/harbor_task/tests/anchors.json

### QA15 评分资源需求估算

观察判定：manual；本轮判定：pass_with_waivers
历史12run最坏训练+评测5837.90s；目标1张H20/L20、16/8CPU合法。6500s仅从历史负载留余量推断，目标卡未实测，旧硬件差异保留。
审阅依据：workspace/harbor_task/task.toml；optimization_evidence/public_crosscheck/reference/seed_1/result.json；expert_evidence/专家作业说明文档.md
- 历史B/R同4080，目标H20/L20的推断未实测；无证据表明本包当前申请超限。；处理：waived
  依据：workspace/harbor_task/task.toml；optimization_evidence/public_crosscheck/reference/seed_1/result.json；expert_evidence/专家作业说明文档.md
  豁免原因：legacy_hardware_record_difference；指定旧批次0.3.10-standard-waiver.5逐原因政策；已读实际材料，只豁免此历史证明/迁移缺口，不改原事实，不要求新增补跑。

### QA16 轨迹实际迭代时长

观察判定：manual；本轮判定：pass_with_waivers
两轨声明36644/40158秒是分段首末轮跨度/并集，不能直接认证为净有效研究。已读分段、重复、排队与准备解释；未知净时长保留null，按历史时长证明缺口处置。
审阅依据：expert_evidence/run_summary.json；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json
- 36644/40158仅为轨迹时间跨度，净有效时长未知；不把工具可读数字当真实净时长。；处理：waived
  依据：expert_evidence/run_summary.json；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json
  豁免原因：legacy_research_duration_gap；指定旧批次0.3.10-standard-waiver.5逐原因政策；已读实际材料，只豁免此历史证明/迁移缺口，不改原事实，不要求新增补跑。

### QA17 Harbor Harness 兼容性

观察判定：fail；本轮判定：fail
H01–H06已审；H04当前评分接口故障阻断，H03镜像平台准备与H06当前NOP缺口按具体历史原因另处置，不能整行豁免。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/tests/trusted_env/envs/wrappers/tensor.py；expert_evidence/nop_trial/result.json
Harbor逐项派生：H01=pass；H02=pass；H03=pass_with_waivers；H04=fail；H05=pass；H06=pass_with_waivers

### QA18 轨迹、日志与分析

观察判定：fail；本轮判定：pass_with_waivers
两轨全部24轮及最终方法/补跑/失败已审；历史旧公开100条含Hidden34条，受影响Dev分invalid，不作正式B/R正证。实际最高档/启动及部分历史条件证据有限，未查实两轨有实质条件差异。
审阅依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/两轨可比性对照表_20261027.md；expert_evidence/best_method/REPRODUCIBILITY_STATUS.md；expert_evidence/专家作业说明文档.md
- 两轨旧公开集含Hidden34条，受影响历史Dev分invalid；现行15k正式B/R未采用这些Agent分。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/两轨可比性对照表_20261027.md；expert_evidence/best_method/REPRODUCIBILITY_STATUS.md；expert_evidence/专家作业说明文档.md
  豁免原因：historical_agent_runtime_finding；指定旧批次0.3.10-standard-waiver.5逐原因政策；已读实际材料，只豁免此历史证明/迁移缺口，不改原事实，不要求新增补跑。
  原分数状态：invalid
  历史事实：leakage/confirmed；分数影响：invalid
  影响依据：原数据切分说明与两轨对照表确认旧100=公开66+Hidden34；正式15k单独切分和重跑。
  受污染或未证实的Agent分数不作为作者正式 B/R 正证；仅部署规则差异不自动改写分数。
- 实际模型由artifact端点/轨迹支持；最高档与独立空输出的历史启动材料不完整，未确认非独立运行。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/两轨可比性对照表_20261027.md；expert_evidence/best_method/REPRODUCIBILITY_STATUS.md；expert_evidence/专家作业说明文档.md
  豁免原因：legacy_runtime_proof_gap；指定旧批次0.3.10-standard-waiver.5逐原因政策；已读实际材料，只豁免此历史证明/迁移缺口，不改原事实，不要求新增补跑。
- 已实际对比现有两轨材料，旧版材料仍不足以证明所有历史条件一致；仅此记录缺口豁免，不声称已证实同条件。已逐维读两轨、方法、artifact协议、旧Dev切分、失败摘要、对照表和专家说明。两边记录同30000步/seed1/10回合与旧100条集，独立最佳方法及输出有支持；但没有各自原Prompt/反馈/IPC只读启动原件，当前Docker配置不能追溯证明当时权限相同。未发现已确认的实质差异，也不认定已证明完全同条件。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/两轨可比性对照表_20261027.md；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md；expert_evidence/best_method/box1/artifact.json；expert_evidence/best_method/box2/artifact.json
  豁免原因：legacy_runtime_proof_gap；本轮旧题迁移不要求新增Prompt快照、hash或重跑；已读资料中没有已确认的实质条件差异。

### QA19 seed 与有效提升阈值

观察判定：pass；本轮判定：pass
题面说明随机性、正式种子口径与Δ≥3σ_B；不额外要求题面说明replicate数。
审阅依据：workspace/harbor_task/instruction.md

### QA20 修改范围、网络与工具策略

观察判定：pass；本轮判定：pass
题面明确可改/冻结范围、禁止取外部模型/数据/答案，引用平台默认工具策略；无需要额外环境的任务运行调用。
审阅依据：workspace/harbor_task/instruction.md

### QA21 三个 JSON 的填写内容

观察判定：manual；本轮判定：pass_with_waivers
两轨JSON八字段均解析、失败null与原因及best相符，annotation/run_summary属本题；实算四项95文件指纹匹配。声明hash是当前迁移包身份，不证明历史字节；旧status=ok与历史版本绑定按迁移缺口单列。
审阅依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/expert_annotation.json；expert_evidence/run_summary.json
- 四项当前指纹匹配，但补记当前hash只表题目归属，不是历史运行字节；不伪造历史绑定。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/expert_annotation.json；expert_evidence/run_summary.json
  豁免原因：legacy_task_binding_migration；指定旧批次0.3.10-standard-waiver.5逐原因政策；已读实际材料，只豁免此历史证明/迁移缺口，不改原事实，不要求新增补跑。
- 两轨八字段均有；历史status=ok等与新版枚举有差异，保留原JSON。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/expert_annotation.json；expert_evidence/run_summary.json
  豁免原因：legacy_trajectory_schema_gap；指定旧批次0.3.10-standard-waiver.5逐原因政策；已读实际材料，只豁免此历史证明/迁移缺口，不改原事实，不要求新增补跑。

## Harbor 六项

### H01 任务目录

观察判定：pass；本轮判定：pass
任务根与核心构建/入口在位；真实Hidden文件由专用tests镜像预置，evaluate读取；Agent environment上下文仅公开Dev/数据/starter。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/hidden_assets/README.md；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/environment/Dockerfile

### H02 版本与配置

观察判定：pass；本轮判定：pass
TOML可解析；显式separate，双方GPU为H20/L20，16/8CPU，无有效storage/禁网/Compose；自定义注释元数据不冒充原生执行字段。
审阅依据：workspace/harbor_task/task.toml

### H03 环境与运行路径

观察判定：manual；本轮判定：pass_with_waivers
两沙盒各单容器静态路径与artifacts一致，GPU由当前进程使用，无题目自建远端工作环境；镜像未填内场tag，实际构建/解释器/root隔离由平台准备核验，不声称本次已运行。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/evaluate_verify.py
- 存在完整双Dockerfile源方案，内场ICM标签准备未完成。；处理：waived
  依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/evaluate_verify.py
  豁免原因：platform_image_preparation_pending；指定旧批次0.3.10-standard-waiver.5逐原因政策；已读实际材料，只豁免此历史证明/迁移缺口，不改原事实，不要求新增补跑。
- 当前实际构建/解释器/root与sandbox传输验证未运行；仅此平台验证欠缺免补证。；处理：waived
  依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/evaluate_verify.py
  豁免原因：platform_execution_verification_pending；指定旧批次0.3.10-standard-waiver.5逐原因政策；已读实际材料，只豁免此历史证明/迁移缺口，不改原事实，不要求新增补跑。

### H04 测试入口与 reward

观察判定：fail；本轮判定：fail
入口和reward原子输出存在，但当前正常候选被docstring冻结指纹误拒；即使通过该关，动作ndarray与TensorWrapper接口冲突使首步失败，不能输出真实正常分数。
审阅依据：workspace/harbor_task/tests/evaluate_verify.py:590-599；workspace/harbor_task/tests/trusted_env/envs/__init__.py:80-83；workspace/harbor_task/tests/trusted_env/envs/wrappers/tensor.py:36-40；workspace/harbor_task/tests/evaluate_verify.py:720-740；workspace/harbor_task/tests/evaluate_verify.py:805-831；workspace/harbor_task/tests/evaluate_verify.py:927-945；workspace/harbor_task/tests/hard_gate.py:603-632；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:146-168；workspace/harbor_task/tests/trusted_env/trusted_tdmpc2.py；workspace/harbor_task/tests/test.sh
- 评分父进程将动作构造成 np.ndarray 后传入 TensorWrapper.step；该包装器调用 action.numpy()，ndarray 无此方法，正常动作在首步即抛 AttributeError，并被当作候选侧失败计 -1。；处理：unwaived
  依据：workspace/harbor_task/tests/evaluate_verify.py:590-599；workspace/harbor_task/tests/trusted_env/envs/__init__.py:80-83；workspace/harbor_task/tests/trusted_env/envs/wrappers/tensor.py:36-40
  修改方向：统一父进程动作与 TensorWrapper 接口，例如校验后转 CPU float32 Tensor 再 step；将评测器自身接口异常与候选违规分开归因。
  验收：提交修正后的真实源码；复验时用原样 Starter 和 Reference 各走正常动作的完整入口，确认冻结检查通过、环境至少完成一个完整回合并产出真实 reward；另确认实际改写冻结代码仍拒绝。本次不执行候选或 Verifier，也不要求重做历史两轨。
- 静态 G6 剥离 docstring，但运行时 _code_fp 将 co_consts 中的 docstring 纳入指纹；当前 Starter 的 _estimate_value_iq 说明字符串与可信副本不同，实际方法体相同也会被 _guard 误判篡改。Reference 的说明字符串亦不同。；处理：unwaived
  依据：workspace/harbor_task/tests/evaluate_verify.py:720-740；workspace/harbor_task/tests/evaluate_verify.py:805-831；workspace/harbor_task/tests/evaluate_verify.py:927-945；workspace/harbor_task/tests/hard_gate.py:603-632；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:146-168；workspace/harbor_task/tests/trusted_env/trusted_tdmpc2.py
  修改方向：统一静态与运行时冻结比较的语义范围，排除仅 docstring 差异；保留对可执行代码变化的拒绝。
  验收：提交修正后的真实源码；复验时用原样 Starter 和 Reference 各走正常动作的完整入口，确认冻结检查通过、环境至少完成一个完整回合并产出真实 reward；另确认实际改写冻结代码仍拒绝。本次不执行候选或 Verifier，也不要求重做历史两轨。
- 当前格式实质问题（来自 F07）：当前评分有两项确证静态故障：动作ndarray与TensorWrapper契约冲突，以及运行时docstring指纹误拒合规Starter/Reference。
  定位：workspace/harbor_task/tests/evaluate_verify.py:590-599；workspace/harbor_task/tests/trusted_env/envs/__init__.py:80-83；workspace/harbor_task/tests/trusted_env/envs/wrappers/tensor.py:36-40；workspace/harbor_task/tests/evaluate_verify.py:720-740；workspace/harbor_task/tests/evaluate_verify.py:805-831；workspace/harbor_task/tests/evaluate_verify.py:927-945；workspace/harbor_task/tests/hard_gate.py:603-632；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:146-168；workspace/harbor_task/tests/trusted_env/trusted_tdmpc2.py

### H05 Job/Trial 调用配置

观察判定：pass；本轮判定：pass
已审旧NOP配置、脚本及日志：task选择、NOP身份、独立镜像、候选docker cp与Verifier非禁用可定位；属旧自验封装，不冒称当前MASO原生Job已运行。
审阅依据：expert_evidence/nop_trial/config.json；expert_evidence/nop_trial/reproduce_nop_full.sh；expert_evidence/nop_trial/trial.log

### H06 NOP 自检记录

观察判定：fail；本轮判定：pass_with_waivers
已有NOP两处nop、separate、正常结束无异常，JSON优先7数值与result逐项一致、日志非空、完整15k/30回合。运行于旧41835e1a版本/V100，当前版未跑，不以旧记录证明当前链路。
审阅依据：expert_evidence/nop_trial/config.json；expert_evidence/nop_trial/result.json；expert_evidence/nop_trial/verifier/reward.json；expert_evidence/nop_trial/verifier/reward.txt；expert_evidence/nop_trial/trial.log
- 已审旧NOP的config/result/reward/log，成功记录属于41835e1a历史字节；现包已改评分冻结面，当前NOP未跑。；处理：waived
  依据：expert_evidence/nop_trial/config.json；expert_evidence/nop_trial/result.json；expert_evidence/nop_trial/verifier/reward.json；expert_evidence/nop_trial/verifier/reward.txt；expert_evidence/nop_trial/trial.log
  豁免原因：legacy_nop_or_current_trial_gap；指定旧批次0.3.10-standard-waiver.5逐原因政策；已读实际材料，只豁免此历史证明/迁移缺口，不改原事实，不要求新增补跑。

## 两轨已有内容

### T01 第一条轨迹已有内容

观察判定：fail；本轮判定：pass_with_waivers
8轮，7次出分、1次失败；依次探索 continuation/support、counterfactual、planner residual、support kernel、ORRA-IQ、potential、失败residual及RACR；第2轮85.168为最佳。
审阅依据：expert_evidence/trajectory_codex.json；expert_evidence/run_summary.json；expert_evidence/best_method/box1/artifact.json；expert_evidence/best_method/REPRODUCIBILITY_STATUS.md；expert_evidence/best_method/rerun_result/rerun_summary.json；expert_evidence/两轨可比性对照表_20261027.md
方法：Calibrated Counterfactual Anchor：专家 continuation RTG、反事实动作距离惩罚、actor 行为锚定、ensemble 保守 TD。
迭代内容：8轮，7次出分、1次失败；依次探索 continuation/support、counterfactual、planner residual、support kernel、ORRA-IQ、potential、失败residual及RACR；第2轮85.168为最佳。
最终结果：历史最佳85.168；干净Dev补跑56.405；独立旧入口54.305，协议不同不直接比较。
分数采用范围：原值仅作受污染历史过程记录；invalid保持，不因豁免恢复valid，也不替代作者现行15k B/R。
已读来源：expert_evidence/trajectory_codex.json；expert_evidence/run_summary.json；expert_evidence/best_method/box1/artifact.json；expert_evidence/best_method/REPRODUCIBILITY_STATUS.md；expert_evidence/best_method/rerun_result/rerun_summary.json；expert_evidence/两轨可比性对照表_20261027.md；expert_evidence/best_method/box1/tdmpc2/tdmpc2.py
- 旧公开100条包含Hidden34条，历史Dev分invalid，不能作当前正式科学证据。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/run_summary.json；expert_evidence/best_method/box1/artifact.json；expert_evidence/best_method/REPRODUCIBILITY_STATUS.md；expert_evidence/best_method/rerun_result/rerun_summary.json；expert_evidence/两轨可比性对照表_20261027.md
  豁免原因：historical_agent_runtime_finding；指定旧批次0.3.10-standard-waiver.5逐原因政策；已读实际材料，只豁免此历史证明/迁移缺口，不改原事实，不要求新增补跑。
  原分数状态：invalid
  历史事实：leakage/confirmed；分数影响：invalid
  影响依据：同QA18；旧Agent分不用于15k正式B/R归一化。
  受污染或未证实的Agent分数不作为作者正式 B/R 正证；仅部署规则差异不自动改写分数。
- 既有时间是分段跨度，非独立可核净时长。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/run_summary.json；expert_evidence/best_method/box1/artifact.json；expert_evidence/best_method/REPRODUCIBILITY_STATUS.md；expert_evidence/best_method/rerun_result/rerun_summary.json；expert_evidence/两轨可比性对照表_20261027.md
  豁免原因：legacy_research_duration_gap；指定旧批次0.3.10-standard-waiver.5逐原因政策；已读实际材料，只豁免此历史证明/迁移缺口，不改原事实，不要求新增补跑。
- 旧启动/最高推理档证明范围有限，未证实非独立或实质条件差异。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/run_summary.json；expert_evidence/best_method/box1/artifact.json；expert_evidence/best_method/REPRODUCIBILITY_STATUS.md；expert_evidence/best_method/rerun_result/rerun_summary.json；expert_evidence/两轨可比性对照表_20261027.md
  豁免原因：legacy_runtime_proof_gap；指定旧批次0.3.10-standard-waiver.5逐原因政策；已读实际材料，只豁免此历史证明/迁移缺口，不改原事实，不要求新增补跑。

### T02 第二条轨迹已有内容

观察判定：fail；本轮判定：pass_with_waivers
16轮，4次出分、12次失败；完整保留重启重复时间戳及无代码变更；RTG、latent rollout、V bootstrap、BC、distributional Q、CQL、全回合RTG；第14轮12.2079最佳（旧局部r4-scored）。
审阅依据：expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/best_method/box2/artifact.json；expert_evidence/best_method/REPRODUCIBILITY_STATUS.md；expert_evidence/best_method/rerun_result/rerun_summary.json；expert_evidence/两轨可比性对照表_20261027.md
方法：DistTD-ExpertAnchor-BC：修复历史标量Q交叉熵退化为分布Q，专家MC目标锚定与BC；不得将历史修bug收益混入现行健康B/R方法收益。
迭代内容：16轮，4次出分、12次失败；完整保留重启重复时间戳及无代码变更；RTG、latent rollout、V bootstrap、BC、distributional Q、CQL、全回合RTG；第14轮12.2079最佳（旧局部r4-scored）。
最终结果：历史最佳12.2079原轮权重已缺；同方法补跑27.5285和14.5289均非原轮，不补造原权重。
分数采用范围：原值仅作受污染历史过程记录；invalid保持，不因豁免恢复valid，也不替代作者现行15k B/R。
已读来源：expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/best_method/box2/artifact.json；expert_evidence/best_method/REPRODUCIBILITY_STATUS.md；expert_evidence/best_method/rerun_result/rerun_summary.json；expert_evidence/两轨可比性对照表_20261027.md；expert_evidence/best_method/box2/tdmpc2/tdmpc2.py
- 旧公开100条包含Hidden34条，历史Dev分invalid，不能作当前正式科学证据。；处理：waived
  依据：expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/best_method/box2/artifact.json；expert_evidence/best_method/REPRODUCIBILITY_STATUS.md；expert_evidence/best_method/rerun_result/rerun_summary.json；expert_evidence/两轨可比性对照表_20261027.md
  豁免原因：historical_agent_runtime_finding；指定旧批次0.3.10-standard-waiver.5逐原因政策；已读实际材料，只豁免此历史证明/迁移缺口，不改原事实，不要求新增补跑。
  原分数状态：invalid
  历史事实：leakage/confirmed；分数影响：invalid
  影响依据：同QA18；旧Agent分不用于15k正式B/R归一化。
  受污染或未证实的Agent分数不作为作者正式 B/R 正证；仅部署规则差异不自动改写分数。
- 既有时间是分段跨度，非独立可核净时长。；处理：waived
  依据：expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/best_method/box2/artifact.json；expert_evidence/best_method/REPRODUCIBILITY_STATUS.md；expert_evidence/best_method/rerun_result/rerun_summary.json；expert_evidence/两轨可比性对照表_20261027.md
  豁免原因：legacy_research_duration_gap；指定旧批次0.3.10-standard-waiver.5逐原因政策；已读实际材料，只豁免此历史证明/迁移缺口，不改原事实，不要求新增补跑。
- 旧启动/最高推理档证明范围有限，未证实非独立或实质条件差异。；处理：waived
  依据：expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/best_method/box2/artifact.json；expert_evidence/best_method/REPRODUCIBILITY_STATUS.md；expert_evidence/best_method/rerun_result/rerun_summary.json；expert_evidence/两轨可比性对照表_20261027.md
  豁免原因：legacy_runtime_proof_gap；指定旧批次0.3.10-standard-waiver.5逐原因政策；已读实际材料，只豁免此历史证明/迁移缺口，不改原事实，不要求新增补跑。

## 两轨实际条件对比

对比已完成：是
条件判断：historical_evidence_gap；成对对照有效性：unverified
已逐维读两轨、方法、artifact协议、旧Dev切分、失败摘要、对照表和专家说明。两边记录同30000步/seed1/10回合与旧100条集，独立最佳方法及输出有支持；但没有各自原Prompt/反馈/IPC只读启动原件，当前Docker配置不能追溯证明当时权限相同。未发现已确认的实质差异，也不认定已证明完全同条件。
已对比维度：prompt、task、dev、feedback、constraints、resources
对比依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/两轨可比性对照表_20261027.md；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md；expert_evidence/best_method/box1/artifact.json；expert_evidence/best_method/box2/artifact.json
质检员内部对比底稿；不要求专家新增字段、Prompt快照、hash或重跑。语义判断须实际阅读原材料，脚本只核验审阅覆盖及判定一致性。
- resources / legacy_format_or_resource：历史研究记4090，补跑在3080Ti；窗口不同、历史卡型与当前H20/L20声明不同，不冒充同卡实测。
  依据：expert_evidence/专家作业说明文档.md；expert_evidence/best_method/rerun_result/rerun_summary.json

## 当前格式前检 F01–F07（子检查）

format_decision：FAIL
以下仅为当前格式子检查；整题结论以本报告顶部完整质检结果为准。

- F01 [pass] 当前必需目录、文件与 TOML 接口：三目录与任务根完整，TOML可解析，核心接口存在。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md
- F02 [pass] 有效构建或镜像方案、构建上下文及 COPY 来源：Agent context=environment、Verifier context=tests，COPY来源均在各自context；有效源构建方案存在，ICM镜像由平台准备。
  格式审阅依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile
- F03 [pass] 评分入口、独立依赖声明与固定输出路径：评分入口/tests/test.sh及独立依赖在位，reward固定/logs/verifier路径；实际逻辑故障列F07。
  格式审阅依据：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/requirements.txt
- F04 [pass] 提交物 artifacts 移交契约：顶层artifacts覆盖/workspace/solution，与评分读取路径一致。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/test.sh
- F05 [pass] 公开 Dev、私有 Hidden 供给与 Agent 隔离：公开Dev/data随Agent，Hidden仅tests专用镜像；真实文件/manifest非占位；不反序列化数据。
  格式审阅依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/hidden_assets/dataset/hidden_manifest.json
- F06 [pass] separate、单容器、无 Compose 与当前目标资源配置：separate、双方单容器、无正式Compose文件，目标H20/L20和CPU数合法；启动/训练调用不创建额外工作环境。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/environment/public_eval/eval_dev.py
- F07 [fail] 当前评分实现与冻结面无确证故障或作者泄漏造假：当前评分有两项确证静态故障：动作ndarray与TensorWrapper契约冲突，以及运行时docstring指纹误拒合规Starter/Reference。
  格式审阅依据：workspace/harbor_task/tests/evaluate_verify.py:590-599；workspace/harbor_task/tests/trusted_env/envs/__init__.py:80-83；workspace/harbor_task/tests/trusted_env/envs/wrappers/tensor.py:36-40；workspace/harbor_task/tests/evaluate_verify.py:720-740；workspace/harbor_task/tests/evaluate_verify.py:805-831；workspace/harbor_task/tests/evaluate_verify.py:927-945；workspace/harbor_task/tests/hard_gate.py:603-632；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:146-168；workspace/harbor_task/tests/trusted_env/trusted_tdmpc2.py
  修改方向：统一父进程动作与 TensorWrapper 接口，例如校验后转 CPU float32 Tensor 再 step；将评测器自身接口异常与候选违规分开归因。 统一静态与运行时冻结比较的语义范围，排除仅 docstring 差异；保留对可执行代码变化的拒绝。
  验收：提交修正后的真实源码；复验时用原样 Starter 和 Reference 各走正常动作的完整入口，确认冻结检查通过、环境至少完成一个完整回合并产出真实 reward；另确认实际改写冻结代码仍拒绝。本次不执行候选或 Verifier，也不要求重做历史两轨。

## 平台后续事项（不阻断本轮已有材料审阅）

- 字节内部准备、构建或导入镜像并配置实际 ICM tag；本轮不要求专家补内部镜像运行记录。
- 平台实际构建和启动，核对依赖、基础镜像 digest 及 bash/解释器；静态推断不能冒充运行结果。
- 平台核对 root、seccomp、网络及实际分配的沙盒权限设置。
- 平台后续执行当前版本 Harbor Trial/NOP、独立 Verifier 和 reward 收集；其缺口不作为本轮专家返修门槛。
- 已有原硬件结果本轮复核；不把旧值改称新硬件实测，不要求新环境补跑；平台核对实际当前提交物移交及目标硬件运行。
- 移除不支持的禁网字段后，新的联网或外部查表防护尚未落实，列为平台迁移事项，不要求本批专家新增防护实现或补跑；当前确证 Hidden 暴露或假 reward 仍属当前核心缺陷。
- 基础镜像 nvidia/cuda:11.8.0-cudnn8-devel-ubuntu20.04 的 bash/解释器不可由当前声明确认；需补充镜像说明、依赖声明或已有运行证据。静态文件映射不能证明运行成功。

## 原 v0.3.10 自动检查及 NOP 原判

已调用原标准审计入口：True
NOP：{"status": "manual", "runtime_status": "unverified", "trials": [{"trial_dir": "expert_evidence/nop_trial", "evidence": ["expert_evidence/nop_trial/config.json", "expert_evidence/nop_trial/result.json", "expert_evidence/nop_trial/verifier/reward.json", "expert_evidence/nop_trial/verifier/reward.txt", "expert_evidence/nop_trial/trial.log"], "details": {"trial_dir": "expert_evidence/nop_trial", "agent": "nop", "verifier_environment_mode": "separate", "rewards": {"reward": -9.641584358476253e-05, "reward_raw": 0.006078036245889961, "episode_reward_mean_across_seeds": 0.006078036245889961, "episode_reward_std_across_seeds": 0.0, "episode_success_mean": 0.0, "eval_episodes": 30, "steps": 15000}, "task_binding": {"status": "manual", "basis": "name_only"}}, "status": "manual", "summary": "已有 NOP 的同次 Trial、Agent、separate、sandbox 反证、结束与异常、reward 数值和非空日志已按原校验器核查。"}], "summary": "逐份读取并校验已有 NOP 记录；未启动新的 Trial。"}

原报告与全部详细结果：standard/report.json；不因豁免覆盖原判。

| 来源 | 项目 | 原判 | 本轮处理 | 依据及原因 |
|---|---|---|---|---|
| checks/QA05 | QA05 | fail | fail | 静态 G6 剥离 docstring，但运行时 _code_fp 将 co_consts 中的 docstring 纳入指纹；当前 Starter 的 _estimate_value_iq 说明字符串与可信副本不同，实际方法体相同也会被 _guard 误判篡改。Reference 的说明字符串亦不同。 |
| checks/QA06 | QA06 | fail | fail | 评分父进程将动作构造成 np.ndarray 后传入 TensorWrapper.step；该包装器调用 action.numpy()，ndarray 无此方法，正常动作在首步即抛 AttributeError，并被当作候选侧失败计 -1。 |
| checks/QA11 | QA11 | fail | fail | 八项实质内容齐，但题面将超时列为基础设施错误；当前评测超时 eval_timeout_* 被默认归候选并计-1，实际错误归因与题面矛盾。 |
| checks/QA15 | QA15 | manual | pass_with_waivers | 缺少：当前成绩的硬件归属/换卡影响尚未确认 |
| checks/QA16 | QA16 | manual | pass_with_waivers | Codex + GPT-5.6 Sol缺少有效时长或排除排队/安装/故障的核算证据；Codex + Seed 2.1 Turbo缺少有效时长或排除排队/安装/故障的核算证据 |
| checks/QA17 | QA17 | fail | derived_from_details | Harbor 子项未通过：H03 环境与运行路径；H04 测试入口与 reward；H06 NOP 自检记录；详细原因与证据保留在 report.json。 |
| checks/QA18 | QA18 | fail | pass_with_waivers | 两轨全部24轮及最终方法/补跑/失败已审；历史旧公开100条含Hidden34条，受影响Dev分invalid，不作正式B/R正证。实际最高档/启动及部分历史条件证据有限，未查实两轨有实质条件差异。 |
| checks/QA21 | QA21 | manual | pass_with_waivers | 两轨JSON八字段均解析、失败null与原因及best相符，annotation/run_summary属本题；实算四项95文件指纹匹配。声明hash是当前迁移包身份，不证明历史字节；旧status=ok与历史版本绑定按迁移缺口单列。 |
| harbor/H03 | H03 | manual | pass_with_waivers | 两沙盒各单容器静态路径与artifacts一致，GPU由当前进程使用，无题目自建远端工作环境；镜像未填内场tag，实际构建/解释器/root隔离由平台准备核验，不声称本次已运行。 |
| harbor/H04 | H04 | fail | fail | 入口和reward原子输出存在，但当前正常候选被docstring冻结指纹误拒；即使通过该关，动作ndarray与TensorWrapper接口冲突使首步失败，不能输出真实正常分数。 |
| harbor/H06 | H06 | fail | derived_from_details | 已有NOP两处nop、separate、正常结束无异常，JSON优先7数值与result逐项一致、日志非空、完整15k/30回合。运行于旧41835e1a版本/V100，当前版未跑，不以旧记录证明当前链路。 |
| harbor/path_contract/1 | H03 | manual | pass_with_waivers | 基础镜像 nvidia/cuda:11.8.0-cudnn8-devel-ubuntu20.04 的 bash/解释器不可由当前声明确认；需补充镜像说明、依赖声明或已有运行证据。静态文件映射不能证明运行成功。 |
| resources/gaps/0 | QA15 | manual | pass_with_waivers | 当前成绩的硬件归属/换卡影响尚未确认 |
| trajectory/0/finding/0 | QA18 | fail | pass_with_waivers | 两轨使用旧100条公开数据，包含后续Hidden34条，历史Dev分受污染；系历史作者数据边界缺陷，不推定Agent主观作弊。 |
| trajectory/1/finding/0 | QA18 | fail | pass_with_waivers | 两轨使用旧100条公开数据，包含后续Hidden34条，历史Dev分受污染；系历史作者数据边界缺陷，不推定Agent主观作弊。 |
| nop/trials/0 | H06 | manual | pass_with_waivers | 已有 NOP 的同次 Trial、Agent、separate、sandbox 反证、结束与异常、reward 数值和非空日志已按原校验器核查。 |
