# 旧题完整质检与逐原因豁免

本轮结论：FAIL
阶段：standard_review_with_waivers
已完成全部内容审阅：是

原 v0.3.10 全部检查及完整内容审阅已完成，包括已有 NOP；仅按具体历史原因豁免。未执行题包代码或新增 Harbor Trial。
平台实跑：not_executed；未执行模型、题目程序、Docker 或 Harbor。

## 方法与正式对照

APAVA受试者级EEG二分类；开放模型Python接口，可设计时域/频域编码、SSM/注意力/图结构、增广与损失。解析器直接调用Model.forward，不限常量。
可修改：models/模型结构与可执行forward；run.py训练组件、损失/增广/正则；允许预算内batch调整；正式B/R固定同batch16
冻结面：受试者划分与冻结数据管线；Adam lr=1e-4、12epochs、seed41/42/43；正式SWA ep3-12均匀平均；macro-F1 argmax及B/U锚点、20M与1800s训练上限
指标与质量门：maximize hidden TEST macro-F1；B=0.6492613306723667，U=1；Δ≥3σ_B且归一化[0.15,0.8]；公开Dev n=1413，TEST n=1431。
Baseline：正式B为BaselineFormer：三尺度Conv(3/5/7)+2层pre-norm Transformer，d64/ff128，76,529参数；Adam1e-4，batch16，12轮，SWA ep3-12。它是未经结构修改Starter的独立完整训练对照；示例脚本batch32不作锚点。
Reference：正式R为MedMamba：原始/差分/频域SSM三支路门控、空间图Mamba与DAG/稀疏损失，d256/ff512/4层，15,955,713参数；dropout0.2、Adam wd0.01；同batch16/12轮/seed/SWA。不是Agent r101最佳方法。
正式改善：全部三seed逐项正向；Δ=0.13218856661518463；σ_B=0.04297184600022364；3.0761668143σ_B；归一化0.37688620666945666。3–5σ区间可接受，保留复核建议。
质量有效性：6/6 COMPLETE，全部12轮、2352 update、37476 samples；六份checkpoint大小/SHA与artifact和reload逐一吻合，F1与重载记录一致；固定ep3-12。历史不对称和未达标敏感性未并入正式值。
已有原始对照：[{"seed": 41, "baseline": 0.6066176791433583, "reference": 0.7913161611199804, "baseline_valid": true, "reference_valid": true}, {"seed": 42, "baseline": 0.6486122942127497, "reference": 0.7653705736679517, "baseline_valid": true, "reference_valid": true}, {"seed": 43, "baseline": 0.692554018660992, "reference": 0.7876629570747218, "baseline_valid": true, "reference_valid": true}]
依据：workspace/harbor_task/instruction.md；optimization_evidence/comparison_summary.json；expert_evidence/g02_support/matched_control/frozen_protocol.json；workspace/harbor_task/environment/starter/models/BaselineFormer.py；expert_evidence/g02_support/improved_method_source/models/MedMamba.py；optimization_evidence/baseline_runs/seed_41/result.json；optimization_evidence/baseline_runs/seed_42/result.json；optimization_evidence/baseline_runs/seed_43/result.json；optimization_evidence/reference_runs/seed_41/result.json；optimization_evidence/reference_runs/seed_42/result.json；optimization_evidence/reference_runs/seed_43/result.json；optimization_evidence/baseline_runs/seed_41/reload_worker.json；optimization_evidence/baseline_runs/seed_42/reload_worker.json；optimization_evidence/baseline_runs/seed_43/reload_worker.json；optimization_evidence/reference_runs/seed_41/reload_worker.json；optimization_evidence/reference_runs/seed_42/reload_worker.json；optimization_evidence/reference_runs/seed_43/reload_worker.json；optimization_evidence/baseline_runs/seed_41/model/artifact.json；optimization_evidence/baseline_runs/seed_42/model/artifact.json；optimization_evidence/baseline_runs/seed_43/model/artifact.json；optimization_evidence/reference_runs/seed_41/model/artifact.json；optimization_evidence/reference_runs/seed_42/model/artifact.json；optimization_evidence/reference_runs/seed_43/model/artifact.json

## 研究三门

### G01 方法级优化空间

观察判定：pass；本轮判定：pass
模型接口开放可执行结构方法；BaselineTransformer与Reference三支路SSM/图结构差异实质，Reference末轮正则调整不使整题成为纯调参。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/environment/starter/models/BaselineFormer.py；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/tests/infer_candidate.py；expert_evidence/g02_support/improved_method_source/models/MedMamba.py

### G02 Baseline 合理性

观察判定：pass；本轮判定：pass
正式Baseline在已交材料范围内合理：完成共同固定预算、训练/推理健全、成对seed完整，未发现人为削弱或挑差B的直接反证。
审阅依据：workspace/harbor_task/instruction.md；optimization_evidence/comparison_summary.json；expert_evidence/g02_support/matched_control/frozen_protocol.json；workspace/harbor_task/environment/starter/models/BaselineFormer.py；expert_evidence/g02_support/improved_method_source/models/MedMamba.py；optimization_evidence/baseline_runs/seed_41/result.json；optimization_evidence/baseline_runs/seed_42/result.json；optimization_evidence/baseline_runs/seed_43/result.json；optimization_evidence/reference_runs/seed_41/result.json；optimization_evidence/reference_runs/seed_42/result.json；optimization_evidence/reference_runs/seed_43/result.json；optimization_evidence/baseline_runs/seed_41/reload_worker.json；optimization_evidence/baseline_runs/seed_42/reload_worker.json；optimization_evidence/baseline_runs/seed_43/reload_worker.json；optimization_evidence/reference_runs/seed_41/reload_worker.json；optimization_evidence/reference_runs/seed_42/reload_worker.json；optimization_evidence/reference_runs/seed_43/reload_worker.json；optimization_evidence/baseline_runs/seed_41/model/artifact.json；optimization_evidence/baseline_runs/seed_42/model/artifact.json；optimization_evidence/baseline_runs/seed_43/model/artifact.json；optimization_evidence/reference_runs/seed_41/model/artifact.json；optimization_evidence/reference_runs/seed_42/model/artifact.json；optimization_evidence/reference_runs/seed_43/model/artifact.json；optimization_evidence/baseline_runs/seed_41/run.log；optimization_evidence/baseline_runs/seed_42/run.log；optimization_evidence/baseline_runs/seed_43/run.log；optimization_evidence/reference_runs/seed_41/run.log；optimization_evidence/reference_runs/seed_42/run.log；optimization_evidence/reference_runs/seed_43/run.log
训练充分性：六份原日志均12轮196步，events逐行扫描各2352次连续成功更新和37476样本；B训练loss约0.58→0.00475、0.56→0.00141、0.62→0.00907，无无依据截短；固定窗口SWA并非选最坏轮。
  依据：optimization_evidence/baseline_runs/seed_41/run.log；optimization_evidence/baseline_runs/seed_42/run.log；optimization_evidence/baseline_runs/seed_43/run.log；optimization_evidence/reference_runs/seed_41/run.log；optimization_evidence/reference_runs/seed_42/run.log；optimization_evidence/reference_runs/seed_43/run.log；optimization_evidence/baseline_runs/seed_41/events.jsonl
