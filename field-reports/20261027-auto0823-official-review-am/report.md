# 优化面介绍

CIFAR-10-LT IF=100，固定划分及width=64三stage骨干，开放可执行训练目标、采样、辅助任务、日程与推理读出；可实现方法研究。

可修改：solution/内训练损失及辅助目标；重加权、采样、训练日程；固定骨干上的视图聚合和affine/custom读出。

固定面：train=9929/val=5000/test=10000及类别计数；固定骨干参数布局、评测及私有标签；单轮7200s资源合同。

指标与质量门：Hidden top1百分比maximize；(x-67.104)/(80-67.104)不裁剪；int64预测、固定架构、可信重放匹配门，失败-1；基础设施ERROR为0且rc2。

# Baseline 与 Reference 跑分

Baseline 方法：未修改Starter的全量长尾数据ERM/CE，随机初始化固定ResNetCIFAR(width64)，SGD lr0.1/momentum0.9/wd5e-4、batch128、100epoch余弦，最后模型；无采样、外部数据或预训练。

Reference 方法：workspace/reference/train_lt.py --loss logit_adj --tau 1：训练CE(logits+log prior,y)，其他数据/骨干/优化器/100epoch及seed集合与B相同；非BNS/IP-DPP备选，也不是Agent最佳解。

主指标：hidden_overall_accuracy_percent（越高越好）。

| training_seed | Baseline | Reference | 配对改善 | 有效性 |
|---|---:|---:|---:|---|
| 1 | 66.59 | 76.94 | 10.35 | B:是 / R:是 |
| 2 | 66.1 | 72.6 | 6.5 | B:是 / R:是 |
| 3 | 66.96 | 75.4 | 8.44 | B:是 / R:是 |
| 4 | 67.62 | 77.37 | 9.75 | B:是 / R:是 |
| 5 | 68.25 | 75.69 | 7.44 | B:是 / R:是 |

汇总：Baseline 均值 67.104，样本标准差 0.847425512951；Reference 均值 75.6，样本标准差 1.86926456126。

改善结论：完整5对改善10.35/6.50/8.44/9.75/7.44pp；B=67.104, σB=0.8474255129508454, R=75.6, σR=1.869264561264673, Δ=8.495999999999995, Δ/σB=10.025659919555434, normalized=0.658808933002481。seed5当前75.69；旧75.68仅历史订正台账。

质量门：10次正式训练日志均到100epoch、质量门PASS；10份checkpoint字节哈希/大小匹配artifact，独立重载记录Dev差0；Hidden采用已交复算记录，不冒充本次重载或新硬件实测。

# 前置内容门槛

| 门槛 | 结论 | 原因 |
|---|---|---|
| G01 方法级优化空间 | 通过 | 开放训练过程及可执行读出，固定骨干不限制为常量字典；Reference从CE变为先验调整目标，非纯超参题。 |
| G02 Baseline 合理性 | 通过 | 在已有材料范围内Baseline合理：全量ERM正常100epoch、同数据预算和seed、完整选择记录；无直接不公平反证，进程级认证非必交。 |
| G03 Reference 提升充分性 | 通过 | 5对有效原值复算：Δ=8.496=10.02566σB，normalized=0.658809，门槛达标；U=80有更充分预算探针支持但不认证严格预注册。 |

G03 复算：Δ=8.496；σ_B（样本标准差）=0.847425512951；U=80；归一化分数=0.658808933002。

# 两条轨迹迭代概况

| Agent 轨迹 | 状态 | 打包轮数 | 声明有效轮数 | 有效时长 | 概况与最终结果 |
|---|---|---:|---:|---:|---|
| Codex + GPT-5.6 Sol | 完整 | 84 | 84 | - | ERM→先验调整/BS→Cutout→TTA→正则/学习率→Dev偏置/affine与top1细化；84轮，含标签平滑/EMA等退化与回退。 只有轮次摘要，无sessions；原始窗口不是已确认有效时长；历史round84自报86.66；选用干净复验86.54（对应round69式单模型18-view/affine），Hidden83.96，reward1.307072；源hash与选优时点差异已有说明。 |
| Codex + Seed 2.1 Turbo | 完整 | 47 | 47 | - | ERM→CB/Focal失败→LA/Mixup/CutMix→多seed集成与TTA→dropout/LS；47轮，原JSONL inner标签缺30/时区归一化有说明，EMA9.98失败保留。 只有轮次摘要，无sessions；原始窗口不是已确认有效时长；历史round33/34最高86.36属于31/36模型、超当前24 member-view预算，process_record_only；round35式重训85.08只为方法对照，原85.70配置不同且权重不齐无法核对；整轨不主张可复算得分。 |

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
| historical_NR_s5 | training | 299.2 | 1 / RTX 3080 Ti | 20 |

