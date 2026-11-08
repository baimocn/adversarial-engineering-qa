# 旧题完整质检与逐原因豁免

本轮结论：FAIL
阶段：standard_review_with_waivers
已完成全部内容审阅：是

原 v0.3.10 全部检查及完整内容审阅已完成，包括已有 NOP；仅按具体历史原因豁免。未执行题包代码或新增 Harbor Trial。
平台实跑：not_executed；未执行模型、题目程序、Docker 或 Harbor。

## 方法与正式对照

Hopper-Hop在线模型化RL，允许重新设计训练期critic目标、价值锚定、专家数据使用和actor/critic模块；实际执行固定use_expert=false的可编程更新函数，并非仅搜索常量。
可修改：_update_vanilla/_td_target_vanilla的损失、目标与数据策略；actor/critic模块及专家数据混合
冻结面：hopper-hop奖励/环境与30回合eval_mode=True评测；plan/_estimate_value_iq与分支开关；数据内容及可信评分文件
指标与质量门：episode_reward maximize；score=(x-B)/(489.3319-B)，无clip；正式seeds=1/2/3，100000步、30回合；数值要求Δ≥3σ_B和归一化[0.15,0.8]，但健康Baseline质量门当前失败。
Baseline：Starter原样，中性TD目标r+γQ_target，reward-free世界模型，标量Q集成和symlog回归；100000步在线训练，不使用已加载专家样本。当前零初始化与预测端symlog组合仍阻断Q梯度，故不是健康正式锚点。
Reference：IQ式隐式奖励Q−γV，专家/在线样本混合、软Q目标、χ²正则与初态价值锚定；同100000步及seeds=1/2/3，官方eval_agent重载30回合。
正式改善：原始记录Δ=361.780061770，3σ_B=0.509812579，归一化=0.739541794；算术在门槛内，但Baseline实现故障，不能认证真实方法改善。
质量有效性：记录均COMPLETE且模型文件SHA一致；Baseline健康质量门失败，因此baseline_valid=false；Reference原始实测值保留，不伪称全部正式对照有效。旧comparison_summary已明示作废，不与新值混用。
已有原始对照：[{"seed": 1, "baseline": 0.3299457737952859, "reference": 367.1391427026705, "baseline_valid": false, "reference_valid": true}, {"seed": 2, "baseline": 0.07157723124073527, "reference": 397.4439462740368, "baseline_valid": false, "reference_valid": true}, {"seed": 3, "baseline": 0.009527193800568056, "reference": 321.16814653102824, "baseline_valid": false, "reference_valid": true}]
依据：optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；workspace/harbor_task/tests/anchors.json；optimization_evidence/hidden_20261022/README.md；workspace/harbor_task/environment/starter/tdmpc2/common/math.py；workspace/harbor_task/environment/starter/tdmpc2/common/world_model.py

## 研究三门

### G01 方法级优化空间

观察判定：pass；本轮判定：pass
可执行的训练损失、目标和模块设计空间开放；Reference改变数据混合和目标形式，超出常量调参。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:250-342；workspace/reference/tdmpc2/tdmpc2.py:377-470；workspace/reference/tdmpc2/iq.py

### G02 Baseline 合理性

观察判定：fail；本轮判定：fail
Q头末层权重和偏置均为0；soft_ce_scalar对预测值应用sign×log(1+abs)，零点计算图梯度为0，Q无法启动学习。真实Ensemble消融fixed仍q_grad=0；随机线性头控制不能排除此故障。
审阅依据：workspace/harbor_task/environment/starter/tdmpc2/common/math.py:5-29；workspace/harbor_task/environment/starter/tdmpc2/common/math.py:71-77；workspace/harbor_task/environment/starter/tdmpc2/common/world_model.py:30-34；workspace/harbor_task/environment/starter/tdmpc2/common/init.py:4-22；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:293-312；expert_evidence/repair/value_loss_ablation/README.md；expert_evidence/repair/value_loss_ablation/ablation_fixed.json
训练充分性：12份原始日志全部覆盖0至100000步、无Traceback；达到共同预算不证明Q有效更新；不以低分或缺曲线判训练截短。
  依据：optimization_evidence/hidden_20261022/README.md；optimization_evidence/baseline_runs/seed_1/run.log；optimization_evidence/reference_runs/seed_1/run.log
方法代表性：中性TD可作为合理朴素方法角色；不要求SOTA，也未使用包外强基线否定它。实际故障另列。
  依据：workspace/harbor_task/instruction.md；workspace/reference/README.md
原协议预算可比性：两臂同数据、100000步、batch256、seed集合和30回合评测；专家数据使用为允许变量。历史Hidden同vGPU卡，Public同4080S；超时属于QA15而非预算不公平。
  依据：optimization_evidence/hidden_20261022/README.md；expert_evidence/repair/rerun_20261021/run_one.py；workspace/harbor_task/environment/starter/tdmpc2/config.yaml；workspace/reference/tdmpc2/config.yaml
实现正确性：Q头末层权重和偏置均为0；soft_ce_scalar对预测值应用sign×log(1+abs)，零点计算图梯度为0，Q无法启动学习。真实Ensemble消融fixed仍q_grad=0；随机线性头控制不能排除此故障。
  依据：workspace/harbor_task/environment/starter/tdmpc2/common/math.py:5-29；workspace/harbor_task/environment/starter/tdmpc2/common/math.py:71-77；workspace/harbor_task/environment/starter/tdmpc2/common/world_model.py:30-34；workspace/harbor_task/environment/starter/tdmpc2/common/init.py:4-22；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:293-312；expert_evidence/repair/value_loss_ablation/README.md；expert_evidence/repair/value_loss_ablation/ablation_fixed.json
选择与对照完整性：同角色固定tdmpc2.py哈希，三seed各独立训练，六模型SHA逐一吻合且互异；final选择已披露；旧失败协议与当前重跑分开。
  依据：optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/hidden_20261022/checkpoint_manifest.json；expert_evidence/repair/rerun_20261021/run_one.py
- Q头末层权重和偏置均为0；soft_ce_scalar对预测值应用sign×log(1+abs)，零点计算图梯度为0，Q无法启动学习。真实Ensemble消融fixed仍q_grad=0；随机线性头控制不能排除此故障。；处理：unwaived
  依据：workspace/harbor_task/environment/starter/tdmpc2/common/math.py:5-29；workspace/harbor_task/environment/starter/tdmpc2/common/math.py:71-77；workspace/harbor_task/environment/starter/tdmpc2/common/world_model.py:30-34；workspace/harbor_task/environment/starter/tdmpc2/common/init.py:4-22；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:293-312；expert_evidence/repair/value_loss_ablation/README.md；expert_evidence/repair/value_loss_ablation/ablation_fixed.json
  修改方向：修复标量价值回归在真实零初始化Q头的梯度通路（例如直接对Q回归变换后的目标，或使用零点梯度正确的实现），保留健康朴素Starter及共同预算；撤回故障Baseline支持的改善主张。
  验收：真实WorldModel零初始化、非零TD目标下的Q参数梯度及一次更新差异；同协议健康B/R完整seed结果与对应源码/模型。无需为历史轨迹重新roll。

### G03 Reference 提升充分性

