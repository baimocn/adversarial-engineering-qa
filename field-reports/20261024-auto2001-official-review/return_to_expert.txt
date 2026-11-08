# 旧题完整质检与逐原因豁免

本轮结论：FAIL
阶段：standard_review_with_waivers
已完成全部内容审阅：是

原 v0.3.10 全部检查及完整内容审阅已完成，包括已有 NOP；仅按具体历史原因豁免。未执行题包代码或新增 Harbor Trial。
平台实跑：not_executed；未执行模型、题目程序、Docker 或 Harbor。

## 方法与正式对照

APAVA受试者级EEG二分类，输入(256,16)，输出2类logits；允许替换特征表示、序列建模、通道图、增广与损失等可执行方法。固定数据划分、种子和12轮SWA协议；并非固定框架内纯常量搜索。
可修改：models/SolutionModel.py中的架构/编码器/融合/图建模；run.py训练方法组件、增广、损失、正则；预算内结构配置与推理建模策略
冻结面：受试者train15/val4/test4、真实标签和评价口径；Adam lr1e-4、12 epochs、SWA ep3..12、协议seeds41/42/43；data_provider、preprocess_apava.py、evaluate.py、make_submission.py及tests评分器；单卡≤24GB、单次训练≤1800s、参数≤20M
指标与质量门：test argmax macro-F1 maximize；reward=(F1−B)/(1−B)，U=1；Δ≥3σ_B(ddof1)及归一化[.15,.8]，并须协议/质量有效。
Baseline：Starter=正式 BaselineFormer：三尺度 Conv1d[3,5,7]+d64/ff128/e2 Transformer，76529 参数；随机初始化，Adam1e-4，12轮无早停，SWA ep3..12；最新正式对照双方 batch32、1176 updates、37476 样本暴露。主评分 B 仍硬编码旧正式均值0.644488，最新正式B均值0.644707676857，二者未统一。
Reference：MedMamba d256/ff512/e4：原始/差分/频域三分支状态空间编码、门控融合与空间图Mamba，15955713 参数；同数据、seeds41/42/43、12轮SWA。历史batch16/2352更新；最新作为正式主张的batch32/1176更新，将显存上限24e9放宽到44e9，Reference三次峰值28456255488字节，违反题面24GB协议。
正式改善：最新batch32：B=0.644707676857，σ_B=0.042197857953，R=0.777577087752，Δ=0.132869410895=3.148724σ_B，Δ/(1−B)=0.373972085069；算术达标但三次R超题目显存预算，不是有效正式提升。历史非对称B@32/R@16：0.644488361634±0.042473252271 vs0.781203875269，3.218861σ；同batch16控制：B=0.649261330672，σ=.042971846000，R=.766720520604，2.733399σ，未达3σ。仪器化历史协议重跑3.199216σ仍为非对称batch。seed44/45仅开发敏感性，非正式五seed配对。 全部附加原值（按seed41/42/43）：historical_32_16 0.6051946724893178/0.7697259024835059,0.6387190370707312/0.7897113310241901,0.6895513753423668/0.7841743922985706；within_24GB_matched_16_16 0.6066176791433583/0.7861593985128246,0.6486122942127497/0.7935919225350538,0.692554018660992/0.7204102407641555；historical_protocol_instrumented_rerun_32_16 0.605780033316546/0.7820844856093527,0.6381183899585481/0.7738999715597448,0.6901751690383764/0.7867546638016436。
质量有效性：新正式R三次数据均可读取且退出0，但协议显存硬门失效（上限44GB、峰值28.456GB>24GB），reference_valid=false；不能用迁移豁免恢复有效性。未将历史Agent污染Dev分数用于作者正式B/R。 即使不采用全卡采样值，三次PyTorch allocator自身峰值均27,429,162,496字节，仍超过24GB及24GiB；并非仅凭全设备共享占用推定超预算。
已有原始对照：[{"seed": 41, "baseline": 0.605780033316546, "reference": 0.7865558004407934, "baseline_valid": true, "reference_valid": false}, {"seed": 42, "baseline": 0.6387916219119227, "reference": 0.775106082036775, "baseline_valid": true, "reference_valid": false}, {"seed": 43, "baseline": 0.6895513753423668, "reference": 0.7710693807777037, "baseline_valid": true, "reference_valid": false}]
依据：workspace/harbor_task/instruction.md；optimization_evidence/comparison_summary.json；expert_evidence/g02_support/batch32_matched_control/frozen_protocol.json；expert_evidence/g02_support/batch32_matched_control/RUN_META.json；expert_evidence/g02_support/batch32_matched_control/G02_G03_响应说明.md；workspace/harbor_task/tests/evaluate_verify.py；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed43/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed43/result.json

## 研究三门

### G01 方法级优化空间

观察判定：pass；本轮判定：pass
开放执行模型、损失/增广及图结构，Reference为真实多分支SSM/图模块替换；方法空间满足，非纯调参。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/environment/starter/models/BaselineFormer.py；workspace/reference/ref_code/models/MedMamba.py

### G02 Baseline 合理性

观察判定：fail；本轮判定：fail
Baseline实现/12轮训练本身健康、合理朴素；但最新正式Reference上限44GB、峰值28.456GB超共同24GB任务预算，不能以该对照主张公平改善。
审阅依据：workspace/harbor_task/instruction.md；expert_evidence/g02_support/batch32_matched_control/frozen_protocol.json；expert_evidence/g02_support/batch32_matched_control/RUN_META.json；optimization_evidence/comparison_summary.json
训练充分性：六次原B/R及新batch32六次均完整12轮；每epoch3123训练样本，总37476；原B98/R196步，新双方98步，SWA均ep3..12。B验证峰值多在2-3轮，后续回落，训练loss继续下降不构成被截短；早停计数只存best，不触发break。
  依据：workspace/harbor_task/environment/starter/exp/exp_classification.py；optimization_evidence/learning_curves.json；optimization_evidence/budget_ledger.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed41/train.stdout.log
方法代表性：Baseline为可运行常规多尺度Conv+Transformer朴素起点，76529参数；Reference较大是允许架构变量。包内没有证明更强常见同协议低成本锚点必须替换它，不以旧/小/分数差判弱。
  依据：workspace/harbor_task/environment/starter/models/BaselineFormer.py；workspace/harbor_task/instruction.md；workspace/reference/README.md
原协议预算可比性：最新双方batch32、1176更新、相同样本量与12轮，但Reference上限放宽44e9且峰值28.456e9>题面24GB；两侧在同44GB平台运行不等于满足共同24GB任务预算。旧batch32/16不对称已披露；batch16控制2.733σ。
  依据：workspace/harbor_task/instruction.md；expert_evidence/g02_support/batch32_matched_control/frozen_protocol.json；expert_evidence/g02_support/batch32_matched_control/RUN_META.json；optimization_evidence/comparison_summary.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed43/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed43/result.json