资源需求估算：完整一轮约 6000 秒，1 张 GPU，20 核 CPU；已有B/R单训练173–299s，gpt逐调用最慢1985s；固定骨干模型11.15MB，24 member-view最多约1680s CPU重放（contract预算注释）。加Dev、独立重载及余量估计6000s，历史3080Ti迁移到目标卡的上限估算非实测。

计时口径：代表完整一轮训练+模型/预测产物+公开Dev+独立Hidden重放；不把整轨10.5h或Seed20,400s多轮会话当单轮。

# 目标部署能力

配置范围：innerfield-maso-v1

题面仍声明Agent无出网且工具不可用；当前TOML已移除不支持的禁网字段，仅HF_HUB_OFFLINE与custom-readout seccomp不等于整个Agent禁网。属已批准unsupported_network_policy_transition，非宣称已落实网络隔离。
- 题面仍声明Agent无出网且工具不可用；当前TOML已移除不支持的禁网字段，仅HF_HUB_OFFLINE与custom-readout seccomp不等于整个Agent禁网。属已批准unsupported_network_policy_transition，非宣称已落实网络隔离。；证据：workspace/harbor_task/instruction.md；workspace/harbor_task/task.toml；workspace/harbor_task/tests/sandbox_readout.py

任务硬件与成绩对应：gpu / unverified；当前成绩的硬件归属/换卡影响尚未确认
证据：workspace/harbor_task/task.toml；expert_evidence/专家作业说明文档.md；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_1/result.json

# 格式对齐建议

三目录职责可辨；两轨run对象包装含rounds八字段，Seed原JSONL是审计原件非第三条正式轨迹；所有5对正式训练证据完整。当前最佳说明对应错误由QA21保留，非额外文件本身导致失败。

