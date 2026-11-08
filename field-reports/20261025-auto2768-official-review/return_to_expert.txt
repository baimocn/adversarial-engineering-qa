# 旧题完整质检与逐原因豁免

本轮结论：FAIL
阶段：standard_review_with_waivers
已完成全部内容审阅：是

原 v0.3.10 全部检查及完整内容审阅已完成，包括已有 NOP；仅按具体历史原因豁免。未执行题包代码或新增 Harbor Trial。
平台实跑：not_executed；未执行模型、题目程序、Docker 或 Harbor。

## 方法与正式对照

在冻结噪声标签和两层GCN骨干下，研究抗噪损失、样本/邻居加权、训练标签可靠性、图一致性与标签无关推断读出；可新增静态方法类或PLAN数值方法，不限常量搜索。
可修改：training_objective与数值方法钩子；训练样本权重、伪标签及辅助损失；同骨干inference_readout与分阶段集成PLAN；共同7200秒预算内的epoch日程
冻结面：两图特征/边/划分及冻结噪声标签；GCN hidden64/2层/dropout0.5；Adam lr0.01 weight_decay0.0005；验证标签仅评价选点；测试标签仅Verifier
指标与质量门：隐藏测试两图accuracy百分数宏平均，maximize；score=(x-B)/(U-B)，B=61.8833 U=75.1333，不裁剪；题面要求模型可加载和非恒定预测。资格三seed改善≥3σ_B且归一化[0.15,0.8]。
Baseline：未修改Starter：两层GCN，冻结损坏训练标签交叉熵，Adam固定超参，200次更新，验证准确率选最佳checkpoint。
Reference：修复版DREAM：仅损坏训练标签的结构/特征kNN双路LP估计同类锚点，用语义同质性加权交叉熵并辅以对比损失和温度缩放；500次更新，同骨干、同选点规则。
正式改善：全部三组正式成对值：3000 60.05→70.25；3001 62.6→71.4；3002 63→69.95。Δ=8.65000000，σ_B=1.60026040，Δ/σ_B=5.40537029；生效U归一化=0.65283183，预声明100天花板对照=0.22693485，均达标。
质量有效性：正式12个模型的字节SHA/大小与artifact、training_summary、正式测试索引一致；记录全部正常结束、非退化且独立重载预测相同。未独立复跑。当前grader没有实施模型加载质量门，单列当前实现缺陷；不据此无差别否认历史正式记录。
已有原始对照：[{"seed": 3000, "baseline": 60.05, "reference": 70.25, "baseline_valid": true, "reference_valid": true}, {"seed": 3001, "baseline": 62.6, "reference": 71.4, "baseline_valid": true, "reference_valid": true}, {"seed": 3002, "baseline": 63.0, "reference": 69.95, "baseline_valid": true, "reference_valid": true}]
依据：optimization_evidence/formal_test_scoring_declared.json；optimization_evidence/comparison_summary.json；optimization_evidence/训练证据说明.md；workspace/harbor_task/tests/calibration.json；expert_evidence/repair/protocol_decisions.json

## 研究三门

### G01 方法级优化空间

观察判定：pass；本轮判定：pass
开放损失、可靠性权重、数值PLAN与图读出，固定框架未把研究空间缩为常量。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/contract_guard.py；workspace/harbor_task/environment/starter/predictor/Base_Predictor.py；workspace/reference/predictor/DREAM_Predictor.py

### G02 Baseline 合理性

观察判定：pass；本轮判定：pass
Baseline在已有材料范围内合理；五维与B01–B08已核，未见故障、挑seed或无依据截短。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/environment/starter/predictor/Base_Predictor.py；optimization_evidence/formal_test_scoring_declared.json；expert_evidence/repair/protocol_decisions.json
训练充分性：B每图完整200步，末期验证已从选中峰值回落；R每图500步，均epoch_budget_exhausted、无异常。B选中epoch 8/39、7/4、6/5，未见无依据截短。
  依据：workspace/harbor_task/environment/starter/predictor/Base_Predictor.py；optimization_evidence/baseline_runs/seed_3000/result.json；optimization_evidence/baseline_runs/seed_3001/model/cora/training.jsonl；optimization_evidence/baseline_runs/seed_3002/model/citeseer/training.jsonl
方法代表性：正式B与Starter和主评分0锚点明确映射；普通GCN+CE是本题噪声鲁棒性研究的可解释朴素起点。未见适用同预算常见更强锚点反证，不按年份或分差判弱化。
  依据：workspace/harbor_task/instruction.md；expert_evidence/expert_annotation.json；workspace/harbor_task/environment/starter/predictor/GCN_Predictor.py
原协议预算可比性：B200/R500为已披露原默认日程；当前题面明确epoch是共同7200s预算下允许变量，两侧同CPU、两图和数据边界。实际B约56–59s、R约426–494s，不能把资源内日程差直接判不公平；收益属于整体方法加日程，不声称单项消融贡献。
  依据：workspace/harbor_task/instruction.md；expert_evidence/repair/protocol_decisions.json；optimization_evidence/baseline_runs/seed_3000/result.json；optimization_evidence/reference_runs/seed_3000/result.json
