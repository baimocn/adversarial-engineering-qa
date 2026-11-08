# 旧题完整质检与逐原因豁免

本轮结论：PASS_WITH_WAIVERS
阶段：standard_review_with_waivers
已完成全部内容审阅：是

原 v0.3.10 全部检查及完整内容审阅已完成，包括已有 NOP；仅按具体历史原因豁免。未执行题包代码或新增 Harbor Trial。
平台实跑：not_executed；未执行模型、题目程序、Docker 或 Harbor。

## 方法与正式对照

在两张固定噪声标签引文图上研究鲁棒训练与图推断读出；开放可执行方法接口，冻结骨干、优化器、数据与评分。
可修改：训练目标/损失、样本或邻居加权、训练标签可靠性估计；辅助自监督/一致性目标及训练日程；同骨干图读出；经审计的多阶段/集成数值 PLAN 与四个开放 hook
冻结面：Cora/CiteSeer 图特征/边/划分及 uniform@0.3 冻结训练标签；GCN 64宽2层/ReLU/dropout=.5；Adam lr=.01 wd=.0005；验证标签仅作评价/选点；私有测试标签；7200s 两图训练预算与最终单组预测评分
指标与质量门：maximize 两图未加权平均 Hidden test accuracy (%)；score=(x−61.8833)/(75.1333−61.8833)，不裁剪；模型可加载、非退化及源码契约门。
Baseline：Starter plain GCN，损坏训练标签 CE；200 epoch/图，Adam .01/.0005，按验证准确率选点，正式3000/3001/3002均独立初始化训练及独立进程重载。
Reference：修复 DREAM：只从损坏训练标签做结构+特征kNN双路传播推断同类锚点，以语义同质性重加权CE并加图增强对比损失/温度缩放；500 epoch/图，同骨干、优化器、数据、预算与验证选点。
正式改善：全部正式seed改善10.20/8.80/6.95；均值改善8.65000000，σ_B=1.60026040，改善/σ=5.405370。生效U=75.1333归一化0.652830；原定U=100为0.226935，两者均在[.15,.8]。U为出分后改用独立clean-label oracle，非预注册；资格结论不依赖该变更。
质量有效性：12个正式图训练正常结束、预测非退化，checkpoint文件哈希与manifest/逐图summary吻合；独立重载日志exit=0且预测一致。result.metrics是公开val，Hidden值来自formal_test_scoring_declared的12条逐图记录，未混用。历史v7泄漏Reference已隔离无效，未采用。
已有原始对照：[{"seed": 3000, "baseline": 60.05, "reference": 70.25, "baseline_valid": true, "reference_valid": true, "evidence": ["optimization_evidence/formal_test_scoring_declared.json", "optimization_evidence/baseline_runs/seed_3000/result.json", "optimization_evidence/reference_runs/seed_3000/result.json"]}, {"seed": 3001, "baseline": 62.6, "reference": 71.4, "baseline_valid": true, "reference_valid": true, "evidence": ["optimization_evidence/formal_test_scoring_declared.json", "optimization_evidence/baseline_runs/seed_3001/result.json", "optimization_evidence/reference_runs/seed_3001/result.json"]}, {"seed": 3002, "baseline": 63.0, "reference": 69.95, "baseline_valid": true, "reference_valid": true, "evidence": ["optimization_evidence/formal_test_scoring_declared.json", "optimization_evidence/baseline_runs/seed_3002/result.json", "optimization_evidence/reference_runs/seed_3002/result.json"]}]
依据：optimization_evidence/formal_test_scoring_declared.json；optimization_evidence/comparison_summary.json；optimization_evidence/训练证据说明.md；optimization_evidence/u_anchor_oracle/measurement.json；expert_evidence/repair/protocol_decisions.json；optimization_evidence/baseline_runs/seed_3000/result.json；optimization_evidence/baseline_runs/seed_3001/result.json；optimization_evidence/baseline_runs/seed_3002/result.json；optimization_evidence/reference_runs/seed_3000/result.json；optimization_evidence/reference_runs/seed_3001/result.json；optimization_evidence/reference_runs/seed_3002/result.json；optimization_evidence/baseline_runs/seed_3000/model/artifact.json；optimization_evidence/baseline_runs/seed_3001/model/artifact.json；optimization_evidence/baseline_runs/seed_3002/model/artifact.json；optimization_evidence/reference_runs/seed_3000/model/artifact.json；optimization_evidence/reference_runs/seed_3001/model/artifact.json；optimization_evidence/reference_runs/seed_3002/model/artifact.json；optimization_evidence/baseline_runs/seed_3000/model/reload.log；optimization_evidence/baseline_runs/seed_3001/model/reload.log；optimization_evidence/baseline_runs/seed_3002/model/reload.log；optimization_evidence/reference_runs/seed_3000/model/reload.log；optimization_evidence/reference_runs/seed_3001/model/reload.log；optimization_evidence/reference_runs/seed_3002/model/reload.log

## 研究三门

### G01 方法级优化空间

观察判定：pass；本轮判定：pass
实际允许训练目标/加权/可靠性/数值hook及图读出；guard保留可执行方法空间。Reference双路锚点与对比目标是方法变化，不是仅常量搜索。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/contract_guard.py；workspace/reference/predictor/DREAM_Predictor.py；workspace/harbor_task/environment/starter/stage_runtime.py

