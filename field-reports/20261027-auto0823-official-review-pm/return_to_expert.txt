# 旧题完整质检与逐原因豁免

本轮结论：FAIL
阶段：standard_review_with_waivers
已完成全部内容审阅：是

原 v0.3.10 全部检查及完整内容审阅已完成，包括已有 NOP；仅按具体历史原因豁免。未执行题包代码或新增 Harbor Trial。
平台实跑：not_executed；未执行模型、题目程序、Docker 或 Harbor。

## 方法与正式对照

在固定长尾CIFAR10划分与ResNet家族下设计训练损失、采样、辅助目标、训练日程和推理读出；接口允许任意Python方法实现并由独立可信骨干限制架构，非固定字面量搜索。
可修改：损失/辅助目标；样本与类别重加权/采样；训练日程；固定骨干上的视图池化及读出
冻结面：train/val/test划分和类别计数；骨干家族及width64；隐藏标签、评价和归一化锚点；单轮7200秒
指标与质量门：最大化隐藏均衡测试集top1百分比；score=(x-67.104)/(80-67.104)，连续不裁剪；格式/架构/读出/失配门失败-1，infra失败0且ERROR。
Baseline：正式B=未修改Starter的朴素ERM：固定CIFAR ResNet width64，全部9929个长尾训练样本、CE、SGD lr0.1/wd5e-4/batch128/cosine100ep；无额外预训练。保留快照与当前train.py相同，多出的未调用sampling与lt_metrics说明文字解释树哈希差异。
Reference：正式R=workspace/reference/train_lt.py --loss logit_adj --tau 1：CE(logits+log类先验,y)，与B同数据、骨干、优化器、100ep和seed集合。train_reference.py/IP-DPP为未采用的探索备选；Agent最佳方法另列，未混入R。
正式改善：五对改善10.35/6.50/8.44/9.75/7.44pp；B=67.104，σB=0.84742551295，R=75.600，σR=1.86926456126，Δ=8.496=10.0256599σB，3σB=2.54227654，归一化0.658808933；headroom4.400pp。seed5由75.68订正75.69，原始物证保留，未用旧值。
质量有效性：十份正式记录quality_gate=PASS、独立Dev reload差0，QA05重放表覆盖全部checkpoint；当前可信评分检查原始int64、长度、范围、非常数、固定骨干与预测一致性。静态材料支持有效，不等于本次独立复跑。
已有原始对照：[{"seed": 1, "baseline": 66.59, "reference": 76.94, "baseline_valid": true, "reference_valid": true}, {"seed": 2, "baseline": 66.1, "reference": 72.6, "baseline_valid": true, "reference_valid": true}, {"seed": 3, "baseline": 66.96, "reference": 75.4, "baseline_valid": true, "reference_valid": true}, {"seed": 4, "baseline": 67.62, "reference": 77.37, "baseline_valid": true, "reference_valid": true}, {"seed": 5, "baseline": 68.25, "reference": 75.69, "baseline_valid": true, "reference_valid": true}]
依据：optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/baseline_runs/seed_4/result.json；optimization_evidence/reference_runs/seed_4/result.json；optimization_evidence/baseline_runs/seed_5/result.json；optimization_evidence/reference_runs/seed_5/result.json；optimization_evidence/comparison_summary.json；expert_evidence/QA05_整改证据/QA05_anchor_reverify.json；expert_evidence/source_provenance/remote_forensics_20261025/independent_reproduction_20261025.json；workspace/harbor_task/tests/private/anchors.json；expert_evidence/source_provenance/manifest.json

## 研究三门

### G01 方法级优化空间

观察判定：pass；本轮判定：pass
题面开放目标/采样/日程/读出，实际接口允许方法代码；正式R改变训练损失而非仅常量搜索。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/environment/starter/train.py；workspace/reference/train_lt.py；workspace/harbor_task/tests/submission_contract.py

### G02 Baseline 合理性

观察判定：pass；本轮判定：pass
在已给材料范围内Baseline合理：全量ERM正确、100ep完成、预算与seed公平、选择完整；B01–B08见专项。进程级运行认证缺口不等于已证实不公平。
审阅依据：workspace/harbor_task/environment/starter/train.py；workspace/reference/train_lt.py；expert_evidence/source_provenance/manifest.json；expert_evidence/validation/formal_br_run.log；expert_evidence/QA05_整改证据/QA05_anchor_reverify.json
训练充分性：十份原始stdout均记录epoch20/40/60/80/100，B末端loss0.0033–0.0039、R0.0032–0.0042，无guard提前终止/异常；按共同100ep预算完成，未凭配置推定训练完成。
  依据：optimization_evidence/baseline_runs/seed_1/run.log；optimization_evidence/baseline_runs/seed_5/run.log；expert_evidence/validation/formal_br_run.log
方法代表性：全量ERM是本任务朴素研究起点与正式B；包内CB=63.31、随机均衡欠采样61.27均低于ERM的公开Dev约67.54，选较强ERM而非劣质占位。无需SOTA。
  依据：workspace/harbor_task/environment/starter/train.py；optimization_evidence/训练证据说明.md
原协议预算可比性：B/R同9929样本、固定骨干、batch128/SGD/cosine100ep、同一RTX3080Ti与20CPU上限；差异仅合法损失方法。H20/L20仅当前部署目标，未把旧耗时改标新卡。
  依据：workspace/reference/train_lt.py；workspace/harbor_task/environment/starter/train.py；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_1/result.json；expert_evidence/专家作业说明文档.md