实现正确性：共同trainer执行zero_grad/backward/Adam step、验证选点后strict重载；B损坏train标签CE，R伪锚点来自train-only LP；12个checkpoint大小/SHA与正式测试索引一致。
  依据：workspace/harbor_task/environment/starter/predictor/Base_Predictor.py；workspace/reference/predictor/DREAM_Predictor.py；optimization_evidence/formal_test_scoring_declared.json；optimization_evidence/reference_runs/seed_3000/model/artifact.json
选择与对照完整性：3000/3001/3002全部成对；每侧同一候选配置独立初始化；12个权重哈希均不同；失败的三组公开开发实验和v7失效记录保留且未混入正式TEST聚合。
  依据：optimization_evidence/comparison_summary.json；expert_evidence/repair/protocol_decisions.json；optimization_evidence/historical_v7_invalid_reference/README.md；expert_evidence/repair/README_NOT_READY.md

### G03 Reference 提升充分性

观察判定：pass；本轮判定：pass
三组正式测试改善8.65=5.4054σ_B；生效锚点分数0.65283，预声明100口径0.22693，均达标。
审阅依据：optimization_evidence/formal_test_scoring_declared.json；optimization_evidence/comparison_summary.json；workspace/harbor_task/tests/calibration.json；expert_evidence/repair/protocol_decisions.json；optimization_evidence/u_anchor_oracle/measurement.json
正式复算：{"baseline_mean": 61.88333333333333, "reference_mean": 70.53333333333335, "baseline_sample_std": 1.6002603954773547, "reference_sample_std": 0.765397500213671, "improvement": 8.650000000000013, "run_count": 3, "sigma_multiplier": 5.405370291264212, "three_sigma_baseline": 4.800781186432064, "normalized_score": 0.652831831023475}

## 21 项内容与实现

### QA01 八章节与题面信息泄露

观察判定：pass；本轮判定：pass
八章节齐全，描述任务和接口，未给DREAM名、论文或仓库来源。
审阅依据：workspace/harbor_task/instruction.md

### QA02 评分公式与 0/1 锚点

观察判定：pass；本轮判定：pass
可信calibration B=61.8833 U=75.1333；normalize_score直接(x-B)/(U-B)，连续单调且不裁剪，B→0/U→1。
审阅依据：workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/contract_guard.py；workspace/harbor_task/tests/calibration.json

### QA03 参考解分数与复现材料

观察判定：pass；本轮判定：pass
Reference源码/入口和三个正式seed的实际日志、模型索引及独立重载俱全；归一化0.65283有效，历史v7失效结果未采用。
审阅依据：workspace/reference/predictor/DREAM_Predictor.py；workspace/reference/train.py；optimization_evidence/formal_test_scoring_declared.json；optimization_evidence/comparison_summary.json；optimization_evidence/reference_runs/seed_3000/result.json；optimization_evidence/reference_runs/seed_3001/result.json；optimization_evidence/reference_runs/seed_3002/result.json

### QA04 波动指标的 3σ 可分辨性

观察判定：pass；本轮判定：pass
setup_seed进入Python/numpy/torch；三seed同集合固定方法独立重训，改善8.65≥3×1.6002604；不是同checkpoint重复评估。
审阅依据：workspace/harbor_task/environment/starter/utils/tools.py；optimization_evidence/formal_test_scoring_declared.json；optimization_evidence/comparison_summary.json

### QA05 约束执行实现

观察判定：fail；本轮判定：fail
单轮7200秒仅声明而未执行；模型加载质量门未实施。网络约束迁移单独保留豁免。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/task.toml；workspace/harbor_task/environment/starter/predictor/Base_Predictor.py；workspace/harbor_task/tests/grader.py
- 题面仍规定单轮7200秒有效预算，但task.toml明确declared_only；训练、run.sh与grader无单轮timeout。43200秒Agent总超时和3600秒纯Verifier超时不覆盖该训练阶段。；处理：unwaived
  依据：workspace/harbor_task/instruction.md；workspace/harbor_task/task.toml；workspace/harbor_task/environment/starter/run.sh；workspace/harbor_task/environment/starter/predictor/Base_Predictor.py
  修改方向：在可信启动/训练控制链加入覆盖每轮两图训练、导出与必要重载的7200秒计时与超时处理，保持题面和配置一致。
  验收：可定位的可信计时/终止实现与阶段覆盖说明；平台后续运行验证不作为本轮要求补跑历史轨迹。
- instruction §3要求模型可加载，§6要求模型产物；grader仅读取test_pred.npy，既不检查model.pt存在也不重载。源码AST检查不证明模型可加载，缺模型仍可进入正常评分。；处理：unwaived
  依据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/contract_guard.py；workspace/harbor_task/environment/public_eval/protocol.json
  修改方向：在独立可信Verifier实施模型存在及可加载质量门并使用与题面一致的安全重载接口；同步准备独立依赖。
  验收：可信评分调用链中可定位的模型检查/加载与失败分支，明确模型和预测对应路径。
- 当前不申请禁网/白名单；题面禁止外部查表但无网络执行机制，源AST不能认证外部训练或查表。；处理：waived
  依据：workspace/harbor_task/instruction.md；workspace/harbor_task/task.toml；workspace/harbor_task/tests/contract_guard.py
  豁免原因：unsupported_network_policy_transition；仅按本批已授权网络政策迁移处理无机制部分，不覆盖直接Hidden暴露、未支持字段或其他静态缺陷。