### G02 Baseline 合理性

观察判定：pass；本轮判定：pass
朴素噪声GCN为Starter/正式B；3 seed每图实训200更新、按val选点且reload一致。R500更新是允许日程变量，共7200s预算；未发现故障、削弱或挑seed反证。
审阅依据：optimization_evidence/训练证据说明.md；expert_evidence/专家作业说明文档.md；workspace/harbor_task/environment/starter/predictor/Base_Predictor.py；optimization_evidence/baseline_runs/seed_3000/result.json；optimization_evidence/baseline_runs/seed_3001/result.json；optimization_evidence/baseline_runs/seed_3002/result.json；optimization_evidence/reference_runs/seed_3000/result.json；optimization_evidence/reference_runs/seed_3001/result.json；optimization_evidence/reference_runs/seed_3002/result.json
训练充分性：实际日志每图B200、R500条epoch，optimizer_steps相等；均epoch_budget_exhausted/无异常。B选点Cora8/7/6、Cite39/4/5，后期train loss低而val下降，早期best合理，非初始化或未训练。
  依据：optimization_evidence/baseline_runs/seed_3000/result.json；optimization_evidence/baseline_runs/seed_3001/result.json；optimization_evidence/baseline_runs/seed_3002/result.json；optimization_evidence/reference_runs/seed_3000/result.json；optimization_evidence/reference_runs/seed_3001/result.json；optimization_evidence/reference_runs/seed_3002/result.json；optimization_evidence/baseline_runs/seed_3000/run.log；optimization_evidence/baseline_runs/seed_3001/run.log；optimization_evidence/baseline_runs/seed_3002/run.log；optimization_evidence/reference_runs/seed_3000/run.log；optimization_evidence/reference_runs/seed_3001/run.log；optimization_evidence/reference_runs/seed_3002/run.log
方法代表性：固定GCN与噪声标签下plain CE为可解释naive对照并与Starter一致；不要求SOTA；包内无可比且预算可行更强常见锚点证明该选择失当。
  依据：workspace/harbor_task/instruction.md；expert_evidence/专家作业说明文档.md；workspace/harbor_task/environment/starter/predictor/GCN_Predictor.py
原协议预算可比性：双方同CPU协议/同冻结数据及seed，同7200秒两图训练上限；n_epochs为可研究日程，200/500披露，实际两图55.77–493.55s。整体方案收益未作单项消融归因。
  依据：workspace/harbor_task/instruction.md；workspace/harbor_task/task.toml；expert_evidence/repair/protocol_decisions.json；optimization_evidence/baseline_runs/seed_3000/result.json；optimization_evidence/baseline_runs/seed_3001/result.json；optimization_evidence/baseline_runs/seed_3002/result.json；optimization_evidence/reference_runs/seed_3000/result.json；optimization_evidence/reference_runs/seed_3001/result.json；optimization_evidence/reference_runs/seed_3002/result.json
实现正确性：输入标签分离、CE/Adam梯度更新正常；12模型manifest哈希均匹配，独立reload exit=0/预测一致；R锚点仅由训练噪声标签推断，旧v7泄漏对照另存不计。
  依据：workspace/harbor_task/environment/starter/data.py；workspace/harbor_task/environment/starter/predictor/Base_Predictor.py；workspace/reference/predictor/DREAM_Predictor.py；optimization_evidence/baseline_runs/seed_3000/model/artifact.json；optimization_evidence/baseline_runs/seed_3001/model/artifact.json；optimization_evidence/baseline_runs/seed_3002/model/artifact.json；optimization_evidence/reference_runs/seed_3000/model/artifact.json；optimization_evidence/reference_runs/seed_3001/model/artifact.json；optimization_evidence/reference_runs/seed_3002/model/artifact.json；optimization_evidence/baseline_runs/seed_3000/model/reload.log；optimization_evidence/baseline_runs/seed_3001/model/reload.log；optimization_evidence/baseline_runs/seed_3002/model/reload.log；optimization_evidence/reference_runs/seed_3000/model/reload.log；optimization_evidence/reference_runs/seed_3001/model/reload.log；optimization_evidence/reference_runs/seed_3002/model/reload.log
选择与对照完整性：正式3000/3001/3002全集成对固定方法配置；不同seed文件hash不同；按公开val选checkpoint，保留历史3次未达标探索与v7无效Reference，不选差B/好R。
  依据：optimization_evidence/comparison_summary.json；optimization_evidence/formal_test_scoring_declared.json；optimization_evidence/README.md；optimization_evidence/baseline_runs/seed_3000/result.json；optimization_evidence/baseline_runs/seed_3001/result.json；optimization_evidence/baseline_runs/seed_3002/result.json；optimization_evidence/reference_runs/seed_3000/result.json；optimization_evidence/reference_runs/seed_3001/result.json；optimization_evidence/reference_runs/seed_3002/result.json

### G03 Reference 提升充分性