观察判定：fail；本轮判定：fail
全部成对数值算术达标，但正式Baseline存在Q零梯度静态故障，三组B均不能作健康对照；大幅提升不能消除此质量门失败。
审阅依据：optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；workspace/harbor_task/environment/starter/tdmpc2/common/math.py:5-29；workspace/harbor_task/environment/starter/tdmpc2/common/math.py:71-77；workspace/harbor_task/environment/starter/tdmpc2/common/world_model.py:30-34；workspace/harbor_task/environment/starter/tdmpc2/common/init.py:4-22；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:293-312；expert_evidence/repair/value_loss_ablation/README.md；expert_evidence/repair/value_loss_ablation/ablation_fixed.json
正式复算：{"baseline_mean": 0.13701673294552974, "reference_mean": 361.91707850257853, "baseline_sample_std": 0.1699375264295285, "reference_sample_std": 38.40510216743731, "improvement": 361.780061769633, "run_count": 3, "sigma_multiplier": 2128.9003633912475, "three_sigma_baseline": 0.5098125792885855, "normalized_score": 0.7395417943734605}
- 全部成对数值算术达标，但正式Baseline存在Q零梯度静态故障，三组B均不能作健康对照；大幅提升不能消除此质量门失败。；处理：unwaived
  依据：optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；workspace/harbor_task/environment/starter/tdmpc2/common/math.py:5-29；workspace/harbor_task/environment/starter/tdmpc2/common/math.py:71-77；workspace/harbor_task/environment/starter/tdmpc2/common/world_model.py:30-34；workspace/harbor_task/environment/starter/tdmpc2/common/init.py:4-22；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:293-312；expert_evidence/repair/value_loss_ablation/README.md；expert_evidence/repair/value_loss_ablation/ablation_fixed.json
  修改方向：修复标量价值回归在真实零初始化Q头的梯度通路（例如直接对Q回归变换后的目标，或使用零点梯度正确的实现），保留健康朴素Starter及共同预算；撤回故障Baseline支持的改善主张。
  验收：真实WorldModel零初始化、非零TD目标下的Q参数梯度及一次更新差异；同协议健康B/R完整seed结果与对应源码/模型。无需为历史轨迹重新roll。
- 质量门有效性未满足；seed 1 的 baseline_valid 为 false；seed 2 的 baseline_valid 为 false；seed 3 的 baseline_valid 为 false；处理：unwaived
  依据：optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；workspace/harbor_task/tests/anchors.json；optimization_evidence/hidden_20261022/README.md；workspace/harbor_task/environment/starter/tdmpc2/common/math.py；workspace/harbor_task/environment/starter/tdmpc2/common/world_model.py
  修改方向：核对已有正式 B/R 与评分定义，纠正实质数值、协议或质量有效性问题；迁移记录豁免不能证明科学门达标。
  验收：可信已有原始对照结果、相同协议与质量门依据及可重算的阈值计算。

## 21 项内容与实现

### QA01 八章节与题面信息泄露

观察判定：pass；本轮判定：pass
八章节有实质内容；仅通用TD-MPC2风格和必要接口说明，无参考论文标题、arXiv或参考解配置。
审阅依据：workspace/harbor_task/instruction.md

### QA02 评分公式与 0/1 锚点

观察判定：pass；本轮判定：pass
归一化为(mean_r-B)/(U-B)，方向连续单调且无clip；B/upper采用当前Hidden锚点；Baseline健康性独立在G02/G03失败。
审阅依据：workspace/harbor_task/tests/evaluate_verify.py:466-499；workspace/harbor_task/tests/anchors.json；workspace/harbor_task/instruction.md

### QA03 参考解分数与复现材料

观察判定：manual；本轮判定：pass_with_waivers
Reference三seed正式结果和非空日志、模型SHA齐全，原始归一化约0.73954；新增独立reload标NOT_RUN，但当次run_one已有训练后eval_agent加载，不伪造补验。
审阅依据：optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；workspace/reference/tdmpc2/tdmpc2.py；expert_evidence/repair/rerun_20261021/run_one.py:291-306；optimization_evidence/reference_runs/seed_1/model/reload.log
- 当次run_one在训练后调用eval_agent加载并评测，六模型哈希一致；另行独立复评标NOT_RUN是新环境验证缺口，不当成源码或结果作假。；处理：waived
  依据：expert_evidence/repair/rerun_20261021/run_one.py；optimization_evidence/reference_runs/seed_1/model/reload.log；optimization_evidence/hidden_20261022/README.md
  豁免原因：legacy_new_validation_dependency；依本批 format-repair-policy.md 逐原因处置：当次run_one在训练后调用eval_agent加载并评测，六模型哈希一致；另行独立复评标NOT_RUN是新环境验证缺口，不当成源码或结果作假。；保留原始观察，不补造历史记录，不要求新增平台验证或历史重跑。

### QA04 波动指标的 3σ 可分辨性

观察判定：pass；本轮判定：pass
训练seed通过set_seed进入random/numpy/torch及环境；两臂固定候选，完整1/2/3配对。样本σ_B=.169937526、Δ=361.780061770，算术超过3σ；故障锚点效力另列G02/G03。
审阅依据：workspace/harbor_task/environment/starter/tdmpc2/common/seed.py；workspace/harbor_task/environment/starter/tdmpc2/train.py；workspace/harbor_task/tests/trusted_env/envs/dmcontrol.py；expert_evidence/repair/rerun_20261021/run_one.py；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json

### QA05 约束执行实现

观察判定：fail；本轮判定：fail
环境文件有hash门禁，但题面固定的plan/_estimate_value_iq与config分支未恢复或校验；build_eval_cfg直接读取候选config并导入候选TDMPC2，固定评测边界可被改动。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/hard_gate.py；workspace/harbor_task/tests/evaluate_verify.py:173-245
- 环境文件有hash门禁，但题面固定的plan/_estimate_value_iq与config分支未恢复或校验；build_eval_cfg直接读取候选config并导入候选TDMPC2，固定评测边界可被改动。；处理：unwaived
  依据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/hard_gate.py；workspace/harbor_task/tests/evaluate_verify.py:173-245
  修改方向：将固定planner/分支配置从可信副本调用或做实际校验，开放方法接口仅用于允许研究面。
  验收：干净候选通过；改固定planner/分支配置被拒或不生效；整个评测时限含训练和评估。

### QA06 Verifier 入口、分数与错误处理

观察判定：pass；本轮判定：pass
单入口test.sh调用评分器；成功输出非空有限数值reward.json并写reward.txt；基础设施失败退出，降级有detail记录。
审阅依据：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/evaluate_verify.py:537-557

### QA07 instruction 中的 Hidden 信息泄露

观察判定：pass；本轮判定：pass
题面只描述Hidden规模/统计量/注入路径及禁令，未公开样本、标签或可恢复答案。
审阅依据：workspace/harbor_task/instruction.md

### QA08 instruction 中的参考解信息泄露

观察判定：pass；本轮判定：pass
题面未给参考代码、参考具体损失或参考分数；允许空间说明和朴素TD介绍不等同答案。
审阅依据：workspace/harbor_task/instruction.md

### QA09 结果清理与原子写入

观察判定：pass；本轮判定：pass
入口先清reward及预写结果，正常结果使用同目录临时文件和os.replace原子替换。
审阅依据：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/evaluate_verify.py:40-82

### QA10 冻结面保护或恢复实现