### QA06 Verifier 入口、分数与错误处理

观察判定：pass；本轮判定：pass
bash /tests/test.sh经隔离Python进入grader，异常分层并落有限reward.json/txt；不把模型门缺陷掩盖为已加载。
审阅依据：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/grader.py

### QA07 instruction 中的 Hidden 信息泄露

观察判定：pass；本轮判定：pass
仅审题面：未披露私有测试标签、样本答案或可恢复答案。
审阅依据：workspace/harbor_task/instruction.md

### QA08 instruction 中的参考解信息泄露

观察判定：fail；本轮判定：fail
题面第69行披露Reference采用500 epochs，而n_epochs本身为研究变量；属于参考具体可变配置泄露。
审阅依据：workspace/harbor_task/instruction.md:69
- instruction第69行直接披露正式Reference采用500 epochs，同时明确n_epochs是可研究变量。这是参考实现实际可变配置，不是必须固定的骨干接口；不符合QA08题面不得披露参考具体配置的要求。；处理：unwaived
  依据：workspace/harbor_task/instruction.md:69
  修改方向：将正式B/R各自实际epoch日程移到专家侧证据，题面仅保留共同预算与epoch可研究的规则。
  验收：instruction保留完整可操作接口和预算，且不再披露Reference的实际可变日程；专家侧预算对照仍保留。

### QA09 结果清理与原子写入

观察判定：pass；本轮判定：pass
main预清理reward.json/txt；临时文件写入后os.replace原子替换。
审阅依据：workspace/harbor_task/tests/grader.py

### QA10 冻结面保护或恢复实现

观察判定：pass；本轮判定：pass
Verifier-owned policy固定AST和配置，冻结数据/调度/训练及评价骨架；独立镜像calibration不执行候选自证钩子，Agent仅solution可写。
审阅依据：workspace/harbor_task/tests/contract_guard.py；workspace/harbor_task/tests/contract_policy.json；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile

### QA11 instruction 八项内容

观察判定：fail；本轮判定：fail
八项内容俱全，但可加载模型门与仅预测数组评分不一致；配置的公开Dev输出与默认身份权限不一致。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/grader.py；workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/environment/public_eval/evaluate.py
- instruction §3要求模型可加载，§6要求模型产物；grader仅读取test_pred.npy，既不检查model.pt存在也不重载。源码AST检查不证明模型可加载，缺模型仍可进入正常评分。；处理：unwaived
  依据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/contract_guard.py；workspace/harbor_task/environment/public_eval/protocol.json
  修改方向：在独立可信Verifier实施模型存在及可加载质量门并使用与题面一致的安全重载接口；同步准备独立依赖。
  验收：可信评分调用链中可定位的模型检查/加载与失败分支，明确模型和预测对应路径。
- task.toml dev_score_command将--out设为/workspace/results.json；Agent Dockerfile使/workspace root所有0755并切换USER agent，仅/workspace/solution属于agent。evaluate.py无条件open该输出，配置命令在默认身份下不可写并退出失败。；处理：unwaived
  依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/environment/public_eval/evaluate.py
  修改方向：将配置的Dev输出改到Agent可写目录，例如/workspace/solution/results.json，并同步任何引用；或在镜像中仅准备所需可写输出位置。
  验收：task.toml命令、镜像权限与evaluate.py实际写路径静态一致；无需通过放宽公开/私有冻结面权限修复。

### QA12 Git 清理

观察判定：pass；本轮判定：pass
安全清点题包未见.git目录；不把报告工作区的.git占位目录当题包内容。
审阅依据：workspace/harbor_task/task.toml

### QA13 Baseline 与参考解提升

观察判定：pass；本轮判定：pass
三组正式隐藏TEST成对原值完整，方法和种子固定，均正改善、质量记录通过；验证集字段更名不混用；B合理，G03数值达标。
审阅依据：optimization_evidence/formal_test_scoring_declared.json；optimization_evidence/comparison_summary.json；expert_evidence/repair/protocol_decisions.json；optimization_evidence/训练证据说明.md

### QA14 合法改进空间

观察判定：pass；本轮判定：pass
开放数值方法接口支持损失/样本选择/图读出联合设计；R尚非饱和，双路一致性和可靠性更新存在合法方法空间，未在题面给出答案。
审阅依据：workspace/harbor_task/instruction.md；workspace/reference/predictor/DREAM_Predictor.py；workspace/harbor_task/tests/contract_guard.py

### QA15 评分资源需求估算

观察判定：pass；本轮判定：pass
CPU题，两侧16CPU/0GPU；按最慢正式R493.55s及额外重载开销留余量估整轮900s/16CPU/0GPU，<2h/<64CPU。CPU历史结果未改标H20实测。
审阅依据：workspace/harbor_task/task.toml；optimization_evidence/reference_runs/seed_3001/result.json；optimization_evidence/reference_runs/seed_3001/model/reload.log

### QA16 轨迹实际迭代时长