观察判定：pass；本轮判定：pass
三seed全部有效，Hidden Δ=8.65≈5.40537σ_B，生效U归一化.65283、原定100为.226935，均达标。U出分后变更披露且有独立oracle，资格结论不靠改U通过。
审阅依据：optimization_evidence/formal_test_scoring_declared.json；optimization_evidence/comparison_summary.json；optimization_evidence/u_anchor_oracle/measurement.json；expert_evidence/repair/protocol_decisions.json
正式复算：{"baseline_mean": 61.88333333333333, "reference_mean": 70.53333333333335, "baseline_sample_std": 1.6002603954773547, "reference_sample_std": 0.765397500213671, "improvement": 8.650000000000013, "run_count": 3, "sigma_multiplier": 5.405370291264212, "three_sigma_baseline": 4.800781186432064, "normalized_score": 0.652831831023475}

## 21 项内容与实现

### QA01 八章节与题面信息泄露

观察判定：pass；本轮判定：pass
八节实质内容齐全，题面未给参考方法名称、来源论文或仓库；开放接口说明属于必要契约。
审阅依据：workspace/harbor_task/instruction.md

### QA02 评分公式与 0/1 锚点

观察判定：pass；本轮判定：pass
normalize_score直接(x-B)/(U-B)，B=61.8833、U=75.1333；连续单调无裁剪，0/1锚点正确。经验U事后变更已披露，原定U=100亦达资格门。
审阅依据：workspace/harbor_task/tests/contract_guard.py；workspace/harbor_task/tests/calibration.json；optimization_evidence/formal_test_scoring_declared.json

### QA03 参考解分数与复现材料

观察判定：pass；本轮判定：pass
Reference入口与3 seed×2图记录、非空原日志、12个B/R模型及独立reload齐全；Hidden R均值70.5333，归一化.65283；不拿val代替Hidden。
审阅依据：workspace/reference/train.py；optimization_evidence/formal_test_scoring_declared.json；optimization_evidence/reference_runs/seed_3000/result.json；optimization_evidence/reference_runs/seed_3001/result.json；optimization_evidence/reference_runs/seed_3002/result.json；optimization_evidence/reference_runs/seed_3000/model/artifact.json；optimization_evidence/reference_runs/seed_3001/model/artifact.json；optimization_evidence/reference_runs/seed_3002/model/artifact.json；optimization_evidence/reference_runs/seed_3000/model/reload.log；optimization_evidence/reference_runs/seed_3001/model/reload.log；optimization_evidence/reference_runs/seed_3002/model/reload.log

### QA04 波动指标的 3σ 可分辨性

观察判定：pass；本轮判定：pass
三seed均进入setup_seed实际随机过程；每角色固定配置独立训练，同集合成对。Δ=8.65≥3σ_B=4.80078，约5.40537σ；未用标准误。
审阅依据：workspace/harbor_task/environment/starter/train.py；workspace/harbor_task/environment/starter/utils/tools.py；optimization_evidence/formal_test_scoring_declared.json；optimization_evidence/baseline_runs/seed_3000/result.json；optimization_evidence/baseline_runs/seed_3001/result.json；optimization_evidence/baseline_runs/seed_3002/result.json；optimization_evidence/reference_runs/seed_3000/result.json；optimization_evidence/reference_runs/seed_3001/result.json；optimization_evidence/reference_runs/seed_3002/result.json

### QA05 约束执行实现

观察判定：fail；本轮判定：pass_with_waivers
固定源码/标签流守卫、模型加载门、run.sh每图timeout均有实现且范围与题面一致；禁外部查表仅规则，删禁网字段未形成可信网络执行，保留该迁移缺口。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/contract_guard.py；workspace/harbor_task/tests/grader.py；workspace/harbor_task/environment/starter/run.sh；workspace/harbor_task/task.toml
- 删除未支持禁网配置后，无可信外部查表网络防护；题面禁止不能替代执行。；处理：waived
  依据：workspace/harbor_task/instruction.md；workspace/harbor_task/task.toml
  豁免原因：unsupported_network_policy_transition；仅获准禁网/白名单过渡缺口免本批返修；当前守卫/私有隔离仍独立审查，无直接Hidden暴露。

### QA06 Verifier 入口、分数与错误处理

观察判定：pass；本轮判定：pass
bash /tests/test.sh以隔离Python调用grader，正常与失败均落有限reward；JSON优先且标量主指标明确。
审阅依据：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/grader.py

### QA07 instruction 中的 Hidden 信息泄露

观察判定：pass；本轮判定：pass
仅审题面：未披露私有测试标签/样本答案或可恢复答案；提及Hidden与禁令不构成泄露。
审阅依据：workspace/harbor_task/instruction.md

### QA08 instruction 中的参考解信息泄露

观察判定：pass；本轮判定：pass
仅审题面：未披露Reference代码/具体epoch配置/成绩、论文或仓库；GCN/Adam固定量为任务契约。
审阅依据：workspace/harbor_task/instruction.md

### QA09 结果清理与原子写入

观察判定：pass；本轮判定：pass
main先clean_stale_rewards，reward两格式均经同目录tmp、os.replace原子替换。
审阅依据：workspace/harbor_task/tests/grader.py

### QA10 冻结面保护或恢复实现

观察判定：pass；本轮判定：pass
独立Verifier持有policy/calibration/private，候选只作AST检查；Agent镜像公开冻结面chmod只读且USER agent；评分不导入候选模块。
审阅依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/contract_guard.py；workspace/harbor_task/tests/grader.py