实现正确性：输入按受试者ID、CE/Adam/backward/step路径正常，当前正式B无零训练/标签错位/关键输入故障直接反证。原六组模型字节哈希与artifact一致且各seed不同，reload主指标吻合SWA；与早期Agent错误加载器不同，不能自动宣布正式B受污染。
  依据：workspace/harbor_task/environment/starter/models/BaselineFormer.py；workspace/harbor_task/environment/starter/exp/exp_classification.py；workspace/harbor_task/environment/starter/run.py；optimization_evidence/baseline_runs/seed_41/model/artifact.json；optimization_evidence/baseline_runs/seed_41/model/reload.log；expert_evidence/g02_support/current_data_alignment_audit.json
选择与对照完整性：正式seed41/42/43成对完整、同一候选架构按seed重训，所有三组与batch16未达3σ结果均披露。额外seed44/45敏感性非正式五seed配对。最新将超24GB对照选作正式主张无效，需纠正，但无证据认定挑最差B seed。
  依据：optimization_evidence/comparison_summary.json；expert_evidence/g02_support/batch32_matched_control/RUN_META.json；workspace/reference/README.md
- Baseline实现/12轮训练本身健康、合理朴素；但最新正式Reference上限44GB、峰值28.456GB超共同24GB任务预算，不能以该对照主张公平改善。；处理：unwaived
  依据：workspace/harbor_task/instruction.md；expert_evidence/g02_support/batch32_matched_control/frozen_protocol.json；expert_evidence/g02_support/batch32_matched_control/RUN_META.json；optimization_evidence/comparison_summary.json
  修改方向：保留当前开放Starter与历史结果；正式主张只使用符合题面24GB和共同冻结协议的成对结果，撤回44GB对照已闭合原协议的声明。已有同batch16结果须如实保留2.7334σ未达标；不得将当前无效R标为有效。
  验收：可定位的同协议全seed结果、原日志和阶段显存/退出记录符合原24GB与1800秒限制，重算3σ及归一化；不要求因格式迁移或换卡重做全部历史研究。

### G03 Reference 提升充分性

观察判定：fail；本轮判定：fail
最新成对数值3.148724σ、归一化.373972算术达标，但三R超题面24GB而无效；预算内同batch16对照2.733399σ未达3σ，原非对称batch不能代替。
审阅依据：workspace/harbor_task/instruction.md；optimization_evidence/comparison_summary.json；expert_evidence/g02_support/batch32_matched_control/frozen_protocol.json；expert_evidence/g02_support/batch32_matched_control/RUN_META.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed43/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed43/result.json
正式复算：{"baseline_mean": 0.6447076768569452, "reference_mean": 0.7775770877517574, "baseline_sample_std": 0.04219785795258044, "reference_sample_std": 0.008033473746016706, "improvement": 0.1328694108948122, "run_count": 3, "sigma_multiplier": 3.1487240666131275, "three_sigma_baseline": 0.12659357385774134, "normalized_score": 0.3739720850689861}
- 最新成对数值3.148724σ、归一化.373972算术达标，但三R超题面24GB而无效；预算内同batch16对照2.733399σ未达3σ，原非对称batch不能代替。；处理：unwaived
  依据：workspace/harbor_task/instruction.md；optimization_evidence/comparison_summary.json；expert_evidence/g02_support/batch32_matched_control/frozen_protocol.json；expert_evidence/g02_support/batch32_matched_control/RUN_META.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed43/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed43/result.json
  修改方向：保留当前开放Starter与历史结果；正式主张只使用符合题面24GB和共同冻结协议的成对结果，撤回44GB对照已闭合原协议的声明。已有同batch16结果须如实保留2.7334σ未达标；不得将当前无效R标为有效。
  验收：可定位的同协议全seed结果、原日志和阶段显存/退出记录符合原24GB与1800秒限制，重算3σ及归一化；不要求因格式迁移或换卡重做全部历史研究。
- 质量门有效性未满足；seed 41 的 reference_valid 为 false；seed 42 的 reference_valid 为 false；seed 43 的 reference_valid 为 false；处理：unwaived
  依据：workspace/harbor_task/instruction.md；optimization_evidence/comparison_summary.json；expert_evidence/g02_support/batch32_matched_control/frozen_protocol.json；expert_evidence/g02_support/batch32_matched_control/RUN_META.json；expert_evidence/g02_support/batch32_matched_control/G02_G03_响应说明.md；workspace/harbor_task/tests/evaluate_verify.py；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed43/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed43/result.json
  修改方向：核对已有正式 B/R 与评分定义，纠正实质数值、协议或质量有效性问题；迁移记录豁免不能证明科学门达标。
  验收：可信已有原始对照结果、相同协议与质量门依据及可重算的阈值计算。

## 21 项内容与实现

### QA01 八章节与题面信息泄露

观察判定：pass；本轮判定：pass
题面有八部分及补充提升判据；给通用SSM/图等允许方法类别，未给MedMamba论文、仓库或参考配置。
审阅依据：workspace/harbor_task/instruction.md

### QA02 评分公式与 0/1 锚点

观察判定：fail；本轮判定：fail
公式线性单调且未裁剪，U=1有效；但评分器B_ANCHOR=.644488仍是旧均值，新正式B=.644707676857代入reward=.000617918而非0，锚点映射未统一。
审阅依据：workspace/harbor_task/tests/evaluate_verify.py；optimization_evidence/comparison_summary.json
- 公式线性单调且未裁剪，U=1有效；但评分器B_ANCHOR=.644488仍是旧均值，新正式B=.644707676857代入reward=.000617918而非0，锚点映射未统一。；处理：unwaived
  依据：workspace/harbor_task/tests/evaluate_verify.py；optimization_evidence/comparison_summary.json
  修改方向：先确定合法正式B/R版本，统一评分器B_ANCHOR、comparison_summary与expert_annotation的锚点及成绩映射，不能混用旧B和新统计量。
  验收：真实正式Baseline聚合值在评分公式中对应0，U=1对应1；公式/原值/汇总/说明一致。

### QA03 参考解分数与复现材料

观察判定：fail；本轮判定：fail
参考实现、原三seed日志/模型/reload齐全；最新batch32正式三R退出0但峰值28.456GB且上限44GB，超过题面24GB，不能作为有效正式参考成绩。
审阅依据：workspace/harbor_task/instruction.md；optimization_evidence/comparison_summary.json；workspace/reference/ref_code/run_ref.sh；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed43/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed43/result.json
- 参考实现、原三seed日志/模型/reload齐全；最新batch32正式三R退出0但峰值28.456GB且上限44GB，超过题面24GB，不能作为有效正式参考成绩。；处理：unwaived
  依据：workspace/harbor_task/instruction.md；optimization_evidence/comparison_summary.json；workspace/reference/ref_code/run_ref.sh；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed43/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed43/result.json
  修改方向：保留当前开放Starter与历史结果；正式主张只使用符合题面24GB和共同冻结协议的成对结果，撤回44GB对照已闭合原协议的声明。已有同batch16结果须如实保留2.7334σ未达标；不得将当前无效R标为有效。
  验收：可定位的同协议全seed结果、原日志和阶段显存/退出记录符合原24GB与1800秒限制，重算3σ及归一化；不要求因格式迁移或换卡重做全部历史研究。