观察判定：manual；本轮判定：pass_with_waivers
已审全部计时表及原session事件映射，声明时长与可计有效时长分开；映射明确provisional，未证明当前协议各10h。
审阅依据：expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/run_summary.json；expert_evidence/timing_codex.tsv；expert_evidence/timing_seed.tsv
- TSV宣称Codex39613/Seed41572秒；timing_map分别给出38589.395/39236.909 provisional秒、直接训练评测下界11488/19413.651秒，strict_fully_bound为null；存在缺行、重复窗口及阻塞未完整分类，原标准有效时长未获确认。；处理：waived
  依据：expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/timing_codex.tsv；expert_evidence/timing_seed.tsv；expert_evidence/run_summary.json
  豁免原因：legacy_research_duration_gap；保留原manual与全部实际数值；历史时长证明差异免补跑，训练题不使用7h例外。

### QA17 Harbor Harness 兼容性

观察判定：fail；本轮判定：fail
由H01–H06派生：当前Dev写权限和模型门静态缺陷保留；内部镜像准备、运行验证及历史NOP迁移分别处理。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/grader.py；expert_evidence/repair/harbor/native_nop_trial/native_trial/result.json
Harbor逐项派生：H01=pass；H02=pass；H03=fail；H04=fail；H05=pass_with_waivers；H06=pass_with_waivers

### QA18 轨迹、日志与分析

观察判定：manual；本轮判定：pass_with_waivers
全读Codex193/Seed53轮与事件映射、best及复验；没有已交原始sessions，行为范围为现有摘要/事件。实际模型可识别；原启动/同条件证明缺口，Seed71.4不改写为当前71.2。
审阅依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/run_summary.json；expert_evidence/best_method_selection.json
- 实际模型由run_summary和轨迹头交叉映射；独立session ID与不同演进支持分别运行，但无完整原Prompt、最高推理档位/空输出启动证明；无已确认两轨实质条件不同反证。；处理：waived
  依据：expert_evidence/run_summary.json；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/repair/historical_timing_mapping/timing_map.json
  豁免原因：legacy_runtime_proof_gap；只豁免旧启动/同条件证明不足，不将其写成已证明相同，也不覆盖可定位条件差异。
- 已实际对比现有两轨材料，旧版材料仍不足以证明所有历史条件一致；仅此记录缺口豁免，不声称已证实同条件。已比较两轨全部轮次、公共起点59.7/相同两图、数据/反馈/约束/资源说明及源事件映射。现有材料支持不同session的独立研究，无identical_prompt=false或已确认反馈/IPC/只读条件被逐轨改变的证据。没有原始完整启动Prompt/资源配置快照，不能把摘要相同升级为已证明同条件。当前v8接口迁移发生于两条历史v7研究之后，与历史两轨彼此不同分开。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/run_summary.json；workspace/harbor_task/instruction.md；expert_evidence/专家作业说明文档.md
  豁免原因：legacy_runtime_proof_gap；本轮旧题迁移不要求新增Prompt快照、hash或重跑；已读资料中没有已确认的实质条件差异。

### QA19 seed 与有效提升阈值

观察判定：pass；本轮判定：pass
题面明确冻结corruption seed3000、训练seed3000/3001/3002和样本σ_B的3σ有效提升阈值；区分资格多seed与单候选reward。
审阅依据：workspace/harbor_task/instruction.md

### QA20 修改范围、网络与工具策略

观察判定：pass；本轮判定：pass
题面有可改文件/数值边界、网络查表禁令、平台默认工具策略和禁止评分器篡改。
审阅依据：workspace/harbor_task/instruction.md

### QA21 三个 JSON 的填写内容

观察判定：manual；本轮判定：pass_with_waivers
两轨八字段246轮均具备，旧ok状态/展示时区已识别；annotation/summary/best可解析。当前四项e5a5eb…匹配45文件，历史v7到当前接口绑定仅按迁移处理。
审阅依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/expert_annotation.json；expert_evidence/best_method_selection.json；workspace/harbor_task/instruction.md
- 当前45文件四项指纹与run_summary匹配；两条研究保留原v7身份，当前train-only接口为返修迁移，不能用当前hash追溯认证历史。；处理：waived
  依据：expert_evidence/run_summary.json；workspace/harbor_task/instruction.md；expert_evidence/repair/historical_timing_mapping/timing_map.json
  豁免原因：legacy_task_binding_migration；只处理历史研究到当前返修包的版本绑定迁移，不处理历史两轨彼此实质条件变化。

## Harbor 六项

### H01 任务目录

观察判定：pass；本轮判定：pass
任务根、两侧构建、私有npz与公开Dev资产都有明确来源；Hidden仅复制进tests专用镜像。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/grader.py

### H02 版本与配置

观察判定：pass；本轮判定：pass
完整TOML可解析，目标本地Harbor0.24.0提交明确；固定按innerfield-maso-v1复核，两侧CPU16/GPU0、显式separate，无不支持字段或正式Compose。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile

### H03 环境与运行路径

观察判定：fail；本轮判定：fail
当前Agent仅solution可写，配置Dev输出/workspace/results.json不可写。两侧单容器、直接本地执行，无任务自部署额外环境；镜像准备和运行验证另列。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/environment/public_eval/evaluate.py；workspace/harbor_task/tests/test.sh
- task.toml dev_score_command将--out设为/workspace/results.json；Agent Dockerfile使/workspace root所有0755并切换USER agent，仅/workspace/solution属于agent。evaluate.py无条件open该输出，配置命令在默认身份下不可写并退出失败。；处理：unwaived
  依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/environment/public_eval/evaluate.py
  修改方向：将配置的Dev输出改到Agent可写目录，例如/workspace/solution/results.json，并同步任何引用；或在镜像中仅准备所需可写输出位置。
  验收：task.toml命令、镜像权限与evaluate.py实际写路径静态一致；无需通过放宽公开/私有冻结面权限修复。