实现正确性：CE标签、opt.zero_grad/backward/step与预测/保存路径正常；10个model大小11153922、流式sha256全部匹配artifact，10份reload记录为独立Dev复评零差；B保留树aa98…与当前7a3b…的差异已定位未调用sampling和docstring，train.py逐字节一致。进程argv/cwd未留存，不强制新认证。
  依据：workspace/harbor_task/environment/starter/train.py；workspace/reference/train_lt.py；expert_evidence/source_provenance/manifest.json；expert_evidence/source_provenance/G02_源码溯源说明.txt；expert_evidence/QA05_整改证据/QA05_anchor_reverify.json
选择与对照完整性：正式1..5完整成对，十个checkpoint不同哈希，同角色固定方法；拼接10份run.log逐字节等于formal_br_run.log。未将Agent选种结果或U的300ep探针作为正式R；seed5更正有原件与订正台账。
  依据：optimization_evidence/comparison_summary.json；expert_evidence/validation/formal_br_run.log；expert_evidence/source_provenance/manifest.json；workspace/harbor_task/tests/private/anchors.json

### G03 Reference 提升充分性

观察判定：pass；本轮判定：pass
五对全部正向，Δ8.496≥3σB2.542277，归一化0.658809；固定U80有300ep探针支持且未为本轮改值。无独立预注册证明不冒称已取得。
审阅依据：optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/baseline_runs/seed_4/result.json；optimization_evidence/reference_runs/seed_4/result.json；optimization_evidence/baseline_runs/seed_5/result.json；optimization_evidence/reference_runs/seed_5/result.json；optimization_evidence/comparison_summary.json；expert_evidence/QA05_整改证据/QA05_anchor_reverify.json；expert_evidence/source_provenance/remote_forensics_20261025/independent_reproduction_20261025.json；workspace/harbor_task/tests/private/anchors.json；expert_evidence/source_provenance/manifest.json
正式复算：{"baseline_mean": 67.104, "reference_mean": 75.6, "baseline_sample_std": 0.8474255129508454, "reference_sample_std": 1.869264561264673, "improvement": 8.495999999999995, "run_count": 5, "sigma_multiplier": 10.025659919555434, "three_sigma_baseline": 2.542276538852536, "normalized_score": 0.658808933002481}

## 21 项内容与实现

### QA01 八章节与题面信息泄露

观察判定：pass；本轮判定：pass
八部分齐全；题面给出任务/评分接口及B，不直接给出logit-adjust参考解、论文名或仓库线索。
审阅依据：workspace/harbor_task/instruction.md

### QA02 评分公式与 0/1 锚点

观察判定：pass；本轮判定：pass
grader以(accuracy-B)/(U-B)计算；B67.104/U80，单调连续不裁剪，Baseline聚合映射0。质量门-1与合法归一化负分分开。
审阅依据：workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/private/anchors.json

### QA03 参考解分数与复现材料

观察判定：pass；本轮判定：pass
正式R入口train_lt.py、5seed原值/非空原始日志/模型及reload齐全；归一化0.658809在区间内。Agent得分不冒充正式R。
审阅依据：workspace/reference/train_lt.py；expert_evidence/QA05_整改证据/QA05_anchor_reverify.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_4/result.json；optimization_evidence/reference_runs/seed_5/result.json

### QA04 波动指标的 3σ 可分辨性

观察判定：pass；本轮判定：pass
训练seed进入torch/np及epoch洗牌/增广；同角色固定方法、两侧1..5全配对，Δ=10.0257σB；给定模型推理确定不等于训练评估确定。
审阅依据：workspace/harbor_task/environment/starter/train.py；workspace/reference/train_lt.py；optimization_evidence/comparison_summary.json

### QA05 约束执行实现

观察判定：manual；本轮判定：pass_with_waivers
已有共享7200秒训练/产物推理/Dev计时入口、固定骨干可信重放与读出隔离；移除禁网字段后，Agent整体禁网/外部数据防护仍未落实，读出seccomp只覆盖读出进程。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/environment/public_eval/run_round.sh；workspace/harbor_task/tests/submission_contract.py；workspace/harbor_task/tests/sandbox_readout.py；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/task.toml
- 资产预置/HF_HUB_OFFLINE不构成Agent整体禁网，读出seccomp只在自定义读出进程生效；移除不支持网络字段后的过渡按批次授权免本轮补证，未认证联网约束。；处理：waived
  依据：workspace/harbor_task/instruction.md；workspace/harbor_task/environment/public_eval/run_round.sh；workspace/harbor_task/tests/submission_contract.py；workspace/harbor_task/tests/sandbox_readout.py；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/task.toml
  豁免原因：unsupported_network_policy_transition；适用0.3.10-standard-waiver.5指定旧批次format-repair-policy逐原因白名单；仅免此历史/平台证明差异，保留原判与事实，不证明已运行、不免当前实错。

### QA06 Verifier 入口、分数与错误处理

观察判定：pass；本轮判定：pass
/tests/test.sh调用grader，有限reward.json/txt；CandidateError=-1、INFRA=0且退出2；优先JSON数值对象与状态detail分开。
审阅依据：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/grader.py

### QA07 instruction 中的 Hidden 信息泄露

观察判定：pass；本轮判定：pass
仅审题面：未给隐藏样本标签或可恢复答案，公开训练/验证与隐藏标签职责明确。
审阅依据：workspace/harbor_task/instruction.md

### QA08 instruction 中的参考解信息泄露

观察判定：pass；本轮判定：pass
仅审题面：未给Reference代码/具体结果或方法名称；B与评分合同是任务所需接口说明。
审阅依据：workspace/harbor_task/instruction.md

### QA09 结果清理与原子写入

观察判定：pass；本轮判定：pass
main开头clear_outputs删除预写reward/detail；mkstemp同目录写入、os.replace原子替换。
审阅依据：workspace/harbor_task/tests/grader.py

### QA10 冻结面保护或恢复实现