方法代表性：三尺度卷积+Transformer为可运行朴素正式基线；无包内同协议更强必需锚点反证。不能以年代、分数低或比R小直接判不合理。
  依据：workspace/harbor_task/environment/starter/models/BaselineFormer.py；expert_evidence/专家作业说明文档.md
原协议预算可比性：共同数据/seed/Adam学习率、12轮、batch16、2352updates/37476samples、20M和1800s上限；结构容量与正则属允许变量。B在4090、R在4080 SUPER历史校准机，均实测小于1800s，不冒称H20实测。
  依据：workspace/harbor_task/instruction.md；expert_evidence/g02_support/matched_control/frozen_protocol.json；expert_evidence/g02_support/matched_control/preflight.json；expert_evidence/g02_support/improved_method_runs/reference_seed41/preflight.json；optimization_evidence/baseline_runs/seed_41/result.json；optimization_evidence/baseline_runs/seed_42/result.json；optimization_evidence/baseline_runs/seed_43/result.json；optimization_evidence/reference_runs/seed_41/result.json；optimization_evidence/reference_runs/seed_42/result.json；optimization_evidence/reference_runs/seed_43/result.json
实现正确性：loss.backward/clip/Adam.step生效；数据受试者ID映射有当前等价性分析；训练只使用Public/VAL，freeze后reload TEST。六份独立checkpoint hash互异且各自reload匹配。
  依据：workspace/harbor_task/environment/starter/exp/exp_classification.py；expert_evidence/g02_support/improved_method_source/exp/exp_classification.py；expert_evidence/w1_recompute/data_pipeline_equivalence.md；optimization_evidence/baseline_runs/seed_41/reload_worker.json；optimization_evidence/baseline_runs/seed_42/reload_worker.json；optimization_evidence/baseline_runs/seed_43/reload_worker.json；optimization_evidence/reference_runs/seed_41/reload_worker.json；optimization_evidence/reference_runs/seed_42/reload_worker.json；optimization_evidence/reference_runs/seed_43/reload_worker.json
选择与对照完整性：正式seed41/42/43固定同一方法各自独立重训，无挑seed；旧batch16 2.7334σ、后建batch32 3.1487σ、非配对5seed2.0541σ和不对称口径均留存且不作正式主张。
  依据：optimization_evidence/comparison_summary.json；optimization_evidence/训练证据说明.md；expert_evidence/g02_support/matched_control/frozen_protocol.json

### G03 Reference 提升充分性

观察判定：pass；本轮判定：pass
全部有效成对值复算：Δ=0.1321885666=3.0762σ_B，归一化0.376886，剩余headroom0.2185501=5.0859σ_B，满足门槛。
审阅依据：workspace/harbor_task/instruction.md；optimization_evidence/comparison_summary.json；expert_evidence/g02_support/matched_control/frozen_protocol.json；workspace/harbor_task/environment/starter/models/BaselineFormer.py；expert_evidence/g02_support/improved_method_source/models/MedMamba.py；optimization_evidence/baseline_runs/seed_41/result.json；optimization_evidence/baseline_runs/seed_42/result.json；optimization_evidence/baseline_runs/seed_43/result.json；optimization_evidence/reference_runs/seed_41/result.json；optimization_evidence/reference_runs/seed_42/result.json；optimization_evidence/reference_runs/seed_43/result.json；optimization_evidence/baseline_runs/seed_41/reload_worker.json；optimization_evidence/baseline_runs/seed_42/reload_worker.json；optimization_evidence/baseline_runs/seed_43/reload_worker.json；optimization_evidence/reference_runs/seed_41/reload_worker.json；optimization_evidence/reference_runs/seed_42/reload_worker.json；optimization_evidence/reference_runs/seed_43/reload_worker.json；optimization_evidence/baseline_runs/seed_41/model/artifact.json；optimization_evidence/baseline_runs/seed_42/model/artifact.json；optimization_evidence/baseline_runs/seed_43/model/artifact.json；optimization_evidence/reference_runs/seed_41/model/artifact.json；optimization_evidence/reference_runs/seed_42/model/artifact.json；optimization_evidence/reference_runs/seed_43/model/artifact.json
正式复算：{"baseline_mean": 0.6492613306723666, "reference_mean": 0.7814498972875512, "baseline_sample_std": 0.04297184600022364, "reference_sample_std": 0.014044392510782851, "improvement": 0.13218856661518463, "run_count": 3, "sigma_multiplier": 3.076166814302012, "three_sigma_baseline": 0.12891553800067093, "normalized_score": 0.37688620666945655}

## 21 项内容与实现

### QA01 八章节与题面信息泄露

观察判定：pass；本轮判定：pass
题面含目标、环境、指标、修改范围、边界、提交、流程、完成条件；未披露MedMamba论文/源码或参考方法答案。
审阅依据：workspace/harbor_task/instruction.md

### QA02 评分公式与 0/1 锚点

观察判定：pass；本轮判定：pass
评分器使用未裁剪连续归一化(F1-B)/(1-B)，正向单调；B三seed均值代入0，U=1代入1。
审阅依据：workspace/harbor_task/tests/evaluate_verify.py；optimization_evidence/comparison_summary.json；expert_evidence/expert_annotation.json

### QA03 参考解分数与复现材料