- 两侧有效Dockerfile和依赖方案可读，当前内场预构建、内部镜像tag与实际可达性待平台准备。；处理：waived
  依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/task.toml；expert_evidence/repair/IMAGER_VERIFICATION_20261022.md
  豁免原因：platform_image_preparation_pending；按本批由平台准备内部镜像；不覆盖本报告已定位的Dev写权限静态错误。
- 专用Verifier CMD仅sh -c sleep infinity保持存活，Harness移交后调用/tests/test.sh；实际内场启动/身份/移交待平台验证。；处理：waived
  依据：workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/task.toml；expert_evidence/repair/harbor/native_nop_trial/native_trial/result.json
  豁免原因：platform_execution_verification_pending；保留静态路径分析与平台待执行状态，不宣称已构建或已验证物理隔离。
- 当前格式实质问题（来自 F05）：task.toml dev_score_command将--out设为/workspace/results.json；Agent Dockerfile使/workspace root所有0755并切换USER agent，仅/workspace/solution属于agent。evaluate.py无条件open该输出，配置命令在默认身份下不可写并退出失败。
  定位：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/environment/public_eval/evaluate.py

### H04 测试入口与 reward

观察判定：fail；本轮判定：fail
入口/reward清理、原子写入和错误分层存在；但模型可加载质量门未实现，缺model.pt仍只凭预测数组进入正常评分。
审阅依据：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/grader.py；workspace/harbor_task/instruction.md；workspace/harbor_task/tests/contract_guard.py
- instruction §3要求模型可加载，§6要求模型产物；grader仅读取test_pred.npy，既不检查model.pt存在也不重载。源码AST检查不证明模型可加载，缺模型仍可进入正常评分。；处理：unwaived
  依据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/contract_guard.py；workspace/harbor_task/environment/public_eval/protocol.json
  修改方向：在独立可信Verifier实施模型存在及可加载质量门并使用与题面一致的安全重载接口；同步准备独立依赖。
  验收：可信评分调用链中可定位的模型检查/加载与失败分支，明确模型和预测对应路径。
- 当前格式实质问题（来自 F07）：instruction §3要求模型可加载，§6要求模型产物；grader仅读取test_pred.npy，既不检查model.pt存在也不重载。源码AST检查不证明模型可加载，缺模型仍可进入正常评分。
  定位：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/contract_guard.py；workspace/harbor_task/environment/public_eval/protocol.json

### H05 Job/Trial 调用配置

观察判定：manual；本轮判定：pass_with_waivers
已有历史native Trial配置选择nop/docker、verifier未禁用，额外Compose覆盖仅旧本地运行；当前内场调用/内部镜像覆盖未执行确认，不套用为当前有效配置。
审阅依据：expert_evidence/repair/harbor/native_nop_trial/native_trial/config.json；expert_evidence/repair/harbor/native_nop_trial/native_trial/result.json；workspace/harbor_task/task.toml
- 两侧有效Dockerfile和依赖方案可读，当前内场预构建、内部镜像tag与实际可达性待平台准备。；处理：waived
  依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/task.toml；expert_evidence/repair/IMAGER_VERIFICATION_20261022.md
  豁免原因：platform_image_preparation_pending；按本批由平台准备内部镜像；不覆盖本报告已定位的Dev写权限静态错误。
- 专用Verifier CMD仅sh -c sleep infinity保持存活，Harness移交后调用/tests/test.sh；实际内场启动/身份/移交待平台验证。；处理：waived
  依据：workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/task.toml；expert_evidence/repair/harbor/native_nop_trial/native_trial/result.json
  豁免原因：platform_execution_verification_pending；保留静态路径分析与平台待执行状态，不宣称已构建或已验证物理隔离。

### H06 NOP 自检记录

观察判定：manual；本轮判定：pass_with_waivers
已核两种历史记录：手工模拟不算NOP；原生NOP正常结束reward0且仅缺提交早退，44/46历史绑定，当前版本未跑；不声称完整Hidden覆盖。
审阅依据：expert_evidence/repair/harbor/native_nop_trial/native_trial/config.json；expert_evidence/repair/harbor/native_nop_trial/native_trial/result.json；expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/reward.json；expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/test-stdout.txt；expert_evidence/repair/harbor/native_nop_trial/VERSION_BINDING.md；expert_evidence/repair/historical_docker_simulation_not_nop/result.json；expert_evidence/repair/historical_evidence_assessment.json
- 原生NOP两处身份nop、separate、finished且exception=null，reward.json优先0.0与result一致，日志非空，无相同sandbox ID反证；仅无提交FORMAT_ERROR分支。历史绑定44/46，task.toml及instruction不同；手工simulation明确不充当NOP。当前Trial未跑。；处理：waived
  依据：expert_evidence/repair/harbor/native_nop_trial/native_trial/config.json；expert_evidence/repair/harbor/native_nop_trial/native_trial/result.json；expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/reward.json；expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/test-stdout.txt；expert_evidence/repair/harbor/native_nop_trial/VERSION_BINDING.md；expert_evidence/repair/historical_docker_simulation_not_nop/result.json；expert_evidence/repair/historical_evidence_assessment.json
  豁免原因：legacy_nop_or_current_trial_gap；原记录不改判成当前成功；旧模拟/历史NOP与迁移后当前版本Trial的具体缺口按政策豁免，无需专家补跑。