### QA11 instruction 八项内容

观察判定：pass；本轮判定：pass
八部分输入输出/可改边界/评分/资源/迭代/完成条件一致；Dev输出为可写solution/results.json。预算明示仅两图train，reload另计；旧run.sh注释提reload与代码不符属注释遗留，题面已准确界定。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/task.toml；workspace/harbor_task/environment/starter/run.sh；workspace/harbor_task/environment/starter/README.md；workspace/harbor_task/environment/public_eval/evaluate.py

### QA12 Git 清理

观察判定：pass；本轮判定：pass
安全清点题包无.git目录；无remotes/tags/reflog待清理。
审阅依据：@legacy_inventory

### QA13 Baseline 与参考解提升

观察判定：pass；本轮判定：pass
正式三组Hidden原值逐图配对完整，Δ10.20/8.80/6.95与说明一致，宏均值改善8.65；质量门与模型hash/reload无反证，旧泄漏Reference未用。
审阅依据：optimization_evidence/formal_test_scoring_declared.json；optimization_evidence/comparison_summary.json；expert_evidence/专家作业说明文档.md；optimization_evidence/baseline_runs/seed_3000/result.json；optimization_evidence/baseline_runs/seed_3001/result.json；optimization_evidence/baseline_runs/seed_3002/result.json；optimization_evidence/reference_runs/seed_3000/result.json；optimization_evidence/reference_runs/seed_3001/result.json；optimization_evidence/reference_runs/seed_3002/result.json

### QA14 合法改进空间

观察判定：pass；本轮判定：pass
可实现新损失、可信度估计与图推断而非只调常量；可继续研究结构/特征分歧下的稳健加权。R未饱和；经验U余量4.6略小于3σ约4.8008，作为风险保留不设额外硬门。
审阅依据：workspace/harbor_task/instruction.md；workspace/reference/predictor/DREAM_Predictor.py；expert_evidence/best_method/stage_runtime.py；optimization_evidence/comparison_summary.json

### QA15 评分资源需求估算

观察判定：pass；本轮判定：pass
CPU题两侧GPU=0、各16CPU。正式两图train≤493.55s，迁移best两图541.97s；加独立reload/评分及余量估完整单轮1200s，≤7200s/64CPU。估算非目标平台实测。
审阅依据：workspace/harbor_task/task.toml；optimization_evidence/baseline_runs/seed_3000/result.json；optimization_evidence/baseline_runs/seed_3001/result.json；optimization_evidence/baseline_runs/seed_3002/result.json；optimization_evidence/reference_runs/seed_3000/result.json；optimization_evidence/reference_runs/seed_3001/result.json；optimization_evidence/reference_runs/seed_3002/result.json；optimization_evidence/baseline_runs/seed_3000/model/reload.log；optimization_evidence/baseline_runs/seed_3001/model/reload.log；optimization_evidence/baseline_runs/seed_3002/model/reload.log；optimization_evidence/reference_runs/seed_3000/model/reload.log；optimization_evidence/reference_runs/seed_3001/model/reload.log；optimization_evidence/reference_runs/seed_3002/model/reload.log；expert_evidence/repair/current_source_revalidation/reference_seed_3000_cora/result.json；expert_evidence/repair/current_source_revalidation/reference_seed_3000_citeseer/result.json

### QA16 轨迹实际迭代时长

观察判定：manual；本轮判定：pass_with_waivers
TSV有效合计声明39613/41572s；timing_map另有38589.395/39236.909s暂定窗口且strict有效秒数null，不能称已严格达10h。训练题不适用7h；当前协议无新10h轨迹。
审阅依据：expert_evidence/run_summary.json；expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/timing_codex.tsv；expert_evidence/timing_seed.tsv
- 历史TSV声明11.00/11.55h，但映射strict_fully_bound_effective_seconds为null；本轮无当前协议10h研究。；处理：waived
  依据：expert_evidence/run_summary.json；expert_evidence/repair/historical_timing_mapping/timing_map.json
  豁免原因：legacy_research_duration_gap；保留历史申报数与暂定窗口差异，不以墙钟冒充有效秒数；按本批免新增时长证明及补跑。

### QA17 Harbor Harness 兼容性

观察判定：fail；本轮判定：pass_with_waivers
由H01–H06派生：静态路径/Hidden/移交成立；内部镜像准备、当前构建/运行与NOP版本迁移缺口保留原判，非当前代码确证故障。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；expert_evidence/repair/harbor/native_nop_trial/VERSION_BINDING.md
Harbor逐项派生：H01=pass；H02=pass；H03=pass_with_waivers；H04=pass；H05=pass_with_waivers；H06=pass_with_waivers

### QA18 轨迹、日志与分析

观察判定：manual；本轮判定：pass_with_waivers
已审Codex193轮与Seed53轮、全部方法/分数/best和计时映射。两轨属本题且演进不同；缺原启动Prompt/最高推理档/完整工具记录，历史最佳不可冒称当前复现71.4。未发现已确认A/B实质条件差异。
审阅依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/best_method_selection.json；expert_evidence/qa16_best_method_revalidation.json
- 模型/runtime可由轨迹及摘要交叉识别，原Prompt/最高推理档/空输出与方法来源绑定仍属旧证明缺口。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/repair/historical_timing_mapping/timing_map.json
  豁免原因：legacy_runtime_proof_gap；两轨内容均已读，不因缺启动证明补跑；现有材料无已确认A/B实质权限/反馈差异。