### QA04 波动指标的 3σ 可分辨性

观察判定：fail；本轮判定：fail
seeds41/42/43实际传入RNG，固定方法各seed独立训练；最新3.148724σ算术达标但R超预算无效；预算内同batch16为2.733399σ未达门槛。
审阅依据：workspace/harbor_task/environment/starter/run.py；optimization_evidence/comparison_summary.json；expert_evidence/g02_support/batch32_matched_control/RUN_META.json；expert_evidence/g02_support/matched_control/verification_recompute.json
- seeds41/42/43实际传入RNG，固定方法各seed独立训练；最新3.148724σ算术达标但R超预算无效；预算内同batch16为2.733399σ未达门槛。；处理：unwaived
  依据：workspace/harbor_task/environment/starter/run.py；optimization_evidence/comparison_summary.json；expert_evidence/g02_support/batch32_matched_control/RUN_META.json；expert_evidence/g02_support/matched_control/verification_recompute.json
  修改方向：保留当前开放Starter与历史结果；正式主张只使用符合题面24GB和共同冻结协议的成对结果，撤回44GB对照已闭合原协议的声明。已有同batch16结果须如实保留2.7334σ未达标；不得将当前无效R标为有效。
  验收：可定位的同协议全seed结果、原日志和阶段显存/退出记录符合原24GB与1800秒限制，重算3σ及归一化；不要求因格式迁移或换卡重做全部历史研究。

### QA05 约束执行实现

观察判定：fail；本轮判定：pass_with_waivers
模型20M门及训练脚本1800s timeout有实现；当前仍禁止外网但移除no-network后没有等价执行防护，仅该网络迁移缺口适用授权豁免。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/task.toml；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/environment/starter/scripts/APAVA_Subject.sh
- 模型20M门及训练脚本1800s timeout有实现；当前仍禁止外网但移除no-network后没有等价执行防护，仅该网络迁移缺口适用授权豁免。；处理：waived
  依据：workspace/harbor_task/instruction.md；workspace/harbor_task/task.toml；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/environment/starter/scripts/APAVA_Subject.sh
  豁免原因：unsupported_network_policy_transition；本轮用户指定0.3.10-standard-waiver.5授权边界：仅免该具体历史/平台证明差异，原事实、分数状态及当前静态缺陷均保留。

### QA06 Verifier 入口、分数与错误处理

观察判定：pass；本轮判定：pass
/tests/test.sh启动独立评分器，缺资产exit2、冻结不符exit3、缺权重或超参量reward=-1；正常写数值reward.json/reward.txt，有限标量主分数可识别。
审阅依据：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/task.toml

### QA07 instruction 中的 Hidden 信息泄露

观察判定：pass；本轮判定：pass
题面只声明测试受试者ID与禁止访问，不披露特征/标签/可恢复答案；本项只审instruction。
审阅依据：workspace/harbor_task/instruction.md

### QA08 instruction 中的参考解信息泄露

观察判定：pass；本轮判定：pass
题面未披露参考代码、具体MedMamba配置、参考分数或论文来源；通用结构选择不等于给答案。
审阅依据：workspace/harbor_task/instruction.md

### QA09 结果清理与原子写入

观察判定：pass；本轮判定：pass
test.sh预清理reward.txt/json/verifier.log；evaluate_verify正常和无效候选均先写.tmp再os.replace，满足清理与原子替换。
审阅依据：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/evaluate_verify.py

### QA10 冻结面保护或恢复实现

观察判定：pass；本轮判定：pass
trusted_data_provider独立副本+TRUSTED_HASHES校验data_provider四文件和三个根协议文件，拒绝缺失/额外py/哈希差；当前Starter与solution全部冻结哈希吻合。
审阅依据：workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/tests/trusted_data_provider/TRUSTED_HASHES.json；workspace/harbor_task/environment/starter/exp/exp_classification.py

### QA11 instruction 八项内容

观察判定：pass；本轮判定：pass
八部分覆盖输入输出、资源/协议、范围/禁止、提交/迭代/完成；30min为训练而非CPU最终评分时限，脚本机制与题面已限定；正式证据超显存另在G02/G03判退。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/task.toml；workspace/harbor_task/tests/evaluate_verify.py

### QA12 Git 清理

观察判定：pass；本轮判定：pass
提交包612个普通文件清点未发现.git、remotes/tags/reflog；工作目录自身.git不属提交包。
审阅依据：workspace/harbor_task/task.toml

### QA13 Baseline 与参考解提升

观察判定：fail；本轮判定：fail
全seed原始训练与模型证据可读，但最新正式batch32 R放宽显存并实测超24GB；旧非对称batch成绩已降敏感性，合法batch16对照不足3σ。
审阅依据：optimization_evidence/comparison_summary.json；expert_evidence/g02_support/batch32_matched_control/frozen_protocol.json；expert_evidence/g02_support/batch32_matched_control/RUN_META.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed43/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed43/result.json
- 全seed原始训练与模型证据可读，但最新正式batch32 R放宽显存并实测超24GB；旧非对称batch成绩已降敏感性，合法batch16对照不足3σ。；处理：unwaived
  依据：optimization_evidence/comparison_summary.json；expert_evidence/g02_support/batch32_matched_control/frozen_protocol.json；expert_evidence/g02_support/batch32_matched_control/RUN_META.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/baseline_seed43/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed41/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed42/result.json；expert_evidence/g02_support/batch32_matched_control/runs/reference_seed43/result.json
  修改方向：保留当前开放Starter与历史结果；正式主张只使用符合题面24GB和共同冻结协议的成对结果，撤回44GB对照已闭合原协议的声明。已有同batch16结果须如实保留2.7334σ未达标；不得将当前无效R标为有效。
  验收：可定位的同协议全seed结果、原日志和阶段显存/退出记录符合原24GB与1800秒限制，重算3σ及归一化；不要求因格式迁移或换卡重做全部历史研究。

### QA14 合法改进空间

观察判定：pass；本轮判定：pass
方法接口开放；可探索跨受试者不变表征/训练集内部自监督一致性等题面未给具体方案的方向；正式R约.778远未到1，剩余headroom=.2224>3σ_B=.1266。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/environment/starter/models/BaselineFormer.py；workspace/reference/ref_code/models/MedMamba.py；optimization_evidence/comparison_summary.json