观察判定：pass；本轮判定：pass
可信骨干/锚点/私有标签在Verifier自身镜像；不导入候选训练代码，自定义读出chroot降权且不传私有材料；Agent冻结面非root只读。
审阅依据：workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/submission_contract.py；workspace/harbor_task/tests/sandbox_readout.py

### QA11 instruction 八项内容

观察判定：pass；本轮判定：pass
八项实质内容完整；公开输出为可写solution/results.json，提交路径/资源/指标与实现对应。网络过渡问题归QA05单列。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/task.toml；workspace/harbor_task/environment/public_eval/evaluate.py

### QA12 Git 清理

观察判定：pass；本轮判定：pass
只读全树清点未见提交内.git；报告工作区的.git并非题包数据。
审阅依据：workspace/harbor_task/instruction.md

### QA13 Baseline 与参考解提升

观察判定：pass；本轮判定：pass
正式五对B/R隐藏指标均正向、质量门PASS，模型/reload/非空原始训练记录完整；更正seed5值有复算与原件留痕。
审阅依据：optimization_evidence/comparison_summary.json；expert_evidence/QA05_整改证据/QA05_anchor_reverify.json；expert_evidence/source_provenance/remote_forensics_20261025/independent_reproduction_20261025.json

### QA14 合法改进空间

观察判定：pass；本轮判定：pass
损失/采样/日程/读出接口开放；可探索自适应类条件权重/一致性日程，非仅调数字；正式R距U4.4pp大于3σB，Agent更高结果另列。
审阅依据：workspace/harbor_task/instruction.md；workspace/reference/train_lt.py；workspace/harbor_task/tests/submission_contract.py；expert_evidence/best_selection.json

### QA15 评分资源需求估算

观察判定：manual；本轮判定：pass_with_waivers
Agent1张H20/L20/20CPU、Verifier0GPU/8CPU；历史B/R172.7–299.2秒、读出有2700秒预算。目标卡完整单轮未实测；估算与历史3080Ti须分开。
审阅依据：workspace/harbor_task/task.toml；expert_evidence/专家作业说明文档.md；optimization_evidence/reference_runs/seed_5/result.json；workspace/harbor_task/tests/submission_contract.py
- 原记录3080Ti与当前目标H20/L20不同，旧测量未改标；正式B/R仍在同机同上限可比。；处理：waived
  依据：workspace/harbor_task/task.toml；expert_evidence/专家作业说明文档.md；optimization_evidence/reference_runs/seed_5/result.json；workspace/harbor_task/tests/submission_contract.py
  豁免原因：legacy_hardware_record_difference；适用0.3.10-standard-waiver.5指定旧批次format-repair-policy逐原因白名单；仅免此历史/平台证明差异，保留原判与事实，不证明已运行、不免当前实错。
- 6600秒为保守工程估计，缺目标卡训练/Dev/CPU重放完整测量，历史31模型高成本方案不是当前可提交方法。；处理：waived
  依据：workspace/harbor_task/task.toml；expert_evidence/专家作业说明文档.md；optimization_evidence/reference_runs/seed_5/result.json；workspace/harbor_task/tests/submission_contract.py
  豁免原因：legacy_target_resource_evidence_gap；适用0.3.10-standard-waiver.5指定旧批次format-repair-policy逐原因白名单；仅免此历史/平台证明差异，保留原判与事实，不证明已运行、不免当前实错。

### QA16 轨迹实际迭代时长

观察判定：manual；本轮判定：pass_with_waivers
GPT墙钟37831秒、轮窗口合计37829；Seed37810秒、末45秒无新行，产出窗口37765。内部排队/API/故障未分类，无法把墙钟直接认作≥10h有效研究；训练题不用7h例外。
审阅依据：expert_evidence/runtime_forensics_20261025/README.md；expert_evidence/runtime/timing_codex.tsv；expert_evidence/runtime/timing_seed.tsv
- 窗口合计约10.5h但内部空转/故障扣除不足；实际有效秒数未知，保持原manual，不声称达标。；处理：waived
  依据：expert_evidence/runtime_forensics_20261025/README.md；expert_evidence/runtime/timing_codex.tsv；expert_evidence/runtime/timing_seed.tsv
  豁免原因：legacy_research_duration_gap；适用0.3.10-standard-waiver.5指定旧批次format-repair-policy逐原因白名单；仅免此历史/平台证明差异，保留原判与事实，不证明已运行、不免当前实错。

### QA17 Harbor Harness 兼容性

观察判定：fail；本轮判定：pass_with_waivers
由H01–H06汇总：静态目录/路径/reward可核；网络过渡、镜像与当前平台执行待验；只有历史NOP，当前版本未运行。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/Dockerfile；expert_evidence/nop_trial/README.md
Harbor逐项派生：H01=pass；H02=pass_with_waivers；H03=pass_with_waivers；H04=pass；H05=pass_with_waivers；H06=pass_with_waivers

### QA18 轨迹、日志与分析

观察判定：manual；本轮判定：pass_with_waivers
已审84/47轮及Seed原始47行、选优/复验/启动驱动；无工具sessions可审。实际模型可追溯，最高推理档/历史同Prompt完整证明不足；Seed旧集成分仅记录，未进入正式B/R。
审阅依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/best_selection.json；expert_evidence/runtime_forensics_20261025/launch_track.sh；expert_evidence/reverify/track_seed_reverify.json
- 实际模型可由轨迹/header/启动说明关联；推理最高档位、完整公共Prompt快照和空输出启动认证缺口按旧证明豁免。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/best_selection.json；expert_evidence/runtime_forensics_20261025/launch_track.sh；expert_evidence/reverify/track_seed_reverify.json
  豁免原因：legacy_runtime_proof_gap；适用0.3.10-standard-waiver.5指定旧批次format-repair-policy逐原因白名单；仅免此历史/平台证明差异，保留原判与事实，不证明已运行、不免当前实错。