- 旧status=ok、Seed35/36重复及计时映射未完全闭合，保留映射而不补造历史字段。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/seed_round_mapping.json
  豁免原因：legacy_trajectory_schema_gap；完整八字段实存；旧状态与时间映射差异获免，不把Seed重复行算独立方法增益。
- 已实际对比现有两轨材料，旧版材料仍不足以证明所有历史条件一致；仅此记录缺口豁免，不声称已证实同条件。两轨均从59.7的GCN起点在两图公开val迭代，同类允许训练/读出空间，模型和方法演进独立；已有轨迹/映射没有确认的Prompt、任务、Dev、反馈、权限或资源实质差异。未交原启动Prompt/原任务快照/全部原sessions，不能证实完全同条件。当前标签视图/接口返修与旧dream-v1差异是历史到返修迁移，不能反推A/B条件相同。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/专家作业说明文档.md；expert_evidence/repair/standalone_migration_history.json
  豁免原因：legacy_runtime_proof_gap；本轮旧题迁移不要求新增Prompt快照、hash或重跑；已读资料中没有已确认的实质条件差异。

### QA19 seed 与有效提升阈值

观察判定：pass；本轮判定：pass
题面明确冻结corruption seed、独立训练seed全集3000/3001/3002，Δ>0且≥3样本σ_B与归一化区间；区分单次候选reward和资格统计。
审阅依据：workspace/harbor_task/instruction.md

### QA20 修改范围、网络与工具策略

观察判定：pass；本轮判定：pass
题面列可改范围、禁止联网查原标签及平台默认工具策略；无需外部服务，公开工具与solution工作区明确。
审阅依据：workspace/harbor_task/instruction.md

### QA21 三个 JSON 的填写内容

观察判定：manual；本轮判定：pass_with_waivers
三JSON可解析，193/53轮八字段齐全、状态ok且time非null；当前四项hash重算与run_summary一致。显式说明两轨历史dream-v1，当前绑定不能证明历史版本；best历史71.4与迁移71.2分开。
审阅依据：expert_evidence/run_summary.json；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/expert_annotation.json；expert_evidence/best_method_selection.json；expert_evidence/qa16_best_method_revalidation.json
- 当前四项hash一致，但历史dream-v1与返修安全标签视图/数值接口不同，当前摘要hash不证明过去执行绑定。另对best_method_selection.method_sha256逐文件重算：23/24一致，唯一README.md旧hash87c499…与当前428e8a…不同，修复日志v12说明Dev输出路径/权限说明更新；23项方法源码及配置一致。属历史复验到文档返修迁移，不能声称当前24项完全同字节。；处理：waived
  依据：expert_evidence/run_summary.json；expert_evidence/repair/standalone_migration_history.json；expert_evidence/qa16_best_method_revalidation.json；expert_evidence/best_method_selection.json；expert_evidence/best_method/README.md；expert_evidence/repair/REPAIR_MANIFEST.json
  豁免原因：legacy_task_binding_migration；仅历史研究到本次返修的版本迁移获免；未将历史B轨与A轨差异或正式无效成绩豁免。

## Harbor 六项

### H01 任务目录

观察判定：pass；本轮判定：pass
选定workspace/harbor_task；两侧context完整，私有npz由专用tests镜像预置并由grader读取，公开Dev进入Agent；Reference不进入Agent。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/grader.py；workspace/harbor_task/environment/public_assets/manifest.json

### H02 版本与配置

观察判定：pass；本轮判定：pass
TOML可解析、显式separate；以包内Harbor0.24.0锁定源码/模式记录核对。innerfield-maso-v1：无storage_mb/no-network/白名单，双侧gpus=0；网络过渡另列QA05。
审阅依据：workspace/harbor_task/task.toml；expert_evidence/repair/harbor/schema_validation.json；expert_evidence/repair/harbor/upstream_sources.json

### H03 环境与运行路径

观察判定：manual；本轮判定：pass_with_waivers
environment/tests各自单容器构建context；专用Verifier预置/tests/test.sh及numpy/CPU torch，不依赖Agent缓存。artifacts保持solution绝对路径。调用链仅本沙盒进程，无任务额外环境；内部镜像/当前构建启动待平台。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/requirements.txt；workspace/harbor_task/tests/test.sh；workspace/harbor_task/environment/starter/run.sh；workspace/harbor_task/tests/grader.py
- 有完整Dockerfile/context来源方案，内部ICM镜像tag由平台准备。；处理：waived
  依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/task.toml
  豁免原因：platform_image_preparation_pending；有效源镜像构建方案已读，缺内部tag不是当前静态路径错误。
- 当前镜像构建/启动/权限/物理隔离与移交未独立验证，旧NOP不覆盖当前字节。；处理：waived
  依据：expert_evidence/repair/harbor/native_nop_trial/VERSION_BINDING.md；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile
  豁免原因：platform_execution_verification_pending；保留未运行事实，仅免平台动态验收缺口，不宣称实际成功。

### H04 测试入口与 reward