### QA15 评分资源需求估算

观察判定：manual；本轮判定：pass_with_waivers
历史完整三seed训练/SWA/reload约2905s，估算目标≤5400s、1张H20/L20、16CPU（Verifier8CPU/0GPU）；历史5090/4090并非目标卡实测，迁移时效证明不足，单列豁免；24GB成绩违例不在此豁免。
审阅依据：workspace/harbor_task/task.toml；expert_evidence/g02_support/batch32_matched_control/RUN_META.json；expert_evidence/g02_support/batch32_matched_control/matched_control_summary.json；expert_evidence/run_summary.json
- 历史完整三seed训练/SWA/reload约2905s，估算目标≤5400s、1张H20/L20、16CPU（Verifier8CPU/0GPU）；历史5090/4090并非目标卡实测，迁移时效证明不足，单列豁免；24GB成绩违例不在此豁免。；处理：waived
  依据：workspace/harbor_task/task.toml；expert_evidence/g02_support/batch32_matched_control/RUN_META.json；expert_evidence/g02_support/batch32_matched_control/matched_control_summary.json；expert_evidence/run_summary.json
  豁免原因：legacy_hardware_record_difference；本轮用户指定0.3.10-standard-waiver.5授权边界：仅免该具体历史/平台证明差异，原事实、分数状态及当前静态缺陷均保留。
- 目标H20/L20与CPU评分时效未实测，完整单轮保守估算5400s，未冒充已运行。；处理：waived
  依据：workspace/harbor_task/task.toml；expert_evidence/g02_support/batch32_matched_control/RUN_META.json；expert_evidence/g02_support/batch32_matched_control/matched_control_summary.json；expert_evidence/run_summary.json
  豁免原因：legacy_target_resource_evidence_gap；本轮用户指定0.3.10-standard-waiver.5授权边界：仅免该具体历史/平台证明差异，原事实、分数状态及当前静态缺陷均保留。

### QA16 轨迹实际迭代时长

观察判定：manual；本轮判定：pass_with_waivers
两轨声明有效13.96h/10.58h且称扣除中转故障约2h，材料无完整起止/扣除台账；不从时间戳跨度或轮数推算有效秒数。涉及训练，不适用7h例外。
审阅依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md
- 两轨声明有效13.96h/10.58h且称扣除中转故障约2h，材料无完整起止/扣除台账；不从时间戳跨度或轮数推算有效秒数。涉及训练，不适用7h例外。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md
  豁免原因：legacy_research_duration_gap；本轮用户指定0.3.10-standard-waiver.5授权边界：仅免该具体历史/平台证明差异，原事实、分数状态及当前静态缺陷均保留。

### QA17 Harbor Harness 兼容性

观察判定：manual；本轮判定：fail
按H01-H06逐项派生：当前路径/Dev/Hidden注入/reward/artifacts已审；网络迁移、目标镜像与当前Trial运行证明缺口分别在H02/H03/H05/H06处理，非整项豁免。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；expert_evidence/run_summary.json
Harbor逐项派生：H01=pass；H02=pass_with_waivers；H03=pass_with_waivers；H04=fail；H05=pass_with_waivers；H06=pass_with_waivers

### QA18 轨迹、日志与分析

观察判定：fail；本轮判定：fail
已读216+104全部轮次；早期共享输出且互用候选，三元组无交集不足证全程独立；旧765口径污染分数无效，GPT215末态.765665；Seed1.0仅有摘要复验，不能把各口径混用作同条件比较。
审阅依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md；expert_evidence/run_summary.json
- 已读216+104全部轮次；早期共享输出且互用候选，三元组无交集不足证全程独立；旧765口径污染分数无效，GPT215末态.765665；Seed1.0仅有摘要复验，不能把各口径混用作同条件比较。；处理：unwaived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md；expert_evidence/run_summary.json
  修改方向：纠正将共享OUTPUT_DIR和互用候选的完整历史记作两条全程独立研究的声明，按既有证据限定可独立归属的修复后片段；不能凭三元组零交集证明独立起跑或消除既有串用。
  验收：现有轮次归属、共享区间、各组候选来源及独立续跑范围清楚，报告不再将共享阶段作独立对照；不要求新增sessions或全面补跑。
- 旧加载器造成公开验证受试者泄漏，污染旧765分数保持invalid；未将这些Agent分数当作者正式B/R；不新增追责补跑义务。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md
  豁免原因：historical_agent_runtime_finding；本轮用户指定0.3.10-standard-waiver.5授权边界：仅免该具体历史/平台证明差异，原事实、分数状态及当前静态缺陷均保留。
  原分数状态：invalid
  历史事实：leakage/confirmed；分数影响：invalid
  影响依据：GPT210明确宣告旧1.0作废；当前正式B/R为独立全量数据原记录/新匹配控制，不采用Agent Dev1.0作正证。
  受污染或未证实的Agent分数不作为作者正式 B/R 正证；仅部署规则差异不自动改写分数。
- 实际模型runtime有run_summary/专家说明交叉支持，但最高推理档位与空输出启动证明未留存。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md
  豁免原因：legacy_runtime_proof_gap；本轮用户指定0.3.10-standard-waiver.5授权边界：仅免该具体历史/平台证明差异，原事实、分数状态及当前静态缺陷均保留。
- 已实际对比现有两轨材料，旧版材料仍不足以证明所有历史条件一致；仅此记录缺口豁免，不声称已证实同条件。逐维审两轨与专家§6。两组同属APAVA方法研究；模型不同允许。两组历史均历经765→1413修复，现有材料没有确认作者给两组不同Prompt/反馈/IPC权限的事实，不能把各Agent实际不同代码/成绩误判为出题条件差异。原始启动Prompt/最高档和完整历史任务快照未提供，故同条件只能记unverified；早期共享OUTPUT_DIR是已证实独立性问题，另在QA18保留失败，不能被该证明缺口豁免。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md；expert_evidence/run_summary.json；workspace/harbor_task/instruction.md
  豁免原因：legacy_runtime_proof_gap；本轮旧题迁移不要求新增Prompt快照、hash或重跑；已读资料中没有已确认的实质条件差异。

### QA19 seed 与有效提升阈值

观察判定：pass；本轮判定：pass
题面明确预注册seeds41/42/43、固定12轮与SWA ep3..12，并说明ddof1的3σ与归一化[.15,.8]，不另加重复次数字段要求。
审阅依据：workspace/harbor_task/instruction.md

### QA20 修改范围、网络与工具策略

观察判定：pass；本轮判定：pass
Allowed Scope列可改架构/增广/损失；Hard Boundaries列工具、网络、外部数据和冻结限制，引用本环境Shell/Python明确。
审阅依据：workspace/harbor_task/instruction.md

### QA21 三个 JSON 的填写内容

