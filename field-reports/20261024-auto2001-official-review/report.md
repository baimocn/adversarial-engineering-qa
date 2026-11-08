# 优化面介绍

APAVA受试者级EEG二分类，输入(256,16)，输出2类logits；允许替换特征表示、序列建模、通道图、增广与损失等可执行方法。固定数据划分、种子和12轮SWA协议；并非固定框架内纯常量搜索。

可修改：models/SolutionModel.py中的架构/编码器/融合/图建模；run.py训练方法组件、增广、损失、正则；预算内结构配置与推理建模策略。

固定面：受试者train15/val4/test4、真实标签和评价口径；Adam lr1e-4、12 epochs、SWA ep3..12、协议seeds41/42/43；data_provider、preprocess_apava.py、evaluate.py、make_submission.py及tests评分器；单卡≤24GB、单次训练≤1800s、参数≤20M。

指标与质量门：test argmax macro-F1 maximize；reward=(F1−B)/(1−B)，U=1；Δ≥3σ_B(ddof1)及归一化[.15,.8]，并须协议/质量有效。

# Baseline 与 Reference 跑分

Baseline 方法：Starter=正式 BaselineFormer：三尺度 Conv1d[3,5,7]+d64/ff128/e2 Transformer，76529 参数；随机初始化，Adam1e-4，12轮无早停，SWA ep3..12；最新正式对照双方 batch32、1176 updates、37476 样本暴露。主评分 B 仍硬编码旧正式均值0.644488，最新正式B均值0.644707676857，二者未统一。

Reference 方法：MedMamba d256/ff512/e4：原始/差分/频域三分支状态空间编码、门控融合与空间图Mamba，15955713 参数；同数据、seeds41/42/43、12轮SWA。历史batch16/2352更新；最新作为正式主张的batch32/1176更新，将显存上限24e9放宽到44e9，Reference三次峰值28456255488字节，违反题面24GB协议。

主指标：test argmax macro_f1（越高越好）。

| training_seed | Baseline | Reference | 配对改善 | 有效性 |
|---|---:|---:|---:|---|
| 41 | 0.605780033317 | 0.786555800441 | 0.180775767124 | B:是 / R:否 |
| 42 | 0.638791621912 | 0.775106082037 | 0.136314460125 | B:是 / R:否 |
| 43 | 0.689551375342 | 0.771069380778 | 0.0815180054353 | B:是 / R:否 |

汇总：Baseline 均值 0.644707676857，样本标准差 0.0421978579526；Reference 均值 0.777577087752，样本标准差 0.00803347374602。

改善结论：最新batch32：B=0.644707676857，σ_B=0.042197857953，R=0.777577087752，Δ=0.132869410895=3.148724σ_B，Δ/(1−B)=0.373972085069；算术达标但三次R超题目显存预算，不是有效正式提升。历史非对称B@32/R@16：0.644488361634±0.042473252271 vs0.781203875269，3.218861σ；同batch16控制：B=0.649261330672，σ=.042971846000，R=.766720520604，2.733399σ，未达3σ。仪器化历史协议重跑3.199216σ仍为非对称batch。seed44/45仅开发敏感性，非正式五seed配对。 全部附加原值（按seed41/42/43）：historical_32_16 0.6051946724893178/0.7697259024835059,0.6387190370707312/0.7897113310241901,0.6895513753423668/0.7841743922985706；within_24GB_matched_16_16 0.6066176791433583/0.7861593985128246,0.6486122942127497/0.7935919225350538,0.692554018660992/0.7204102407641555；historical_protocol_instrumented_rerun_32_16 0.605780033316546/0.7820844856093527,0.6381183899585481/0.7738999715597448,0.6901751690383764/0.7867546638016436。

质量门：新正式R三次数据均可读取且退出0，但协议显存硬门失效（上限44GB、峰值28.456GB>24GB），reference_valid=false；不能用迁移豁免恢复有效性。未将历史Agent污染Dev分数用于作者正式B/R。 即使不采用全卡采样值，三次PyTorch allocator自身峰值均27,429,162,496字节，仍超过24GB及24GiB；并非仅凭全设备共享占用推定超预算。