- Seed轨原集成4成员未保存，85.70另一配置无从核对；分数unverified且不作现行成绩/B/R，已有方法重训与全47轮仍审完。免的是迁移后的证明义务，不把历史分判有效。；处理：waived
  依据：expert_evidence/reverify/track_seed_reverify.json；expert_evidence/reverify/SEED_TRACK_REPRODUCIBILITY_STATEMENT.md；expert_evidence/best_selection.json
  豁免原因：legacy_runtime_proof_gap；适用0.3.10-standard-waiver.5指定旧批次format-repair-policy逐原因白名单；仅免此历史/平台证明差异，保留原判与事实，不证明已运行、不免当前实错。
- 已实际对比现有两轨材料，旧版材料仍不足以证明所有历史条件一致；仅此记录缺口豁免，不声称已证实同条件。已逐维比较实际材料：两轨同题CIFAR10-LT、相同baseline起点67.16、公开Dev与seed训练规则，分别独立凭据/CODEX_HOME/output；共同prompt构造器引用shared HARNESS_PROMPT/AGENT_BRIEF，但两份模板原件未交，故不能声称已证明逐字/语义完全相同。没有identical_prompt=false或已确认反馈/IPC/只读实质分轨差异的记录。历史两轨使用3080Ti而当前目标H20/L20的迁移另列；共用旧评分→当前可信重放改变双方验收，不等于A/B间差异。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/runtime_forensics_20261025/build_round_prompt.py；expert_evidence/runtime_forensics_20261025/launch_track.sh；expert_evidence/专家作业说明文档.md；expert_evidence/任务版本冻结记录_20261008.md
  豁免原因：legacy_runtime_proof_gap；本轮旧题迁移不要求新增Prompt快照、hash或重跑；已读资料中没有已确认的实质条件差异。

### QA19 seed 与有效提升阈值

观察判定：pass；本轮判定：pass
题面明示训练seed1..5与有效改善3σB，给定模型评分确定；审训练波动仍适用该项，不添加新版逐轮证明要求。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/environment/starter/train.py；workspace/reference/train_lt.py

### QA20 修改范围、网络与工具策略

观察判定：pass；本轮判定：pass
题面§4可改范围、§5网络与平台默认工具策略均明确；禁网执行缺口已独立归QA05，不能说工具条款不存在。
审阅依据：workspace/harbor_task/instruction.md

### QA21 三个 JSON 的填写内容

观察判定：fail；本轮判定：fail
主JSON/八字段可解析，当前四项指纹一致；但best_method训练输出未生成inference.json，run.sh直接调用当前Dev合同，实际回放缺省单视图恒等读出，与所称18视图仿射方法不符。
审阅依据：expert_evidence/best_method/train.py:297-335；expert_evidence/best_method/run.sh:24-35；workspace/harbor_task/tests/submission_contract.py:193-199；expert_evidence/best_method/README.md；expert_evidence/run_summary.json；expert_evidence/best_selection.json
- 当前四项指纹一致但注明仅返修树；历史轨迹使用早期评分/部署版本，不能用当前hash补造历史绑定。；处理：waived
  依据：expert_evidence/run_summary.json；expert_evidence/任务版本冻结记录_20261008.md
  豁免原因：legacy_task_binding_migration；适用0.3.10-standard-waiver.5指定旧批次format-repair-policy逐原因白名单；仅免此历史/平台证明差异，保留原判与事实，不证明已运行、不免当前实错。
- 主JSON/八字段可解析，当前四项指纹一致；但best_method训练输出未生成inference.json，run.sh直接调用当前Dev合同，实际回放缺省单视图恒等读出，与所称18视图仿射方法不符。；处理：unwaived
  依据：expert_evidence/best_method/train.py:297-335；expert_evidence/best_method/run.sh:24-35；workspace/harbor_task/tests/submission_contract.py:193-199；expert_evidence/best_method/README.md；expert_evidence/run_summary.json；expert_evidence/best_selection.json
  修改方向：使best_method当前训练/快速开始入口在每次运行后，依据该次新模型和校准矩阵生成inference.json：单model.pt、18视图、log_mean_probabilities、该次calibration_weight/class_bias，并在Dev调用前交付；不能盲复制旧checkpoint的矩阵。同步说明训练先验系数1与推理初始化0.7375的区别。
  验收：提交修改后的源码与调用链，静态核对训练输出、清单、Dev输入一致；可利用既有匹配checkpoint及其已交复验清单证明映射。无需本批重做双轨历史研究或五对B/R；本次未执行该快速开始，未断言实际失配数量。

## Harbor 六项

### H01 任务目录

观察判定：pass；本轮判定：pass
任务根、双构建、预置Hidden图像/标签/锚点、公开Dev与评分调用清楚，只有environment上下文进入Agent。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/private/anchors.json

### H02 版本与配置

观察判定：manual；本轮判定：pass_with_waivers
tomllib可解析，显式separate、原生CPU/GPU配置；旧entrypoint/submit为信息扩展不替代真实tests入口。默认内场不支持整体禁网；题面禁网承诺尚有迁移缺口。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md；workspace/harbor_task/tests/sandbox_readout.py
- tomllib可解析，显式separate、原生CPU/GPU配置；旧entrypoint/submit为信息扩展不替代真实tests入口。默认内场不支持整体禁网；题面禁网承诺尚有迁移缺口。；处理：waived
  依据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md；workspace/harbor_task/tests/sandbox_readout.py
  豁免原因：unsupported_network_policy_transition；适用0.3.10-standard-waiver.5指定旧批次format-repair-policy逐原因白名单；仅免此历史/平台证明差异，保留原判与事实，不证明已运行、不免当前实错。

### H03 环境与运行路径