观察判定：fail；本轮判定：fail
八字段JSON可解析，当前四项指纹e7eec996…匹配；历史绑定为迁移说明而非实跑认证。best_method缺冻结根文件preprocess_apava.py，且TTA/bias/权重与solution不同，需明确最终候选映射。
审阅依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/expert_annotation.json；expert_evidence/best_method/models/SolutionModel.py；workspace/harbor_task/solution/models/SolutionModel.py；workspace/harbor_task/tests/trusted_data_provider/TRUSTED_HASHES.json
- 八字段JSON可解析，当前四项指纹e7eec996…匹配；历史绑定为迁移说明而非实跑认证。best_method缺冻结根文件preprocess_apava.py，且TTA/bias/权重与solution不同，需明确最终候选映射。；处理：unwaived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/expert_annotation.json；expert_evidence/best_method/models/SolutionModel.py；workspace/harbor_task/solution/models/SolutionModel.py；workspace/harbor_task/tests/trusted_data_provider/TRUSTED_HASHES.json
  修改方向：在现有记录中明确唯一最终方法及两轨各自候选；补回best_method缺失的冻结preprocess_apava.py并保持可信哈希，解释solution与best_method的模型/TTA/bias/权重映射，纠正无法定位的同一性声明。
  验收：不执行模型即可核对完整冻结文件清单、代码/配置/权重哈希、轨迹best与run_summary的一致映射；有效成绩引用对应已有口径记录。
- run_summary四项hash与当前包一致，但实际为2026-10-21/22/23迁移后指纹，不能追溯认证历史运行所用版本。；处理：waived
  依据：expert_evidence/run_summary.json；workspace/harbor_task/task.toml
  豁免原因：legacy_task_binding_migration；本轮用户指定0.3.10-standard-waiver.5授权边界：仅免该具体历史/平台证明差异，原事实、分数状态及当前静态缺陷均保留。

## Harbor 六项

### H01 任务目录

观察判定：pass；本轮判定：pass
task根明确；公开19受试者随Agent提供，私有TEST由独立Verifier注入；读取README及已有NOP test-stdout的test ids验证调用关系，非凭空目录通过。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/hidden_assets/README.md；expert_evidence/nop_trial_native/verifier/test-stdout.txt

### H02 版本与配置

观察判定：fail；本轮判定：pass_with_waivers
TOML语法可解析、显式separate、资源表H20/L20与CPU侧0GPU；禁网字段已删但题面仍禁止外网，缺等价执行策略，仅该迁移缺口待平台落实。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md
- TOML语法可解析、显式separate、资源表H20/L20与CPU侧0GPU；禁网字段已删但题面仍禁止外网，缺等价执行策略，仅该迁移缺口待平台落实。；处理：waived
  依据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md
  豁免原因：unsupported_network_policy_transition；本轮用户指定0.3.10-standard-waiver.5授权边界：仅免该具体历史/平台证明差异，原事实、分数状态及当前静态缺陷均保留。

### H03 环境与运行路径

观察判定：manual；本轮判定：pass_with_waivers
Agent context=environment、Verifier=tests，COPY/入口/依赖/artifacts可定位，运行只本沙盒本地训练/评分，无题目另部署环境；内场镜像准备及启动/权限实际验证待平台。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/environment/starter/exp/exp_classification.py
- Agent context=environment、Verifier=tests，COPY/入口/依赖/artifacts可定位，运行只本沙盒本地训练/评分，无题目另部署环境；内场镜像准备及启动/权限实际验证待平台。；处理：waived
  依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/environment/starter/exp/exp_classification.py
  豁免原因：platform_image_preparation_pending；本轮用户指定0.3.10-standard-waiver.5授权边界：仅免该具体历史/平台证明差异，原事实、分数状态及当前静态缺陷均保留。
- 实际镜像启动/权限/GPU/移交未在当前平台运行验证。；处理：waived
  依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/environment/starter/exp/exp_classification.py
  豁免原因：platform_execution_verification_pending；本轮用户指定0.3.10-standard-waiver.5授权边界：仅免该具体历史/平台证明差异，原事实、分数状态及当前静态缺陷均保留。

### H04 测试入口与 reward

观察判定：pass；本轮判定：fail
独立/tests/test.sh读取/workspace/solution，test隐藏资产缺失fail-closed，写/logs/verifier/reward.json并提取reward.txt；使用自身requirements与可信加载器。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/tests/Dockerfile
- 当前格式实质问题（来自 F07）：当前评分器仍用旧B=.644488，新正式汇总B=.644707676857，主分数锚点与正式来源有确定静态冲突；并非历史换卡验证缺口。
  定位：workspace/harbor_task/tests/evaluate_verify.py；optimization_evidence/comparison_summary.json

### H05 Job/Trial 调用配置

观察判定：manual；本轮判定：pass_with_waivers
已有Harbor0.24.0本地docker NOP Job/Trial/config已审；运行任务harbor_task映射本题，separate与artifacts记录一致；当前MASO镜像tag、权限及覆盖配置尚由平台验证。
审阅依据：workspace/harbor_task/task.toml；expert_evidence/nop_trial_native/config.json；expert_evidence/nop_trial_native/result.json；expert_evidence/nop_trial_native/job/job_config.json；expert_evidence/nop_trial_native/job/job_result.json；expert_evidence/nop_trial_native/task_identity_binding.md
- 已有Harbor0.24.0本地docker NOP Job/Trial/config已审；运行任务harbor_task映射本题，separate与artifacts记录一致；当前MASO镜像tag、权限及覆盖配置尚由平台验证。；处理：waived
  依据：workspace/harbor_task/task.toml；expert_evidence/nop_trial_native/config.json；expert_evidence/nop_trial_native/result.json；expert_evidence/nop_trial_native/job/job_config.json；expert_evidence/nop_trial_native/job/job_result.json；expert_evidence/nop_trial_native/task_identity_binding.md
  豁免原因：platform_execution_verification_pending；本轮用户指定0.3.10-standard-waiver.5授权边界：仅免该具体历史/平台证明差异，原事实、分数状态及当前静态缺陷均保留。

### H06 NOP 自检记录