# 前置内容门槛

| 门槛 | 结论 | 原因 |
|---|---|---|
| G01 方法级优化空间 | 通过 | 开放执行模型、损失/增广及图结构，Reference为真实多分支SSM/图模块替换；方法空间满足，非纯调参。 |
| G02 Baseline 合理性 | 不通过 | Baseline实现/12轮训练本身健康、合理朴素；但最新正式Reference上限44GB、峰值28.456GB超共同24GB任务预算，不能以该对照主张公平改善。 |
| G03 Reference 提升充分性 | 不通过 | 最新成对数值3.148724σ、归一化.373972算术达标，但三R超题面24GB而无效；预算内同batch16对照2.733399σ未达3σ，原非对称batch不能代替。；重算核验：质量门有效性未满足；seed 41 的 reference_valid 为 false；seed 42 的 reference_valid 为 false；seed 43 的 reference_valid 为 false |

复核建议：改善达到 3σ_B 但低于 5σ_B，建议复核稳定性；不单独判失败。

G03 复算：Δ=0.132869410895；σ_B（样本标准差）=0.0421978579526；U=1；归一化分数=0.373972085069。

# 两条轨迹迭代概况

| Agent 轨迹 | 状态 | 打包轮数 | 声明有效轮数 | 有效时长 | 概况与最终结果 |
|---|---|---:|---:|---:|---|
| Codex + GPT-5.6 Sol | 完整 | 216 | 216 | - | 已逐轮读取216轮，含共享早期、错误加载器765样本期、canonical修复后1413样本期。声明有效13.96h，但无可核对扣除台账，当前effective_seconds保持未知；GPT在canonical加载器上第211轮重建Baseline，第212-215轮宽核Mamba+dropout/WD+等权正反TTA，最终保留Dev=.7656649504010966；第216轮label smoothing未提升。此前1.0明确由第210轮作废。 |
| Codex + Seed 2.1 Turbo | 完整 | 104 | 104 | - | 已逐轮读取104轮；前65轮转写重建、多seed/结构/集成/TTA/校准探索，后段独立续跑。声明有效10.58h，但无可核对扣除台账，当前effective_seconds保持未知；Seed第89轮纯反向Mamba+bias1.65记录1.0，第94-104轮新尝试均低于1.0；summary声明13:52干净Dev n1413复验1.0。best_method记录该Seed权重，但缺当前冻结根文件preprocess_apava.py，不能直接作为当前有效提交；旧765与新1413口径不得合并排名。 |

# 轨迹可信性与题包绑定

Codex + GPT-5.6 Sol：分数无效；Codex + Seed 2.1 Turbo：分数无效

| 轨迹 | 所交内容审查 | 分数与当前包对应 | 审查范围 | run_summary 哈希 |
|---|---|---|---|---|
| Codex + GPT-5.6 Sol | 不通过 | 无效 | 仅审查已交轮次/方法摘要；未提供工具调用或sessions，结论限于这些材料。 | run_summary 的四项题包哈希与当前包一致。 |
| Codex + Seed 2.1 Turbo | 不通过 | 无效 | 仅审查已交轮次/方法摘要；未提供工具调用或sessions，结论限于这些材料。 | run_summary 的四项题包哈希与当前包一致。 |

- Codex + GPT-5.6 Sol：存在泄漏 / 已确认：GPT第210轮明确旧加载器错误映射使训练混入公开验证受试者，旧765口径1.0已作废；Seed早期共享同一工作区和该旧口径，早期分数不得作清洁独立证据。；受影响分数无效；影响轮次 [210]；证据 expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md
  修复：保留污染旧分数invalid，采用可归属的canonical后续片段；不自动要求历史补跑。；验收：逐段分数口径与采用范围说明；不把旧765满分作为正式B/R或干净双轨对照。