观察判定：pass；本轮判定：pass
正式入口实际写reward.txt及reward.json有限数值；失败码分类，模型存在/可加载检查及非退化硬门与题面对应，旧fixture不冒充当前模型门实测。
审阅依据：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/calibration.json；optimization_evidence/README.md

### H05 Job/Trial 调用配置

观察判定：manual；本轮判定：pass_with_waivers
已有本地NOP配置指向旧树：agent=nop、verifier未禁用，extra_compose仅原Docker构建加速；不能当当前MASO启动配置或部署证明。保留历史事实，平台选当前镜像/覆盖待验。
审阅依据：expert_evidence/repair/harbor/native_nop_trial/native_trial/config.json；expert_evidence/repair/harbor/native_nop_trial/native_trial/result.json；expert_evidence/repair/harbor/native_nop_trial/environment_record.json；workspace/harbor_task/task.toml
- 已有配置为旧本地Docker NOP（含构建加速override与cpu/memory ignore），当前MASO选择/覆盖尚未执行。；处理：waived
  依据：expert_evidence/repair/harbor/native_nop_trial/native_trial/config.json；expert_evidence/repair/harbor/native_nop_trial/environment_record.json；expert_evidence/repair/harbor/native_nop_trial/VERSION_BINDING.md
  豁免原因：platform_execution_verification_pending；历史调用层不作为当前题包Compose入口；当前正式environment/tests无Compose，由平台完成实际配置。

### H06 NOP 自检记录

观察判定：fail；本轮判定：pass_with_waivers
同次旧NOP config/result均nop、separate、有finished_at且无exception；reward.json优先0与result一致、日志非空，solution移交ok。仅缺预测早退分支；与当前38/46一致、8差异，不是当前版本NOP。
审阅依据：expert_evidence/repair/harbor/native_nop_trial/native_trial/config.json；expert_evidence/repair/harbor/native_nop_trial/native_trial/result.json；expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/reward.json；expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/reward.txt；expert_evidence/repair/harbor/native_nop_trial/native_trial/trial.log；expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/test-stdout.txt；expert_evidence/repair/harbor/native_nop_trial/native_trial/artifacts/manifest.json；expert_evidence/repair/harbor/native_nop_trial/VERSION_BINDING.md
- 已有真实旧NOP仅覆盖缺预测早退；8项版本差异含6条构建/评分链路文件，当前NOP未运行。另已审historical_docker_simulation_not_nop：其身份字段由后处理构造，并非原生NOP，拒绝作为成功自检；不因旧模拟被扫描到就掩去其真实性限制。；处理：waived
  依据：expert_evidence/repair/harbor/native_nop_trial/native_trial/result.json；expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/test-stdout.txt；expert_evidence/repair/harbor/native_nop_trial/VERSION_BINDING.md；expert_evidence/repair/historical_evidence_assessment.json；expert_evidence/repair/historical_docker_simulation_not_nop/config.json；expert_evidence/repair/historical_docker_simulation_not_nop/result.json；expert_evidence/repair/historical_docker_simulation_not_nop/trial.log
  豁免原因：legacy_nop_or_current_trial_gap；逐份审同Trial身份/separate/结束/异常/reward/log/移交后确认版本迁移缺口；不把旧0分视为当前Hidden成功，按本批免作者补跑。

## 两轨已有内容

### T01 第一条轨迹已有内容

观察判定：manual；本轮判定：pass_with_waivers
1–8 GCE/前向噪声校正，9–29分类别小损失/配额/渐进筛选，30–56邻域软概率到硬投票，57–112裕量加权/自身不确定带/多邻居独立佐证，113–193多数为局部边界试验与回退；183达到66.7，末轮恢复。
审阅依据：expert_evidence/trajectory_codex.json；expert_evidence/run_summary.json；expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/qa16_best_method_revalidation.json；expert_evidence/best_method_selection.json；expert_evidence/seed_round_mapping.json
方法：1–8 GCE/前向噪声校正，9–29分类别小损失/配额/渐进筛选，30–56邻域软概率到硬投票，57–112裕量加权/自身不确定带/多邻居独立佐证，113–193多数为局部边界试验与回退；183达到66.7，末轮恢复。
迭代内容：已逐轮审193条八字段，探索/失败和回退均保留；计时摘要不足以认证完整有效时长。
最终结果：历史round183 Dev66.7；原字节重跑66.7。
分数采用范围：仅历史公开Dev方法演进；不能当当前Hidden正式B/R，迁移公开复验另列。
已读来源：expert_evidence/trajectory_codex.json；expert_evidence/run_summary.json；expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/qa16_best_method_revalidation.json；expert_evidence/best_method_selection.json；expert_evidence/seed_round_mapping.json
- 完整方法digest/启动/时长证明不闭合；保留历史分数unverified与当前复验区别。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/run_summary.json；expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/qa16_best_method_revalidation.json；expert_evidence/best_method_selection.json；expert_evidence/seed_round_mapping.json
  豁免原因：legacy_runtime_proof_gap；已审本题全部轨迹；历史新证明免补，不将无效旧Reference或历史best当正式成绩。

### T02 第二条轨迹已有内容