观察判定：manual；本轮判定：pass_with_waivers
已有原生及退役本地NOP均agent=nop、separate、正常结束、reward.json优先且与result一致(-1,-1,0)、日志非空；只覆盖缺权重分支。其旧TOML版本与当前迁移包不同，当前Trial未跑。
审阅依据：expert_evidence/nop_trial_native/config.json；expert_evidence/nop_trial_native/result.json；expert_evidence/nop_trial_native/verifier/reward.json；expert_evidence/nop_trial_native/verifier/reward.txt；expert_evidence/nop_trial_native/trial.log；expert_evidence/nop_trial_native/verifier/test-stdout.txt；expert_evidence/nop_trial_native/task_identity_binding.md；expert_evidence/nop_trial_local_equivalent_20261004_superseded/config.json；expert_evidence/nop_trial_local_equivalent_20261004_superseded/result.json；expert_evidence/nop_trial_local_equivalent_20261004_superseded/verifier/reward.json；expert_evidence/nop_trial_local_equivalent_20261004_superseded/trial.log；workspace/harbor_task/task.toml；expert_evidence/run_summary.json
- 已有原生及退役本地NOP均agent=nop、separate、正常结束、reward.json优先且与result一致(-1,-1,0)、日志非空；只覆盖缺权重分支。其旧TOML版本与当前迁移包不同，当前Trial未跑。；处理：waived
  依据：expert_evidence/nop_trial_native/config.json；expert_evidence/nop_trial_native/result.json；expert_evidence/nop_trial_native/verifier/reward.json；expert_evidence/nop_trial_native/verifier/reward.txt；expert_evidence/nop_trial_native/trial.log；expert_evidence/nop_trial_native/verifier/test-stdout.txt；expert_evidence/nop_trial_native/task_identity_binding.md；expert_evidence/nop_trial_local_equivalent_20261004_superseded/config.json；expert_evidence/nop_trial_local_equivalent_20261004_superseded/result.json；expert_evidence/nop_trial_local_equivalent_20261004_superseded/verifier/reward.json；expert_evidence/nop_trial_local_equivalent_20261004_superseded/trial.log；workspace/harbor_task/task.toml；expert_evidence/run_summary.json
  豁免原因：legacy_nop_or_current_trial_gap；本轮用户指定0.3.10-standard-waiver.5授权边界：仅免该具体历史/平台证明差异，原事实、分数状态及当前静态缺陷均保留。

## 两轨已有内容

### T01 第一条轨迹已有内容

观察判定：manual；本轮判定：pass_with_waivers
GPT在canonical加载器上第211轮重建Baseline，第212-215轮宽核Mamba+dropout/WD+等权正反TTA，最终保留Dev=.7656649504010966；第216轮label smoothing未提升。此前1.0明确由第210轮作废。
审阅依据：expert_evidence/trajectory_codex.json；expert_evidence/专家作业说明文档.md；expert_evidence/run_summary.json；expert_evidence/best_method/models/SolutionModel.py；workspace/harbor_task/solution/models/SolutionModel.py
方法：Baseline Transformer→频带分支/池化/PE/CAR→SSM/Mamba→正则/增强/TTA/集成→canonical加载器修复，最终宽核Mamba。
迭代内容：全216轮，1-195含旧口径/共享区；196-209合规误判，210确认污染，211-216在canonical1413口径重建。失败含配置/权重竞态、路径、缺依赖、TEST意外可读以及辅助工具缺失。
最终结果：GPT在canonical加载器上第211轮重建Baseline，第212-215轮宽核Mamba+dropout/WD+等权正反TTA，最终保留Dev=.7656649504010966；第216轮label smoothing未提升。此前1.0明确由第210轮作废。
分数采用范围：旧765污染分数invalid，不能作清洁研究或正式B/R正证；GPT末态canonical .765665有既有记录支持；Seed1.0为summary中的Dev复验声明，当前完整冻结契约不通过，不能写成Hidden有效1.0。
已读来源：expert_evidence/trajectory_codex.json；expert_evidence/专家作业说明文档.md；expert_evidence/run_summary.json；expert_evidence/best_method/models/SolutionModel.py；workspace/harbor_task/solution/models/SolutionModel.py
- 早期共享工作区的错误加载器导致Dev污染，旧分数invalid保留；正式B/R未采用Agent污染分数。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md
  豁免原因：historical_agent_runtime_finding；本轮用户指定0.3.10-standard-waiver.5授权边界：仅免该具体历史/平台证明差异，原事实、分数状态及当前静态缺陷均保留。
  原分数状态：invalid
  历史事实：leakage/confirmed；分数影响：invalid
  影响依据：GPT210明确invalid，专家§6披露共享与Dev口径修复，不能用旧1.0作正证；最新正式R无效另因24GB硬门。
  受污染或未证实的Agent分数不作为作者正式 B/R 正证；仅部署规则差异不自动改写分数。
- 声明13.96/10.58h，有效时间台账未随包留存；不补造秒数。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md
  豁免原因：legacy_research_duration_gap；本轮用户指定0.3.10-standard-waiver.5授权边界：仅免该具体历史/平台证明差异，原事实、分数状态及当前静态缺陷均保留。
- 最高推理档/独立空输出启动旧证明不足；仅豁免证明欠缺，实际共享历史另在QA18保留。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md
  豁免原因：legacy_runtime_proof_gap；本轮用户指定0.3.10-standard-waiver.5授权边界：仅免该具体历史/平台证明差异，原事实、分数状态及当前静态缺陷均保留。

### T02 第二条轨迹已有内容

观察判定：fail；本轮判定：fail
Seed第89轮纯反向Mamba+bias1.65记录1.0，第94-104轮新尝试均低于1.0；summary声明13:52干净Dev n1413复验1.0。best_method记录该Seed权重，但缺当前冻结根文件preprocess_apava.py，不能直接作为当前有效提交；旧765与新1413口径不得合并排名。
审阅依据：expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md；expert_evidence/run_summary.json；expert_evidence/best_method/models/SolutionModel.py；workspace/harbor_task/solution/models/SolutionModel.py
方法：Transformer加深/加宽→Mamba/多seed池→多种参数/概率集成、频域/差分/SE/增广→宽核纯反向TTA+bias；新变体未胜1.0。
迭代内容：全104轮，1-65含转写和共享历史；49/50/51为7/5/7epoch部分SWA，不符合完整12epoch，未保留best；89轮1.0，94-104继续探索、最终104 cosine=.748217。
最终结果：Seed第89轮纯反向Mamba+bias1.65记录1.0，第94-104轮新尝试均低于1.0；summary声明13:52干净Dev n1413复验1.0。best_method记录该Seed权重，但缺当前冻结根文件preprocess_apava.py，不能直接作为当前有效提交；旧765与新1413口径不得合并排名。
分数采用范围：旧765污染分数invalid，不能作清洁研究或正式B/R正证；GPT末态canonical .765665有既有记录支持；Seed1.0为summary中的Dev复验声明，当前完整冻结契约不通过，不能写成Hidden有效1.0。
已读来源：expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md；expert_evidence/run_summary.json；expert_evidence/best_method/models/SolutionModel.py；workspace/harbor_task/solution/models/SolutionModel.py
- 早期共享工作区的错误加载器导致Dev污染，旧分数invalid保留；正式B/R未采用Agent污染分数。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md
  豁免原因：historical_agent_runtime_finding；本轮用户指定0.3.10-standard-waiver.5授权边界：仅免该具体历史/平台证明差异，原事实、分数状态及当前静态缺陷均保留。
  原分数状态：invalid
  历史事实：leakage/confirmed；分数影响：invalid
  影响依据：GPT210明确invalid，专家§6披露共享与Dev口径修复，不能用旧1.0作正证；最新正式R无效另因24GB硬门。
  受污染或未证实的Agent分数不作为作者正式 B/R 正证；仅部署规则差异不自动改写分数。