- Codex + Seed 2.1 Turbo：存在泄漏 / 已确认：GPT第210轮明确旧加载器错误映射使训练混入公开验证受试者，旧765口径1.0已作废；Seed早期共享同一工作区和该旧口径，早期分数不得作清洁独立证据。；受影响分数无效；影响轮次 [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65]；证据 expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md
  修复：保留污染旧分数invalid，采用可归属的canonical后续片段；不自动要求历史补跑。；验收：逐段分数口径与采用范围说明；不把旧765满分作为正式B/R或干净双轨对照。

# QA15 资源证据

缺少：当前成绩的硬件归属/换卡影响尚未确认

| 运行 | 计时范围 | 记录耗时（秒） | GPU 数量/型号 | 分配 CPU 核 |
|---|---|---:|---|---:|

资源需求估算：完整一轮约 5400 秒，1 张 GPU，16 核 CPU；当前已有六次batch32总流水约2905秒、三次Reference每次完整约906秒，三seed约2718秒；在目标卡留约一倍余量估算5400秒，非H20/L20实测。此可行估算不使超24GB正式成绩合法；评分侧CPU依赖与模型规模已审。

计时口径：包含三seed训练、SWA、独立reload/评分；不含镜像构建与排队。最终平台只加载最终候选的CPU评分应少于完整三seed估算；目标时效待平台。

# 目标部署能力

配置范围：innerfield-maso-v1

GPU声明目标H20/L20，Verifier CPU0GPU，无storage_mb/Compose；当前禁网声明已删而题面仍禁网络，等价机制未落实，按本批网络迁移政策豁免。
- GPU声明目标H20/L20，Verifier CPU0GPU，无storage_mb/Compose；当前禁网声明已删而题面仍禁网络，等价机制未落实，按本批网络迁移政策豁免。；证据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md

任务硬件与成绩对应：gpu / unverified；当前成绩的硬件归属/换卡影响尚未确认
证据：workspace/harbor_task/task.toml；optimization_evidence/comparison_summary.json；expert_evidence/g02_support/batch32_matched_control/RUN_META.json

# 格式对齐建议

三目录职责明确，公开Dev由starter/evaluate.py等价提供；6份附加batch32_formal_runs是正文batch32对照同源副本，不是额外seed。模型/日志均有原始材料；保留大量历史G02说明有用但若干汇总仍为旧口径，具体冲突已入QA02/21。

- `optimization_evidence/budget_ledger.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/learning_curves.csv`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/learning_curves.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/README.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `expert_evidence/g02_support`（可保留的额外项）：保留历史/匹配控制并标明正式采用范围，更新陈旧README避免将辅助结果混为主成绩。
- `expert_evidence/nop_trial_local_equivalent_20261004_superseded/`（可保留的额外项）：保留明确superseded标签和原坏绑定，不能当当前NOP成功。

说明：额外材料仅作精简或归位建议，不因多交而单独判错。

# 质检结论：不通过

产物：evidence-input｜通过 11 项｜不通过 8 项｜未完成 2 项｜跳过/不适用 0 项

前置三门：通过 1 项｜不通过 2 项｜待核验 0 项；全部复核完成：否。

口径：只读检查及已有证据复核；QA07/08 查 instruction；QA18 审所交轨迹及提供的 sessions，QA21 单独核对 run_summary 的四项题包哈希；QA15 允许根据日志、轨迹和B/R实现估算资源。QA16 两条各至少 10h；仅无训练且单轮很短、例外证据完整时可各至少 7h。排队、安装与故障不计有效迭代时长。未执行提交代码、未独立复跑或反序列化模型。

Harbor 格式/接口：不通过；已提交 NOP 的运行或任务版本关联待核实。

