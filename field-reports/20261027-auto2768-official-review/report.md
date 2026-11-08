# 优化面介绍

在两张固定噪声标签引文图上研究鲁棒训练与图推断读出；开放可执行方法接口，冻结骨干、优化器、数据与评分。

可修改：训练目标/损失、样本或邻居加权、训练标签可靠性估计；辅助自监督/一致性目标及训练日程；同骨干图读出；经审计的多阶段/集成数值 PLAN 与四个开放 hook。

固定面：Cora/CiteSeer 图特征/边/划分及 uniform@0.3 冻结训练标签；GCN 64宽2层/ReLU/dropout=.5；Adam lr=.01 wd=.0005；验证标签仅作评价/选点；私有测试标签；7200s 两图训练预算与最终单组预测评分。

指标与质量门：maximize 两图未加权平均 Hidden test accuracy (%)；score=(x−61.8833)/(75.1333−61.8833)，不裁剪；模型可加载、非退化及源码契约门。

# Baseline 与 Reference 跑分

Baseline 方法：Starter plain GCN，损坏训练标签 CE；200 epoch/图，Adam .01/.0005，按验证准确率选点，正式3000/3001/3002均独立初始化训练及独立进程重载。

Reference 方法：修复 DREAM：只从损坏训练标签做结构+特征kNN双路传播推断同类锚点，以语义同质性重加权CE并加图增强对比损失/温度缩放；500 epoch/图，同骨干、优化器、数据、预算与验证选点。

主指标：macro_average_hidden_test_accuracy_percent（越高越好）。

| training_seed | Baseline | Reference | 配对改善 | 有效性 |
|---|---:|---:|---:|---|
| 3000 | 60.05 | 70.25 | 10.2 | B:是 / R:是 |
| 3001 | 62.6 | 71.4 | 8.8 | B:是 / R:是 |
| 3002 | 63 | 69.95 | 6.95 | B:是 / R:是 |

汇总：Baseline 均值 61.8833333333，样本标准差 1.60026039548；Reference 均值 70.5333333333，样本标准差 0.765397500214。

改善结论：全部正式seed改善10.20/8.80/6.95；均值改善8.65000000，σ_B=1.60026040，改善/σ=5.405370。生效U=75.1333归一化0.652830；原定U=100为0.226935，两者均在[.15,.8]。U为出分后改用独立clean-label oracle，非预注册；资格结论不依赖该变更。

质量门：12个正式图训练正常结束、预测非退化，checkpoint文件哈希与manifest/逐图summary吻合；独立重载日志exit=0且预测一致。result.metrics是公开val，Hidden值来自formal_test_scoring_declared的12条逐图记录，未混用。历史v7泄漏Reference已隔离无效，未采用。

# 前置内容门槛

| 门槛 | 结论 | 原因 |
|---|---|---|
| G01 方法级优化空间 | 通过 | 实际允许训练目标/加权/可靠性/数值hook及图读出；guard保留可执行方法空间。Reference双路锚点与对比目标是方法变化，不是仅常量搜索。 |
| G02 Baseline 合理性 | 通过 | 朴素噪声GCN为Starter/正式B；3 seed每图实训200更新、按val选点且reload一致。R500更新是允许日程变量，共7200s预算；未发现故障、削弱或挑seed反证。 |
| G03 Reference 提升充分性 | 通过 | 三seed全部有效，Hidden Δ=8.65≈5.40537σ_B，生效U归一化.65283、原定100为.226935，均达标。U出分后变更披露且有独立oracle，资格结论不靠改U通过。 |

G03 复算：Δ=8.65；σ_B（样本标准差）=1.60026039548；U=75.1333；归一化分数=0.652831831023。

# 两条轨迹迭代概况

| Agent 轨迹 | 状态 | 打包轮数 | 声明有效轮数 | 有效时长 | 概况与最终结果 |
|---|---|---:|---:|---:|---|
| Codex / gpt-5.6-sol | 完整 | 193 | 193 | - | 1–8 GCE/前向噪声校正，9–29分类别小损失/配额/渐进筛选，30–56邻域软概率到硬投票，57–112裕量加权/自身不确定带/多邻居独立佐证，113–193多数为局部边界试验与回退；183达到66.7，末轮恢复；历史round183 Dev66.7；原字节重跑66.7。 |
| Seed / Doubao-Seed-2.1-turbo | 完整 | 53 | 52 | - | 1–9 small-loss/平滑/双路LP与退火，10–18测试时传播、自训练到3阶段5成员共识；19–30更深阶段/EMA/重加权/蒸馏多次下降均保留；31后集成TLP、多程冷却与度数硬化，43达71.4；44–53回退最佳。35/36重复映射、48/49共享窗不作额外独立闭环；历史round43 Dev71.4；旧字节重跑71.1，迁移当前字节公开复验71.2；不得混作同一结果。 |