观察判定：pass；本轮判定：pass
三正式Reference有完整方法源码、可识别入口run.py及冻结脚本/原日志/模型索引与重载，归一化0.376886。workspace/reference/ref_code是已标明的历史核心摘录，不作为独立正式入口。
审阅依据：expert_evidence/g02_support/improved_method_source/run.py；expert_evidence/g02_support/improved_method_source/models/MedMamba.py；expert_evidence/g02_support/improved_method_runs/reference_seed41/frozen_protocol.json；expert_evidence/w1_recompute/w1_recompute_report.json；optimization_evidence/reference_runs/seed_41/result.json；optimization_evidence/reference_runs/seed_42/result.json；optimization_evidence/reference_runs/seed_43/result.json；optimization_evidence/reference_runs/seed_41/run.log；optimization_evidence/reference_runs/seed_42/run.log；optimization_evidence/reference_runs/seed_43/run.log；optimization_evidence/reference_runs/seed_41/model/artifact.json；optimization_evidence/reference_runs/seed_42/model/artifact.json；optimization_evidence/reference_runs/seed_43/model/artifact.json；optimization_evidence/reference_runs/seed_41/reload_worker.json；optimization_evidence/reference_runs/seed_42/reload_worker.json；optimization_evidence/reference_runs/seed_43/reload_worker.json

### QA04 波动指标的 3σ 可分辨性

观察判定：pass；本轮判定：pass
seed41/42/43进入Python/NumPy/Torch/CUDA随机初始化；同一B/R方法版本各seed独立重训，六hash互异；样本σ_B复算3.0762σ。
审阅依据：expert_evidence/g02_support/improved_method_source/run.py；optimization_evidence/comparison_summary.json；optimization_evidence/baseline_runs/seed_41/result.json；optimization_evidence/baseline_runs/seed_42/result.json；optimization_evidence/baseline_runs/seed_43/result.json；optimization_evidence/reference_runs/seed_41/result.json；optimization_evidence/reference_runs/seed_42/result.json；optimization_evidence/reference_runs/seed_43/result.json；optimization_evidence/baseline_runs/seed_41/model/artifact.json；optimization_evidence/baseline_runs/seed_42/model/artifact.json；optimization_evidence/baseline_runs/seed_43/model/artifact.json；optimization_evidence/reference_runs/seed_41/model/artifact.json；optimization_evidence/reference_runs/seed_42/model/artifact.json；optimization_evidence/reference_runs/seed_43/model/artifact.json

### QA05 约束执行实现

观察判定：fail；本轮判定：fail
有冻结面SHA、参数量前置门、1800s训练wrapper与1200s推理计时；但题面把Python子进程宣称为候选不可触及Hidden/评分文件的边界，与当前调用链不符。禁网迁移另按白名单。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/tests/infer_candidate.py；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/environment/starter/scripts/APAVA_Subject.sh
- 题面声称候选代码无法影响评分且不能接触标签；实际子进程仅python -I/start_new_session，仍在同一Verifier文件系统/身份执行，候选模型import前未建立/tests/hidden_assets与评分文件的访问边界。-I隔离Python搜索路径，不限制文件访问，故当前绝对安全声明与实现不符。；处理：unwaived
  依据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/tests/infer_candidate.py；workspace/harbor_task/tests/Dockerfile
  修改方向：将当前声明限定到实际已有的Python进程隔离与可信后处理；若保留不可读写Hidden/评分文件承诺，应把可执行的权限/文件访问边界接入候选执行调用链，平台验证其效果。
  验收：静态调用链不再把-I/进程组称为文件隔离；保留的硬性承诺有对应实现。缺平台root/seccomp运行证明本身不判失败。
- 有效TOML已删除禁网字段；题面仍以交付审计核验禁外部资源，当前无网络约束执行点，保留原缺口但免本批新防护/补跑。；处理：waived
  依据：workspace/harbor_task/instruction.md；workspace/harbor_task/task.toml；workspace/harbor_task/tests/evaluate_verify.py
  豁免原因：unsupported_network_policy_transition；0.3.10-standard-waiver.5 本批白名单；已读所引原材料，保留事实与原判，仅免此历史/平台缺口，不宣称实际已完成。

### QA06 Verifier 入口、分数与错误处理

观察判定：fail；本轮判定：fail
test.sh与可信主进程有正式reward及无权重/超参数处理；超时分支返回3项而调用接收2项，导致约定的失败reward路径失效。
审阅依据：workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/tests/test.sh
- run_isolated_inference超时分支返回(status,None,None)，main以status,logits二元解包；该分支必然ValueError，无法进入约定的推理失败reward=-1处理。；处理：unwaived
  依据：workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/tests/test.sh
  修改方向：统一推理函数所有分支返回二元组，并由可信主进程处理超时与失败输出。
  验收：源码所有返回分支与调用方参数个数一致；平台后续验证超时能产生约定有限reward或明确约定的失败状态。

### QA07 instruction 中的 Hidden 信息泄露

观察判定：pass；本轮判定：pass
题面只列测试受试者ID及不可访问规则，没有测试特征、真实标签或可恢复答案。
审阅依据：workspace/harbor_task/instruction.md

### QA08 instruction 中的参考解信息泄露

观察判定：pass；本轮判定：pass
题面没有参考实现、具体参考配置/成绩或直接解法；允许SSM/注意力等一般方法类不等于泄露答案。
审阅依据：workspace/harbor_task/instruction.md

### QA09 结果清理与原子写入

观察判定：pass；本轮判定：pass
test.sh评分前删除已有reward与临时文件；write_reward使用O_EXCL唯一临时名、fsync与os.replace原子写出并回读。
审阅依据：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/evaluate_verify.py

### QA10 冻结面保护或恢复实现

观察判定：pass；本轮判定：pass
评分数据管线从tests自带可信副本加载，不导入候选数据管线；候选冻结面以TRUSTED_HASHES前后校验，有可识别保护逻辑。此项通过不认证完整进程/文件隔离。
审阅依据：workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/tests/trusted_data_provider/TRUSTED_HASHES.json；workspace/harbor_task/tests/trusted_data_provider/data_factory.py

### QA11 instruction 八项内容

观察判定：fail；本轮判定：fail
八部分实质内容齐全；公开Dev命令与镜像路径不一致，且不可触及评分/Hidden文件的绝对声明超出-I子进程实际边界。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/task.toml；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/tests/infer_candidate.py
- 题面/submit.dev_score_command为python evaluate.py --solution_dir ./solution；镜像只将evaluate.py放入/workspace/solution与starter，/workspace没有evaluate.py；在solution内执行又会寻找solution/solution/models，所给单命令与实际布局不一致。；处理：unwaived
  依据：workspace/harbor_task/instruction.md；workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/environment/starter/evaluate.py
  修改方向：将题面和submit命令统一为明确cwd与绝对solution/data路径，例如从/workspace调用solution/evaluate.py并指定/workspace/solution。
  验收：题面、配置和镜像布局形成同一有效路径链，公开Dev可通过所声明命令找到模型、权重和公开数据。