| 检查项 | 是否通过 | 原因 |
|---|---|---|
| QA01 八章节与题面信息泄露 | 通过 | 题面有八部分及补充提升判据；给通用SSM/图等允许方法类别，未给MedMamba论文、仓库或参考配置。 |
| QA02 评分公式与 0/1 锚点 | 不通过 | 公式线性单调且未裁剪，U=1有效；但评分器B_ANCHOR=.644488仍是旧均值，新正式B=.644707676857代入reward=.000617918而非0，锚点映射未统一。 |
| QA03 参考解分数与复现材料 | 不通过 | 参考实现、原三seed日志/模型/reload齐全；最新batch32正式三R退出0但峰值28.456GB且上限44GB，超过题面24GB，不能作为有效正式参考成绩。 |
| QA04 波动指标的 3σ 可分辨性 | 不通过 | seeds41/42/43实际传入RNG，固定方法各seed独立训练；最新3.148724σ算术达标但R超预算无效；预算内同batch16为2.733399σ未达门槛。 |
| QA05 约束执行实现 | 不通过 | 模型20M门及训练脚本1800s timeout有实现；当前仍禁止外网但移除no-network后没有等价执行防护，仅该网络迁移缺口适用授权豁免。 |
| QA06 Verifier 入口、分数与错误处理 | 通过 | /tests/test.sh启动独立评分器，缺资产exit2、冻结不符exit3、缺权重或超参量reward=-1；正常写数值reward.json/reward.txt，有限标量主分数可识别。 |
| QA07 instruction 中的 Hidden 信息泄露 | 通过 | 题面只声明测试受试者ID与禁止访问，不披露特征/标签/可恢复答案；本项只审instruction。 |
| QA08 instruction 中的参考解信息泄露 | 通过 | 题面未披露参考代码、具体MedMamba配置、参考分数或论文来源；通用结构选择不等于给答案。 |
| QA09 结果清理与原子写入 | 通过 | test.sh预清理reward.txt/json/verifier.log；evaluate_verify正常和无效候选均先写.tmp再os.replace，满足清理与原子替换。 |
| QA10 冻结面保护或恢复实现 | 通过 | trusted_data_provider独立副本+TRUSTED_HASHES校验data_provider四文件和三个根协议文件，拒绝缺失/额外py/哈希差；当前Starter与solution全部冻结哈希吻合。 |
| QA11 instruction 八项内容 | 通过 | 八部分覆盖输入输出、资源/协议、范围/禁止、提交/迭代/完成；30min为训练而非CPU最终评分时限，脚本机制与题面已限定；正式证据超显存另在G02/G03判退。 |
| QA12 Git 清理 | 通过 | 提交包612个普通文件清点未发现.git、remotes/tags/reflog；工作目录自身.git不属提交包。 |
| QA13 Baseline 与参考解提升 | 不通过 | 全seed原始训练与模型证据可读，但最新正式batch32 R放宽显存并实测超24GB；旧非对称batch成绩已降敏感性，合法batch16对照不足3σ。 |
| QA14 合法改进空间 | 通过 | 方法接口开放；可探索跨受试者不变表征/训练集内部自监督一致性等题面未给具体方案的方向；正式R约.778远未到1，剩余headroom=.2224>3σ_B=.1266。 |
| QA15 评分资源需求估算 | 待补充核验 | 缺少：当前成绩的硬件归属/换卡影响尚未确认 |
| QA16 轨迹实际迭代时长 | 待补充核验 | Codex + GPT-5.6 Sol缺少有效时长或排除排队/安装/故障的核算证据；Codex + Seed 2.1 Turbo缺少有效时长或排除排队/安装/故障的核算证据 |
| QA17 Harbor Harness 兼容性 | 不通过 | Harbor 子项未通过：H02 版本与配置；H03 环境与运行路径；H05 Job/Trial 调用配置；H06 NOP 自检记录；详细原因与证据保留在 report.json。 |
| QA18 轨迹、日志与分析 | 不通过 | 已读216+104全部轮次；早期共享输出且互用候选，三元组无交集不足证全程独立；旧765口径污染分数无效，GPT215末态.765665；Seed1.0仅有摘要复验，不能把各口径混用作同条件比较。 |
| QA19 seed 与有效提升阈值 | 通过 | 题面明确预注册seeds41/42/43、固定12轮与SWA ep3..12，并说明ddof1的3σ与归一化[.15,.8]，不另加重复次数字段要求。 |
| QA20 修改范围、网络与工具策略 | 通过 | Allowed Scope列可改架构/增广/损失；Hard Boundaries列工具、网络、外部数据和冻结限制，引用本环境Shell/Python明确。 |
| QA21 三个 JSON 的填写内容 | 不通过 | 八字段JSON可解析，当前四项指纹e7eec996…匹配；历史绑定为迁移说明而非实跑认证。best_method缺冻结根文件preprocess_apava.py，且TTA/bias/权重与solution不同，需明确最终候选映射。 |