观察判定：manual；本轮判定：pass_with_waivers
1–9 small-loss/平滑/双路LP与退火，10–18测试时传播、自训练到3阶段5成员共识；19–30更深阶段/EMA/重加权/蒸馏多次下降均保留；31后集成TLP、多程冷却与度数硬化，43达71.4；44–53回退最佳。35/36重复映射、48/49共享窗不作额外独立闭环。
审阅依据：expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/qa16_best_method_revalidation.json；expert_evidence/best_method_selection.json；expert_evidence/seed_round_mapping.json
方法：1–9 small-loss/平滑/双路LP与退火，10–18测试时传播、自训练到3阶段5成员共识；19–30更深阶段/EMA/重加权/蒸馏多次下降均保留；31后集成TLP、多程冷却与度数硬化，43达71.4；44–53回退最佳。35/36重复映射、48/49共享窗不作额外独立闭环。
迭代内容：已逐轮审53条八字段，探索/失败和回退均保留；计时摘要不足以认证完整有效时长。
最终结果：历史round43 Dev71.4；旧字节重跑71.1，迁移当前字节公开复验71.2；不得混作同一结果。
分数采用范围：仅历史公开Dev方法演进；不能当当前Hidden正式B/R，迁移公开复验另列。
已读来源：expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/qa16_best_method_revalidation.json；expert_evidence/best_method_selection.json；expert_evidence/seed_round_mapping.json
- 完整方法digest/启动/时长证明不闭合；保留历史分数unverified与当前复验区别。；处理：waived
  依据：expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/qa16_best_method_revalidation.json；expert_evidence/best_method_selection.json；expert_evidence/seed_round_mapping.json
  豁免原因：legacy_runtime_proof_gap；已审本题全部轨迹；历史新证明免补，不将无效旧Reference或历史best当正式成绩。

## 两轨实际条件对比

对比已完成：是
条件判断：historical_evidence_gap；成对对照有效性：unverified
两轨均从59.7的GCN起点在两图公开val迭代，同类允许训练/读出空间，模型和方法演进独立；已有轨迹/映射没有确认的Prompt、任务、Dev、反馈、权限或资源实质差异。未交原启动Prompt/原任务快照/全部原sessions，不能证实完全同条件。当前标签视图/接口返修与旧dream-v1差异是历史到返修迁移，不能反推A/B条件相同。
已对比维度：prompt、task、dev、feedback、constraints、resources
对比依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/专家作业说明文档.md；expert_evidence/repair/standalone_migration_history.json
质检员内部对比底稿；不要求专家新增字段、Prompt快照、hash或重跑。语义判断须实际阅读原材料，脚本只核验审阅覆盖及判定一致性。

## 当前格式前检 F01–F07（子检查）

format_decision：PASS_WITH_WAIVERS
以下仅为当前格式子检查；整题结论以本报告顶部完整质检结果为准。

- F01 [pass] 当前必需目录、文件与 TOML 接口：当前三目录及TOML/题面/tests入口齐全，显式separate。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md
- F02 [pass] 有效构建或镜像方案、构建上下文及 COPY 来源：两侧Dockerfile各自context所有COPY源存在；tests专用预置，Agent无Hidden/Reference。内部ICM tag按平台准备。
  格式审阅依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile
- F03 [pass] 评分入口、独立依赖声明与固定输出路径：sh -c sleep infinity仅镜像保活；真实评分由/tests/test.sh调用绝对路径grader。numpy+CPU torch独立依赖，reward固定/logs/verifier。
  格式审阅依据：workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/requirements.txt
- F04 [pass] 提交物 artifacts 移交契约：artifacts=/workspace/solution覆盖grader实际输入；source绝对路径保持，不把destination当容器重映射。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/grader.py
- F05 [pass] 公开 Dev、私有 Hidden 供给与 Agent 隔离：public_assets/public_eval COPY到Agent，tests/private仅Verifier；两标签npz有评分读取路径，来源manifest及安全adapter可追溯。
  格式审阅依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/grader.py；workspace/harbor_task/environment/starter/data.py
- F06 [pass] separate、单容器、无 Compose 与当前目标资源配置：两侧单容器/gpus0/cpus16，正式environment/tests直属无Compose，不支持网络/存储字段已删；无额外工作环境依赖。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/environment/starter/run.sh
- F07 [pass] 当前评分实现与冻结面无确证故障或作者泄漏造假：当前源码守卫、模型可加载与非退化门、连续归一化及原子reward均有实现；参考方法与私有资产未入Agent，旧记录/已修问题不当当前缺陷。
  格式审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/contract_guard.py；workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/calibration.json

## 平台后续事项（不阻断本轮已有材料审阅）

- 字节内部准备、构建或导入镜像并配置实际 ICM tag；本轮不要求专家补内部镜像运行记录。
- 平台实际构建和启动，核对依赖、基础镜像 digest 及 bash/解释器；静态推断不能冒充运行结果。
- 平台核对 root、seccomp、网络及实际分配的沙盒权限设置。
- 平台后续执行当前版本 Harbor Trial/NOP、独立 Verifier 和 reward 收集；其缺口不作为本轮专家返修门槛。
- 已有原硬件结果本轮复核；不把旧值改称新硬件实测，不要求新环境补跑；平台核对实际当前提交物移交及目标硬件运行。
- 移除不支持的禁网字段后，新的联网或外部查表防护尚未落实，列为平台迁移事项，不要求本批专家新增防护实现或补跑；当前确证 Hidden 暴露或假 reward 仍属当前核心缺陷。