- 题面声称候选代码无法影响评分且不能接触标签；实际子进程仅python -I/start_new_session，仍在同一Verifier文件系统/身份执行，候选模型import前未建立/tests/hidden_assets与评分文件的访问边界。-I隔离Python搜索路径，不限制文件访问，故当前绝对安全声明与实现不符。；处理：unwaived
  依据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/tests/infer_candidate.py；workspace/harbor_task/tests/Dockerfile
  修改方向：将当前声明限定到实际已有的Python进程隔离与可信后处理；若保留不可读写Hidden/评分文件承诺，应把可执行的权限/文件访问边界接入候选执行调用链，平台验证其效果。
  验收：静态调用链不再把-I/进程组称为文件隔离；保留的硬性承诺有对应实现。缺平台root/seccomp运行证明本身不判失败。

### QA12 Git 清理

观察判定：pass；本轮判定：pass
1076普通文件清单中无.git路径；未据外部Git仓库或包内旧结论推定完成。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/task.toml

### QA13 Baseline 与参考解提升

观察判定：pass；本轮判定：pass
六正式运行全部同batch16/12轮/SWA，成对seed完整，模型哈希及独立重载匹配，全部正向且3.0762σ；无效旧Agent峰值不作正式B/R。
审阅依据：optimization_evidence/comparison_summary.json；expert_evidence/g02_support/matched_control/frozen_protocol.json；optimization_evidence/baseline_runs/seed_41/result.json；optimization_evidence/baseline_runs/seed_42/result.json；optimization_evidence/baseline_runs/seed_43/result.json；optimization_evidence/reference_runs/seed_41/result.json；optimization_evidence/reference_runs/seed_42/result.json；optimization_evidence/reference_runs/seed_43/result.json；optimization_evidence/baseline_runs/seed_41/run.log；optimization_evidence/baseline_runs/seed_42/run.log；optimization_evidence/baseline_runs/seed_43/run.log；optimization_evidence/reference_runs/seed_41/run.log；optimization_evidence/reference_runs/seed_42/run.log；optimization_evidence/reference_runs/seed_43/run.log；optimization_evidence/baseline_runs/seed_41/reload_worker.json；optimization_evidence/baseline_runs/seed_42/reload_worker.json；optimization_evidence/baseline_runs/seed_43/reload_worker.json；optimization_evidence/reference_runs/seed_41/reload_worker.json；optimization_evidence/reference_runs/seed_42/reload_worker.json；optimization_evidence/reference_runs/seed_43/reload_worker.json

### QA14 合法改进空间

观察判定：pass；本轮判定：pass
R均值0.78145未饱和，剩余0.21855；可在开放forward设计题面未直接给出的受试者不变表示/频谱统计与时序模块联合方法，现有r101结构为实际方法空间证据。
审阅依据：workspace/harbor_task/instruction.md；expert_evidence/g02_support/improved_method_source/models/MedMamba.py；workspace/harbor_task/solution/models/SolutionModel.py；optimization_evidence/comparison_summary.json

### QA15 评分资源需求估算

观察判定：manual；本轮判定：pass_with_waivers
按完整三seed训练/SWA/reload并加CPU推理余量估算6000s、1张H20/L20、16CPU；历史B/R为4090/4080 SUPER实测，目标卡耗时为推断，缺当前平台资源实测不等于超限。
审阅依据：workspace/harbor_task/task.toml；expert_evidence/g02_support/matched_control/preflight.json；expert_evidence/g02_support/improved_method_runs/reference_seed41/preflight.json；expert_evidence/w1_recompute/w1_recompute_report.json；optimization_evidence/baseline_runs/seed_41/result.json；optimization_evidence/baseline_runs/seed_42/result.json；optimization_evidence/baseline_runs/seed_43/result.json；optimization_evidence/reference_runs/seed_41/result.json；optimization_evidence/reference_runs/seed_42/result.json；optimization_evidence/reference_runs/seed_43/result.json
- B/R原机卡型真实保留，目标H20/L20资源仅据完整日志估算，未把原卡成绩/时间改标新卡实测。；处理：waived
  依据：expert_evidence/g02_support/matched_control/preflight.json；expert_evidence/g02_support/improved_method_runs/reference_seed41/preflight.json；workspace/harbor_task/task.toml
  豁免原因：legacy_hardware_record_difference；0.3.10-standard-waiver.5 本批白名单；已读所引原材料，保留事实与原判，仅免此历史/平台缺口，不宣称实际已完成。
- 有6000s/1GPU/16CPU有据估算，缺新版目标资源验证免补证；当前配置不超限。；处理：waived
  依据：workspace/harbor_task/task.toml；expert_evidence/w1_recompute/w1_recompute_report.json；optimization_evidence/baseline_runs/seed_41/result.json；optimization_evidence/baseline_runs/seed_42/result.json；optimization_evidence/baseline_runs/seed_43/result.json；optimization_evidence/reference_runs/seed_41/result.json；optimization_evidence/reference_runs/seed_42/result.json；optimization_evidence/reference_runs/seed_43/result.json
  豁免原因：legacy_target_resource_evidence_gap；0.3.10-standard-waiver.5 本批白名单；已读所引原材料，保留事实与原判，仅免此历史/平台缺口，不宣称实际已完成。

### QA16 轨迹实际迭代时长

观察判定：manual；本轮判定：pass_with_waivers
Codex扣尾150s后37666s；Seed扣尾1496s后36562s，但11948s未分类，有效秒数未知，保守24614s；训练任务不套7h例外。
审阅依据：expert_evidence/run_summary.json；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md
- Seed11948s未分类，有效时长未知；训练任务不作7h例外，按获准历史时长/证明缺口免补跑。；处理：waived
  依据：expert_evidence/run_summary.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md
  豁免原因：legacy_research_duration_gap；0.3.10-standard-waiver.5 本批白名单；已读所引原材料，保留事实与原判，仅免此历史/平台缺口，不宣称实际已完成。

### QA17 Harbor Harness 兼容性