## 两轨已有内容

### T01 第一条轨迹已有内容

观察判定：manual；本轮判定：pass_with_waivers
193轮：GCE和前向校正→分类别小损失/等额配额筛选→软邻域平滑和硬投票→裕量、度数和独立邻居门控；round183达到66.7，后10轮持平或回退。
审阅依据：expert_evidence/trajectory_codex.json；expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/repair/original_v7_current_bytes/codex/summary.json；expert_evidence/best_method_selection.json
方法：193轮：GCE和前向校正→分类别小损失/等额配额筛选→软邻域平滑和硬投票→裕量、度数和独立邻居门控；round183达到66.7，后10轮持平或回退。
迭代内容：全部轮次的保留/回退及分数已逐行核对；两条记录全部ok，不把失败未映射session变成新成功轮。193轮：GCE和前向校正→分类别小损失/等额配额筛选→软邻域平滑和硬投票→裕量、度数和独立邻居门控；round183达到66.7，后10轮持平或回退。
最终结果：原合同round183=66.7；原字节独立公开复验66.7。
分数采用范围：仅历史公开Dev探索；不作当前协议同条件优劣认证，不作正式B/R成绩来源。原合同round183=66.7；原字节独立公开复验66.7。
已读来源：expert_evidence/trajectory_codex.json；expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/run_summary.json；expert_evidence/repair/original_v7_current_bytes/codex/summary.json；expert_evidence/best_method_selection.json
- 实际模型由run_summary和轨迹头交叉映射；独立session ID与不同演进支持分别运行，但无完整原Prompt、最高推理档位/空输出启动证明；无已确认两轨实质条件不同反证。；处理：waived
  依据：expert_evidence/run_summary.json；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/repair/historical_timing_mapping/timing_map.json
  豁免原因：legacy_runtime_proof_gap；只豁免旧启动/同条件证明不足，不将其写成已证明相同，也不覆盖可定位条件差异。
- TSV宣称Codex39613/Seed41572秒；timing_map分别给出38589.395/39236.909 provisional秒、直接训练评测下界11488/19413.651秒，strict_fully_bound为null；存在缺行、重复窗口及阻塞未完整分类，原标准有效时长未获确认。；处理：waived
  依据：expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/timing_codex.tsv；expert_evidence/timing_seed.tsv；expert_evidence/run_summary.json
  豁免原因：legacy_research_duration_gap；保留原manual与全部实际数值；历史时长证明差异免补跑，训练题不使用7h例外。

### T02 第二条轨迹已有内容

观察判定：manual；本轮判定：pass_with_waivers
53轮：small-loss与LP→结构/特征双路LP→自适应TLP→三阶段自训练与五成员共识修正→后TLP迭代、冷却及度数硬化；round43记录71.4，后续EMA/SWA/扩展传播等未刷新。
审阅依据：expert_evidence/trajectory_seed.json；expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/repair/original_v7_current_bytes/seed/summary.json；expert_evidence/best_method_selection.json
方法：53轮：small-loss与LP→结构/特征双路LP→自适应TLP→三阶段自训练与五成员共识修正→后TLP迭代、冷却及度数硬化；round43记录71.4，后续EMA/SWA/扩展传播等未刷新。
迭代内容：全部轮次的保留/回退及分数已逐行核对；两条记录全部ok，不把失败未映射session变成新成功轮。53轮：small-loss与LP→结构/特征双路LP→自适应TLP→三阶段自训练与五成员共识修正→后TLP迭代、冷却及度数硬化；round43记录71.4，后续EMA/SWA/扩展传播等未刷新。
最终结果：原合同round43=71.4；原字节公开复验71.1，受信任接口迁移后当前字节公开复验71.2；不把三个值互相替换。
分数采用范围：仅历史公开Dev探索；不作当前协议同条件优劣认证，不作正式B/R成绩来源。原合同round43=71.4；原字节公开复验71.1，受信任接口迁移后当前字节公开复验71.2；不把三个值互相替换。
已读来源：expert_evidence/trajectory_seed.json；expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/run_summary.json；expert_evidence/repair/original_v7_current_bytes/seed/summary.json；expert_evidence/best_method_selection.json
- 实际模型由run_summary和轨迹头交叉映射；独立session ID与不同演进支持分别运行，但无完整原Prompt、最高推理档位/空输出启动证明；无已确认两轨实质条件不同反证。；处理：waived
  依据：expert_evidence/run_summary.json；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/repair/historical_timing_mapping/timing_map.json
  豁免原因：legacy_runtime_proof_gap；只豁免旧启动/同条件证明不足，不将其写成已证明相同，也不覆盖可定位条件差异。