- 声明13.96/10.58h，有效时间台账未随包留存；不补造秒数。；处理：waived
  依据：expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md
  豁免原因：legacy_research_duration_gap；本轮用户指定0.3.10-standard-waiver.5授权边界：仅免该具体历史/平台证明差异，原事实、分数状态及当前静态缺陷均保留。
- 最高推理档/独立空输出启动旧证明不足；仅豁免证明欠缺，实际共享历史另在QA18保留。；处理：waived
  依据：expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md
  豁免原因：legacy_runtime_proof_gap；本轮用户指定0.3.10-standard-waiver.5授权边界：仅免该具体历史/平台证明差异，原事实、分数状态及当前静态缺陷均保留。
- Seed best_method缺当前冻结根文件preprocess_apava.py，且与solution推理/TTA/bias/权重不同，不能以旧Dev摘要宣称当前完整提交复验通过。；处理：unwaived
  依据：expert_evidence/best_method/models/SolutionModel.py；workspace/harbor_task/solution/models/SolutionModel.py；workspace/harbor_task/tests/evaluate_verify.py；expert_evidence/run_summary.json
  修改方向：在现有记录中明确唯一最终方法及两轨各自候选；补回best_method缺失的冻结preprocess_apava.py并保持可信哈希，解释solution与best_method的模型/TTA/bias/权重映射，纠正无法定位的同一性声明。
  验收：不执行模型即可核对完整冻结文件清单、代码/配置/权重哈希、轨迹best与run_summary的一致映射；有效成绩引用对应已有口径记录。

## 两轨实际条件对比

对比已完成：是
条件判断：historical_evidence_gap；成对对照有效性：unverified
逐维审两轨与专家§6。两组同属APAVA方法研究；模型不同允许。两组历史均历经765→1413修复，现有材料没有确认作者给两组不同Prompt/反馈/IPC权限的事实，不能把各Agent实际不同代码/成绩误判为出题条件差异。原始启动Prompt/最高档和完整历史任务快照未提供，故同条件只能记unverified；早期共享OUTPUT_DIR是已证实独立性问题，另在QA18保留失败，不能被该证明缺口豁免。
已对比维度：prompt、task、dev、feedback、constraints、resources
对比依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md；expert_evidence/run_summary.json；workspace/harbor_task/instruction.md
质检员内部对比底稿；不要求专家新增字段、Prompt快照、hash或重跑。语义判断须实际阅读原材料，脚本只核验审阅覆盖及判定一致性。

## 当前格式前检 F01–F07（子检查）

format_decision：FAIL
以下仅为当前格式子检查；整题结论以本报告顶部完整质检结果为准。

- F01 [pass] 当前必需目录、文件与 TOML 接口：当前三目录/TOML结构有效，显式separate和artifacts；未依赖旧resources。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md
- F02 [pass] 有效构建或镜像方案、构建上下文及 COPY 来源：Agent和Verifier采用各自Dockerfile/context；COPY来源存在，模型/数据仅当前沙盒本地运行。
  格式审阅依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/environment/starter/exp/exp_classification.py
- F03 [pass] 评分入口、独立依赖声明与固定输出路径：test.sh及独立requirements/可信数据管线完整，固定/logs/verifier输出。
  格式审阅依据：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/tests/requirements.txt
- F04 [pass] 提交物 artifacts 移交契约：artifacts源/workspace/solution与评分读取绝对路径一致。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/test.sh
- F05 [pass] 公开 Dev、私有 Hidden 供给与 Agent 隔离：公开Dev评价与19受试者在Agent；私有TEST经已有注入契约及NOP日志支持，fail-closed，不把空README当实际数据。
  格式审阅依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；expert_evidence/nop_trial_native/verifier/test-stdout.txt
- F06 [pass] separate、单容器、无 Compose 与当前目标资源配置：当前H20/L20、Verifier0GPU、separate无Compose/未支持资源字段；网络防护迁移缺口独立按H02白名单处理。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile
- F07 [fail] 当前评分实现与冻结面无确证故障或作者泄漏造假：当前评分器仍用旧B=.644488，新正式汇总B=.644707676857，主分数锚点与正式来源有确定静态冲突；并非历史换卡验证缺口。
  格式审阅依据：workspace/harbor_task/tests/evaluate_verify.py；optimization_evidence/comparison_summary.json
  修改方向：统一合法正式Baseline及评分器锚点，修正混用旧/新成绩的汇总。
  验收：正式B代入reward为0，U=1为1，题面/公式/正式汇总一致。

## 平台后续事项（不阻断本轮已有材料审阅）

- 字节内部准备、构建或导入镜像并配置实际 ICM tag；本轮不要求专家补内部镜像运行记录。
- 平台实际构建和启动，核对依赖、基础镜像 digest 及 bash/解释器；静态推断不能冒充运行结果。
- 平台核对 root、seccomp、网络及实际分配的沙盒权限设置。
- 平台后续执行当前版本 Harbor Trial/NOP、独立 Verifier 和 reward 收集；其缺口不作为本轮专家返修门槛。
- 已有原硬件结果本轮复核；不把旧值改称新硬件实测，不要求新环境补跑；平台核对实际当前提交物移交及目标硬件运行。
- 移除不支持的禁网字段后，新的联网或外部查表防护尚未落实，列为平台迁移事项，不要求本批专家新增防护实现或补跑；当前确证 Hidden 暴露或假 reward 仍属当前核心缺陷。

## 原 v0.3.10 自动检查及 NOP 原判