观察判定：fail；本轮判定：fail
由H01-H06汇总：当前评分超时处理静态错误、内场镜像/运行待平台验证、历史NOP非当前版本；仅后两类可按具体原因豁免。
审阅依据：workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/tests/test.sh；workspace/harbor_task/task.toml；expert_evidence/nop_trial_native/task_identity_binding.md
Harbor逐项派生：H01=pass；H02=pass；H03=pass_with_waivers；H04=fail；H05=pass；H06=pass_with_waivers

### QA18 轨迹、日志与分析

观察判定：fail；本轮判定：pass_with_waivers
两主轨已逐轮审读317轮；有学习率/SWA窗违约、峰值与SWA混用及retained_best矛盾，相关旧分无效且不入正式B/R；实际Prompt/最高档等仅历史证明有限，另逐因豁免。
审阅依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md；expert_evidence/score_patch_record.json；expert_evidence/best_method_manifest.json
- 两轨历史研究存在固定lr/提交窗口违约、单epoch峰值混作SWA及保留标记矛盾；受影响旧分invalid，免新增追责/重跑。正式作者六次B/R独立，未采用旧Agent分。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；workspace/harbor_task/instruction.md；expert_evidence/专家作业说明文档.md；expert_evidence/best_method_manifest.json；expert_evidence/score_patch_record.json
  豁免原因：historical_agent_runtime_finding；0.3.10-standard-waiver.5 本批白名单；已读所引原材料，保留事实与原判，仅免此历史/平台缺口，不宣称实际已完成。
  原分数状态：invalid
  历史事实：cheating/confirmed；分数影响：invalid
  影响依据：明确固定协议与逐轮记录相冲突；codex r51/r101单epoch、seed r1改LR及r51-54改SWA窗；不推断动机。
  受污染或未证实的Agent分数不作为作者正式 B/R 正证；仅部署规则差异不自动改写分数。
- 已有实际模型名、独立box和空OUTPUT_DIR说明；无原始启动Prompt/最高推理档/全工具会话，核实范围有限，免新启动证明。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md
  豁免原因：legacy_runtime_proof_gap；0.3.10-standard-waiver.5 本批白名单；已读所引原材料，保留事实与原判，仅免此历史/平台缺口，不宣称实际已完成。
- Seed r44 no_result表示agent正常退出但无方法/评分产物，score=null、failure_reason非空、retained_best=false；旧自定义状态已据实审明，不是成功分数。；处理：waived
  依据：expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json
  豁免原因：legacy_trajectory_schema_gap；0.3.10-standard-waiver.5 本批白名单；已读所引原材料，保留事实与原判，仅免此历史/平台缺口，不宣称实际已完成。
- 已实际对比现有两轨材料，旧版材料仍不足以证明所有历史条件一致；仅此记录缺口豁免，不声称已证实同条件。已对比现行10-25/26两轨，不混用已退役10-03/04共用输出/765→1413口径史。两轨均描述APAVA/公开Dev n1413、独立box1/box2和空输出、4070 SUPER；模型不同合法。无原始Prompt与完整启动/反馈快照，不能证实全部条件相同；未发现已确认给两轨不同任务权限/IPC/反馈的反证。Agent各自改lr/SWA属行为而非被分配条件变化。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md；workspace/harbor_task/instruction.md；expert_evidence/trajectory_crosscheck.json
  豁免原因：legacy_runtime_proof_gap；本轮旧题迁移不要求新增Prompt快照、hash或重跑；已读资料中没有已确认的实质条件差异。

### QA19 seed 与有效提升阈值

观察判定：pass；本轮判定：pass
题面明确41/42/43、Δ≥3σ_B与归一化[0.15,0.8]；按随机训练评估审查，不因固定推理seed误作确定性不适用。
审阅依据：workspace/harbor_task/instruction.md

### QA20 修改范围、网络与工具策略

观察判定：pass；本轮判定：pass
题面列出可改范围、禁止外部资源和按平台默认工具策略；规则文字齐全。禁网实际执行缺口在QA05迁移原因记录。
审阅依据：workspace/harbor_task/instruction.md

### QA21 三个 JSON 的填写内容

观察判定：manual；本轮判定：pass_with_waivers
两轨JSON均严格八字段、轮次连续；annotation/run_summary可解析；四范围58文件指纹实算c58b5e60…与run_summary一致。r101峰值0.9781与最终SWA Dev0.9596006382已明确分层，历史版本绑定另列。
审阅依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/expert_annotation.json；expert_evidence/best_method_manifest.json；expert_evidence/swa_dev_measurement.json
- 当前c58b5e60…四项指纹一致；历史两轨发生于10-25/26，之后格式/评分器返修不能当成轨迹当时启动hash。保留迁移差异，不伪造旧绑定。；处理：waived
  依据：expert_evidence/run_summary.json；workspace/harbor_task/instruction.md；workspace/harbor_task/tests/evaluate_verify.py；expert_evidence/专家作业说明文档.md
  豁免原因：legacy_task_binding_migration；0.3.10-standard-waiver.5 本批白名单；已读所引原材料，保留事实与原判，仅免此历史/平台缺口，不宣称实际已完成。
- Seed r44 no_result的语义已读：正常退出但无方法/评分产物，score=null且有failure_reason、不保留best；旧自定义状态不等同成功。；处理：waived
  依据：expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json
  豁免原因：legacy_trajectory_schema_gap；本批明确免旧自定义status字段差异，仍保留真实内容及无分数事实。

## Harbor 六项

### H01 任务目录

观察判定：pass；本轮判定：pass
任务根workspace/harbor_task完整；公开Dev代码/19名受试者数据仅进入Agent；Hidden以注入契约、预检与历史Trial调用证据支持，缺资产fail-closed。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/hidden_assets/inject_contract.json；expert_evidence/nop_trial_native/verifier/test-stdout.txt

### H02 版本与配置

观察判定：pass；本轮判定：pass
TOML可解析，显式separate；innerfield-maso-v1，Agent1张H20/L20/16CPU，Verifier0GPU/8CPU；有效配置无storage/no-network/Compose，历史egress日志不当作当前生效。
审阅依据：workspace/harbor_task/task.toml；expert_evidence/run_summary.json

### H03 环境与运行路径

