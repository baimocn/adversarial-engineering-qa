# 优化面介绍

在冻结噪声标签和两层GCN骨干下，研究抗噪损失、样本/邻居加权、训练标签可靠性、图一致性与标签无关推断读出；可新增静态方法类或PLAN数值方法，不限常量搜索。

可修改：training_objective与数值方法钩子；训练样本权重、伪标签及辅助损失；同骨干inference_readout与分阶段集成PLAN；共同7200秒预算内的epoch日程。

固定面：两图特征/边/划分及冻结噪声标签；GCN hidden64/2层/dropout0.5；Adam lr0.01 weight_decay0.0005；验证标签仅评价选点；测试标签仅Verifier。

指标与质量门：隐藏测试两图accuracy百分数宏平均，maximize；score=(x-B)/(U-B)，B=61.8833 U=75.1333，不裁剪；题面要求模型可加载和非恒定预测。资格三seed改善≥3σ_B且归一化[0.15,0.8]。

# Baseline 与 Reference 跑分

Baseline 方法：未修改Starter：两层GCN，冻结损坏训练标签交叉熵，Adam固定超参，200次更新，验证准确率选最佳checkpoint。

Reference 方法：修复版DREAM：仅损坏训练标签的结构/特征kNN双路LP估计同类锚点，用语义同质性加权交叉熵并辅以对比损失和温度缩放；500次更新，同骨干、同选点规则。

主指标：macro_average_test_accuracy_percent（越高越好）。

| training_seed | Baseline | Reference | 配对改善 | 有效性 |
|---|---:|---:|---:|---|
| 3000 | 60.05 | 70.25 | 10.2 | B:是 / R:是 |
| 3001 | 62.6 | 71.4 | 8.8 | B:是 / R:是 |
| 3002 | 63 | 69.95 | 6.95 | B:是 / R:是 |

汇总：Baseline 均值 61.8833333333，样本标准差 1.60026039548；Reference 均值 70.5333333333，样本标准差 0.765397500214。

改善结论：全部三组正式成对值：3000 60.05→70.25；3001 62.6→71.4；3002 63→69.95。Δ=8.65000000，σ_B=1.60026040，Δ/σ_B=5.40537029；生效U归一化=0.65283183，预声明100天花板对照=0.22693485，均达标。

质量门：正式12个模型的字节SHA/大小与artifact、training_summary、正式测试索引一致；记录全部正常结束、非退化且独立重载预测相同。未独立复跑。当前grader没有实施模型加载质量门，单列当前实现缺陷；不据此无差别否认历史正式记录。

# 前置内容门槛

| 门槛 | 结论 | 原因 |
|---|---|---|
| G01 方法级优化空间 | 通过 | 开放损失、可靠性权重、数值PLAN与图读出，固定框架未把研究空间缩为常量。 |
| G02 Baseline 合理性 | 通过 | Baseline在已有材料范围内合理；五维与B01–B08已核，未见故障、挑seed或无依据截短。 |
| G03 Reference 提升充分性 | 通过 | 三组正式测试改善8.65=5.4054σ_B；生效锚点分数0.65283，预声明100口径0.22693，均达标。 |

G03 复算：Δ=8.65；σ_B（样本标准差）=1.60026039548；U=75.1333；归一化分数=0.652831831023。

# 两条轨迹迭代概况

| Agent 轨迹 | 状态 | 打包轮数 | 声明有效轮数 | 有效时长 | 概况与最终结果 |
|---|---|---:|---:|---:|---|
| codex | 完整 | 193 | 193 | - | 193轮：GCE和前向校正→分类别小损失/等额配额筛选→软邻域平滑和硬投票→裕量、度数和独立邻居门控；round183达到66.7，后10轮持平或回退。 时长声明分别39613/41572秒，但原始映射未完成扣除认证；非当前协议研究；原合同round183=66.7；原字节独立公开复验66.7。 |
| seed | 完整 | 53 | 52 | - | 53轮：small-loss与LP→结构/特征双路LP→自适应TLP→三阶段自训练与五成员共识修正→后TLP迭代、冷却及度数硬化；round43记录71.4，后续EMA/SWA/扩展传播等未刷新。 时长声明分别39613/41572秒，但原始映射未完成扣除认证；非当前协议研究；原合同round43=71.4；原字节公开复验71.1，受信任接口迁移后当前字节公开复验71.2；不把三个值互相替换。 |

# 轨迹可信性与题包绑定

codex：分数有效性待确认；seed：分数有效性待确认