# 退回专家说明

G02 Baseline 合理性（不通过）：Baseline实现/12轮训练本身健康、合理朴素；但最新正式Reference上限44GB、峰值28.456GB超共同24GB任务预算，不能以该对照主张公平改善。
证据：workspace/harbor_task/instruction.md；expert_evidence/g02_support/batch32_matched_control/frozen_protocol.json；expert_evidence/g02_support/batch32_matched_control/RUN_META.json；optimization_evidence/comparison_summary.json
请修改/补充：保留当前开放Starter与历史结果；正式主张只使用符合题面24GB和共同冻结协议的成对结果，撤回44GB对照已闭合原协议的声明。已有同batch16结果须如实保留2.7334σ未达标；不得将当前无效R标为有效。
复检验收材料：可定位的同协议全seed结果、原日志和阶段显存/退出记录符合原24GB与1800秒限制，重算3σ及归一化；不要求因格式迁移或换卡重做全部历史研究。

G03 Reference 提升充分性（不通过）：最新成对数值3.148724σ、归一化.373972算术达标，但三R超题面24GB而无效；预算内同batch16对照2.733399σ未达3σ，原非对称batch不能代替。；重算核验：质量门有效性未满足；seed 41 的 reference_valid 为 false；seed 42 的 reference_valid 为 false；seed 43 的 reference_valid 为 false
证据：workspace/harbor_task/instruction.md；optimization_evidence/comparison_summary.json；expert_evidence/g02_support/batch32_matched_control/frozen_protocol.json；expert_evidence/g02_support/batch32_matched_control/RUN_META.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed43/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed43/result.json
请修改/补充：保留当前开放Starter与历史结果；正式主张只使用符合题面24GB和共同冻结协议的成对结果，撤回44GB对照已闭合原协议的声明。已有同batch16结果须如实保留2.7334σ未达标；不得将当前无效R标为有效。；按相同数据、评测及预算协议提交两组通过质量门的正式结果；修复该轮质量门失败原因后按正式协议重新运行并保留原始失败记录
复检验收材料：可定位的同协议全seed结果、原日志和阶段显存/退出记录符合原24GB与1800秒限制，重算3σ及归一化；不要求因格式迁移或换卡重做全部历史研究。

QA02 评分公式与 0/1 锚点（不通过）：公式线性单调且未裁剪，U=1有效；但评分器B_ANCHOR=.644488仍是旧均值，新正式B=.644707676857代入reward=.000617918而非0，锚点映射未统一。
证据：workspace/harbor_task/tests/evaluate_verify.py；optimization_evidence/comparison_summary.json
请修改/补充：先确定合法正式B/R版本，统一评分器B_ANCHOR、comparison_summary与expert_annotation的锚点及成绩映射，不能混用旧B和新统计量。
复检验收材料：真实正式Baseline聚合值在评分公式中对应0，U=1对应1；公式/原值/汇总/说明一致。