观察判定：manual；本轮判定：pass_with_waivers
Agent context=environment、Verifier context=tests，COPY来源与入口存在；专用tests镜像预置/tests/test.sh，顶层artifacts移交/workspace/solution。运行链仅本沙盒本地Python进程，无任务自建额外工作环境；内场镜像/启动待平台。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/tests/infer_candidate.py
- 有效双Dockerfile/COPY方案已交；实际ICM预构建镜像选择由平台准备，不冒称已在内场构建成功。；处理：waived
  依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/task.toml
  豁免原因：platform_image_preparation_pending；0.3.10-standard-waiver.5 本批白名单；已读所引原材料，保留事实与原判，仅免此历史/平台缺口，不宣称实际已完成。
- 路径与本地执行调用链已审，当前目标平台启动/依赖/移交运行仍待验证；未发现任务部署额外工作环境。；处理：waived
  依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/task.toml；workspace/harbor_task/tests/evaluate_verify.py
  豁免原因：platform_execution_verification_pending；0.3.10-standard-waiver.5 本批白名单；已读所引原材料，保留事实与原判，仅免此历史/平台缺口，不宣称实际已完成。

### H04 测试入口与 reward

观察判定：fail；本轮判定：fail
test.sh输出reward.json与reward.txt，优先JSON；正常分支数值有限，JSON附加指标合法。推理超时返回值个数错误导致失败处理无法写出约定reward。
审阅依据：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/evaluate_verify.py
- run_isolated_inference超时分支返回(status,None,None)，main以status,logits二元解包；该分支必然ValueError，无法进入约定的推理失败reward=-1处理。；处理：unwaived
  依据：workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/tests/test.sh
  修改方向：统一推理函数所有分支返回二元组，并由可信主进程处理超时与失败输出。
  验收：源码所有返回分支与调用方参数个数一致；平台后续验证超时能产生约定有限reward或明确约定的失败状态。
- 当前格式实质问题（来自 F03）：当前评分器超时分支返回3项，调用接收2项，约定的失败reward处理有确定静态错误。
  定位：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/evaluate_verify.py
- 当前格式实质问题（来自 F07）：评分器存在确定超时错误；题面公开Dev单命令路径与镜像实际布局不一致。
  定位：workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/instruction.md；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/task.toml

### H05 Job/Trial 调用配置

观察判定：pass；本轮判定：pass
已有NOP Trial config/job选择本题与nop，verifier未disable；Docker为历史provider记录，当前验收profile仍内场MASO，无将历史配置冒称当前平台实跑。
审阅依据：expert_evidence/nop_trial_native/config.json；expert_evidence/nop_trial_native/result.json；expert_evidence/run_summary.json

### H06 NOP 自检记录

观察判定：manual；本轮判定：pass_with_waivers
历史原生NOP两处agent=nop、separate、finished/无异常、JSON奖励优先且与result一致、日志非空；仅无权重早退n_test=0，不覆盖完整Hidden；绑定10-08历史版本，当前未跑。
审阅依据：expert_evidence/nop_trial_native/config.json；expert_evidence/nop_trial_native/result.json；expert_evidence/nop_trial_native/trial.log；expert_evidence/nop_trial_native/verifier/reward.json；expert_evidence/nop_trial_native/verifier/reward.txt；expert_evidence/nop_trial_native/verifier/test-stdout.txt；expert_evidence/nop_trial_native/task_identity_binding.md
- 原生NOP只绑定10-08版本，reward=-1/n_test=0早退分支并非完整Hidden；旧本地等效记录已退役。当前版本缺NOP免补跑，已有坏记录仍保留。；处理：waived
  依据：expert_evidence/nop_trial_native/config.json；expert_evidence/nop_trial_native/result.json；expert_evidence/nop_trial_native/trial.log；expert_evidence/nop_trial_native/verifier/reward.json；expert_evidence/nop_trial_native/verifier/reward.txt；expert_evidence/nop_trial_native/verifier/test-stdout.txt；expert_evidence/nop_trial_native/task_identity_binding.md；expert_evidence/nop_trial_local_equivalent_20261004_superseded/README.md
  豁免原因：legacy_nop_or_current_trial_gap；0.3.10-standard-waiver.5 本批白名单；已读所引原材料，保留事实与原判，仅免此历史/平台缺口，不宣称实际已完成。

## 两轨已有内容

### T01 第一条轨迹已有内容

观察判定：fail；本轮判定：pass_with_waivers
r1-50探索频带、相关性、池化和增广；r51起用单epoch最优替代SWA；r62/68/72稳健空间统计；r94/101软delta边界达到峰值；r133-260逐步退化为增广浮点微调，无后续净提升。轨迹r101单ep11 Dev=0.9781为违约峰值，不能当提交分；当前同代码SWA权重39fe274f…独立既有Dev记录0.9596006381555247，非Hidden。
审阅依据：expert_evidence/trajectory_codex.json；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md；expert_evidence/score_patch_record.json；expert_evidence/trajectory_crosscheck.json；expert_evidence/best_method_manifest.json；expert_evidence/swa_dev_measurement.json
方法：r1-50探索频带、相关性、池化和增广；r51起用单epoch最优替代SWA；r62/68/72稳健空间统计；r94/101软delta边界达到峰值；r133-260逐步退化为增广浮点微调，无后续净提升。
迭代内容：r1-50探索频带、相关性、池化和增广；r51起用单epoch最优替代SWA；r62/68/72稳健空间统计；r94/101软delta边界达到峰值；r133-260逐步退化为增广浮点微调，无后续净提升。
最终结果：轨迹r101单ep11 Dev=0.9781为违约峰值，不能当提交分；当前同代码SWA权重39fe274f…独立既有Dev记录0.9596006381555247，非Hidden。
分数采用范围：违规历史分invalid；其余训练峰值/summary/文件名只能按声明范围参考，均不并入作者正式B/R。最终SWA Dev单列，不称Hidden正式分。
已读来源：expert_evidence/trajectory_codex.json；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md；expert_evidence/score_patch_record.json；expert_evidence/trajectory_crosscheck.json；expert_evidence/best_method_manifest.json；expert_evidence/swa_dev_measurement.json
- 两轨历史研究存在固定lr/提交窗口违约、单epoch峰值混作SWA及保留标记矛盾；受影响旧分invalid，免新增追责/重跑。正式作者六次B/R独立，未采用旧Agent分。；处理：waived
  依据：expert_evidence/trajectory_codex.json；workspace/harbor_task/instruction.md；expert_evidence/专家作业说明文档.md；expert_evidence/best_method_manifest.json
  豁免原因：historical_agent_runtime_finding；0.3.10-standard-waiver.5 本批白名单；已读所引原材料，保留事实与原判，仅免此历史/平台缺口，不宣称实际已完成。
  原分数状态：invalid
  历史事实：cheating/confirmed；分数影响：invalid
  影响依据：明确固定协议与逐轮记录相冲突；codex r51/r101单epoch、seed r1改LR及r51-54改SWA窗；不推断动机。
  受污染或未证实的Agent分数不作为作者正式 B/R 正证；仅部署规则差异不自动改写分数。