观察判定：manual；本轮判定：pass_with_waivers
Agent environment/、Verifier tests/构建，私有数据仅后者，/workspace/solution按绝对路径移交；运行调用都是本沙盒进程/chroot，无额外工作环境。内部镜像tag及当前root/seccomp/传输需平台验证。
审阅依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/task.toml；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/sandbox_readout.py
- 有完整双Dockerfile源镜像构建方案；内场最终tag/选中镜像由平台准备，未声明已导入。；处理：waived
  依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/task.toml；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/sandbox_readout.py
  豁免原因：platform_image_preparation_pending；适用0.3.10-standard-waiver.5指定旧批次format-repair-policy逐原因白名单；仅免此历史/平台证明差异，保留原判与事实，不证明已运行、不免当前实错。
- 本沙盒本地进程/降权chroot静态调用清楚，当前root/seccomp、构建和实际移交未验证；并非额外容器。；处理：waived
  依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/task.toml；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/sandbox_readout.py
  豁免原因：platform_execution_verification_pending；适用0.3.10-standard-waiver.5指定旧批次format-repair-policy逐原因白名单；仅免此历史/平台证明差异，保留原判与事实，不证明已运行、不免当前实错。

### H04 测试入口与 reward

观察判定：pass；本轮判定：pass
绝对路径test.sh→grader，启动清理并原子输出/logs/verifier/reward.json/txt；JSON仅有限数值，状态在detail，退出码可传播。
审阅依据：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/grader.py

### H05 Job/Trial 调用配置

观察判定：manual；本轮判定：pass_with_waivers
已审三套历史NOP调用；正式v2声明nop/separate和双镜像，未禁用Verifier，但其task.toml哈希为旧103cec…，不能冒称当前平台Job成功。
审阅依据：expert_evidence/nop_trial/config.json；expert_evidence/nop_trial/README.md；workspace/harbor_task/task.toml
- 已有历史Trial配置已审；迁移后当前Job配置与启动/镜像选择由平台核验。；处理：waived
  依据：expert_evidence/nop_trial/config.json；expert_evidence/nop_trial/README.md；workspace/harbor_task/task.toml
  豁免原因：platform_execution_verification_pending；适用0.3.10-standard-waiver.5指定旧批次format-repair-policy逐原因白名单；仅免此历史/平台证明差异，保留原判与事实，不证明已运行、不免当前实错。

### H06 NOP 自检记录

观察判定：fail；本轮判定：pass_with_waivers
正式v2历史NOP两处身份nop、separate、结束无exception、reward/result一致且日志非空，可信重放28.81/-2.9694；无sandbox同ID反证但身份未交。历史v1和GPU宿主记录另列，均不证明当前49ee…版本已跑。
审阅依据：expert_evidence/nop_trial/config.json；expert_evidence/nop_trial/result.json；expert_evidence/nop_trial/verifier/reward.json；expert_evidence/nop_trial/verifier/reward.txt；expert_evidence/nop_trial/trial.log；expert_evidence/nop_trial/verifier/test-stdout.txt；expert_evidence/nop_trial/README.md；expert_evidence/nop_trial_v1_superseded/config.json；expert_evidence/nop_trial_v1_superseded/result.json；expert_evidence/nop_trial_v1_superseded/verifier/reward.json；expert_evidence/nop_trial_v1_superseded/verifier/test-stdout.txt；expert_evidence/validation/nop_gpu_fullbudget/config.json；expert_evidence/validation/nop_gpu_fullbudget/result.json；expert_evidence/validation/nop_gpu_fullbudget/reward.json；expert_evidence/validation/nop_gpu_fullbudget/nop_run.log
- 正式v2旧NOP身份/终止/reward/日志一致，task_toml103cec…与当前49ee…不同，旧v1记录和GPU宿主补充均不冒充现行NOP。当前runtime=not_run；免补跑但原记录不改判当前成功。；处理：waived
  依据：expert_evidence/nop_trial/config.json；expert_evidence/nop_trial/result.json；expert_evidence/nop_trial/verifier/reward.json；expert_evidence/nop_trial/verifier/reward.txt；expert_evidence/nop_trial/trial.log；expert_evidence/nop_trial/verifier/test-stdout.txt；expert_evidence/nop_trial/README.md；expert_evidence/nop_trial_v1_superseded/config.json；expert_evidence/nop_trial_v1_superseded/result.json；expert_evidence/nop_trial_v1_superseded/verifier/reward.json；expert_evidence/nop_trial_v1_superseded/verifier/test-stdout.txt；expert_evidence/validation/nop_gpu_fullbudget/config.json；expert_evidence/validation/nop_gpu_fullbudget/result.json；expert_evidence/validation/nop_gpu_fullbudget/reward.json；expert_evidence/validation/nop_gpu_fullbudget/nop_run.log
  豁免原因：legacy_nop_or_current_trial_gap；适用0.3.10-standard-waiver.5指定旧批次format-repair-policy逐原因白名单；仅免此历史/平台证明差异，保留原判与事实，不证明已运行、不免当前实错。
- v2历史NOP同Trial身份、separate、结束、reward与日志一致；原校验器只因旧task.toml103cec…不同于当前49ee…记manual。此原因免补跑，不写成当前成功。；处理：waived
  依据：expert_evidence/nop_trial/config.json；expert_evidence/nop_trial/result.json；expert_evidence/nop_trial/README.md
  豁免原因：legacy_nop_or_current_trial_gap；适用0.3.10-standard-waiver.5指定旧批次format-repair-policy逐原因白名单；仅免此历史/平台证明差异，保留原判与事实，不证明已运行、不免当前实错。