# 轨迹可信性与题包绑定

Codex / gpt-5.6-sol：评分来源未确认、分数有效性待确认；Seed / Doubao-Seed-2.1-turbo：评分来源未确认、分数有效性待确认

| 轨迹 | 所交内容审查 | 分数与当前包对应 | 审查范围 | run_summary 哈希 |
|---|---|---|---|---|
| Codex / gpt-5.6-sol | 待补充核验 | 评分来源未确认、分数有效性待确认 | 仅审查已交轮次/方法摘要；未提供工具调用或sessions，结论限于这些材料。 | run_summary 的四项题包哈希与当前包一致。 |
| Seed / Doubao-Seed-2.1-turbo | 待补充核验 | 评分来源未确认、分数有效性待确认 | 仅审查已交轮次/方法摘要；未提供工具调用或sessions，结论限于这些材料。 | run_summary 的四项题包哈希与当前包一致。 |

# QA15 资源证据

CPU题两侧GPU=0、各16CPU。正式两图train≤493.55s，迁移best两图541.97s；加独立reload/评分及余量估完整单轮1200s，≤7200s/64CPU。估算非目标平台实测。

| 运行 | 计时范围 | 记录耗时（秒） | GPU 数量/型号 | 分配 CPU 核 |
|---|---|---:|---|---:|

资源需求估算：完整一轮约 1200 秒，0 张 GPU，16 核 CPU；正式最大两图训练493.55s；迁移best两图248.48+293.49=541.97s，加入独立重载与轻量npz/AST评分及充足余量估1200s。16CPU来自当前配置，CPU模型小于数MB，图张量小于50MB；这是静态需求估算，不是MASO实测。

计时口径：覆盖两图训练、两次独立重载、最终AST/模型门与预测评分；排队/安装/整条研究不计。题面训练预算排除reload，QA15估算仍包括reload。

# 目标部署能力

配置范围：innerfield-maso-v1

当前交付符合内场能力检查；Solver/Verifier 仍须不同 sandbox。

任务硬件与成绩对应：cpu / same_hardware；正式B/R均--device cpu；当前gpus0无需换H20/L20。历史主机含A100/RTX3080Ti不代表CPU运行使用GPU；不同Python校准环境不冒充平台实测，不影响已审同环境B/R。
证据：optimization_evidence/baseline_runs/seed_3000/run.log；optimization_evidence/baseline_runs/seed_3001/run.log；optimization_evidence/baseline_runs/seed_3002/run.log；optimization_evidence/reference_runs/seed_3000/run.log；optimization_evidence/reference_runs/seed_3001/run.log；optimization_evidence/reference_runs/seed_3002/run.log；workspace/harbor_task/task.toml；expert_evidence/repair/current_source_revalidation/runtime.json

# 格式对齐建议