- `optimization_evidence/README.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `tests_private_test_labels.npz`（可合并）：仅专家侧重复私有标签，可精简；不得进入Agent context。
- `expert_evidence/source_provenance`（可保留的额外项）：保留源码溯源与历史原件，清晰标示历史/生效字段。
- `expert_evidence/u300_budget_probe`（可保留的额外项）：作为U依据附件保留，勿混入100epoch正式R。
- `workspace/reference/train_reference.py`（可保留的额外项）：标清未采用BNS/IP-DPP备选；正式Reference为train_lt.py。

说明：额外材料仅作精简或归位建议，不因多交而单独判错。

# 质检结论：不通过

产物：evidence-input｜通过 15 项｜不通过 3 项｜未完成 3 项｜跳过/不适用 0 项

前置三门：通过 3 项｜不通过 0 项｜待核验 0 项；全部复核完成：否。

口径：只读检查及已有证据复核；QA07/08 查 instruction；QA18 审所交轨迹及提供的 sessions，QA21 单独核对 run_summary 的四项题包哈希；QA15 允许根据日志、轨迹和B/R实现估算资源。QA16 两条各至少 10h；仅无训练且单轮很短、例外证据完整时可各至少 7h。排队、安装与故障不计有效迭代时长。未执行提交代码、未独立复跑或反序列化模型。

Harbor 格式/接口：不通过；已提交自检记录不满足 NOP 运行要求。

| 检查项 | 是否通过 | 原因 |
|---|---|---|
| QA01 八章节与题面信息泄露 | 通过 | 八章实质内容齐全，无具体参考算法名、论文或repo线索；公布B聚合及seed原值不含可恢复标签。 |
| QA02 评分公式与 0/1 锚点 | 通过 | grader使用(x-B)/(U-B)，U>B，无clip；B=67.104、U=80，B均值0/U为1；单seed基线可负分。 |
| QA03 参考解分数与复现材料 | 通过 | 正式Reference为train_lt logit_adj；5seed日志、权重、artifact与重载齐全，聚合归一化0.658809；历史换环境未补跑不作当前缺陷。 |
| QA04 波动指标的 3σ 可分辨性 | 通过 | 训练seed1..5进入初始化、shuffle和augmentation，B/R固定各自同一方法；Δ8.496≥3σB2.542277，未将Dev或Agent分混入。 |
| QA05 约束执行实现 | 不通过 | 题面仍声明Agent无出网且工具不可用；当前TOML已移除不支持的禁网字段，仅HF_HUB_OFFLINE与custom-readout seccomp不等于整个Agent禁网。属已批准unsupported_network_policy_transition，非宣称已落实网络隔离。 |
| QA06 Verifier 入口、分数与错误处理 | 通过 | /tests/test.sh调用grader，finite数值reward.json优先及reward.txt；CandidateError写-1，infra写0/status ERROR且rc2。 |
| QA07 instruction 中的 Hidden 信息泄露 | 通过 | 仅审题面：未披露Hidden标签、逐样本答案或可恢复映射；B统计不构成测试答案。 |
| QA08 instruction 中的参考解信息泄露 | 通过 | 仅审题面：无Reference代码、算法配方或参考解成绩；接口与质量门是必要合同说明。 |
| QA09 结果清理与原子写入 | 通过 | clear_outputs清旧reward/detail，mkstemp写入后os.replace原子替换，奖励文件chmod0644。 |
| QA10 冻结面保护或恢复实现 | 通过 | 可信标签/锚点/骨干来自独立Verifier镜像；候选仅weights_only权重及受控readout，后者chroot降权且无private；非root只读公开面有实现。 |
| QA11 instruction 八项内容 | 通过 | 目标、环境、指标、范围、禁止、提交、流程、完成条件均有实质内容；7200s wrapper覆盖train/产物/Dev，不接受无界运行；禁网落实差异由QA05单列。 |
| QA12 Git 清理 | 通过 | 清点题包无.git目录；本工作区的受保护.git不属于题包。 |
| QA13 Baseline 与参考解提升 | 通过 | 全部正式5对同seed同协议且同向提升；B合理非平凡、R75.600，质量门及重载记录完整，Seed研究分未参与。 |
| QA14 合法改进空间 | 通过 | 目标/采样/辅助训练/读出接口开放，可从代码设计非数值搜索方法；训练损失变更与两轨方法尝试提供可发现方向；R距U4.4>3σB。 |
| QA15 评分资源需求估算 | 待补充核验 | 缺少：当前成绩的硬件归属/换卡影响尚未确认 |
| QA16 轨迹实际迭代时长 | 待补充核验 | Codex + GPT-5.6 Sol缺少有效时长或排除排队/安装/故障的核算证据；Codex + Seed 2.1 Turbo缺少有效时长或排除排队/安装/故障的核算证据 |
| QA17 Harbor Harness 兼容性 | 不通过 | Harbor 子项未通过：H02 版本与配置；H03 环境与运行路径；H05 Job/Trial 调用配置；H06 NOP 自检记录；详细原因与证据保留在 report.json。 |
| QA18 轨迹、日志与分析 | 待补充核验 | 两轨84/47轮及所交原始JSONL、索引、源码/复验均已读。独立目录模型有自述/启动器支持；原始Prompt及最高档证明不齐。Seed多成员旧分无完整权重且已撤回得分主张，仅研究记录，不用作正式B/R。 |
| QA19 seed 与有效提升阈值 | 通过 | 题面声明训练seed{1..5}与有效提升3σB；训练随机、固定模型前向确定，不以单checkpoint确定性取消正式seed检验。 |
| QA20 修改范围、网络与工具策略 | 通过 | 题面明确可改训练/读出范围、数据/权重来源禁令、网络与平台工具策略；禁网能力另列QA05迁移缺口。 |
| QA21 三个 JSON 的填写内容 | 不通过 | 当前最佳方法说明仍有两处实质对应错误：gpt56的README把Seed的5成员仅保存1个缺口写成本目录限制；专家表把winner隐藏reward写1.3179，与83.96及现B/U应得1.307072不符。原B/R与JSON复算值不因此无效。 |

风险提示（不额外计入清单结论）：U=80为估计可达界，有300epoch探针支持；原mtime晚于正式训练而早于结果整理，不能称严格预注册。未新增可信时间戳要求。（依据：workspace/harbor_task/tests/private/anchors.json、expert_evidence/source_provenance/remote_forensics_20261025/G02_运行源码绑定补证_20261025.md）；仅轮次摘要与原JSONL，无完整工具sessions；未发现已确认泄漏，不能据此认证全部网络行为。（依据：expert_evidence/trajectory_codex.json、expert_evidence/trajectory_seed.json）。

# 退回专家说明

QA05 约束执行实现（不通过）：题面仍声明Agent无出网且工具不可用；当前TOML已移除不支持的禁网字段，仅HF_HUB_OFFLINE与custom-readout seccomp不等于整个Agent禁网。属已批准unsupported_network_policy_transition，非宣称已落实网络隔离。
证据：workspace/harbor_task/instruction.md；workspace/harbor_task/task.toml；workspace/harbor_task/tests/sandbox_readout.py；workspace/harbor_task/environment/public_eval/run_round.sh
请修改/补充：按该项具体历史缺口记录适用豁免；不要求新增历史证明或补跑。
复检验收材料：保留原始事实与引用，按本批对应白名单逐原因处置。

QA15 评分资源需求估算（待补充核验）：缺少：当前成绩的硬件归属/换卡影响尚未确认
证据：workspace/harbor_task/task.toml；expert_evidence/专家作业说明文档.md；optimization_evidence/reference_runs/seed_5/result.json；expert_evidence/runtime_forensics_20261025/README.md；workspace/harbor_task/tests/submission_contract.py；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_1/result.json
请修改/补充：按任务性质核对当前Solver/Verifier资源。换卡只复核受影响的成绩或耗时，并引用已有配置、说明或运行记录；旧测量保留原硬件标签。
复检验收材料：CPU题不申请GPU；GPU题的实际目标卡型为H20/L20；受影响正式分数有目标硬件对应依据，不能只改型号沿用旧分。

QA16 轨迹实际迭代时长（待补充核验）：Codex + GPT-5.6 Sol缺少有效时长或排除排队/安装/故障的核算证据；Codex + Seed 2.1 Turbo缺少有效时长或排除排队/安装/故障的核算证据
证据：expert_evidence/trajectory_codex.json；expert_evidence/runtime_forensics_20261025/README.md；expert_evidence/best_selection.json；expert_evidence/reverify/track_gpt56_reverify.json；expert_evidence/trajectory_seed.json；expert_evidence/reverify/track_seed_reverify.json
请修改/补充：为Codex + GPT-5.6 Sol、Codex + Seed 2.1 Turbo补一张时长表：研究起止、排队/安装/API失联/故障区间、仍正常运行的训练重叠及有效秒数。可引用已交轨迹和日志片段；不强制提交完整timer或sessions。
复检验收材料：可复算的两轨起止/扣除表，与轨迹时间相符；默认每轨≥36000有效秒。最终复验、收集和明确故障不计，健康训练并发只计一次。

QA17 Harbor Harness 兼容性（不通过）：Harbor 子项未通过：H02 版本与配置；H03 环境与运行路径；H05 Job/Trial 调用配置；H06 NOP 自检记录；详细原因与证据保留在 report.json。
证据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/private/anchors.json；workspace/harbor_task/tests/private/test_labels.npz；workspace/harbor_task/instruction.md；workspace/harbor_task/tests/sandbox_readout.py；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/test.sh；expert_evidence/nop_trial/verifier/reward.json；expert_evidence/nop_trial/config.json；expert_evidence/nop_trial/result.json；expert_evidence/nop_trial/trial.log；expert_evidence/nop_trial/verifier/reward.txt；expert_evidence/nop_trial/verifier/test-stdout.txt；expert_evidence/nop_trial/README.md；expert_evidence/nop_trial_v1_superseded/config.json；expert_evidence/nop_trial_v1_superseded/result.json
请修改/补充：按该项具体历史缺口记录适用豁免；不要求新增历史证明或补跑。
复检验收材料：保留原始事实与引用，按本批对应白名单逐原因处置。

QA18 轨迹、日志与分析（待补充核验）：两轨84/47轮及所交原始JSONL、索引、源码/复验均已读。独立目录模型有自述/启动器支持；原始Prompt及最高档证明不齐。Seed多成员旧分无完整权重且已撤回得分主张，仅研究记录，不用作正式B/R。
证据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/reverify/track_seed_artifacts/trajectory.jsonl；expert_evidence/best_selection.json；expert_evidence/runtime_forensics_20261025/launch_track.sh；expert_evidence/reverify/track_seed_reverify.json；expert_evidence/reverify/track_gpt56_reverify.json；expert_evidence/run_summary.json#task_binding
请修改/补充：按该项具体历史缺口记录适用豁免；不要求新增历史证明或补跑。
复检验收材料：保留原始事实与引用，按本批对应白名单逐原因处置。

QA21 三个 JSON 的填写内容（不通过）：当前最佳方法说明仍有两处实质对应错误：gpt56的README把Seed的5成员仅保存1个缺口写成本目录限制；专家表把winner隐藏reward写1.3179，与83.96及现B/U应得1.307072不符。原B/R与JSON复算值不因此无效。
证据：expert_evidence/best_method/README.md:85-91；expert_evidence/best_method/train.py；expert_evidence/best_method/run_meta.json；expert_evidence/专家作业说明文档.md:123-130；expert_evidence/reverify/track_gpt56_reverify.json；workspace/harbor_task/tests/private/anchors.json；expert_evidence/run_summary.json；expert_evidence/expert_annotation.json；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json
请修改/补充：仅修正当前说明：best_method/README.md:87-89的5成员缺失说明应归track_seed；专家作业说明文档.md:125的winner隐藏reward应与83.96及现锚点一致为1.3070719603，明确旧口径时另标；不改原始轨迹或正式B/R，不要求重跑历史研究。
复检验收材料：提交当前说明与best_method单模型+18视图代码、run_meta及track_gpt56_reverify.json一致的修订；验证(83.96-67.104)/(80-67.104)=1.3070719603，Seed缺权重说明有明确归属。