- TSV宣称Codex39613/Seed41572秒；timing_map分别给出38589.395/39236.909 provisional秒、直接训练评测下界11488/19413.651秒，strict_fully_bound为null；存在缺行、重复窗口及阻塞未完整分类，原标准有效时长未获确认。；处理：waived
  依据：expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/timing_codex.tsv；expert_evidence/timing_seed.tsv；expert_evidence/run_summary.json
  豁免原因：legacy_research_duration_gap；保留原manual与全部实际数值；历史时长证明差异免补跑，训练题不使用7h例外。

## 两轨实际条件对比

对比已完成：是
条件判断：historical_evidence_gap；成对对照有效性：unverified
已比较两轨全部轮次、公共起点59.7/相同两图、数据/反馈/约束/资源说明及源事件映射。现有材料支持不同session的独立研究，无identical_prompt=false或已确认反馈/IPC/只读条件被逐轨改变的证据。没有原始完整启动Prompt/资源配置快照，不能把摘要相同升级为已证明同条件。当前v8接口迁移发生于两条历史v7研究之后，与历史两轨彼此不同分开。
已对比维度：prompt、task、dev、feedback、constraints、resources
对比依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/run_summary.json；workspace/harbor_task/instruction.md；expert_evidence/专家作业说明文档.md
质检员内部对比底稿；不要求专家新增字段、Prompt快照、hash或重跑。语义判断须实际阅读原材料，脚本只核验审阅覆盖及判定一致性。
- prompt / legacy_format_or_resource：缺原完整启动Prompt，旧记录仅方法与结果摘要；没有已确认的两轨不同任务指令。按旧启动证明缺口处理。
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/repair/historical_timing_mapping/timing_map.json
- resources / legacy_format_or_resource：历史记录为Docker/旧环境，当前内场CPU配置为格式迁移；两次历史研究实际资源完全一致的证明不足，不声称发现已确认不公平，正式B/R CPU比较另审。
  依据：expert_evidence/run_summary.json；workspace/harbor_task/task.toml；expert_evidence/repair/historical_timing_mapping/timing_map.json

## 当前格式前检 F01–F07（子检查）

format_decision：FAIL
以下仅为当前格式子检查；整题结论以本报告顶部完整质检结果为准。

- F01 [pass] 当前必需目录、文件与 TOML 接口：任务根和三目录、task.toml原生接口完整。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md
- F02 [pass] 有效构建或镜像方案、构建上下文及 COPY 来源：两侧Dockerfile分别使用environment/tests上下文，COPY来源齐全。
  格式审阅依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile
- F03 [pass] 评分入口、独立依赖声明与固定输出路径：评分入口绝对/tests/test.sh，numpy独立依赖，reward固定/logs/verifier；sleep CMD仅存活。
  格式审阅依据：workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/grader.py
- F04 [pass] 提交物 artifacts 移交契约：顶层artifacts覆盖/workspace/solution，Verifier按原绝对路径读取。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/grader.py
- F05 [fail] 公开 Dev、私有 Hidden 供给与 Agent 隔离：task.toml dev_score_command将--out设为/workspace/results.json；Agent Dockerfile使/workspace root所有0755并切换USER agent，仅/workspace/solution属于agent。evaluate.py无条件open该输出，配置命令在默认身份下不可写并退出失败。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/environment/public_eval/evaluate.py
  修改方向：将配置的Dev输出改到Agent可写目录，例如/workspace/solution/results.json，并同步任何引用；或在镜像中仅准备所需可写输出位置。
  验收：task.toml命令、镜像权限与evaluate.py实际写路径静态一致；无需通过放宽公开/私有冻结面权限修复。
- F06 [pass] separate、单容器、无 Compose 与当前目标资源配置：显式separate、两侧CPU16/GPU0；无正式Compose和不支持字段；源码无另起工作环境要求。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh
- F07 [fail] 当前评分实现与冻结面无确证故障或作者泄漏造假：instruction §3要求模型可加载，§6要求模型产物；grader仅读取test_pred.npy，既不检查model.pt存在也不重载。源码AST检查不证明模型可加载，缺模型仍可进入正常评分。
  格式审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/contract_guard.py；workspace/harbor_task/environment/public_eval/protocol.json
  修改方向：在独立可信Verifier实施模型存在及可加载质量门并使用与题面一致的安全重载接口；同步准备独立依赖。
  验收：可信评分调用链中可定位的模型检查/加载与失败分支，明确模型和预测对应路径。

## 平台后续事项（不阻断本轮已有材料审阅）

- 字节内部准备、构建或导入镜像并配置实际 ICM tag；本轮不要求专家补内部镜像运行记录。
- 平台实际构建和启动，核对依赖、基础镜像 digest 及 bash/解释器；静态推断不能冒充运行结果。
- 平台核对 root、seccomp、网络及实际分配的沙盒权限设置。
- 平台后续执行当前版本 Harbor Trial/NOP、独立 Verifier 和 reward 收集；其缺口不作为本轮专家返修门槛。
- 已有原硬件结果本轮复核；不把旧值改称新硬件实测，不要求新环境补跑；平台核对实际当前提交物移交及目标硬件运行。
- 移除不支持的禁网字段后，新的联网或外部查表防护尚未落实，列为平台迁移事项，不要求本批专家新增防护实现或补跑；当前确证 Hidden 暴露或假 reward 仍属当前核心缺陷。