观察判定：fail；本轮判定：fail
训练子进程虽降权，eval_agent在test.sh的root评分父进程中import候选tdmpc2/common并调用构造、load和act；候选代码因此取得可信文件属主权限，a-w不能保护冻结面。
审阅依据：workspace/harbor_task/tests/evaluate_verify.py:205-245；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh
- 训练子进程虽降权，eval_agent在test.sh的root评分父进程中import候选tdmpc2/common并调用构造、load和act；候选代码因此取得可信文件属主权限，a-w不能保护冻结面。；处理：unwaived
  依据：workspace/harbor_task/tests/evaluate_verify.py:205-245；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh
  修改方向：将候选模型加载/推理也放入受限进程，可信环境、锚点和reward写入进程独立；拒绝降权失败时回退root。
  验收：完整调用链无高权限导入候选代码；候选不能修改原始环境/锚点/评分器，可信侧独立统计指标。

### QA11 instruction 八项内容

观察判定：fail；本轮判定：fail
题面称评测固定30回合，默认Dev入口实际10回合/30000步并自称与Hidden同协议；正式run_one的eval seed_offset=1000，而正式评分1000+seed，协议说明应区分。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/environment/public_eval/eval_dev.py:5-14；workspace/harbor_task/environment/public_eval/eval_dev.py:67-99；expert_evidence/repair/rerun_20261021/run_one.py:296-306；workspace/harbor_task/tests/evaluate_verify.py:384-391
- 题面称评测固定30回合，默认Dev入口实际10回合/30000步并自称与Hidden同协议；正式run_one的eval seed_offset=1000，而正式评分1000+seed，协议说明应区分。；处理：unwaived
  依据：workspace/harbor_task/instruction.md；workspace/harbor_task/environment/public_eval/eval_dev.py:5-14；workspace/harbor_task/environment/public_eval/eval_dev.py:67-99；expert_evidence/repair/rerun_20261021/run_one.py:296-306；workspace/harbor_task/tests/evaluate_verify.py:384-391
  修改方向：明确Dev与正式评分各自步数/回合/seed协议；统一需要一致的评测种子与正式锚点口径。
  验收：题面、公开入口、正式评分和锚点生成参数逐项一致或清楚披露合法差别。

### QA12 Git 清理

观察判定：pass；本轮判定：pass
清点提交数据无.git目录；当前审查工作区自身.git不属于提交材料，不混用。
审阅依据：workspace/harbor_task/instruction.md

### QA13 Baseline 与参考解提升

观察判定：fail；本轮判定：fail
六组正式Hidden原值、训练及模型均存在，但Baseline仍有零梯度故障；不能用当前B证明健康方法差异，旧被作废数字不参与。
审阅依据：optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；workspace/harbor_task/environment/starter/tdmpc2/common/math.py:5-29；workspace/harbor_task/environment/starter/tdmpc2/common/math.py:71-77；workspace/harbor_task/environment/starter/tdmpc2/common/world_model.py:30-34；workspace/harbor_task/environment/starter/tdmpc2/common/init.py:4-22；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:293-312；expert_evidence/repair/value_loss_ablation/README.md；expert_evidence/repair/value_loss_ablation/ablation_fixed.json
- 六组正式Hidden原值、训练及模型均存在，但Baseline仍有零梯度故障；不能用当前B证明健康方法差异，旧被作废数字不参与。；处理：unwaived
  依据：optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；workspace/harbor_task/environment/starter/tdmpc2/common/math.py:5-29；workspace/harbor_task/environment/starter/tdmpc2/common/math.py:71-77；workspace/harbor_task/environment/starter/tdmpc2/common/world_model.py:30-34；workspace/harbor_task/environment/starter/tdmpc2/common/init.py:4-22；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:293-312；expert_evidence/repair/value_loss_ablation/README.md；expert_evidence/repair/value_loss_ablation/ablation_fixed.json
  修改方向：修复标量价值回归在真实零初始化Q头的梯度通路（例如直接对Q回归变换后的目标，或使用零点梯度正确的实现），保留健康朴素Starter及共同预算；撤回故障Baseline支持的改善主张。
  验收：真实WorldModel零初始化、非零TD目标下的Q参数梯度及一次更新差异；同协议健康B/R完整seed结果与对应源码/模型。无需为历史轨迹重新roll。

### QA14 合法改进空间

观察判定：pass；本轮判定：pass
可研究时间限RTG校正、支持域/反事实价值目标等合法方向；Reference约0.7395仍有约127.4原始回报headroom，非饱和。
审阅依据：workspace/harbor_task/instruction.md；workspace/reference/tdmpc2/iq.py；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；workspace/harbor_task/tests/anchors.json

### QA15 评分资源需求估算

观察判定：fail；本轮判定：fail
完整单seed实测16639.7–25337.7s，task声明39600s，均超7200；Verifier gpus=0却assert CUDA。历史非H20实测如实保留，不冒称目标卡结果。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/starter/tdmpc2/train.py:47-49；optimization_evidence/hidden_20261022/README.md；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json
- 完整单seed实测16639.7–25337.7s，task声明39600s，均超7200；Verifier gpus=0却assert CUDA。历史非H20实测如实保留，不冒称目标卡结果。；处理：unwaived
  依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/starter/tdmpc2/train.py:47-49；optimization_evidence/hidden_20261022/README.md；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json
  修改方向：优化实现或重新设计满足2h的可比协议并同步全部正式锚点；Verifier按实际GPU需求声明H20/L20，不能只改时限数字。
  验收：有据完整一轮≤7200s、≤8张H20/L20、≤64CPU；有效Verifier配置满足CUDA依赖。
- 历史vGPU/4080S/4090与目标H20/L20不同，保留真实测量；只免换卡证明缺口，不免39600s及0GPU配置错误。；处理：waived
  依据：optimization_evidence/hidden_20261022/README.md；workspace/harbor_task/task.toml
  豁免原因：legacy_hardware_record_difference；依本批 format-repair-policy.md 逐原因处置：历史vGPU/4080S/4090与目标H20/L20不同，保留真实测量；只免换卡证明缺口，不免39600s及0GPU配置错误。；保留原始观察，不补造历史记录，不要求新增平台验证或历史重跑。
- 未做H20/L20当前资源实测；有据估算与旧实测已审，不要求新增目标卡认证。；处理：waived
  依据：optimization_evidence/hidden_20261022/README.md；workspace/harbor_task/task.toml
  豁免原因：legacy_target_resource_evidence_gap；依本批 format-repair-policy.md 逐原因处置：未做H20/L20当前资源实测；有据估算与旧实测已审，不要求新增目标卡认证。；保留原始观察，不补造历史记录，不要求新增平台验证或历史重跑。
- reference_hidden_seed1 完整单次评分 25334.899999999998s 超过7200s；处理：unwaived
  依据：workspace/harbor_task/task.toml；optimization_evidence/hidden_20261022/README.md；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed3/train.log
  修改方向：保持原实测，优化完整单轮或重新设计公平且≤7200s的协议；不能以自报豁免代替硬上限。
  验收：有据完整训练/重载/评分≤7200s，正式成对锚点与最终协议一致。
- reference_hidden_seed2 完整单次评分 25309.4s 超过7200s；处理：unwaived
  依据：workspace/harbor_task/task.toml；optimization_evidence/hidden_20261022/README.md；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed3/train.log
  修改方向：保持原实测，优化完整单轮或重新设计公平且≤7200s的协议；不能以自报豁免代替硬上限。
  验收：有据完整训练/重载/评分≤7200s，正式成对锚点与最终协议一致。
- reference_hidden_seed3 完整单次评分 25337.7s 超过7200s；处理：unwaived
  依据：workspace/harbor_task/task.toml；optimization_evidence/hidden_20261022/README.md；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed3/train.log
  修改方向：保持原实测，优化完整单轮或重新设计公平且≤7200s的协议；不能以自报豁免代替硬上限。
  验收：有据完整训练/重载/评分≤7200s，正式成对锚点与最终协议一致。