| 轨迹 | 所交内容审查 | 分数与当前包对应 | 审查范围 | run_summary 哈希 |
|---|---|---|---|---|
| codex | 待补充核验 | 分数有效性待确认 | 仅审查已交轮次/方法摘要；未提供工具调用或sessions，结论限于这些材料。 | run_summary 的四项题包哈希与当前包一致。 |
| seed | 待补充核验 | 分数有效性待确认 | 仅审查已交轮次/方法摘要；未提供工具调用或sessions，结论限于这些材料。 | run_summary 的四项题包哈希与当前包一致。 |

# QA15 资源证据

CPU题，两侧16CPU/0GPU；按最慢正式R493.55s及额外重载开销留余量估整轮900s/16CPU/0GPU，<2h/<64CPU。CPU历史结果未改标H20实测。

| 运行 | 计时范围 | 记录耗时（秒） | GPU 数量/型号 | 分配 CPU 核 |
|---|---|---:|---|---:|

资源需求估算：完整一轮约 900 秒，0 张 GPU，16 核 CPU；最大正式R execution.elapsed=493.55秒；日志中训练与重载是分别计时，汇总声称含reload不可直接视为严格全阶段测量。追加重载/IO并留约6分钟余量估900秒，两图小GCN/数千节点；这是CPU估算，不是目标卡或内场实测。

计时口径：涵盖完整一轮两图训练、预测导出、独立重载和评分；不含整条研究、排队、安装。

# 目标部署能力

配置范围：innerfield-maso-v1

当前交付符合内场能力检查；Solver/Verifier 仍须不同 sandbox。

任务硬件与成绩对应：cpu / same_hardware；正式B/R均CPU、同声明环境；GPU历史研究/宿主卡型不冒充当前测量，未见硬件变化影响这六个正式结果。
证据：workspace/harbor_task/task.toml；optimization_evidence/formal_test_scoring_declared.json；expert_evidence/repair/protocol_decisions.json

# 格式对齐建议

三目录职责明确；正式B/R轻量结构完整，历史开发/失效v7/oracle为额外材料不机械扣错。八字段和当前指纹有效，历史绑定保留迁移；Dev权限及模型门属于真实实现问题而非布局问题。

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
- `optimization_evidence/historical_development_attempts`（可保留的额外项）：可保留失败开发证据，明确不加入正式聚合。
- `optimization_evidence/historical_v7_invalid_reference`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
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
- `expert_evidence/专家作业说明文档.md`（可合并）：修正seed3000表格Δ=8.10的文字算术错误，成对原值应为10.20；汇总Δ=8.65是正确的。
- `expert_evidence/repair/README_NOT_READY.md`（可保留的额外项）：保留历史快照标签，避免与v9正式结果混用。

说明：额外材料仅作精简或归位建议，不因多交而单独判错。

# 质检结论：不通过

产物：evidence-input｜通过 14 项｜不通过 4 项｜未完成 3 项｜跳过/不适用 0 项

前置三门：通过 3 项｜不通过 0 项｜待核验 0 项；全部复核完成：否。

口径：只读检查及已有证据复核；QA07/08 查 instruction；QA18 审所交轨迹及提供的 sessions，QA21 单独核对 run_summary 的四项题包哈希；QA15 允许根据日志、轨迹和B/R实现估算资源。QA16 两条各至少 10h；仅无训练且单轮很短、例外证据完整时可各至少 7h。排队、安装与故障不计有效迭代时长。未执行提交代码、未独立复跑或反序列化模型。

Harbor 格式/接口：不通过；已提交 NOP 的运行或任务版本关联待核实。