- v1归档NOP在原只读预测评分链下reward一致，旧task.toml103cec…不是当前版本；保留其覆盖边界与版本缺口，未将v1用于现行trusted replay证明。；处理：waived
  依据：expert_evidence/nop_trial_v1_superseded/config.json；expert_evidence/nop_trial_v1_superseded/result.json；expert_evidence/nop_trial_v1_superseded/SUPERSEDED.md
  豁免原因：legacy_nop_or_current_trial_gap；适用0.3.10-standard-waiver.5指定旧批次format-repair-policy逐原因白名单；仅免此历史/平台证明差异，保留原判与事实，不证明已运行、不免当前实错。
- GPU全预算宿主记录缺原生nop Agent/config/result结构、separate/原生reward日志布局，不合原H06；保留原fail。后续已有v2双镜像nop结构与可信评分源码修正，但当前迁移题包尚未Trial，仅此历史当前验证缺口豁免。；处理：waived
  依据：expert_evidence/validation/nop_gpu_fullbudget/config.json；expert_evidence/validation/nop_gpu_fullbudget/result.json；expert_evidence/validation/nop_gpu_fullbudget/README.md；expert_evidence/nop_trial/config.json；expert_evidence/nop_trial/result.json；workspace/harbor_task/task.toml；workspace/harbor_task/tests/grader.py
  豁免原因：legacy_nop_or_current_trial_gap；适用0.3.10-standard-waiver.5指定旧批次format-repair-policy逐原因白名单；仅免此历史/平台证明差异，保留原判与事实，不证明已运行、不免当前实错。

## 两轨已有内容

### T01 第一条轨迹已有内容

观察判定：manual；本轮判定：pass_with_waivers
84轮完整：ERM→先验校正→Balanced Softmax/Cutout→TTA→Dev仿射读出；EMA、平滑、Mixup等低分回退，后期有参数细化但方法面开放。
审阅依据：expert_evidence/trajectory_codex.json；expert_evidence/best_selection.json；expert_evidence/runtime_forensics_20261025/README.md；expert_evidence/reverify/track_gpt56_reverify.json
方法：84轮完整：ERM→先验校正→Balanced Softmax/Cutout→TTA→Dev仿射读出；EMA、平滑、Mixup等低分回退，后期有参数细化但方法面开放。
迭代内容：已完整审阅所有84轮；每轮方法/分数/保留与回退均读取。Seed原始追加序无round30，36/37颠倒与+8h时区规范化有留档，未隐藏低分/失败；GPT后期参数细化如实保留。
最终结果：历史round84 Dev86.66；干净复验86.54（差-0.12），隐藏83.96，当前锚点reward1.3070719602977674；带独立inference清单的复验记录有效。
分数采用范围：作者正式B/R仅采用optimization_evidence五对；GPT历史最佳+单独清单可信复验作为Agent记录，Seed分不作现行可复算成绩；当前best方法快速开始缺清单在QA21保留实错。
已读来源：expert_evidence/trajectory_codex.json；expert_evidence/best_selection.json；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md；expert_evidence/runtime_forensics_20261025/launch_track.sh；expert_evidence/runtime_forensics_20261025/build_round_prompt.py；expert_evidence/reverify/track_gpt56_reverify.json；expert_evidence/best_method/train.py；expert_evidence/reverify/track_gpt56_artifacts/inference.json；expert_evidence/reverify/track_gpt56_reward/reward.json
- 各轨墙钟约10.5h不等于真实有效时长；扣除不足按旧时长缺口处置。；处理：waived
  依据：expert_evidence/runtime_forensics_20261025/README.md；expert_evidence/trajectory_codex.json
  豁免原因：legacy_research_duration_gap；适用0.3.10-standard-waiver.5指定旧批次format-repair-policy逐原因白名单；仅免此历史/平台证明差异，保留原判与事实，不证明已运行、不免当前实错。
- 旧运行无完整最高推理档和Prompt/空输出认证；已交内容审完，不假称认证了未交工具行为。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/best_selection.json；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md；expert_evidence/runtime_forensics_20261025/launch_track.sh；expert_evidence/runtime_forensics_20261025/build_round_prompt.py；expert_evidence/reverify/track_gpt56_reverify.json；expert_evidence/best_method/train.py；expert_evidence/reverify/track_gpt56_artifacts/inference.json；expert_evidence/reverify/track_gpt56_reward/reward.json
  豁免原因：legacy_runtime_proof_gap；适用0.3.10-standard-waiver.5指定旧批次format-repair-policy逐原因白名单；仅免此历史/平台证明差异，保留原判与事实，不证明已运行、不免当前实错。

### T02 第二条轨迹已有内容

观察判定：manual；本轮判定：pass_with_waivers
47轮完整：CB/focal失败，LA/Mixup/CutMix/TTA/多seed集成，31模型历史最高86.36；后续dropout/LS与tau探索。
审阅依据：expert_evidence/trajectory_seed.json；expert_evidence/best_selection.json；expert_evidence/runtime_forensics_20261025/README.md；expert_evidence/reverify/track_seed_reverify.json
方法：47轮完整：CB/focal失败，LA/Mixup/CutMix/TTA/多seed集成，31模型历史最高86.36；后续dropout/LS与tau探索。
迭代内容：已完整审阅所有47轮；每轮方法/分数/保留与回退均读取。Seed原始追加序无round30，36/37颠倒与+8h时区规范化有留档，未隐藏低分/失败；GPT后期参数细化如实保留。
最终结果：历史最高round33/34 Dev86.36；选用方法round35五成员Dev85.08，独立重训复现该配置；原提交85.70为另一配置，缺成员权重，隐藏84.21仅留历史，不作当前成绩或正式B/R。
分数采用范围：作者正式B/R仅采用optimization_evidence五对；GPT历史最佳+单独清单可信复验作为Agent记录，Seed分不作现行可复算成绩；当前best方法快速开始缺清单在QA21保留实错。
已读来源：expert_evidence/trajectory_seed.json；expert_evidence/best_selection.json；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md；expert_evidence/runtime_forensics_20261025/launch_track.sh；expert_evidence/runtime_forensics_20261025/build_round_prompt.py；expert_evidence/reverify/track_seed_reverify.json；expert_evidence/reverify/track_seed_artifacts/trajectory.jsonl；expert_evidence/reverify/track_seed_artifacts/train.py；expert_evidence/reverify/SEED_TRACK_REPRODUCIBILITY_STATEMENT.md
- 各轨墙钟约10.5h不等于真实有效时长；扣除不足按旧时长缺口处置。；处理：waived
  依据：expert_evidence/runtime_forensics_20261025/README.md；expert_evidence/trajectory_seed.json
  豁免原因：legacy_research_duration_gap；适用0.3.10-standard-waiver.5指定旧批次format-repair-policy逐原因白名单；仅免此历史/平台证明差异，保留原判与事实，不证明已运行、不免当前实错。
