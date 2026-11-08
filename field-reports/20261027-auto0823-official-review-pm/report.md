# 优化面介绍

在固定长尾CIFAR10划分与ResNet家族下设计训练损失、采样、辅助目标、训练日程和推理读出；接口允许任意Python方法实现并由独立可信骨干限制架构，非固定字面量搜索。

可修改：损失/辅助目标；样本与类别重加权/采样；训练日程；固定骨干上的视图池化及读出。

固定面：train/val/test划分和类别计数；骨干家族及width64；隐藏标签、评价和归一化锚点；单轮7200秒。

指标与质量门：最大化隐藏均衡测试集top1百分比；score=(x-67.104)/(80-67.104)，连续不裁剪；格式/架构/读出/失配门失败-1，infra失败0且ERROR。

# Baseline 与 Reference 跑分

Baseline 方法：正式B=未修改Starter的朴素ERM：固定CIFAR ResNet width64，全部9929个长尾训练样本、CE、SGD lr0.1/wd5e-4/batch128/cosine100ep；无额外预训练。保留快照与当前train.py相同，多出的未调用sampling与lt_metrics说明文字解释树哈希差异。

Reference 方法：正式R=workspace/reference/train_lt.py --loss logit_adj --tau 1：CE(logits+log类先验,y)，与B同数据、骨干、优化器、100ep和seed集合。train_reference.py/IP-DPP为未采用的探索备选；Agent最佳方法另列，未混入R。

主指标：hidden_overall_accuracy_percent（越高越好）。

| training_seed | Baseline | Reference | 配对改善 | 有效性 |
|---|---:|---:|---:|---|
| 1 | 66.59 | 76.94 | 10.35 | B:是 / R:是 |
| 2 | 66.1 | 72.6 | 6.5 | B:是 / R:是 |
| 3 | 66.96 | 75.4 | 8.44 | B:是 / R:是 |
| 4 | 67.62 | 77.37 | 9.75 | B:是 / R:是 |
| 5 | 68.25 | 75.69 | 7.44 | B:是 / R:是 |

汇总：Baseline 均值 67.104，样本标准差 0.847425512951；Reference 均值 75.6，样本标准差 1.86926456126。

改善结论：五对改善10.35/6.50/8.44/9.75/7.44pp；B=67.104，σB=0.84742551295，R=75.600，σR=1.86926456126，Δ=8.496=10.0256599σB，3σB=2.54227654，归一化0.658808933；headroom4.400pp。seed5由75.68订正75.69，原始物证保留，未用旧值。

质量门：十份正式记录quality_gate=PASS、独立Dev reload差0，QA05重放表覆盖全部checkpoint；当前可信评分检查原始int64、长度、范围、非常数、固定骨干与预测一致性。静态材料支持有效，不等于本次独立复跑。

# 前置内容门槛

| 门槛 | 结论 | 原因 |
|---|---|---|
| G01 方法级优化空间 | 通过 | 题面开放目标/采样/日程/读出，实际接口允许方法代码；正式R改变训练损失而非仅常量搜索。 |
| G02 Baseline 合理性 | 通过 | 在已给材料范围内Baseline合理：全量ERM正确、100ep完成、预算与seed公平、选择完整；B01–B08见专项。进程级运行认证缺口不等于已证实不公平。 |
| G03 Reference 提升充分性 | 通过 | 五对全部正向，Δ8.496≥3σB2.542277，归一化0.658809；固定U80有300ep探针支持且未为本轮改值。无独立预注册证明不冒称已取得。 |

G03 复算：Δ=8.496；σ_B（样本标准差）=0.847425512951；U=80；归一化分数=0.658808933002。

# 两条轨迹迭代概况