- reference_public_seed1 完整单次评分 24776.100000000002s 超过7200s；处理：unwaived
  依据：workspace/harbor_task/task.toml；optimization_evidence/hidden_20261022/README.md；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed3/train.log
  修改方向：保持原实测，优化完整单轮或重新设计公平且≤7200s的协议；不能以自报豁免代替硬上限。
  验收：有据完整训练/重载/评分≤7200s，正式成对锚点与最终协议一致。
- reference_public_seed2 完整单次评分 24811.5s 超过7200s；处理：unwaived
  依据：workspace/harbor_task/task.toml；optimization_evidence/hidden_20261022/README.md；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed3/train.log
  修改方向：保持原实测，优化完整单轮或重新设计公平且≤7200s的协议；不能以自报豁免代替硬上限。
  验收：有据完整训练/重载/评分≤7200s，正式成对锚点与最终协议一致。
- reference_public_seed3 完整单次评分 24760.600000000002s 超过7200s；处理：unwaived
  依据：workspace/harbor_task/task.toml；optimization_evidence/hidden_20261022/README.md；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed3/train.log
  修改方向：保持原实测，优化完整单轮或重新设计公平且≤7200s的协议；不能以自报豁免代替硬上限。
  验收：有据完整训练/重载/评分≤7200s，正式成对锚点与最终协议一致。
- starter_hidden_seed1 完整单次评分 16839.7s 超过7200s；处理：unwaived
  依据：workspace/harbor_task/task.toml；optimization_evidence/hidden_20261022/README.md；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed3/train.log
  修改方向：保持原实测，优化完整单轮或重新设计公平且≤7200s的协议；不能以自报豁免代替硬上限。
  验收：有据完整训练/重载/评分≤7200s，正式成对锚点与最终协议一致。
- starter_hidden_seed2 完整单次评分 16948.9s 超过7200s；处理：unwaived
  依据：workspace/harbor_task/task.toml；optimization_evidence/hidden_20261022/README.md；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed3/train.log
  修改方向：保持原实测，优化完整单轮或重新设计公平且≤7200s的协议；不能以自报豁免代替硬上限。
  验收：有据完整训练/重载/评分≤7200s，正式成对锚点与最终协议一致。
- starter_hidden_seed3 完整单次评分 16934.5s 超过7200s；处理：unwaived
  依据：workspace/harbor_task/task.toml；optimization_evidence/hidden_20261022/README.md；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed3/train.log
  修改方向：保持原实测，优化完整单轮或重新设计公平且≤7200s的协议；不能以自报豁免代替硬上限。
  验收：有据完整训练/重载/评分≤7200s，正式成对锚点与最终协议一致。
- starter_public_seed1 完整单次评分 16647.2s 超过7200s；处理：unwaived
  依据：workspace/harbor_task/task.toml；optimization_evidence/hidden_20261022/README.md；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed3/train.log
  修改方向：保持原实测，优化完整单轮或重新设计公平且≤7200s的协议；不能以自报豁免代替硬上限。
  验收：有据完整训练/重载/评分≤7200s，正式成对锚点与最终协议一致。
- starter_public_seed2 完整单次评分 16639.7s 超过7200s；处理：unwaived
  依据：workspace/harbor_task/task.toml；optimization_evidence/hidden_20261022/README.md；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed3/train.log
  修改方向：保持原实测，优化完整单轮或重新设计公平且≤7200s的协议；不能以自报豁免代替硬上限。
  验收：有据完整训练/重载/评分≤7200s，正式成对锚点与最终协议一致。
- starter_public_seed3 完整单次评分 16757.2s 超过7200s；处理：unwaived
  依据：workspace/harbor_task/task.toml；optimization_evidence/hidden_20261022/README.md；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed3/train.log
  修改方向：保持原实测，优化完整单轮或重新设计公平且≤7200s的协议；不能以自报豁免代替硬上限。
  验收：有据完整训练/重载/评分≤7200s，正式成对锚点与最终协议一致。
- 估算完整一轮评分耗时 39600 超过上限7200；处理：unwaived
  依据：workspace/harbor_task/task.toml；optimization_evidence/hidden_20261022/README.md；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/reference_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/reference_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/reference_public_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_hidden_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/A_hidden/starter_hidden_seed3/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed1.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed1/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed2.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed2/train.log；optimization_evidence/hidden_20261022/raw_result_json/starter_public_seed3.json；optimization_evidence/hidden_20261022/raw_train_log/B_public/starter_public_seed3/train.log
  修改方向：保持原实测，优化完整单轮或重新设计公平且≤7200s的协议；不能以自报豁免代替硬上限。
  验收：有据完整训练/重载/评分≤7200s，正式成对锚点与最终协议一致。

### QA16 轨迹实际迭代时长

观察判定：manual；本轮判定：pass_with_waivers
旧声明Sol43632s/Seed41976s，补审仅有轮次跨度：Sol36644s；Seed分段相加重复了1656s，去重为40158s；跨度未扣失败/阻塞且非有效时长，不冒充双轨已达标。
审阅依据：expert_evidence/run_summary.json；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json
- 两轨历史有效时长无法从混墙钟/跨度严格恢复，Seed跨度去重为40158s仍非有效秒数；不把旧声明改成达标。；处理：waived
  依据：expert_evidence/run_summary.json；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json
  豁免原因：legacy_research_duration_gap；依本批 format-repair-policy.md 逐原因处置：两轨历史有效时长无法从混墙钟/跨度严格恢复，Seed跨度去重为40158s仍非有效秒数；不把旧声明改成达标。；保留原始观察，不补造历史记录，不要求新增平台验证或历史重跑。

### QA17 Harbor Harness 兼容性

观察判定：fail；本轮判定：fail
由H01–H06汇总：专用Verifier构建与artifacts路径可定位，但0GPU与CUDA冲突且高权限导入候选破坏可信边界；历史NOP迁移缺口单列。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/tests/Dockerfile；expert_evidence/nop_trial/config.json
Harbor逐项派生：H01=pass；H02=fail；H03=fail；H04=fail；H05=pass_with_waivers；H06=pass_with_waivers

### QA18 轨迹、日志与分析

观察判定：fail；本轮判定：pass_with_waivers
已读Sol8轮、Seed16轮和best源码/产物；旧公开集含全部Hidden，历史分数不作新Hidden正证；无sessions不扩称行为全覆盖；六维条件对比未见确认的实质差异，历史证明缺口单列。
审阅依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md；expert_evidence/run_summary.json；expert_evidence/repair/dataset_resplit_20261021/resplit_report.json；expert_evidence/best_method/box1/artifact.json；expert_evidence/best_method/box2/artifact.json
- 模型实际身份可由best artifact交叉核对（Sol effort=max，Seed effort=high）；缺完整启动/独立空输出证明，不能确认全部历史条件相同。；处理：waived
  依据：expert_evidence/best_method/box1/artifact.json；expert_evidence/best_method/box2/artifact.json；expert_evidence/run_summary.json；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json
  豁免原因：legacy_runtime_proof_gap；依本批 format-repair-policy.md 逐原因处置：模型实际身份可由best artifact交叉核对（Sol effort=max，Seed effort=high）；缺完整启动/独立空输出证明，不能确认全部历史条件相同。；保留原始观察，不补造历史记录，不要求新增平台验证或历史重跑。