三目录职责及按seed聚合的双图result/model结构可等价追溯；源JSON八字段均可解析，hash当前匹配。historical/repair与旧失败材料仅归档，不按多交或旧源路径误当当前必需运行目录。

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
- `optimization_evidence/historical_development_attempts`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/historical_v7_invalid_reference`（可保留的额外项）：保留明确无效标识，与正式B/R隔离；不删除失败。
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
- `expert_evidence/repair`（可保留的额外项）：保留修复与历史原判，建议用当前索引链接，避免旧报告状态被误读。
- `optimization_evidence/comparison_summary.json`（可合并）：统计字段多处冗余，后续可合并但保留原始值和U变更披露；本轮不因冗余扣错。

说明：额外材料仅作精简或归位建议，不因多交而单独判错。

# 质检结论：不通过

产物：evidence-input｜通过 16 项｜不通过 2 项｜未完成 3 项｜跳过/不适用 0 项

前置三门：通过 3 项｜不通过 0 项｜待核验 0 项；全部复核完成：否。

口径：只读检查及已有证据复核；QA07/08 查 instruction；QA18 审所交轨迹及提供的 sessions，QA21 单独核对 run_summary 的四项题包哈希；QA15 允许根据日志、轨迹和B/R实现估算资源。QA16 两条各至少 10h；仅无训练且单轮很短、例外证据完整时可各至少 7h。排队、安装与故障不计有效迭代时长。未执行提交代码、未独立复跑或反序列化模型。

Harbor 格式/接口：未完成；已提交自检记录不满足 NOP 运行要求。

| 检查项 | 是否通过 | 原因 |
|---|---|---|
| QA01 八章节与题面信息泄露 | 通过 | 八节实质内容齐全，题面未给参考方法名称、来源论文或仓库；开放接口说明属于必要契约。 |
| QA02 评分公式与 0/1 锚点 | 通过 | normalize_score直接(x-B)/(U-B)，B=61.8833、U=75.1333；连续单调无裁剪，0/1锚点正确。经验U事后变更已披露，原定U=100亦达资格门。 |
| QA03 参考解分数与复现材料 | 通过 | Reference入口与3 seed×2图记录、非空原日志、12个B/R模型及独立reload齐全；Hidden R均值70.5333，归一化.65283；不拿val代替Hidden。 |
| QA04 波动指标的 3σ 可分辨性 | 通过 | 三seed均进入setup_seed实际随机过程；每角色固定配置独立训练，同集合成对。Δ=8.65≥3σ_B=4.80078，约5.40537σ；未用标准误。 |
| QA05 约束执行实现 | 不通过 | 固定源码/标签流守卫、模型加载门、run.sh每图timeout均有实现且范围与题面一致；禁外部查表仅规则，删禁网字段未形成可信网络执行，保留该迁移缺口。 |
| QA06 Verifier 入口、分数与错误处理 | 通过 | bash /tests/test.sh以隔离Python调用grader，正常与失败均落有限reward；JSON优先且标量主指标明确。 |
| QA07 instruction 中的 Hidden 信息泄露 | 通过 | 仅审题面：未披露私有测试标签/样本答案或可恢复答案；提及Hidden与禁令不构成泄露。 |
| QA08 instruction 中的参考解信息泄露 | 通过 | 仅审题面：未披露Reference代码/具体epoch配置/成绩、论文或仓库；GCN/Adam固定量为任务契约。 |
| QA09 结果清理与原子写入 | 通过 | main先clean_stale_rewards，reward两格式均经同目录tmp、os.replace原子替换。 |
| QA10 冻结面保护或恢复实现 | 通过 | 独立Verifier持有policy/calibration/private，候选只作AST检查；Agent镜像公开冻结面chmod只读且USER agent；评分不导入候选模块。 |
| QA11 instruction 八项内容 | 通过 | 八部分输入输出/可改边界/评分/资源/迭代/完成条件一致；Dev输出为可写solution/results.json。预算明示仅两图train，reload另计；旧run.sh注释提reload与代码不符属注释遗留，题面已准确界定。 |
| QA12 Git 清理 | 通过 | 安全清点题包无.git目录；无remotes/tags/reflog待清理。 |
| QA13 Baseline 与参考解提升 | 通过 | 正式三组Hidden原值逐图配对完整，Δ10.20/8.80/6.95与说明一致，宏均值改善8.65；质量门与模型hash/reload无反证，旧泄漏Reference未用。 |
| QA14 合法改进空间 | 通过 | 可实现新损失、可信度估计与图推断而非只调常量；可继续研究结构/特征分歧下的稳健加权。R未饱和；经验U余量4.6略小于3σ约4.8008，作为风险保留不设额外硬门。 |
| QA15 评分资源需求估算 | 通过 | CPU题两侧GPU=0、各16CPU。正式两图train≤493.55s，迁移best两图541.97s；加独立reload/评分及余量估完整单轮1200s，≤7200s/64CPU。估算非目标平台实测。 |
| QA16 轨迹实际迭代时长 | 待补充核验 | Codex / gpt-5.6-sol缺少有效时长或排除排队/安装/故障的核算证据；Seed / Doubao-Seed-2.1-turbo缺少有效时长或排除排队/安装/故障的核算证据 |
| QA17 Harbor Harness 兼容性 | 不通过 | Harbor 子项未通过：H03 环境与运行路径；H05 Job/Trial 调用配置；H06 NOP 自检记录；详细原因与证据保留在 report.json。 |
| QA18 轨迹、日志与分析 | 待补充核验 | 已审Codex193轮与Seed53轮、全部方法/分数/best和计时映射。两轨属本题且演进不同；缺原启动Prompt/最高推理档/完整工具记录，历史最佳不可冒称当前复现71.4。未发现已确认A/B实质条件差异。 |
| QA19 seed 与有效提升阈值 | 通过 | 题面明确冻结corruption seed、独立训练seed全集3000/3001/3002，Δ>0且≥3样本σ_B与归一化区间；区分单次候选reward和资格统计。 |
| QA20 修改范围、网络与工具策略 | 通过 | 题面列可改范围、禁止联网查原标签及平台默认工具策略；无需外部服务，公开工具与solution工作区明确。 |
| QA21 三个 JSON 的填写内容 | 待补充核验 | 三JSON可解析，193/53轮八字段齐全、状态ok且time非null；当前四项hash重算与run_summary一致。显式说明两轨历史dream-v1，当前绑定不能证明历史版本；best历史71.4与迁移71.2分开。 |

风险提示（不额外计入清单结论）：经验U出分后由100改为75.1333，不是预注册；两套口径都通过，保留选择披露；经验U剩余headroom4.6略小于3σ_B=4.8008，非额外硬门；历史轨迹/时长/当前NOP尚不具备完整绑定；本次仅只读静态审阅，未独立复跑。

# 退回专家说明

QA05 约束执行实现（不通过）：固定源码/标签流守卫、模型加载门、run.sh每图timeout均有实现且范围与题面一致；禁外部查表仅规则，删禁网字段未形成可信网络执行，保留该迁移缺口。
证据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/contract_guard.py；workspace/harbor_task/tests/grader.py；workspace/harbor_task/environment/starter/run.sh；workspace/harbor_task/task.toml
请修改/补充：本批旧证明/平台事项按具体豁免处理；原标准复核需要对应当前证据，不能改标历史运行。
复检验收材料：核对对应引用、原始事实与适用范围；本批不新增历史研究或平台运行义务。

QA16 轨迹实际迭代时长（待补充核验）：Codex / gpt-5.6-sol缺少有效时长或排除排队/安装/故障的核算证据；Seed / Doubao-Seed-2.1-turbo缺少有效时长或排除排队/安装/故障的核算证据
证据：expert_evidence/trajectory_codex.json；expert_evidence/run_summary.json；expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/qa16_best_method_revalidation.json；expert_evidence/best_method_selection.json；expert_evidence/seed_round_mapping.json；expert_evidence/timing_codex.tsv；expert_evidence/trajectory_seed.json；expert_evidence/timing_seed.tsv
请修改/补充：为Codex / gpt-5.6-sol、Seed / Doubao-Seed-2.1-turbo补一张时长表：研究起止、排队/安装/API失联/故障区间、仍正常运行的训练重叠及有效秒数。可引用已交轨迹和日志片段；不强制提交完整timer或sessions。
复检验收材料：可复算的两轨起止/扣除表，与轨迹时间相符；默认每轨≥36000有效秒。最终复验、收集和明确故障不计，健康训练并发只计一次。

QA17 Harbor Harness 兼容性（不通过）：Harbor 子项未通过：H03 环境与运行路径；H05 Job/Trial 调用配置；H06 NOP 自检记录；详细原因与证据保留在 report.json。
证据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/grader.py；workspace/harbor_task/environment/public_assets/manifest.json；expert_evidence/repair/harbor/schema_validation.json；expert_evidence/repair/harbor/upstream_sources.json；workspace/harbor_task/tests/requirements.txt；workspace/harbor_task/tests/test.sh；workspace/harbor_task/environment/starter/run.sh；workspace/harbor_task/tests/calibration.json；optimization_evidence/README.md；expert_evidence/repair/harbor/native_nop_trial/native_trial/config.json；expert_evidence/repair/harbor/native_nop_trial/native_trial/result.json；expert_evidence/repair/harbor/native_nop_trial/environment_record.json；expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/reward.json；expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/reward.txt；expert_evidence/repair/harbor/native_nop_trial/native_trial/trial.log；expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/test-stdout.txt；expert_evidence/repair/harbor/native_nop_trial/native_trial/artifacts/manifest.json；expert_evidence/repair/harbor/native_nop_trial/VERSION_BINDING.md
请修改/补充：本批旧证明/平台事项按具体豁免处理；原标准复核需要对应当前证据，不能改标历史运行。
复检验收材料：核对对应引用、原始事实与适用范围；本批不新增历史研究或平台运行义务。

QA18 轨迹、日志与分析（待补充核验）：已审Codex193轮与Seed53轮、全部方法/分数/best和计时映射。两轨属本题且演进不同；缺原启动Prompt/最高推理档/完整工具记录，历史最佳不可冒称当前复现71.4。未发现已确认A/B实质条件差异。
证据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/best_method_selection.json；expert_evidence/qa16_best_method_revalidation.json；expert_evidence/seed_round_mapping.json；expert_evidence/run_summary.json#task_binding
请修改/补充：本批旧证明/平台事项按具体豁免处理；原标准复核需要对应当前证据，不能改标历史运行。
复检验收材料：核对对应引用、原始事实与适用范围；本批不新增历史研究或平台运行义务。

QA21 三个 JSON 的填写内容（待补充核验）：三JSON可解析，193/53轮八字段齐全、状态ok且time非null；当前四项hash重算与run_summary一致。显式说明两轨历史dream-v1，当前绑定不能证明历史版本；best历史71.4与迁移71.2分开。
证据：expert_evidence/run_summary.json；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/expert_annotation.json；expert_evidence/best_method_selection.json；expert_evidence/qa16_best_method_revalidation.json
请修改/补充：本批旧证明/平台事项按具体豁免处理；原标准复核需要对应当前证据，不能改标历史运行。
复检验收材料：核对对应引用、原始事实与适用范围；本批不新增历史研究或平台运行义务。