### T02 第二条轨迹已有内容

观察判定：fail；本轮判定：pass_with_waivers
r1-12多尺度卷积、EEG增广与多seed；r15 balanced CE；r20-30 DropPath/SSM/R-Drop/SAM/融合多次失败；r31-50正则与冻结LR；r51-57缩SWA窗、门控读出及频域分支；r44无结果如实null。轨迹r54峰值0.84052，采用SWA ep5-9、lr5e-5/冻结LR，不满足固定lr/SWA协议；r57失败回退r52，摘要保留0.84031，不把0.84052当正式成绩。
审阅依据：expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md；expert_evidence/score_patch_record.json；expert_evidence/trajectory_crosscheck.json
方法：r1-12多尺度卷积、EEG增广与多seed；r15 balanced CE；r20-30 DropPath/SSM/R-Drop/SAM/融合多次失败；r31-50正则与冻结LR；r51-57缩SWA窗、门控读出及频域分支；r44无结果如实null。
迭代内容：r1-12多尺度卷积、EEG增广与多seed；r15 balanced CE；r20-30 DropPath/SSM/R-Drop/SAM/融合多次失败；r31-50正则与冻结LR；r51-57缩SWA窗、门控读出及频域分支；r44无结果如实null。
最终结果：轨迹r54峰值0.84052，采用SWA ep5-9、lr5e-5/冻结LR，不满足固定lr/SWA协议；r57失败回退r52，摘要保留0.84031，不把0.84052当正式成绩。
分数采用范围：违规历史分invalid；其余训练峰值/summary/文件名只能按声明范围参考，均不并入作者正式B/R。最终SWA Dev单列，不称Hidden正式分。
已读来源：expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md；expert_evidence/score_patch_record.json；expert_evidence/trajectory_crosscheck.json
- 两轨历史研究存在固定lr/提交窗口违约、单epoch峰值混作SWA及保留标记矛盾；受影响旧分invalid，免新增追责/重跑。正式作者六次B/R独立，未采用旧Agent分。；处理：waived
  依据：expert_evidence/trajectory_seed.json；workspace/harbor_task/instruction.md；expert_evidence/专家作业说明文档.md；expert_evidence/best_method_manifest.json
  豁免原因：historical_agent_runtime_finding；0.3.10-standard-waiver.5 本批白名单；已读所引原材料，保留事实与原判，仅免此历史/平台缺口，不宣称实际已完成。
  原分数状态：invalid
  历史事实：cheating/confirmed；分数影响：invalid
  影响依据：明确固定协议与逐轮记录相冲突；codex r51/r101单epoch、seed r1改LR及r51-54改SWA窗；不推断动机。
  受污染或未证实的Agent分数不作为作者正式 B/R 正证；仅部署规则差异不自动改写分数。

## 两轨实际条件对比

对比已完成：是
条件判断：historical_evidence_gap；成对对照有效性：unverified
已对比现行10-25/26两轨，不混用已退役10-03/04共用输出/765→1413口径史。两轨均描述APAVA/公开Dev n1413、独立box1/box2和空输出、4070 SUPER；模型不同合法。无原始Prompt与完整启动/反馈快照，不能证实全部条件相同；未发现已确认给两轨不同任务权限/IPC/反馈的反证。Agent各自改lr/SWA属行为而非被分配条件变化。
已对比维度：prompt、task、dev、feedback、constraints、resources
对比依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md；workspace/harbor_task/instruction.md；expert_evidence/trajectory_crosscheck.json
质检员内部对比底稿；不要求专家新增字段、Prompt快照、hash或重跑。语义判断须实际阅读原材料，脚本只核验审阅覆盖及判定一致性。
- resources / legacy_format_or_resource：现行两轨均声明独立4070 SUPER机器；与当前H20/L20配置属历史迁移差异，不改写旧卡。
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；workspace/harbor_task/task.toml

## 当前格式前检 F01–F07（子检查）

format_decision：FAIL
以下仅为当前格式子检查；整题结论以本报告顶部完整质检结果为准。

- F01 [pass] 当前必需目录、文件与 TOML 接口：三目录、选定task根及TOML接口存在。
  格式审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/task.toml
- F02 [pass] 有效构建或镜像方案、构建上下文及 COPY 来源：双Dockerfile按各自context，COPY来源完整；ICM镜像准备是平台事项。
  格式审阅依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile
- F03 [fail] 评分入口、独立依赖声明与固定输出路径：当前评分器超时分支返回3项，调用接收2项，约定的失败reward处理有确定静态错误。
  格式审阅依据：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/evaluate_verify.py
  修改方向：统一推理函数所有分支返回二元组，并由可信主进程处理超时与失败输出。
  验收：源码所有返回分支与调用方参数个数一致；平台后续验证超时能产生约定有限reward或明确约定的失败状态。
- F04 [pass] 提交物 artifacts 移交契约：顶层artifacts含/workspace/solution，与Verifier消费目录一致。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/test.sh
- F05 [pass] 公开 Dev、私有 Hidden 供给与 Agent 隔离：公开Dev和训练/验证数据供Agent；Hidden仅tests注入契约并有历史日志调用，不COPY进Agent。
  格式审阅依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/hidden_assets/inject_contract.json；workspace/harbor_task/tests/test.sh；expert_evidence/nop_trial_native/verifier/test-stdout.txt
- F06 [pass] separate、单容器、无 Compose 与当前目标资源配置：separate、无正式Compose；本沙盒本地进程；AgentH20/L20单卡、VerifierCPU0GPU。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/evaluate_verify.py
- F07 [fail] 当前评分实现与冻结面无确证故障或作者泄漏造假：评分器存在确定超时错误；题面公开Dev单命令路径与镜像实际布局不一致。
  格式审阅依据：workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/instruction.md；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/task.toml
  修改方向：将题面和submit命令统一为明确cwd与绝对solution/data路径，例如从/workspace调用solution/evaluate.py并指定/workspace/solution。
  验收：题面、配置和镜像布局形成同一有效路径链，公开Dev可通过所声明命令找到模型、权重和公开数据。