| Agent 轨迹 | 状态 | 打包轮数 | 声明有效轮数 | 有效时长 | 概况与最终结果 |
|---|---|---:|---:|---:|---|
| Codex + GPT-5.6 Sol | 完整 | 84 | 84 | - | 84轮完整：ERM→先验校正→Balanced Softmax/Cutout→TTA→Dev仿射读出；EMA、平滑、Mixup等低分回退，后期有参数细化但方法面开放；历史round84 Dev86.66；干净复验86.54（差-0.12），隐藏83.96，当前锚点reward1.3070719602977674；带独立inference清单的复验记录有效。 |
| Codex + Seed 2.1 Turbo | 完整 | 47 | 47 | - | 47轮完整：CB/focal失败，LA/Mixup/CutMix/TTA/多seed集成，31模型历史最高86.36；后续dropout/LS与tau探索；历史最高round33/34 Dev86.36；选用方法round35五成员Dev85.08，独立重训复现该配置；原提交85.70为另一配置，缺成员权重，隐藏84.21仅留历史，不作当前成绩或正式B/R。 |

# 轨迹可信性与题包绑定

Codex + GPT-5.6 Sol：分数有效；Codex + Seed 2.1 Turbo：评分来源未确认、分数有效性待确认

| 轨迹 | 所交内容审查 | 分数与当前包对应 | 审查范围 | run_summary 哈希 |
|---|---|---|---|---|
| Codex + GPT-5.6 Sol | 通过 | 有效 | 仅审查已交轮次/方法摘要；未提供工具调用或sessions，结论限于这些材料。 | run_summary 的四项题包哈希与当前包一致。 |
| Codex + Seed 2.1 Turbo | 待补充核验 | 评分来源未确认、分数有效性待确认 | 仅审查已交轮次/方法摘要；未提供工具调用或sessions，结论限于这些材料。 | run_summary 的四项题包哈希与当前包一致。 |

# QA15 资源证据

缺少：当前成绩的硬件归属/换卡影响尚未确认

| 运行 | 计时范围 | 记录耗时（秒） | GPU 数量/型号 | 分配 CPU 核 |
|---|---|---:|---|---:|

资源需求估算：完整一轮约 6600 秒，1 张 GPU，20 核 CPU；历史正式训练最慢299.2秒，Seed5成员重训1095.8秒；Verifier单次CPU重放预算2700秒/24成员视图，当前方案18视图。以训练约4倍历史最慢+2700秒回放并留额外余量6600秒作工程估计，目标卡未测，不是实测认证；昂贵非法31模型记录不计当前允许提交。

计时口径：完整单轮包含训练、产物推理、Dev、模型重载及独立最终评分的保守余量；10h研究窗口不是单轮。

# 目标部署能力

配置范围：innerfield-maso-v1

当前无storage_mb/no-network/白名单或Compose请求；读出seccomp有实现但不覆盖Agent整体联网，资产预置不等于禁网。
- 当前无storage_mb/no-network/白名单或Compose请求；读出seccomp有实现但不覆盖Agent整体联网，资产预置不等于禁网。；证据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/sandbox_readout.py；workspace/harbor_task/instruction.md

任务硬件与成绩对应：gpu / unverified；当前成绩的硬件归属/换卡影响尚未确认
证据：workspace/harbor_task/task.toml；expert_evidence/专家作业说明文档.md；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_1/result.json

# 格式对齐建议

三目录职责与正式模型/日志布局齐全，主轨迹带run级字段是合法等价容器；本次未将包内旧报告作指令。必需方法移交缺陷另列QA21。