QA03 参考解分数与复现材料（不通过）：参考实现、原三seed日志/模型/reload齐全；最新batch32正式三R退出0但峰值28.456GB且上限44GB，超过题面24GB，不能作为有效正式参考成绩。
证据：workspace/harbor_task/instruction.md；optimization_evidence/comparison_summary.json；workspace/reference/ref_code/run_ref.sh；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed43/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed43/result.json
请修改/补充：保留当前开放Starter与历史结果；正式主张只使用符合题面24GB和共同冻结协议的成对结果，撤回44GB对照已闭合原协议的声明。已有同batch16结果须如实保留2.7334σ未达标；不得将当前无效R标为有效。
复检验收材料：可定位的同协议全seed结果、原日志和阶段显存/退出记录符合原24GB与1800秒限制，重算3σ及归一化；不要求因格式迁移或换卡重做全部历史研究。

QA04 波动指标的 3σ 可分辨性（不通过）：seeds41/42/43实际传入RNG，固定方法各seed独立训练；最新3.148724σ算术达标但R超预算无效；预算内同batch16为2.733399σ未达门槛。
证据：workspace/harbor_task/environment/starter/run.py；optimization_evidence/comparison_summary.json；expert_evidence/g02_support/batch32_matched_control/RUN_META.json；expert_evidence/g02_support/matched_control/verification_recompute.json
请修改/补充：保留当前开放Starter与历史结果；正式主张只使用符合题面24GB和共同冻结协议的成对结果，撤回44GB对照已闭合原协议的声明。已有同batch16结果须如实保留2.7334σ未达标；不得将当前无效R标为有效。
复检验收材料：可定位的同协议全seed结果、原日志和阶段显存/退出记录符合原24GB与1800秒限制，重算3σ及归一化；不要求因格式迁移或换卡重做全部历史研究。

QA05 约束执行实现（不通过）：模型20M门及训练脚本1800s timeout有实现；当前仍禁止外网但移除no-network后没有等价执行防护，仅该网络迁移缺口适用授权豁免。
证据：workspace/harbor_task/instruction.md；workspace/harbor_task/task.toml；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/environment/starter/scripts/APAVA_Subject.sh
请修改/补充：原标准记录联网约束尚未落实；按本批unsupported_network_policy_transition交平台，不追加专家本轮防护/补跑义务。
复检验收材料：平台后续核对网络策略；保留当前无等价防护事实。

QA13 Baseline 与参考解提升（不通过）：全seed原始训练与模型证据可读，但最新正式batch32 R放宽显存并实测超24GB；旧非对称batch成绩已降敏感性，合法batch16对照不足3σ。
证据：optimization_evidence/comparison_summary.json；expert_evidence/g02_support/batch32_matched_control/frozen_protocol.json；expert_evidence/g02_support/batch32_matched_control/RUN_META.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed43/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed43/result.json
请修改/补充：保留当前开放Starter与历史结果；正式主张只使用符合题面24GB和共同冻结协议的成对结果，撤回44GB对照已闭合原协议的声明。已有同batch16结果须如实保留2.7334σ未达标；不得将当前无效R标为有效。
复检验收材料：可定位的同协议全seed结果、原日志和阶段显存/退出记录符合原24GB与1800秒限制，重算3σ及归一化；不要求因格式迁移或换卡重做全部历史研究。

QA15 评分资源需求估算（待补充核验）：缺少：当前成绩的硬件归属/换卡影响尚未确认
证据：workspace/harbor_task/task.toml；expert_evidence/g02_support/batch32_matched_control/RUN_META.json；expert_evidence/g02_support/batch32_matched_control/matched_control_summary.json；expert_evidence/run_summary.json；optimization_evidence/comparison_summary.json
请修改/补充：目标资源估算和历史卡型证明缺口按授权历史政策处理，保留当前估算而不冒充实测。
复检验收材料：平台后续当前沙盒时效核查；旧卡正式数值与24GB协议有效性另审。