## 平台后续事项（不阻断本轮已有材料审阅）

- 字节内部准备、构建或导入镜像并配置实际 ICM tag；本轮不要求专家补内部镜像运行记录。
- 平台实际构建和启动，核对依赖、基础镜像 digest 及 bash/解释器；静态推断不能冒充运行结果。
- 平台核对 root、seccomp、网络及实际分配的沙盒权限设置。
- 平台后续执行当前版本 Harbor Trial/NOP、独立 Verifier 和 reward 收集；其缺口不作为本轮专家返修门槛。
- 已有原硬件结果本轮复核；不把旧值改称新硬件实测，不要求新环境补跑；平台核对实际当前提交物移交及目标硬件运行。
- 移除不支持的禁网字段后，新的联网或外部查表防护尚未落实，列为平台迁移事项，不要求本批专家新增防护实现或补跑；当前确证 Hidden 暴露或假 reward 仍属当前核心缺陷。

## 原 v0.3.10 自动检查及 NOP 原判

已调用原标准审计入口：True
NOP：{"status": "manual", "runtime_status": "unverified", "trials": [{"trial_dir": "expert_evidence/nop_trial_local_equivalent_20261004_superseded", "evidence": ["expert_evidence/nop_trial_local_equivalent_20261004_superseded/config.json", "expert_evidence/nop_trial_local_equivalent_20261004_superseded/result.json", "expert_evidence/nop_trial_local_equivalent_20261004_superseded/verifier/reward.json", "expert_evidence/nop_trial_local_equivalent_20261004_superseded/verifier/reward.txt", "expert_evidence/nop_trial_local_equivalent_20261004_superseded/trial.log", "expert_evidence/nop_trial_local_equivalent_20261004_superseded/verifier/test-stdout.txt"], "status": "manual", "summary": "Harbor Trial task.toml hash disagrees with the inspected task", "protected": false}, {"trial_dir": "expert_evidence/nop_trial_native", "evidence": ["expert_evidence/nop_trial_native/config.json", "expert_evidence/nop_trial_native/result.json", "expert_evidence/nop_trial_native/verifier/reward.json", "expert_evidence/nop_trial_native/verifier/reward.txt", "expert_evidence/nop_trial_native/trial.log", "expert_evidence/nop_trial_native/verifier/test-stdout.txt"], "status": "manual", "summary": "Harbor Trial identifies a different task; a reviewed task mapping is required", "protected": false}], "summary": "逐份读取并校验已有 NOP 记录；未启动新的 Trial。"}

原报告与全部详细结果：standard/report.json；不因豁免覆盖原判。

| 来源 | 项目 | 原判 | 本轮处理 | 依据及原因 |
|---|---|---|---|---|
| checks/QA05 | QA05 | fail | fail | 有冻结面SHA、参数量前置门、1800s训练wrapper与1200s推理计时；但题面把Python子进程宣称为候选不可触及Hidden/评分文件的边界，与当前调用链不符。禁网迁移另按白名单。 |
| checks/QA06 | QA06 | fail | fail | test.sh与可信主进程有正式reward及无权重/超参数处理；超时分支返回3项而调用接收2项，导致约定的失败reward路径失效。 |
| checks/QA11 | QA11 | fail | fail | 八部分实质内容齐全；公开Dev命令与镜像路径不一致，且不可触及评分/Hidden文件的绝对声明超出-I子进程实际边界。 |
| checks/QA15 | QA15 | manual | pass_with_waivers | 缺少：当前成绩的硬件归属/换卡影响尚未确认 |
| checks/QA16 | QA16 | manual | pass_with_waivers | Codex + Seed 2.1 Turbo缺少有效时长或排除排队/安装/故障的核算证据 |
| checks/QA17 | QA17 | fail | derived_from_details | Harbor 子项未通过：H03 环境与运行路径；H04 测试入口与 reward；H06 NOP 自检记录；详细原因与证据保留在 report.json。 |
| checks/QA18 | QA18 | fail | pass_with_waivers | 两条轨迹的八字段证据未通过：rounds[43].status='no_result' 为自定义状态；需人工确认成功/失败含义及对应分数、失败原因和最佳标记。 |
| checks/QA21 | QA21 | manual | pass_with_waivers | 两条轨迹的八字段证据未通过：rounds[43].status='no_result' 为自定义状态；需人工确认成功/失败含义及对应分数、失败原因和最佳标记。 |
| harbor/H03 | H03 | manual | pass_with_waivers | Agent context=environment、Verifier context=tests，COPY来源与入口存在；专用tests镜像预置/tests/test.sh，顶层artifacts移交/workspace/solution。运行链仅本沙盒本地Python进程，无任务自建额外工作环境；内场镜像/启动待平台。 |
| harbor/H04 | H04 | fail | fail | test.sh输出reward.json与reward.txt，优先JSON；正常分支数值有限，JSON附加指标合法。推理超时返回值个数错误导致失败处理无法写出约定reward。 |
| harbor/H06 | H06 | manual | derived_from_details | 历史原生NOP两处agent=nop、separate、finished/无异常、JSON奖励优先且与result一致、日志非空；仅无权重早退n_test=0，不覆盖完整Hidden；绑定10-08历史版本，当前未跑。 |
| resources/gaps/0 | QA15 | manual | pass_with_waivers | 当前成绩的硬件归属/换卡影响尚未确认 |
| trajectory_schema/1/0 | QA18 | manual | pass_with_waivers | rounds[43].status='no_result' 为自定义状态；需人工确认成功/失败含义及对应分数、失败原因和最佳标记。 |
| trajectory/0/finding/0 | QA18 | fail | pass_with_waivers | 仅指已确认固定协议违约的历史方法/成绩，不推测主观动机；正式作者B/R另有独立全seed证据且未采用这些分数。 |
| trajectory/1/finding/0 | QA18 | fail | pass_with_waivers | 仅指已确认固定协议违约的历史方法/成绩，不推测主观动机；正式作者B/R另有独立全seed证据且未采用这些分数。 |
| nop/trials/0 | H06 | manual | pass_with_waivers | Harbor Trial task.toml hash disagrees with the inspected task |
| nop/trials/1 | H06 | manual | pass_with_waivers | Harbor Trial identifies a different task; a reviewed task mapping is required |