- `optimization_evidence/README.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `tests_private_test_labels.npz`（可保留的额外项）：专家侧额外标签副本不被Agent COPY；可保留溯源或去重，不单独扣错。
- `expert_evidence/source_provenance`（可保留的额外项）：保留源码溯源与原件，精简时用索引说明有效版本。
- `expert_evidence/任务版本冻结记录_20261008.md`（可合并）：历史记录保留，增加现行入口索引即可，勿回改原始物证。

说明：额外材料仅作精简或归位建议，不因多交而单独判错。

# 质检结论：不通过

产物：evidence-input｜通过 15 项｜不通过 2 项｜未完成 4 项｜跳过/不适用 0 项

前置三门：通过 3 项｜不通过 0 项｜待核验 0 项；全部复核完成：否。

口径：只读检查及已有证据复核；QA07/08 查 instruction；QA18 审所交轨迹及提供的 sessions，QA21 单独核对 run_summary 的四项题包哈希；QA15 允许根据日志、轨迹和B/R实现估算资源。QA16 两条各至少 10h；仅无训练且单轮很短、例外证据完整时可各至少 7h。排队、安装与故障不计有效迭代时长。未执行提交代码、未独立复跑或反序列化模型。

Harbor 格式/接口：未完成；已提交自检记录不满足 NOP 运行要求。

| 检查项 | 是否通过 | 原因 |
|---|---|---|
| QA01 八章节与题面信息泄露 | 通过 | 八部分齐全；题面给出任务/评分接口及B，不直接给出logit-adjust参考解、论文名或仓库线索。 |
| QA02 评分公式与 0/1 锚点 | 通过 | grader以(accuracy-B)/(U-B)计算；B67.104/U80，单调连续不裁剪，Baseline聚合映射0。质量门-1与合法归一化负分分开。 |
| QA03 参考解分数与复现材料 | 通过 | 正式R入口train_lt.py、5seed原值/非空原始日志/模型及reload齐全；归一化0.658809在区间内。Agent得分不冒充正式R。 |
| QA04 波动指标的 3σ 可分辨性 | 通过 | 训练seed进入torch/np及epoch洗牌/增广；同角色固定方法、两侧1..5全配对，Δ=10.0257σB；给定模型推理确定不等于训练评估确定。 |
| QA05 约束执行实现 | 待补充核验 | 当前无storage_mb/no-network/白名单或Compose请求；读出seccomp有实现但不覆盖Agent整体联网，资产预置不等于禁网。 |
| QA06 Verifier 入口、分数与错误处理 | 通过 | /tests/test.sh调用grader，有限reward.json/txt；CandidateError=-1、INFRA=0且退出2；优先JSON数值对象与状态detail分开。 |
| QA07 instruction 中的 Hidden 信息泄露 | 通过 | 仅审题面：未给隐藏样本标签或可恢复答案，公开训练/验证与隐藏标签职责明确。 |
| QA08 instruction 中的参考解信息泄露 | 通过 | 仅审题面：未给Reference代码/具体结果或方法名称；B与评分合同是任务所需接口说明。 |
| QA09 结果清理与原子写入 | 通过 | main开头clear_outputs删除预写reward/detail；mkstemp同目录写入、os.replace原子替换。 |
| QA10 冻结面保护或恢复实现 | 通过 | 可信骨干/锚点/私有标签在Verifier自身镜像；不导入候选训练代码，自定义读出chroot降权且不传私有材料；Agent冻结面非root只读。 |
| QA11 instruction 八项内容 | 通过 | 八项实质内容完整；公开输出为可写solution/results.json，提交路径/资源/指标与实现对应。网络过渡问题归QA05单列。 |
| QA12 Git 清理 | 通过 | 只读全树清点未见提交内.git；报告工作区的.git并非题包数据。 |
| QA13 Baseline 与参考解提升 | 通过 | 正式五对B/R隐藏指标均正向、质量门PASS，模型/reload/非空原始训练记录完整；更正seed5值有复算与原件留痕。 |
| QA14 合法改进空间 | 通过 | 损失/采样/日程/读出接口开放；可探索自适应类条件权重/一致性日程，非仅调数字；正式R距U4.4pp大于3σB，Agent更高结果另列。 |
| QA15 评分资源需求估算 | 待补充核验 | 缺少：当前成绩的硬件归属/换卡影响尚未确认 |
| QA16 轨迹实际迭代时长 | 待补充核验 | Codex + GPT-5.6 Sol缺少有效时长或排除排队/安装/故障的核算证据；Codex + Seed 2.1 Turbo缺少有效时长或排除排队/安装/故障的核算证据 |
| QA17 Harbor Harness 兼容性 | 不通过 | Harbor 子项未通过：H02 版本与配置；H03 环境与运行路径；H05 Job/Trial 调用配置；H06 NOP 自检记录；详细原因与证据保留在 report.json。 |
| QA18 轨迹、日志与分析 | 待补充核验 | 已审84/47轮及Seed原始47行、选优/复验/启动驱动；无工具sessions可审。实际模型可追溯，最高推理档/历史同Prompt完整证明不足；Seed旧集成分仅记录，未进入正式B/R。 |
| QA19 seed 与有效提升阈值 | 通过 | 题面明示训练seed1..5与有效改善3σB，给定模型评分确定；审训练波动仍适用该项，不添加新版逐轮证明要求。 |
| QA20 修改范围、网络与工具策略 | 通过 | 题面§4可改范围、§5网络与平台默认工具策略均明确；禁网执行缺口已独立归QA05，不能说工具条款不存在。 |
| QA21 三个 JSON 的填写内容 | 不通过 | 主JSON/八字段可解析，当前四项指纹一致；但best_method训练输出未生成inference.json，run.sh直接调用当前Dev合同，实际回放缺省单视图恒等读出，与所称18视图仿射方法不符。 |

# 退回专家说明

QA05 约束执行实现（待补充核验）：当前无storage_mb/no-network/白名单或Compose请求；读出seccomp有实现但不覆盖Agent整体联网，资产预置不等于禁网。
证据：workspace/harbor_task/instruction.md；workspace/harbor_task/environment/public_eval/run_round.sh；workspace/harbor_task/tests/submission_contract.py；workspace/harbor_task/tests/sandbox_readout.py；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/task.toml
请修改/补充：按所列有效配置移除未支持约束或 Compose；核对现有配置及日志，说明当前仍依赖的限制是否真实生效。历史 warning 已修正时引用现有修正依据。
复检验收材料：当前目标配置及现有说明/日志相互一致；不以 warning 或联网 fallback 作为约束生效证据。

QA15 评分资源需求估算（待补充核验）：缺少：当前成绩的硬件归属/换卡影响尚未确认
证据：workspace/harbor_task/task.toml；expert_evidence/专家作业说明文档.md；optimization_evidence/reference_runs/seed_5/result.json；workspace/harbor_task/tests/submission_contract.py；expert_evidence/reverify/track_seed_reverify.json；workspace/harbor_task/tests/grader.py；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_1/result.json
请修改/补充：按任务性质核对当前Solver/Verifier资源。换卡只复核受影响的成绩或耗时，并引用已有配置、说明或运行记录；旧测量保留原硬件标签。
复检验收材料：CPU题不申请GPU；GPU题的实际目标卡型为H20/L20；受影响正式分数有目标硬件对应依据，不能只改型号沿用旧分。

QA16 轨迹实际迭代时长（待补充核验）：Codex + GPT-5.6 Sol缺少有效时长或排除排队/安装/故障的核算证据；Codex + Seed 2.1 Turbo缺少有效时长或排除排队/安装/故障的核算证据
证据：expert_evidence/runtime_forensics_20261025/README.md；expert_evidence/runtime/timing_codex.tsv；expert_evidence/runtime/timing_seed.tsv
请修改/补充：为Codex + GPT-5.6 Sol、Codex + Seed 2.1 Turbo补一张时长表：研究起止、排队/安装/API失联/故障区间、仍正常运行的训练重叠及有效秒数。可引用已交轨迹和日志片段；不强制提交完整timer或sessions。
复检验收材料：可复算的两轨起止/扣除表，与轨迹时间相符；默认每轨≥36000有效秒。最终复验、收集和明确故障不计，健康训练并发只计一次。

QA17 Harbor Harness 兼容性（不通过）：Harbor 子项未通过：H02 版本与配置；H03 环境与运行路径；H05 Job/Trial 调用配置；H06 NOP 自检记录；详细原因与证据保留在 report.json。
证据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/private/anchors.json；workspace/harbor_task/tests/sandbox_readout.py；workspace/harbor_task/tests/test.sh；expert_evidence/nop_trial/config.json；expert_evidence/nop_trial/README.md；expert_evidence/nop_trial/result.json；expert_evidence/nop_trial/verifier/reward.json；expert_evidence/nop_trial/verifier/reward.txt；expert_evidence/nop_trial/trial.log；expert_evidence/nop_trial/verifier/test-stdout.txt；expert_evidence/nop_trial_v1_superseded/config.json；expert_evidence/nop_trial_v1_superseded/result.json；expert_evidence/nop_trial_v1_superseded/verifier/reward.json；expert_evidence/nop_trial_v1_superseded/verifier/test-stdout.txt；expert_evidence/validation/nop_gpu_fullbudget/config.json；expert_evidence/validation/nop_gpu_fullbudget/result.json；expert_evidence/validation/nop_gpu_fullbudget/reward.json；expert_evidence/validation/nop_gpu_fullbudget/nop_run.log
请修改/补充：保留所列原标准差异，按指定历史政策逐原因处置；平台核验另列，不要求本轮补跑。
复检验收材料：现有源码、历史记录和逐原因处置依据；不伪造当前平台通过证明。

QA18 轨迹、日志与分析（待补充核验）：已审84/47轮及Seed原始47行、选优/复验/启动驱动；无工具sessions可审。实际模型可追溯，最高推理档/历史同Prompt完整证明不足；Seed旧集成分仅记录，未进入正式B/R。
证据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/best_selection.json；expert_evidence/runtime_forensics_20261025/launch_track.sh；expert_evidence/reverify/track_seed_reverify.json；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md；expert_evidence/runtime_forensics_20261025/build_round_prompt.py；expert_evidence/reverify/track_gpt56_reverify.json；expert_evidence/best_method/train.py；expert_evidence/reverify/track_gpt56_artifacts/inference.json；expert_evidence/reverify/track_gpt56_reward/reward.json；expert_evidence/run_summary.json#task_binding；expert_evidence/reverify/track_seed_artifacts/trajectory.jsonl；expert_evidence/reverify/track_seed_artifacts/train.py；expert_evidence/reverify/SEED_TRACK_REPRODUCIBILITY_STATEMENT.md
请修改/补充：保留所列原标准差异，按指定历史政策逐原因处置；平台核验另列，不要求本轮补跑。
复检验收材料：现有源码、历史记录和逐原因处置依据；不伪造当前平台通过证明。

QA21 三个 JSON 的填写内容（不通过）：主JSON/八字段可解析，当前四项指纹一致；但best_method训练输出未生成inference.json，run.sh直接调用当前Dev合同，实际回放缺省单视图恒等读出，与所称18视图仿射方法不符。
证据：expert_evidence/best_method/train.py:297-335；expert_evidence/best_method/run.sh:24-35；workspace/harbor_task/tests/submission_contract.py:193-199；expert_evidence/best_method/README.md；expert_evidence/run_summary.json；expert_evidence/best_selection.json
请修改/补充：使best_method当前训练/快速开始入口在每次运行后，依据该次新模型和校准矩阵生成inference.json：单model.pt、18视图、log_mean_probabilities、该次calibration_weight/class_bias，并在Dev调用前交付；不能盲复制旧checkpoint的矩阵。同步说明训练先验系数1与推理初始化0.7375的区别。
复检验收材料：提交修改后的源码与调用链，静态核对训练输出、清单、Dev输入一致；可利用既有匹配checkpoint及其已交复验清单证明映射。无需本批重做双轨历史研究或五对B/R；本次未执行该快速开始，未断言实际失配数量。