- 旧运行无完整最高推理档和Prompt/空输出认证；已交内容审完，不假称认证了未交工具行为。；处理：waived
  依据：expert_evidence/trajectory_seed.json；expert_evidence/best_selection.json；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md；expert_evidence/runtime_forensics_20261025/launch_track.sh；expert_evidence/runtime_forensics_20261025/build_round_prompt.py；expert_evidence/reverify/track_seed_reverify.json；expert_evidence/reverify/track_seed_artifacts/trajectory.jsonl；expert_evidence/reverify/track_seed_artifacts/train.py；expert_evidence/reverify/SEED_TRACK_REPRODUCIBILITY_STATEMENT.md
  豁免原因：legacy_runtime_proof_gap；适用0.3.10-standard-waiver.5指定旧批次format-repair-policy逐原因白名单；仅免此历史/平台证明差异，保留原判与事实，不证明已运行、不免当前实错。
- 历史多成员集成只保留首成员；该轨得分unverified、不参与正式B/R或当前winner，已有不同配置重训不能证明85.70。；处理：waived
  依据：expert_evidence/reverify/track_seed_reverify.json
  豁免原因：legacy_runtime_proof_gap；适用0.3.10-standard-waiver.5指定旧批次format-repair-policy逐原因白名单；仅免此历史/平台证明差异，保留原判与事实，不证明已运行、不免当前实错。

## 两轨实际条件对比

对比已完成：是
条件判断：historical_evidence_gap；成对对照有效性：unverified
已逐维比较实际材料：两轨同题CIFAR10-LT、相同baseline起点67.16、公开Dev与seed训练规则，分别独立凭据/CODEX_HOME/output；共同prompt构造器引用shared HARNESS_PROMPT/AGENT_BRIEF，但两份模板原件未交，故不能声称已证明逐字/语义完全相同。没有identical_prompt=false或已确认反馈/IPC/只读实质分轨差异的记录。历史两轨使用3080Ti而当前目标H20/L20的迁移另列；共用旧评分→当前可信重放改变双方验收，不等于A/B间差异。
已对比维度：prompt、task、dev、feedback、constraints、resources
对比依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/runtime_forensics_20261025/build_round_prompt.py；expert_evidence/runtime_forensics_20261025/launch_track.sh；expert_evidence/专家作业说明文档.md；expert_evidence/任务版本冻结记录_20261008.md
质检员内部对比底稿；不要求专家新增字段、Prompt快照、hash或重跑。语义判断须实际阅读原材料，脚本只核验审阅覆盖及判定一致性。

## 当前格式前检 F01–F07（子检查）

format_decision：PASS_WITH_WAIVERS
以下仅为当前格式子检查；整题结论以本报告顶部完整质检结果为准。

- F01 [pass] 当前必需目录、文件与 TOML 接口：必需三目录/任务根/TOML字段、显式separate及真实tests入口可核。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md；workspace/harbor_task/tests/Dockerfile
- F02 [pass] 有效构建或镜像方案、构建上下文及 COPY 来源：environment和tests独立上下文，COPY来源存在，无私有越界COPY。
  格式审阅依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile
- F03 [pass] 评分入口、独立依赖声明与固定输出路径：test.sh绝对路径、CPU torch与numpy依赖声明和reward目录一致。
  格式审阅依据：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/grader.py
- F04 [pass] 提交物 artifacts 移交契约：顶层artifacts移交/workspace/solution，Verifier保持同绝对路径读取。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/grader.py
- F05 [pass] 公开 Dev、私有 Hidden 供给与 Agent 隔离：公开Dev进入Agent；私有标签/锚点/可信图像仅入Verifier，不将根级额外专家资产复制入Agent。
  格式审阅依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/grader.py
- F06 [pass] separate、单容器、无 Compose 与当前目标资源配置：Agent1H20/L20/20CPU，Verifier0GPU/8CPU；单沙盒单容器，本地读出进程不另起环境；无Compose/不支持字段。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/sandbox_readout.py
- F07 [pass] 当前评分实现与冻结面无确证故障或作者泄漏造假：当前正式grader从独立骨干重放，不执行候选训练模块，清理/原子reward路径存在；未见作者伪造正式B/R的确证。
  格式审阅依据：workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/submission_contract.py；workspace/harbor_task/tests/sandbox_readout.py

## 平台后续事项（不阻断本轮已有材料审阅）

- 字节内部准备、构建或导入镜像并配置实际 ICM tag；本轮不要求专家补内部镜像运行记录。
- 平台实际构建和启动，核对依赖、基础镜像 digest 及 bash/解释器；静态推断不能冒充运行结果。
- 平台核对 root、seccomp、网络及实际分配的沙盒权限设置。
- 平台后续执行当前版本 Harbor Trial/NOP、独立 Verifier 和 reward 收集；其缺口不作为本轮专家返修门槛。
- 已有原硬件结果本轮复核；不把旧值改称新硬件实测，不要求新环境补跑；平台核对实际当前提交物移交及目标硬件运行。
- 移除不支持的禁网字段后，新的联网或外部查表防护尚未落实，列为平台迁移事项，不要求本批专家新增防护实现或补跑；当前确证 Hidden 暴露或假 reward 仍属当前核心缺陷。