- 旧公开数据含Hidden的事实及原分数invalid保留；新正式B/R为重切后采集，不采用历史Agent分数。；处理：waived
  依据：expert_evidence/repair/dataset_resplit_20261021/resplit_report.json；expert_evidence/专家作业说明文档.md；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json
  豁免原因：historical_agent_runtime_finding；依本批 format-repair-policy.md 逐原因处置：旧公开数据含Hidden的事实及原分数invalid保留；新正式B/R为重切后采集，不采用历史Agent分数。；保留原始观察，不补造历史记录，不要求新增平台验证或历史重跑。
  原分数状态：invalid
  历史事实：leakage/confirmed；分数影响：invalid
  影响依据：污染来源为旧题公开数据包含Hidden，非推定Agent故意越权；历史Agent分数不得支持当前Hidden改善。正式B/R另有10-22六组新来源，其Baseline故障独立审判。
  受污染或未证实的Agent分数不作为作者正式 B/R 正证；仅部署规则差异不自动改写分数。
- 已实际对比现有两轨材料，旧版材料仍不足以证明所有历史条件一致；仅此记录缺口豁免，不声称已证实同条件。逐读两轨全部方法/失败/best、原过程说明和当前代码：两轨独立身份有不同模型/候选来源；未提供原Prompt或IPC/只读权限快照，也无已确认的A/B实质条件差异记录，不能声称条件完全相同。两轨均属旧100条公开数据阶段，与本轮修复不同是历史到当前迁移，不据此虚构两轨之间差异。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md；expert_evidence/run_summary.json；expert_evidence/best_method/box1/artifact.json；expert_evidence/best_method/box2/artifact.json；workspace/harbor_task/environment/public_eval/eval_dev.py
  豁免原因：legacy_runtime_proof_gap；本轮旧题迁移不要求新增Prompt快照、hash或重跑；已读资料中没有已确认的实质条件差异。

### QA19 seed 与有效提升阈值

观察判定：pass；本轮判定：pass
题面明确训练与评估随机性和Δ≥3σ_B有效提升阈值，固定seed不当作确定性。
审阅依据：workspace/harbor_task/instruction.md

### QA20 修改范围、网络与工具策略

观察判定：pass；本轮判定：pass
有实质可改/禁改范围，禁止外部数据模型答案，允许本地工具且引用平台默认策略；不依赖禁网生效。
审阅依据：workspace/harbor_task/instruction.md

### QA21 三个 JSON 的填写内容

观察判定：manual；本轮判定：pass_with_waivers
两轨八字段完整，当前四项89文件指纹与run_summary一致；旧runs中的.jsonl命名可映射实际.json，但当前hash不能追溯证明10月历史任务版本。
审阅依据：expert_evidence/run_summary.json；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/expert_annotation.json
- 当前四项指纹实算一致，但loss修复/数据重切/锚点/权限变化发生在历史轨迹之后；当前hash不是历史绑定证明。；处理：waived
  依据：expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md；expert_evidence/repair/dataset_resplit_20261021/resplit_report.json
  豁免原因：legacy_task_binding_migration；依本批 format-repair-policy.md 逐原因处置：当前四项指纹实算一致，但loss修复/数据重切/锚点/权限变化发生在历史轨迹之后；当前hash不是历史绑定证明。；保留原始观察，不补造历史记录，不要求新增平台验证或历史重跑。
- run_summary.runs仍写不存在的.jsonl；两条实际.json八字段载体可完整映射，不据旧命名要求重造轨迹。；处理：waived
  依据：expert_evidence/run_summary.json；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json
  豁免原因：legacy_trajectory_schema_gap；依本批 format-repair-policy.md 逐原因处置：run_summary.runs仍写不存在的.jsonl；两条实际.json八字段载体可完整映射，不据旧命名要求重造轨迹。；保留原始观察，不补造历史记录，不要求新增平台验证或历史重跑。

## Harbor 六项

### H01 任务目录

观察判定：pass；本轮判定：pass
任务根定位正确，公开Dev进入Agent；真实Hidden文件在专家侧，明确注入/tests/hidden_assets/dataset，历史NOP日志已实际覆盖带Hidden评分分支；当前安全注入由平台镜像准备。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/hidden_assets/README.md；expert_evidence/hidden_set/README.md；expert_evidence/hidden_set/hidden_expert.dat；expert_evidence/nop_trial/trial.log

### H02 版本与配置

观察判定：pass；本轮判定：fail
TOML可解析，artifacts在顶层、显式separate；未发现有效storage_mb、禁网/白名单或正式目录Compose。MASO配置静态对照，未加载Harbor schema。
审阅依据：workspace/harbor_task/task.toml
- 当前格式实质问题（来自 F06）：显式separate和单容器成立，但Verifier配置0GPU，实际train.py断言CUDA且TDMPC2强制cuda，当前资源配置不满足运行需求。
  定位：workspace/harbor_task/task.toml；workspace/harbor_task/environment/starter/tdmpc2/train.py:47-49；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:61-64

### H03 环境与运行路径

观察判定：fail；本轮判定：fail
Agent/Verifier各自单容器调用本地程序，无任务部署额外工作环境；专用tests构建预置入口。但Verifier申请0GPU而代码强制CUDA，且root父进程导入候选模型破坏可信冻结面。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/environment/starter/tdmpc2/train.py；workspace/harbor_task/tests/test.sh
- Agent/Verifier各自单容器调用本地程序，无任务部署额外工作环境；专用tests构建预置入口。但Verifier申请0GPU而代码强制CUDA，且root父进程导入候选模型破坏可信冻结面。；处理：unwaived
  依据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/environment/starter/tdmpc2/train.py；workspace/harbor_task/tests/test.sh
  修改方向：修正Verifier为实际需要的H20/L20 GPU；所有候选训练和推理以受限权限执行，可信评分单独保留。
  验收：有效资源与CUDA需求一致，可信进程不导入候选代码；路径/Hidden/移交静态链一致。
- 基础镜像bash/解释器静态未仿真，内部tag及当前启动交平台；有效构建方案已存在。当前0GPU及权限问题另外保留FAIL。；处理：waived
  依据：workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/environment/Dockerfile；expert_evidence/nop_trial/README.md
  豁免原因：platform_execution_verification_pending；依本批 format-repair-policy.md 逐原因处置：基础镜像bash/解释器静态未仿真，内部tag及当前启动交平台；有效构建方案已存在。当前0GPU及权限问题另外保留FAIL。；保留原始观察，不补造历史记录，不要求新增平台验证或历史重跑。

### H04 测试入口与 reward

观察判定：pass；本轮判定：fail
/tests/test.sh到evaluate_verify的参数和路径一致；成功reward.json仅有限数值，JSON优先语义明确；reward.txt主数值同步。
审阅依据：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/evaluate_verify.py:537-557
- 当前格式实质问题（来自 F07）：真实零初始化Q与预测端symlog导致Baseline仍无Q学习梯度；root父进程导入候选代码使可信冻结面保护失效。
  定位：workspace/harbor_task/environment/starter/tdmpc2/common/math.py:5-29；workspace/harbor_task/environment/starter/tdmpc2/common/math.py:71-77；workspace/harbor_task/environment/starter/tdmpc2/common/world_model.py:30-34；workspace/harbor_task/environment/starter/tdmpc2/common/init.py:4-22；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:293-312；expert_evidence/repair/value_loss_ablation/README.md；expert_evidence/repair/value_loss_ablation/ablation_fixed.json；workspace/harbor_task/tests/evaluate_verify.py:205-245；workspace/harbor_task/tests/Dockerfile