| 检查项 | 是否通过 | 原因 |
|---|---|---|
| QA01 八章节与题面信息泄露 | 通过 | 八章节齐全，描述任务和接口，未给DREAM名、论文或仓库来源。 |
| QA02 评分公式与 0/1 锚点 | 通过 | 可信calibration B=61.8833 U=75.1333；normalize_score直接(x-B)/(U-B)，连续单调且不裁剪，B→0/U→1。 |
| QA03 参考解分数与复现材料 | 通过 | Reference源码/入口和三个正式seed的实际日志、模型索引及独立重载俱全；归一化0.65283有效，历史v7失效结果未采用。 |
| QA04 波动指标的 3σ 可分辨性 | 通过 | setup_seed进入Python/numpy/torch；三seed同集合固定方法独立重训，改善8.65≥3×1.6002604；不是同checkpoint重复评估。 |
| QA05 约束执行实现 | 不通过 | 单轮7200秒仅声明而未执行；模型加载质量门未实施。网络约束迁移单独保留豁免。 |
| QA06 Verifier 入口、分数与错误处理 | 通过 | bash /tests/test.sh经隔离Python进入grader，异常分层并落有限reward.json/txt；不把模型门缺陷掩盖为已加载。 |
| QA07 instruction 中的 Hidden 信息泄露 | 通过 | 仅审题面：未披露私有测试标签、样本答案或可恢复答案。 |
| QA08 instruction 中的参考解信息泄露 | 不通过 | 题面第69行披露Reference采用500 epochs，而n_epochs本身为研究变量；属于参考具体可变配置泄露。 |
| QA09 结果清理与原子写入 | 通过 | main预清理reward.json/txt；临时文件写入后os.replace原子替换。 |
| QA10 冻结面保护或恢复实现 | 通过 | Verifier-owned policy固定AST和配置，冻结数据/调度/训练及评价骨架；独立镜像calibration不执行候选自证钩子，Agent仅solution可写。 |
| QA11 instruction 八项内容 | 不通过 | 八项内容俱全，但可加载模型门与仅预测数组评分不一致；配置的公开Dev输出与默认身份权限不一致。 |
| QA12 Git 清理 | 通过 | 安全清点题包未见.git目录；不把报告工作区的.git占位目录当题包内容。 |
| QA13 Baseline 与参考解提升 | 通过 | 三组正式隐藏TEST成对原值完整，方法和种子固定，均正改善、质量记录通过；验证集字段更名不混用；B合理，G03数值达标。 |
| QA14 合法改进空间 | 通过 | 开放数值方法接口支持损失/样本选择/图读出联合设计；R尚非饱和，双路一致性和可靠性更新存在合法方法空间，未在题面给出答案。 |
| QA15 评分资源需求估算 | 通过 | CPU题，两侧16CPU/0GPU；按最慢正式R493.55s及额外重载开销留余量估整轮900s/16CPU/0GPU，<2h/<64CPU。CPU历史结果未改标H20实测。 |
| QA16 轨迹实际迭代时长 | 待补充核验 | codex缺少有效时长或排除排队/安装/故障的核算证据；seed缺少有效时长或排除排队/安装/故障的核算证据 |
| QA17 Harbor Harness 兼容性 | 不通过 | Harbor 子项未通过：H03 环境与运行路径；H04 测试入口与 reward；H05 Job/Trial 调用配置；H06 NOP 自检记录；详细原因与证据保留在 report.json。 |
| QA18 轨迹、日志与分析 | 待补充核验 | 全读Codex193/Seed53轮与事件映射、best及复验；没有已交原始sessions，行为范围为现有摘要/事件。实际模型可识别；原启动/同条件证明缺口，Seed71.4不改写为当前71.2。 |
| QA19 seed 与有效提升阈值 | 通过 | 题面明确冻结corruption seed3000、训练seed3000/3001/3002和样本σ_B的3σ有效提升阈值；区分资格多seed与单候选reward。 |
| QA20 修改范围、网络与工具策略 | 通过 | 题面有可改文件/数值边界、网络查表禁令、平台默认工具策略和禁止评分器篡改。 |
| QA21 三个 JSON 的填写内容 | 待补充核验 | 两轨八字段246轮均具备，旧ok状态/展示时区已识别；annotation/summary/best可解析。当前四项e5a5eb…匹配45文件，历史v7到当前接口绑定仅按迁移处理。 |

风险提示（不额外计入清单结论）：U在正式结果之后从100改成75.1333已披露；预声明100下0.22693同样达标，不认作依赖事后调锚点过线。 生效oracle到R剩余4.59997点略低于3σ_B=4.80078；按原则性headroom风险保留，不升级为额外硬门槛；Seed历史71.4原字节复验71.1、当前迁移71.2，不应互换；仅当前复验分数用于当前best说明；已有日志非独立复现；正式模型仅核字节SHA/大小及文本记录，没有加载模型、私有标签或执行提交程序。

# 退回专家说明

QA05 约束执行实现（不通过）：单轮7200秒仅声明而未执行；模型加载质量门未实施。网络约束迁移单独保留豁免。
证据：workspace/harbor_task/instruction.md；workspace/harbor_task/task.toml；workspace/harbor_task/environment/starter/predictor/Base_Predictor.py；workspace/harbor_task/tests/grader.py
请修改/补充：在可信启动/训练控制链加入覆盖每轮两图训练、导出与必要重载的7200秒计时与超时处理，保持题面和配置一致。；在独立可信Verifier实施模型存在及可加载质量门并使用与题面一致的安全重载接口；同步准备独立依赖。
复检验收材料：可定位的可信计时/终止实现与阶段覆盖说明；平台后续运行验证不作为本轮要求补跑历史轨迹。；可信评分调用链中可定位的模型检查/加载与失败分支，明确模型和预测对应路径。