## 原 v0.3.10 自动检查及 NOP 原判

已调用原标准审计入口：True
NOP：{"status": "manual", "runtime_status": "unverified", "trials": [{"trial_dir": "expert_evidence/repair/harbor/native_nop_trial/native_trial", "evidence": ["expert_evidence/repair/harbor/native_nop_trial/native_trial/config.json", "expert_evidence/repair/harbor/native_nop_trial/native_trial/result.json", "expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/reward.json", "expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/reward.txt", "expert_evidence/repair/harbor/native_nop_trial/native_trial/trial.log", "expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/test-stdout.txt"], "details": {"trial_dir": "expert_evidence/repair/harbor/native_nop_trial/native_trial", "agent": "nop", "verifier_environment_mode": "separate", "rewards": {"reward": 0.0}, "task_binding": {"status": "pass", "basis": "reviewed_evidence", "evidence": ["expert_evidence/repair/harbor/native_nop_trial/VERSION_BINDING.md", "expert_evidence/repair/harbor/native_nop_trial/task-tree-hashes.json"], "summary": "原生NOP绑定2026-10-08树，46项与当前44项一致，差异task.toml/instruction；非当前字节成功认证。旧模拟不计NOP。", "authenticity_verified": false}}, "status": "pass", "summary": "已有 NOP 的同次 Trial、Agent、separate、sandbox 反证、结束与异常、reward 数值和非空日志已按原校验器核查。"}, {"trial_dir": "expert_evidence/repair/historical_docker_simulation_not_nop", "evidence": ["expert_evidence/repair/historical_docker_simulation_not_nop/config.json", "expert_evidence/repair/historical_docker_simulation_not_nop/result.json", "expert_evidence/repair/historical_docker_simulation_not_nop/verifier/reward.json", "expert_evidence/repair/historical_docker_simulation_not_nop/verifier/reward.txt", "expert_evidence/repair/historical_docker_simulation_not_nop/trial.log", "expert_evidence/repair/historical_docker_simulation_not_nop/verifier/test-stdout.txt"], "status": "manual", "summary": "Harbor Trial task.toml hash disagrees with the inspected task", "protected": false}], "summary": "逐份读取并校验已有 NOP 记录；未启动新的 Trial。"}

原报告与全部详细结果：standard/report.json；不因豁免覆盖原判。

| 来源 | 项目 | 原判 | 本轮处理 | 依据及原因 |
|---|---|---|---|---|
| checks/QA05 | QA05 | fail | fail | 单轮7200秒仅声明而未执行；模型加载质量门未实施。网络约束迁移单独保留豁免。 |
| checks/QA08 | QA08 | fail | fail | 题面第69行披露Reference采用500 epochs，而n_epochs本身为研究变量；属于参考具体可变配置泄露。 |
| checks/QA11 | QA11 | fail | fail | 八项内容俱全，但可加载模型门与仅预测数组评分不一致；配置的公开Dev输出与默认身份权限不一致。 |
| checks/QA16 | QA16 | manual | pass_with_waivers | codex缺少有效时长或排除排队/安装/故障的核算证据；seed缺少有效时长或排除排队/安装/故障的核算证据 |
| checks/QA17 | QA17 | fail | derived_from_details | Harbor 子项未通过：H03 环境与运行路径；H04 测试入口与 reward；H05 Job/Trial 调用配置；H06 NOP 自检记录；详细原因与证据保留在 report.json。 |
| checks/QA18 | QA18 | manual | pass_with_waivers | 全读Codex193/Seed53轮与事件映射、best及复验；没有已交原始sessions，行为范围为现有摘要/事件。实际模型可识别；原启动/同条件证明缺口，Seed71.4不改写为当前71.2。 |
| checks/QA21 | QA21 | manual | pass_with_waivers | 两轨八字段246轮均具备，旧ok状态/展示时区已识别；annotation/summary/best可解析。当前四项e5a5eb…匹配45文件，历史v7到当前接口绑定仅按迁移处理。 |
| harbor/H03 | H03 | fail | fail | 当前Agent仅solution可写，配置Dev输出/workspace/results.json不可写。两侧单容器、直接本地执行，无任务自部署额外环境；镜像准备和运行验证另列。 |
| harbor/H04 | H04 | fail | fail | 入口/reward清理、原子写入和错误分层存在；但模型可加载质量门未实现，缺model.pt仍只凭预测数组进入正常评分。 |
| harbor/H05 | H05 | manual | pass_with_waivers | 已有历史native Trial配置选择nop/docker、verifier未禁用，额外Compose覆盖仅旧本地运行；当前内场调用/内部镜像覆盖未执行确认，不套用为当前有效配置。 |
| harbor/H06 | H06 | manual | derived_from_details | 已核两种历史记录：手工模拟不算NOP；原生NOP正常结束reward0且仅缺提交早退，44/46历史绑定，当前版本未跑；不声称完整Hidden覆盖。 |
| harbor/path_contract/1 | H03 | manual | pass_with_waivers | 启动命令包含变量或内嵌 shell，需沿调用链核对路径。 |
| nop/trials/1 | H06 | manual | pass_with_waivers | Harbor Trial task.toml hash disagrees with the inspected task |