### H05 Job/Trial 调用配置

观察判定：manual；本轮判定：pass_with_waivers
已有专家Docker NOP配置及字段映射，不能冒充平台原生Job；历史镜像选择可定位，当前内场镜像tag/启动由平台准备。
审阅依据：expert_evidence/nop_trial/config.json；expert_evidence/nop_trial/nop_trial.sh；expert_evidence/nop_trial/README.md
- 已有专家侧Docker顺序链路不能代替平台原生Job当前启动；原配置路径与separate已审，不要求为缺平台运行记录返修。；处理：waived
  依据：expert_evidence/nop_trial/config.json；expert_evidence/nop_trial/nop_trial.sh
  豁免原因：platform_execution_verification_pending；依本批 format-repair-policy.md 逐原因处置：已有专家侧Docker顺序链路不能代替平台原生Job当前启动；原配置路径与separate已审，不要求为缺平台运行记录返修。；保留原始观察，不补造历史记录，不要求新增平台验证或历史重跑。

### H06 NOP 自检记录

观察判定：manual；本轮判定：pass_with_waivers
同Trial两处nop、separate、结束时间、无异常、非空日志；唯一正式reward.txt=-0.000234与result一致。3397步/2回合历史分支确有训练评分；当前返修权限、损失和锚点已变化，不能称当前版本成功。
审阅依据：expert_evidence/nop_trial/config.json；expert_evidence/nop_trial/result.json；expert_evidence/nop_trial/verifier/reward.txt；expert_evidence/nop_trial/trial.log；expert_evidence/nop_trial/verifier/test-stdout.txt；expert_evidence/nop_trial/verifier/reward_full.json
- 已有10-08 NOP确有3397步训练和2回合评测，但早于损失/权限/锚点整改；当前版本未重跑。reward.txt与result一致，reward_full只是诊断，未伪称当前成功。；处理：waived
  依据：expert_evidence/nop_trial/config.json；expert_evidence/nop_trial/result.json；expert_evidence/nop_trial/trial.log；expert_evidence/nop_trial/verifier/reward.txt；expert_evidence/nop_trial/verifier/reward_full.json；expert_evidence/专家作业说明文档.md
  豁免原因：legacy_nop_or_current_trial_gap；依本批 format-repair-policy.md 逐原因处置：已有10-08 NOP确有3397步训练和2回合评测，但早于损失/权限/锚点整改；当前版本未重跑。reward.txt与result一致，reward_full只是诊断，未伪称当前成功。；保留原始观察，不补造历史记录，不要求新增平台验证或历史重跑。

## 两轨已有内容

### T01 第一条轨迹已有内容

观察判定：fail；本轮判定：pass_with_waivers
8轮依次尝试continuation支持、反事实校准、planner残差、支持核、IQ目标、势函数、残差校准、保守间隔；R7评分失败，其余7轮出分；真实最佳R2。
审阅依据：expert_evidence/trajectory_codex.json；expert_evidence/专家作业说明文档.md；expert_evidence/best_method/box1/artifact.json；expert_evidence/repair/dataset_resplit_20261021/resplit_report.json
方法：8轮依次尝试continuation支持、反事实校准、planner残差、支持核、IQ目标、势函数、残差校准、保守间隔；R7评分失败，其余7轮出分；真实最佳R2。 历史Dev最佳R2=85.168；不作为当前新切分Hidden泛化或作者正式B/R证据。
迭代内容：8轮依次尝试continuation支持、反事实校准、planner残差、支持核、IQ目标、势函数、残差校准、保守间隔；R7评分失败，其余7轮出分；真实最佳R2。
最终结果：历史Dev最佳R2=85.168；不作为当前新切分Hidden泛化或作者正式B/R证据。
分数采用范围：原Dev测量保留历史数值；旧公开集污染且任务已修复，invalid用于当前Hidden/正式改善主张；不因迁移豁免变为有效正式成绩。
已读来源：expert_evidence/trajectory_codex.json；expert_evidence/专家作业说明文档.md；expert_evidence/run_summary.json；expert_evidence/best_method/box1/artifact.json；expert_evidence/best_method/box1/tdmpc2/tdmpc2.py；expert_evidence/best_method/official_revalidation_20261007.json
- 旧公开数据含Hidden的事实及原分数invalid保留；新正式B/R为重切后采集，不采用历史Agent分数。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/repair/dataset_resplit_20261021/resplit_report.json；expert_evidence/专家作业说明文档.md
  豁免原因：historical_agent_runtime_finding；依本批 format-repair-policy.md 逐原因处置：旧公开数据含Hidden的事实及原分数invalid保留；新正式B/R为重切后采集，不采用历史Agent分数。；保留原始观察，不补造历史记录，不要求新增平台验证或历史重跑。
  原分数状态：invalid
  历史事实：leakage/confirmed；分数影响：invalid
  影响依据：污染来源为旧题公开数据包含Hidden，非推定Agent故意越权；历史Agent分数不得支持当前Hidden改善。正式B/R另有10-22六组新来源，其Baseline故障独立审判。
  受污染或未证实的Agent分数不作为作者正式 B/R 正证；仅部署规则差异不自动改写分数。
- 模型实际身份可由best artifact交叉核对（Sol effort=max，Seed effort=high）；缺完整启动/独立空输出证明，不能确认全部历史条件相同。；处理：waived
  依据：expert_evidence/best_method/box1/artifact.json；expert_evidence/best_method/box2/artifact.json；expert_evidence/run_summary.json；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json
  豁免原因：legacy_runtime_proof_gap；依本批 format-repair-policy.md 逐原因处置：模型实际身份可由best artifact交叉核对（Sol effort=max，Seed effort=high）；缺完整启动/独立空输出证明，不能确认全部历史条件相同。；保留原始观察，不补造历史记录，不要求新增平台验证或历史重跑。

### T02 第二条轨迹已有内容

观察判定：fail；本轮判定：pass_with_waivers
16条跨4次编排：早期RTG/latent rollout与expectile方向失败或无代码改动；R12首次出分；R14分布式Q+RTG+BC最佳，R15 CQL与R16全回合RTG均未超过。4轮出分、12失败；旧声明7有效轮不等于7成功轮。
审阅依据：expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md；expert_evidence/best_method/box2/artifact.json；expert_evidence/repair/dataset_resplit_20261021/resplit_report.json
方法：16条跨4次编排：早期RTG/latent rollout与expectile方向失败或无代码改动；R12首次出分；R14分布式Q+RTG+BC最佳，R15 CQL与R16全回合RTG均未超过。4轮出分、12失败；旧声明7有效轮不等于7成功轮。 历史Dev最佳R14=12.2079；不作为当前新切分Hidden泛化或作者正式B/R证据。
迭代内容：16条跨4次编排：早期RTG/latent rollout与expectile方向失败或无代码改动；R12首次出分；R14分布式Q+RTG+BC最佳，R15 CQL与R16全回合RTG均未超过。4轮出分、12失败；旧声明7有效轮不等于7成功轮。
最终结果：历史Dev最佳R14=12.2079；不作为当前新切分Hidden泛化或作者正式B/R证据。
分数采用范围：原Dev测量保留历史数值；旧公开集污染且任务已修复，invalid用于当前Hidden/正式改善主张；不因迁移豁免变为有效正式成绩。
已读来源：expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md；expert_evidence/run_summary.json；expert_evidence/best_method/box2/artifact.json；expert_evidence/best_method/box2/tdmpc2/tdmpc2.py；expert_evidence/best_method/official_revalidation_20261007.json
- 旧公开数据含Hidden的事实及原分数invalid保留；新正式B/R为重切后采集，不采用历史Agent分数。；处理：waived
  依据：expert_evidence/trajectory_seed.json；expert_evidence/repair/dataset_resplit_20261021/resplit_report.json；expert_evidence/专家作业说明文档.md
  豁免原因：historical_agent_runtime_finding；依本批 format-repair-policy.md 逐原因处置：旧公开数据含Hidden的事实及原分数invalid保留；新正式B/R为重切后采集，不采用历史Agent分数。；保留原始观察，不补造历史记录，不要求新增平台验证或历史重跑。
  原分数状态：invalid
  历史事实：leakage/confirmed；分数影响：invalid
  影响依据：污染来源为旧题公开数据包含Hidden，非推定Agent故意越权；历史Agent分数不得支持当前Hidden改善。正式B/R另有10-22六组新来源，其Baseline故障独立审判。
  受污染或未证实的Agent分数不作为作者正式 B/R 正证；仅部署规则差异不自动改写分数。