QA08 instruction 中的参考解信息泄露（不通过）：题面第69行披露Reference采用500 epochs，而n_epochs本身为研究变量；属于参考具体可变配置泄露。
证据：workspace/harbor_task/instruction.md:69
请修改/补充：将正式B/R各自实际epoch日程移到专家侧证据，题面仅保留共同预算与epoch可研究的规则。
复检验收材料：instruction保留完整可操作接口和预算，且不再披露Reference的实际可变日程；专家侧预算对照仍保留。

QA11 instruction 八项内容（不通过）：八项内容俱全，但可加载模型门与仅预测数组评分不一致；配置的公开Dev输出与默认身份权限不一致。
证据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/grader.py；workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/environment/public_eval/evaluate.py
请修改/补充：在独立可信Verifier实施模型存在及可加载质量门并使用与题面一致的安全重载接口；同步准备独立依赖。；将配置的Dev输出改到Agent可写目录，例如/workspace/solution/results.json，并同步任何引用；或在镜像中仅准备所需可写输出位置。
复检验收材料：可信评分调用链中可定位的模型检查/加载与失败分支，明确模型和预测对应路径。；task.toml命令、镜像权限与evaluate.py实际写路径静态一致；无需通过放宽公开/私有冻结面权限修复。

QA16 轨迹实际迭代时长（待补充核验）：codex缺少有效时长或排除排队/安装/故障的核算证据；seed缺少有效时长或排除排队/安装/故障的核算证据
证据：expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/timing_codex.tsv；expert_evidence/timing_seed.tsv
请修改/补充：为codex、seed补一张时长表：研究起止、排队/安装/API失联/故障区间、仍正常运行的训练重叠及有效秒数。可引用已交轨迹和日志片段；不强制提交完整timer或sessions。
复检验收材料：可复算的两轨起止/扣除表，与轨迹时间相符；默认每轨≥36000有效秒。最终复验、收集和明确故障不计，健康训练并发只计一次。

QA17 Harbor Harness 兼容性（不通过）：Harbor 子项未通过：H03 环境与运行路径；H04 测试入口与 reward；H05 Job/Trial 调用配置；H06 NOP 自检记录；详细原因与证据保留在 report.json。
证据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/grader.py；workspace/harbor_task/environment/public_eval/evaluate.py；workspace/harbor_task/tests/test.sh；workspace/harbor_task/instruction.md；workspace/harbor_task/tests/contract_guard.py；expert_evidence/repair/harbor/native_nop_trial/native_trial/config.json；expert_evidence/repair/harbor/native_nop_trial/native_trial/result.json；expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/reward.json；expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/test-stdout.txt；expert_evidence/repair/harbor/native_nop_trial/VERSION_BINDING.md；expert_evidence/repair/historical_docker_simulation_not_nop/result.json；expert_evidence/repair/historical_evidence_assessment.json
请修改/补充：修正H03的Dev输出写权限，并在H04可信评分链实施模型可加载质量门。镜像准备、运行验证和历史NOP仅按具体政策处理，不要求补跑历史研究。
复检验收材料：当前task.toml Dev命令与Agent权限一致；独立Verifier存在模型检查/重载失败分支且依赖齐全；原历史NOP和平台待执行状态如实保留。

QA18 轨迹、日志与分析（待补充核验）：全读Codex193/Seed53轮与事件映射、best及复验；没有已交原始sessions，行为范围为现有摘要/事件。实际模型可识别；原启动/同条件证明缺口，Seed71.4不改写为当前71.2。
证据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/repair/historical_timing_mapping/timing_map.json；expert_evidence/run_summary.json；expert_evidence/best_method_selection.json；expert_evidence/repair/original_v7_current_bytes/codex/summary.json；expert_evidence/run_summary.json#task_binding；expert_evidence/repair/original_v7_current_bytes/seed/summary.json
请修改/补充：保留原证据与迁移事实，由本批具体历史政策处理，不要求新增历史运行。
复检验收材料：已交轨迹、计时及版本说明，原状态与豁免分别展示。

QA21 三个 JSON 的填写内容（待补充核验）：两轨八字段246轮均具备，旧ok状态/展示时区已识别；annotation/summary/best可解析。当前四项e5a5eb…匹配45文件，历史v7到当前接口绑定仅按迁移处理。
证据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/expert_annotation.json；expert_evidence/best_method_selection.json；workspace/harbor_task/instruction.md
请修改/补充：保留原证据与迁移事实，由本批具体历史政策处理，不要求新增历史运行。
复检验收材料：已交轨迹、计时及版本说明，原状态与豁免分别展示。