已调用原标准审计入口：True
NOP：{"status": "manual", "runtime_status": "unverified", "trials": [{"trial_dir": "expert_evidence/nop_trial_local_equivalent_20261004_superseded", "evidence": ["expert_evidence/nop_trial_local_equivalent_20261004_superseded/config.json", "expert_evidence/nop_trial_local_equivalent_20261004_superseded/result.json", "expert_evidence/nop_trial_local_equivalent_20261004_superseded/verifier/reward.json", "expert_evidence/nop_trial_local_equivalent_20261004_superseded/verifier/reward.txt", "expert_evidence/nop_trial_local_equivalent_20261004_superseded/trial.log", "expert_evidence/nop_trial_local_equivalent_20261004_superseded/verifier/test-stdout.txt"], "status": "manual", "summary": "Harbor Trial task.toml hash disagrees with the inspected task", "protected": false}, {"trial_dir": "expert_evidence/nop_trial_native", "evidence": ["expert_evidence/nop_trial_native/config.json", "expert_evidence/nop_trial_native/result.json", "expert_evidence/nop_trial_native/verifier/reward.json", "expert_evidence/nop_trial_native/verifier/reward.txt", "expert_evidence/nop_trial_native/trial.log", "expert_evidence/nop_trial_native/verifier/test-stdout.txt"], "details": {"trial_dir": "expert_evidence/nop_trial_native", "agent": "nop", "verifier_environment_mode": "separate", "rewards": {"macro_f1": -1.0, "reward": -1.0, "n_test": 0}, "task_binding": {"status": "pass", "basis": "reviewed_evidence", "evidence": ["expert_evidence/nop_trial_native/task_identity_binding.md", "expert_evidence/run_summary.json", "workspace/harbor_task/task.toml"], "summary": "历史Harbor任务auto2001/apava-eeg-ad-structure-optimization对应当前workspace/harbor_task；仅同题身份映射，旧07015ce3/6486f364 TOML与当前不同，不能据此声明当前版本NOP成功。", "authenticity_verified": false}}, "status": "pass", "summary": "已有 NOP 的同次 Trial、Agent、separate、sandbox 反证、结束与异常、reward 数值和非空日志已按原校验器核查。"}], "summary": "逐份读取并校验已有 NOP 记录；未启动新的 Trial。"}

原报告与全部详细结果：standard/report.json；不因豁免覆盖原判。

| 来源 | 项目 | 原判 | 本轮处理 | 依据及原因 |
|---|---|---|---|---|
| gates/G02 | G02 | fail | fail | Baseline实现/12轮训练本身健康、合理朴素；但最新正式Reference上限44GB、峰值28.456GB超共同24GB任务预算，不能以该对照主张公平改善。 |
| gates/G03 | G03 | fail | fail | 最新成对数值3.148724σ、归一化.373972算术达标，但三R超题面24GB而无效；预算内同batch16对照2.733399σ未达3σ，原非对称batch不能代替。；重算核验：质量门有效性未满足；seed 41 的 reference_valid 为 false；seed 42 的 reference_valid 为 false；seed 43 的 reference_valid 为 false |
| checks/QA02 | QA02 | fail | fail | 公式线性单调且未裁剪，U=1有效；但评分器B_ANCHOR=.644488仍是旧均值，新正式B=.644707676857代入reward=.000617918而非0，锚点映射未统一。 |
| checks/QA03 | QA03 | fail | fail | 参考实现、原三seed日志/模型/reload齐全；最新batch32正式三R退出0但峰值28.456GB且上限44GB，超过题面24GB，不能作为有效正式参考成绩。 |
| checks/QA04 | QA04 | fail | fail | seeds41/42/43实际传入RNG，固定方法各seed独立训练；最新3.148724σ算术达标但R超预算无效；预算内同batch16为2.733399σ未达门槛。 |
| checks/QA05 | QA05 | fail | pass_with_waivers | 模型20M门及训练脚本1800s timeout有实现；当前仍禁止外网但移除no-network后没有等价执行防护，仅该网络迁移缺口适用授权豁免。 |
| checks/QA13 | QA13 | fail | fail | 全seed原始训练与模型证据可读，但最新正式batch32 R放宽显存并实测超24GB；旧非对称batch成绩已降敏感性，合法batch16对照不足3σ。 |
| checks/QA15 | QA15 | manual | pass_with_waivers | 缺少：当前成绩的硬件归属/换卡影响尚未确认 |
| checks/QA16 | QA16 | manual | pass_with_waivers | Codex + GPT-5.6 Sol缺少有效时长或排除排队/安装/故障的核算证据；Codex + Seed 2.1 Turbo缺少有效时长或排除排队/安装/故障的核算证据 |
| checks/QA17 | QA17 | fail | derived_from_details | Harbor 子项未通过：H02 版本与配置；H03 环境与运行路径；H05 Job/Trial 调用配置；H06 NOP 自检记录；详细原因与证据保留在 report.json。 |
| checks/QA18 | QA18 | fail | fail | 已读216+104全部轮次；早期共享输出且互用候选，三元组无交集不足证全程独立；旧765口径污染分数无效，GPT215末态.765665；Seed1.0仅有摘要复验，不能把各口径混用作同条件比较。 |
| checks/QA21 | QA21 | fail | fail | 八字段JSON可解析，当前四项指纹e7eec996…匹配；历史绑定为迁移说明而非实跑认证。best_method缺冻结根文件preprocess_apava.py，且TTA/bias/权重与solution不同，需明确最终候选映射。 |
| harbor/H02 | H02 | fail | pass_with_waivers | TOML语法可解析、显式separate、资源表H20/L20与CPU侧0GPU；禁网字段已删但题面仍禁止外网，缺等价执行策略，仅该迁移缺口待平台落实。；GPU声明目标H20/L20，Verifier CPU0GPU，无storage_mb/Compose；当前禁网声明已删而题面仍禁网络，等价机制未落实，按本批网络迁移政策豁免。 |
| harbor/H03 | H03 | manual | pass_with_waivers | Agent context=environment、Verifier=tests，COPY/入口/依赖/artifacts可定位，运行只本沙盒本地训练/评分，无题目另部署环境；内场镜像准备及启动/权限实际验证待平台。 |
| harbor/H05 | H05 | manual | pass_with_waivers | 已有Harbor0.24.0本地docker NOP Job/Trial/config已审；运行任务harbor_task映射本题，separate与artifacts记录一致；当前MASO镜像tag、权限及覆盖配置尚由平台验证。 |
| harbor/H06 | H06 | manual | derived_from_details | 已有原生及退役本地NOP均agent=nop、separate、正常结束、reward.json优先且与result一致(-1,-1,0)、日志非空；只覆盖缺权重分支。其旧TOML版本与当前迁移包不同，当前Trial未跑。 |
| harbor/deployment_contract/0 | H02 | fail | pass_with_waivers | GPU声明目标H20/L20，Verifier CPU0GPU，无storage_mb/Compose；当前禁网声明已删而题面仍禁网络，等价机制未落实，按本批网络迁移政策豁免。 |
| resources/gaps/0 | QA15 | manual | pass_with_waivers | 当前成绩的硬件归属/换卡影响尚未确认 |
| trajectory/0/finding/0 | QA18 | fail | pass_with_waivers | GPT第210轮明确旧加载器错误映射使训练混入公开验证受试者，旧765口径1.0已作废；Seed早期共享同一工作区和该旧口径，早期分数不得作清洁独立证据。 |
| trajectory/1/finding/0 | QA18 | fail | pass_with_waivers | GPT第210轮明确旧加载器错误映射使训练混入公开验证受试者，旧765口径1.0已作废；Seed早期共享同一工作区和该旧口径，早期分数不得作清洁独立证据。 |
| nop/trials/0 | H06 | manual | pass_with_waivers | Harbor Trial task.toml hash disagrees with the inspected task |