- 模型实际身份可由best artifact交叉核对（Sol effort=max，Seed effort=high）；缺完整启动/独立空输出证明，不能确认全部历史条件相同。；处理：waived
  依据：expert_evidence/best_method/box1/artifact.json；expert_evidence/best_method/box2/artifact.json；expert_evidence/run_summary.json；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json
  豁免原因：legacy_runtime_proof_gap；依本批 format-repair-policy.md 逐原因处置：模型实际身份可由best artifact交叉核对（Sol effort=max，Seed effort=high）；缺完整启动/独立空输出证明，不能确认全部历史条件相同。；保留原始观察，不补造历史记录，不要求新增平台验证或历史重跑。

## 两轨实际条件对比

对比已完成：是
条件判断：historical_evidence_gap；成对对照有效性：unverified
逐读两轨全部方法/失败/best、原过程说明和当前代码：两轨独立身份有不同模型/候选来源；未提供原Prompt或IPC/只读权限快照，也无已确认的A/B实质条件差异记录，不能声称条件完全相同。两轨均属旧100条公开数据阶段，与本轮修复不同是历史到当前迁移，不据此虚构两轨之间差异。
已对比维度：prompt、task、dev、feedback、constraints、resources
对比依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md；expert_evidence/run_summary.json；expert_evidence/best_method/box1/artifact.json；expert_evidence/best_method/box2/artifact.json；workspace/harbor_task/environment/public_eval/eval_dev.py
质检员内部对比底稿；不要求专家新增字段、Prompt快照、hash或重跑。语义判断须实际阅读原材料，脚本只核验审阅覆盖及判定一致性。
- prompt / legacy_format_or_resource：没有原两次启动Prompt全文；两份轮次均属Hopper-Hop critic目标题，未见确认不同任务规则。
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md；expert_evidence/run_summary.json
- task / legacy_format_or_resource：当前修复了数据、损失与在线措辞；两轨均早于修复，不能用当前指纹倒证历史相同。
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md；expert_evidence/run_summary.json
- dev / legacy_format_or_resource：best artifacts均声明30000步/seed1/10回合；旧数据100条；完整两份Dev快照未交。
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md；expert_evidence/run_summary.json
- feedback / legacy_format_or_resource：两轨均有eval退出或无改动反馈，未交原编排反馈模板，不能确认完全等价，也无实质差异证据。
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md；expert_evidence/run_summary.json
- constraints / legacy_format_or_resource：原IPC/只读/允许改动快照未交；未发现已交材料宣称两轨授予不同权限。
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md；expert_evidence/run_summary.json
- resources / legacy_format_or_resource：两轨历史资源未逐轨完整记录；best复验在3080Ti，80核是主机规格并非申请配额；保留证明范围，不声称资源完全相同。
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md；expert_evidence/run_summary.json

## 当前格式前检 F01–F07（子检查）

format_decision：FAIL
以下仅为当前格式子检查；整题结论以本报告顶部完整质检结果为准。

- F01 [pass] 当前必需目录、文件与 TOML 接口：三目录与必需任务文件、TOML环境/独立Verifier接口可定位。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md
- F02 [pass] 有效构建或镜像方案、构建上下文及 COPY 来源：两套本地Dockerfile/context与COPY来源一致；内部镜像准备属平台后续。
  格式审阅依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile
- F03 [pass] 评分入口、独立依赖声明与固定输出路径：专用Verifier预置/test.sh评分入口、独立依赖与固定reward路径齐全；运行资源错误另列F06/H03。
  格式审阅依据：workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/evaluate_verify.py
- F04 [pass] 提交物 artifacts 移交契约：顶层artifacts整体移交/workspace/solution，与test.sh读取一致。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/test.sh
- F05 [pass] 公开 Dev、私有 Hidden 供给与 Agent 隔离：公开66条已进Agent，Hidden真实资产私留专家侧并有明确安全注入路径及已有NOP分支证据。
  格式审阅依据：workspace/harbor_task/environment/Dockerfile；expert_evidence/hidden_set/README.md；expert_evidence/nop_trial/trial.log；expert_evidence/repair/dataset_resplit_20261021/resplit_report.json
- F06 [fail] separate、单容器、无 Compose 与当前目标资源配置：显式separate和单容器成立，但Verifier配置0GPU，实际train.py断言CUDA且TDMPC2强制cuda，当前资源配置不满足运行需求。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/starter/tdmpc2/train.py:47-49；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:61-64
  修改方向：修复实际CUDA资源配置、健康Q更新和候选推理权限边界，保持题面/协议一致。
  验收：相应源码/配置静态链闭合；真实零初始化Q梯度控制及健康正式B/R。
- F07 [fail] 当前评分实现与冻结面无确证故障或作者泄漏造假：真实零初始化Q与预测端symlog导致Baseline仍无Q学习梯度；root父进程导入候选代码使可信冻结面保护失效。
  格式审阅依据：workspace/harbor_task/environment/starter/tdmpc2/common/math.py:5-29；workspace/harbor_task/environment/starter/tdmpc2/common/math.py:71-77；workspace/harbor_task/environment/starter/tdmpc2/common/world_model.py:30-34；workspace/harbor_task/environment/starter/tdmpc2/common/init.py:4-22；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:293-312；expert_evidence/repair/value_loss_ablation/README.md；expert_evidence/repair/value_loss_ablation/ablation_fixed.json；workspace/harbor_task/tests/evaluate_verify.py:205-245；workspace/harbor_task/tests/Dockerfile
  修改方向：修复实际CUDA资源配置、健康Q更新和候选推理权限边界，保持题面/协议一致。
  验收：相应源码/配置静态链闭合；真实零初始化Q梯度控制及健康正式B/R。

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
NOP：{"status": "pass", "runtime_status": "evidence_consistent", "trials": [{"trial_dir": "expert_evidence/nop_trial", "evidence": ["expert_evidence/nop_trial/config.json", "expert_evidence/nop_trial/result.json", "expert_evidence/nop_trial/verifier/reward.txt", "expert_evidence/nop_trial/trial.log", "expert_evidence/nop_trial/verifier/test-stdout.txt"], "details": {"trial_dir": "expert_evidence/nop_trial", "agent": "nop", "verifier_environment_mode": "separate", "rewards": {"reward": -0.000234}, "task_binding": {"status": "pass", "basis": "reviewed_evidence", "evidence": ["expert_evidence/nop_trial/config.json", "expert_evidence/nop_trial/README.md", "expert_evidence/nop_trial/trial.log"], "summary": "历史Docker NOP为harbor_task v1.0.0，config映射和日志关联；10-08旧协议3397步/2回合，与当前锚点/权限/损失修复版本不同，只作历史运行分支证据。", "authenticity_verified": false}}, "status": "pass", "summary": "已有 NOP 的同次 Trial、Agent、separate、sandbox 反证、结束与异常、reward 数值和非空日志已按原校验器核查。"}], "summary": "逐份读取并校验已有 NOP 记录；未启动新的 Trial。"}