## 原 v0.3.10 自动检查及 NOP 原判

已调用原标准审计入口：True
NOP：{"status": "fail", "runtime_status": "failed", "trials": [{"trial_dir": "expert_evidence/nop_trial", "evidence": ["expert_evidence/nop_trial/config.json", "expert_evidence/nop_trial/result.json", "expert_evidence/nop_trial/verifier/reward.json", "expert_evidence/nop_trial/verifier/reward.txt", "expert_evidence/nop_trial/trial.log", "expert_evidence/nop_trial/verifier/test-stdout.txt"], "status": "manual", "summary": "Harbor Trial task.toml hash disagrees with the inspected task", "protected": false}, {"trial_dir": "expert_evidence/nop_trial_v1_superseded", "evidence": ["expert_evidence/nop_trial_v1_superseded/config.json", "expert_evidence/nop_trial_v1_superseded/result.json", "expert_evidence/nop_trial_v1_superseded/verifier/reward.json", "expert_evidence/nop_trial_v1_superseded/verifier/reward.txt", "expert_evidence/nop_trial_v1_superseded/trial.log", "expert_evidence/nop_trial_v1_superseded/verifier/test-stdout.txt"], "status": "manual", "summary": "Harbor Trial task.toml hash disagrees with the inspected task", "protected": false}, {"trial_dir": "expert_evidence/validation/nop_gpu_fullbudget", "evidence": ["expert_evidence/validation/nop_gpu_fullbudget/config.json", "expert_evidence/validation/nop_gpu_fullbudget/result.json"], "status": "fail", "summary": "H06 pass requires config.json, result.json, verifier/reward.*, and trial.log or verifier/test-stdout.txt from the same trial", "protected": true}], "summary": "逐份读取并校验已有 NOP 记录；未启动新的 Trial。"}

原报告与全部详细结果：standard/report.json；不因豁免覆盖原判。

| 来源 | 项目 | 原判 | 本轮处理 | 依据及原因 |
|---|---|---|---|---|
| checks/QA05 | QA05 | manual | pass_with_waivers | 当前无storage_mb/no-network/白名单或Compose请求；读出seccomp有实现但不覆盖Agent整体联网，资产预置不等于禁网。 |
| checks/QA15 | QA15 | manual | pass_with_waivers | 缺少：当前成绩的硬件归属/换卡影响尚未确认 |
| checks/QA16 | QA16 | manual | pass_with_waivers | Codex + GPT-5.6 Sol缺少有效时长或排除排队/安装/故障的核算证据；Codex + Seed 2.1 Turbo缺少有效时长或排除排队/安装/故障的核算证据 |
| checks/QA17 | QA17 | fail | derived_from_details | Harbor 子项未通过：H02 版本与配置；H03 环境与运行路径；H05 Job/Trial 调用配置；H06 NOP 自检记录；详细原因与证据保留在 report.json。 |
| checks/QA18 | QA18 | manual | pass_with_waivers | 已审84/47轮及Seed原始47行、选优/复验/启动驱动；无工具sessions可审。实际模型可追溯，最高推理档/历史同Prompt完整证明不足；Seed旧集成分仅记录，未进入正式B/R。 |
| checks/QA21 | QA21 | fail | fail | 主JSON/八字段可解析，当前四项指纹一致；但best_method训练输出未生成inference.json，run.sh直接调用当前Dev合同，实际回放缺省单视图恒等读出，与所称18视图仿射方法不符。 |
| harbor/H02 | H02 | manual | pass_with_waivers | tomllib可解析，显式separate、原生CPU/GPU配置；旧entrypoint/submit为信息扩展不替代真实tests入口。默认内场不支持整体禁网；题面禁网承诺尚有迁移缺口。；当前无storage_mb/no-network/白名单或Compose请求；读出seccomp有实现但不覆盖Agent整体联网，资产预置不等于禁网。 |
| harbor/H03 | H03 | manual | pass_with_waivers | Agent environment/、Verifier tests/构建，私有数据仅后者，/workspace/solution按绝对路径移交；运行调用都是本沙盒进程/chroot，无额外工作环境。内部镜像tag及当前root/seccomp/传输需平台验证。 |
| harbor/H05 | H05 | manual | pass_with_waivers | 已审三套历史NOP调用；正式v2声明nop/separate和双镜像，未禁用Verifier，但其task.toml哈希为旧103cec…，不能冒称当前平台Job成功。 |
| harbor/H06 | H06 | fail | derived_from_details | 正式v2历史NOP两处身份nop、separate、结束无exception、reward/result一致且日志非空，可信重放28.81/-2.9694；无sandbox同ID反证但身份未交。历史v1和GPU宿主记录另列，均不证明当前49ee…版本已跑。 |
| harbor/deployment_contract/0 | H02 | manual | pass_with_waivers | 当前无storage_mb/no-network/白名单或Compose请求；读出seccomp有实现但不覆盖Agent整体联网，资产预置不等于禁网。 |
| resources/gaps/0 | QA15 | manual | pass_with_waivers | 当前成绩的硬件归属/换卡影响尚未确认 |
| nop/trials/0 | H06 | manual | pass_with_waivers | Harbor Trial task.toml hash disagrees with the inspected task |
| nop/trials/1 | H06 | manual | pass_with_waivers | Harbor Trial task.toml hash disagrees with the inspected task |
| nop/trials/2 | H06 | fail | pass_with_waivers | H06 pass requires config.json, result.json, verifier/reward.*, and trial.log or verifier/test-stdout.txt from the same trial |