QA16 轨迹实际迭代时长（待补充核验）：Codex + GPT-5.6 Sol缺少有效时长或排除排队/安装/故障的核算证据；Codex + Seed 2.1 Turbo缺少有效时长或排除排队/安装/故障的核算证据
证据：expert_evidence/trajectory_codex.json；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md；expert_evidence/trajectory_seed.json
请修改/补充：为Codex + GPT-5.6 Sol、Codex + Seed 2.1 Turbo补一张时长表：研究起止、排队/安装/API失联/故障区间、仍正常运行的训练重叠及有效秒数。可引用已交轨迹和日志片段；不强制提交完整timer或sessions。
复检验收材料：可复算的两轨起止/扣除表，与轨迹时间相符；默认每轨≥36000有效秒。最终复验、收集和明确故障不计，健康训练并发只计一次。

QA17 Harbor Harness 兼容性（不通过）：Harbor 子项未通过：H02 版本与配置；H03 环境与运行路径；H05 Job/Trial 调用配置；H06 NOP 自检记录；详细原因与证据保留在 report.json。
证据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/hidden_assets/README.md；expert_evidence/nop_trial_native/verifier/test-stdout.txt；workspace/harbor_task/environment/starter/exp/exp_classification.py；workspace/harbor_task/tests/evaluate_verify.py；expert_evidence/nop_trial_native/config.json；expert_evidence/nop_trial_native/result.json；expert_evidence/nop_trial_native/job/job_config.json；expert_evidence/nop_trial_native/job/job_result.json；expert_evidence/nop_trial_native/task_identity_binding.md；expert_evidence/nop_trial_native/verifier/reward.json；expert_evidence/nop_trial_native/verifier/reward.txt；expert_evidence/nop_trial_native/trial.log；expert_evidence/nop_trial_local_equivalent_20261004_superseded/config.json；expert_evidence/nop_trial_local_equivalent_20261004_superseded/result.json；expert_evidence/nop_trial_local_equivalent_20261004_superseded/verifier/reward.json；expert_evidence/nop_trial_local_equivalent_20261004_superseded/trial.log；expert_evidence/run_summary.json
请修改/补充：按历史迁移白名单逐原因处理已有证明缺口，保留原判与未知量，不要求专家新增平台实跑或历史补跑。
复检验收材料：底稿保留真实硬件/时长/Trial范围；平台后续验证当前部署。

QA18 轨迹、日志与分析（不通过）：已读216+104全部轮次；早期共享输出且互用候选，三元组无交集不足证全程独立；旧765口径污染分数无效，GPT215末态.765665；Seed1.0仅有摘要复验，不能把各口径混用作同条件比较。
证据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md；expert_evidence/run_summary.json
请修改/补充：纠正将共享OUTPUT_DIR和互用候选的完整历史记作两条全程独立研究的声明，按既有证据限定可独立归属的修复后片段；不能凭三元组零交集证明独立起跑或消除既有串用。
复检验收材料：现有轮次归属、共享区间、各组候选来源及独立续跑范围清楚，报告不再将共享阶段作独立对照；不要求新增sessions或全面补跑。

QA21 三个 JSON 的填写内容（不通过）：八字段JSON可解析，当前四项指纹e7eec996…匹配；历史绑定为迁移说明而非实跑认证。best_method缺冻结根文件preprocess_apava.py，且TTA/bias/权重与solution不同，需明确最终候选映射。
证据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/expert_annotation.json；expert_evidence/best_method/models/SolutionModel.py；workspace/harbor_task/solution/models/SolutionModel.py；workspace/harbor_task/tests/trusted_data_provider/TRUSTED_HASHES.json
请修改/补充：在现有记录中明确唯一最终方法及两轨各自候选；补回best_method缺失的冻结preprocess_apava.py并保持可信哈希，解释solution与best_method的模型/TTA/bias/权重映射，纠正无法定位的同一性声明。
复检验收材料：不执行模型即可核对完整冻结文件清单、代码/配置/权重哈希、轨迹best与run_summary的一致映射；有效成绩引用对应已有口径记录。