原报告与全部详细结果：standard/report.json；不因豁免覆盖原判。

| 来源 | 项目 | 原判 | 本轮处理 | 依据及原因 |
|---|---|---|---|---|
| gates/G02 | G02 | fail | fail | Q头末层权重和偏置均为0；soft_ce_scalar对预测值应用sign×log(1+abs)，零点计算图梯度为0，Q无法启动学习。真实Ensemble消融fixed仍q_grad=0；随机线性头控制不能排除此故障。 |
| gates/G03 | G03 | fail | fail | 全部成对数值算术达标，但正式Baseline存在Q零梯度静态故障，三组B均不能作健康对照；大幅提升不能消除此质量门失败。；重算核验：质量门有效性未满足；seed 1 的 baseline_valid 为 false；seed 2 的 baseline_valid 为 false；seed 3 的 baseline_valid 为 false |
| checks/QA03 | QA03 | manual | pass_with_waivers | Reference三seed正式结果和非空日志、模型SHA齐全，原始归一化约0.73954；新增独立reload标NOT_RUN，但当次run_one已有训练后eval_agent加载，不伪造补验。 |
| checks/QA05 | QA05 | fail | fail | 环境文件有hash门禁，但题面固定的plan/_estimate_value_iq与config分支未恢复或校验；build_eval_cfg直接读取候选config并导入候选TDMPC2，固定评测边界可被改动。 |
| checks/QA10 | QA10 | fail | fail | 训练子进程虽降权，eval_agent在test.sh的root评分父进程中import候选tdmpc2/common并调用构造、load和act；候选代码因此取得可信文件属主权限，a-w不能保护冻结面。 |
| checks/QA11 | QA11 | fail | fail | 题面称评测固定30回合，默认Dev入口实际10回合/30000步并自称与Hidden同协议；正式run_one的eval seed_offset=1000，而正式评分1000+seed，协议说明应区分。 |
| checks/QA13 | QA13 | fail | fail | 六组正式Hidden原值、训练及模型均存在，但Baseline仍有零梯度故障；不能用当前B证明健康方法差异，旧被作废数字不参与。 |
| checks/QA15 | QA15 | fail | fail | reference_hidden_seed1 完整单次评分 25334.899999999998s 超过7200s；reference_hidden_seed2 完整单次评分 25309.4s 超过7200s；reference_hidden_seed3 完整单次评分 25337.7s 超过7200s；reference_public_seed1 完整单次评分 24776.100000000002s 超过7200s；reference_ |
| checks/QA16 | QA16 | manual | pass_with_waivers | Codex + GPT-5.6 Sol缺少有效时长或排除排队/安装/故障的核算证据；Codex + Seed 2.1 Turbo缺少有效时长或排除排队/安装/故障的核算证据 |
| checks/QA17 | QA17 | fail | derived_from_details | Harbor 子项未通过：H03 环境与运行路径；H05 Job/Trial 调用配置；H06 NOP 自检记录；详细原因与证据保留在 report.json。 |
| checks/QA18 | QA18 | fail | pass_with_waivers | 已读Sol8轮、Seed16轮和best源码/产物；旧公开集含全部Hidden，历史分数不作新Hidden正证；无sessions不扩称行为全覆盖；六维条件对比未见确认的实质差异，历史证明缺口单列。 |
| checks/QA21 | QA21 | manual | pass_with_waivers | 两轨八字段完整，当前四项89文件指纹与run_summary一致；旧runs中的.jsonl命名可映射实际.json，但当前hash不能追溯证明10月历史任务版本。 |
| harbor/H03 | H03 | fail | fail | Agent/Verifier各自单容器调用本地程序，无任务部署额外工作环境；专用tests构建预置入口。但Verifier申请0GPU而代码强制CUDA，且root父进程导入候选模型破坏可信冻结面。 |
| harbor/H05 | H05 | manual | pass_with_waivers | 已有专家Docker NOP配置及字段映射，不能冒充平台原生Job；历史镜像选择可定位，当前内场镜像tag/启动由平台准备。 |
| harbor/H06 | H06 | manual | derived_from_details | 同Trial两处nop、separate、结束时间、无异常、非空日志；唯一正式reward.txt=-0.000234与result一致。3397步/2回合历史分支确有训练评分；当前返修权限、损失和锚点已变化，不能称当前版本成功。 |
| harbor/path_contract/1 | H03 | manual | pass_with_waivers | 基础镜像 nvidia/cuda:11.8.0-cudnn8-devel-ubuntu20.04 的 bash/解释器不可由当前声明确认；需补充镜像说明、依赖声明或已有运行证据。静态文件映射不能证明运行成功。 |
| resources/problems/0 | QA15 | fail | fail | reference_hidden_seed1 完整单次评分 25334.899999999998s 超过7200s |
| resources/problems/1 | QA15 | fail | fail | reference_hidden_seed2 完整单次评分 25309.4s 超过7200s |
| resources/problems/2 | QA15 | fail | fail | reference_hidden_seed3 完整单次评分 25337.7s 超过7200s |
| resources/problems/3 | QA15 | fail | fail | reference_public_seed1 完整单次评分 24776.100000000002s 超过7200s |
| resources/problems/4 | QA15 | fail | fail | reference_public_seed2 完整单次评分 24811.5s 超过7200s |
| resources/problems/5 | QA15 | fail | fail | reference_public_seed3 完整单次评分 24760.600000000002s 超过7200s |
| resources/problems/6 | QA15 | fail | fail | starter_hidden_seed1 完整单次评分 16839.7s 超过7200s |
| resources/problems/7 | QA15 | fail | fail | starter_hidden_seed2 完整单次评分 16948.9s 超过7200s |
| resources/problems/8 | QA15 | fail | fail | starter_hidden_seed3 完整单次评分 16934.5s 超过7200s |
| resources/problems/9 | QA15 | fail | fail | starter_public_seed1 完整单次评分 16647.2s 超过7200s |
| resources/problems/10 | QA15 | fail | fail | starter_public_seed2 完整单次评分 16639.7s 超过7200s |
| resources/problems/11 | QA15 | fail | fail | starter_public_seed3 完整单次评分 16757.2s 超过7200s |
| resources/problems/12 | QA15 | fail | fail | 估算完整一轮评分耗时 39600 超过上限7200 |
| resources/gaps/0 | QA15 | manual | pass_with_waivers | 当前成绩的硬件归属/换卡影响尚未确认 |
| trajectory/0/finding/0 | QA18 | fail | pass_with_waivers | 历史研究时公开100条数据含34条Hidden（已由重切报告确认）；这属于旧题公开集污染，不推断Agent主动越权；原Dev数值留档，不能支持当前未见Hidden。 |
| trajectory/1/finding/0 | QA18 | fail | pass_with_waivers | 历史研究时公开100条数据含34条Hidden（已由重切报告确认）；这属于旧题公开集污染，不推断Agent主动越权；原Dev数值留档，不能支持当前未见Hidden。 |