## 原 v0.3.10 自动检查及 NOP 原判

已调用原标准审计入口：True
NOP：{"status": "manual", "runtime_status": "unverified", "trials": [{"trial_dir": "expert_evidence/repair/harbor/native_nop_trial/native_trial", "evidence": ["expert_evidence/repair/harbor/native_nop_trial/native_trial/config.json", "expert_evidence/repair/harbor/native_nop_trial/native_trial/result.json", "expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/reward.json", "expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/reward.txt", "expert_evidence/repair/harbor/native_nop_trial/native_trial/trial.log", "expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/test-stdout.txt"], "details": {"trial_dir": "expert_evidence/repair/harbor/native_nop_trial/native_trial", "agent": "nop", "verifier_environment_mode": "separate", "rewards": {"reward": 0.0}, "task_binding": {"status": "pass", "basis": "reviewed_evidence", "evidence": ["expert_evidence/repair/harbor/native_nop_trial/VERSION_BINDING.md", "expert_evidence/repair/harbor/native_nop_trial/task-tree-hashes.json", "expert_evidence/repair/harbor/native_nop_trial/README.md"], "summary": "真实本题旧NOP，树与当前38/46一致8差异；仅历史版本关联，不能证明当前构建；旧simulation非NOP不采用。", "authenticity_verified": false}}, "status": "pass", "summary": "已有 NOP 的同次 Trial、Agent、separate、sandbox 反证、结束与异常、reward 数值和非空日志已按原校验器核查。"}, {"trial_dir": "expert_evidence/repair/historical_docker_simulation_not_nop", "evidence": ["expert_evidence/repair/historical_docker_simulation_not_nop/config.json", "expert_evidence/repair/historical_docker_simulation_not_nop/result.json", "expert_evidence/repair/historical_docker_simulation_not_nop/verifier/reward.json", "expert_evidence/repair/historical_docker_simulation_not_nop/verifier/reward.txt", "expert_evidence/repair/historical_docker_simulation_not_nop/trial.log", "expert_evidence/repair/historical_docker_simulation_not_nop/verifier/test-stdout.txt"], "status": "manual", "summary": "Harbor Trial task.toml hash disagrees with the inspected task", "protected": false}], "summary": "逐份读取并校验已有 NOP 记录；未启动新的 Trial。"}

原报告与全部详细结果：standard/report.json；不因豁免覆盖原判。

| 来源 | 项目 | 原判 | 本轮处理 | 依据及原因 |
|---|---|---|---|---|
| checks/QA05 | QA05 | fail | pass_with_waivers | 固定源码/标签流守卫、模型加载门、run.sh每图timeout均有实现且范围与题面一致；禁外部查表仅规则，删禁网字段未形成可信网络执行，保留该迁移缺口。 |
| checks/QA16 | QA16 | manual | pass_with_waivers | Codex / gpt-5.6-sol缺少有效时长或排除排队/安装/故障的核算证据；Seed / Doubao-Seed-2.1-turbo缺少有效时长或排除排队/安装/故障的核算证据 |
| checks/QA17 | QA17 | fail | derived_from_details | Harbor 子项未通过：H03 环境与运行路径；H05 Job/Trial 调用配置；H06 NOP 自检记录；详细原因与证据保留在 report.json。 |
| checks/QA18 | QA18 | manual | pass_with_waivers | 已审Codex193轮与Seed53轮、全部方法/分数/best和计时映射。两轨属本题且演进不同；缺原启动Prompt/最高推理档/完整工具记录，历史最佳不可冒称当前复现71.4。未发现已确认A/B实质条件差异。 |
| checks/QA21 | QA21 | manual | pass_with_waivers | 三JSON可解析，193/53轮八字段齐全、状态ok且time非null；当前四项hash重算与run_summary一致。显式说明两轨历史dream-v1，当前绑定不能证明历史版本；best历史71.4与迁移71.2分开。 |
| harbor/H03 | H03 | manual | pass_with_waivers | environment/tests各自单容器构建context；专用Verifier预置/tests/test.sh及numpy/CPU torch，不依赖Agent缓存。artifacts保持solution绝对路径。调用链仅本沙盒进程，无任务额外环境；内部镜像/当前构建启动待平台。 |
| harbor/H05 | H05 | manual | pass_with_waivers | 已有本地NOP配置指向旧树：agent=nop、verifier未禁用，extra_compose仅原Docker构建加速；不能当当前MASO启动配置或部署证明。保留历史事实，平台选当前镜像/覆盖待验。 |
| harbor/H06 | H06 | fail | derived_from_details | 同次旧NOP config/result均nop、separate、有finished_at且无exception；reward.json优先0与result一致、日志非空，solution移交ok。仅缺预测早退分支；与当前38/46一致、8差异，不是当前版本NOP。 |
| harbor/path_contract/1 | H03 | manual | pass | 启动命令包含变量或内嵌 shell，需沿调用链核对路径。 |
| nop/trials/1 | H06 | manual | pass_with_waivers | Harbor Trial task.toml hash disagrees with the inspected task |
