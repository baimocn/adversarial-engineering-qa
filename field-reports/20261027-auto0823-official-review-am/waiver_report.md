# 旧题完整质检与逐原因豁免

本轮结论：FAIL
阶段：standard_review_with_waivers
已完成全部内容审阅：是

原 v0.3.10 全部检查及完整内容审阅已完成，包括已有 NOP；仅按具体历史原因豁免。未执行题包代码或新增 Harbor Trial。
平台实跑：not_executed；未执行模型、题目程序、Docker 或 Harbor。

## 方法与正式对照

CIFAR-10-LT IF=100，固定划分及width=64三stage骨干，开放可执行训练目标、采样、辅助任务、日程与推理读出；可实现方法研究。
可修改：solution/内训练损失及辅助目标；重加权、采样、训练日程；固定骨干上的视图聚合和affine/custom读出
冻结面：train=9929/val=5000/test=10000及类别计数；固定骨干参数布局、评测及私有标签；单轮7200s资源合同
指标与质量门：Hidden top1百分比maximize；(x-67.104)/(80-67.104)不裁剪；int64预测、固定架构、可信重放匹配门，失败-1；基础设施ERROR为0且rc2。
Baseline：未修改Starter的全量长尾数据ERM/CE，随机初始化固定ResNetCIFAR(width64)，SGD lr0.1/momentum0.9/wd5e-4、batch128、100epoch余弦，最后模型；无采样、外部数据或预训练。
Reference：workspace/reference/train_lt.py --loss logit_adj --tau 1：训练CE(logits+log prior,y)，其他数据/骨干/优化器/100epoch及seed集合与B相同；非BNS/IP-DPP备选，也不是Agent最佳解。
正式改善：完整5对改善10.35/6.50/8.44/9.75/7.44pp；B=67.104, σB=0.8474255129508454, R=75.6, σR=1.869264561264673, Δ=8.495999999999995, Δ/σB=10.025659919555434, normalized=0.658808933002481。seed5当前75.69；旧75.68仅历史订正台账。
质量有效性：10次正式训练日志均到100epoch、质量门PASS；10份checkpoint字节哈希/大小匹配artifact，独立重载记录Dev差0；Hidden采用已交复算记录，不冒充本次重载或新硬件实测。
已有原始对照：[{"seed": 1, "baseline": 66.59, "reference": 76.94, "baseline_valid": true, "reference_valid": true}, {"seed": 2, "baseline": 66.1, "reference": 72.6, "baseline_valid": true, "reference_valid": true}, {"seed": 3, "baseline": 66.96, "reference": 75.4, "baseline_valid": true, "reference_valid": true}, {"seed": 4, "baseline": 67.62, "reference": 77.37, "baseline_valid": true, "reference_valid": true}, {"seed": 5, "baseline": 68.25, "reference": 75.69, "baseline_valid": true, "reference_valid": true}]
依据：optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/baseline_runs/seed_4/result.json；optimization_evidence/baseline_runs/seed_5/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_4/result.json；optimization_evidence/reference_runs/seed_5/result.json；optimization_evidence/comparison_summary.json；expert_evidence/validation/hidden_metric_b_r.json；expert_evidence/QA05_整改证据/QA05_anchor_reverify.json；expert_evidence/source_provenance/remote_forensics_20261025/G02_运行源码绑定补证_20261025.md；workspace/harbor_task/tests/private/anchors.json

## 研究三门

### G01 方法级优化空间

观察判定：pass；本轮判定：pass
开放训练过程及可执行读出，固定骨干不限制为常量字典；Reference从CE变为先验调整目标，非纯超参题。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/environment/starter/train.py；workspace/reference/train_lt.py；workspace/harbor_task/tests/submission_contract.py

### G02 Baseline 合理性

观察判定：pass；本轮判定：pass
在已有材料范围内Baseline合理：全量ERM正常100epoch、同数据预算和seed、完整选择记录；无直接不公平反证，进程级认证非必交。
审阅依据：workspace/harbor_task/environment/starter/train.py；workspace/reference/train_lt.py；expert_evidence/source_provenance/remote_forensics_20261025/G02_运行源码绑定补证_20261025.md；optimization_evidence/训练证据说明.md
训练充分性：10次原日志到100/100、无guard早停；B loss末轮0.0033–0.0042，非仅配置100；每epoch ceil(9929/128)=78步，约7800次更新。
  依据：optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_1/run.log；optimization_evidence/baseline_runs/seed_5/run.log；workspace/harbor_task/environment/starter/train.py
方法代表性：全量ERM正常朴素对照，有明确起点/锚点映射；未用较弱随机欠采样61.27作B，不要求SOTA。
  依据：workspace/harbor_task/environment/starter/train.py；optimization_evidence/训练证据说明.md
原协议预算可比性：B/R同数据/划分/骨干/100epoch/batch128/SGD/真实3080Ti，同7200s上限；只改损失，NR_s5较慢299s但仍同训练量。新H20/L20为交付目标，非新成绩。
  依据：optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_5/result.json；expert_evidence/专家作业说明文档.md
实现正确性：CE输入/标签/梯度/optimizer.step和最后模型推理无显式故障；Reference加logprior。10个真实文件哈希匹配且不同，原重载Dev差0。历史argv缺失不新增为硬门槛。
  依据：workspace/harbor_task/environment/starter/train.py；workspace/reference/train_lt.py；expert_evidence/source_provenance/reference_dependency_manifest.json；expert_evidence/source_provenance/remote_forensics_20261025/G02_运行源码绑定补证_20261025.md
选择与对照完整性：seed1..5均交，B/R同方法版本跨seed初始化；失败的BNS/IP-DPP及CB方向有披露，未挑差B；不使用Agent搜索best充R。
  依据：optimization_evidence/comparison_summary.json；optimization_evidence/训练证据说明.md；expert_evidence/best_selection.json

### G03 Reference 提升充分性

观察判定：pass；本轮判定：pass
5对有效原值复算：Δ=8.496=10.02566σB，normalized=0.658809，门槛达标；U=80有更充分预算探针支持但不认证严格预注册。
审阅依据：optimization_evidence/comparison_summary.json；workspace/harbor_task/tests/private/anchors.json；expert_evidence/u300_budget_probe/hidden_u.json；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/baseline_runs/seed_4/result.json；optimization_evidence/baseline_runs/seed_5/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_4/result.json；optimization_evidence/reference_runs/seed_5/result.json
正式复算：{"baseline_mean": 67.104, "reference_mean": 75.6, "baseline_sample_std": 0.8474255129508454, "reference_sample_std": 1.869264561264673, "improvement": 8.495999999999995, "run_count": 5, "sigma_multiplier": 10.025659919555434, "three_sigma_baseline": 2.542276538852536, "normalized_score": 0.658808933002481}

## 21 项内容与实现

### QA01 八章节与题面信息泄露

观察判定：pass；本轮判定：pass
八章实质内容齐全，无具体参考算法名、论文或repo线索；公布B聚合及seed原值不含可恢复标签。
审阅依据：workspace/harbor_task/instruction.md

### QA02 评分公式与 0/1 锚点

观察判定：pass；本轮判定：pass
grader使用(x-B)/(U-B)，U>B，无clip；B=67.104、U=80，B均值0/U为1；单seed基线可负分。
审阅依据：workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/private/anchors.json；workspace/harbor_task/instruction.md

### QA03 参考解分数与复现材料

观察判定：pass；本轮判定：pass
正式Reference为train_lt logit_adj；5seed日志、权重、artifact与重载齐全，聚合归一化0.658809；历史换环境未补跑不作当前缺陷。
审阅依据：workspace/reference/train_lt.py；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_4/result.json；optimization_evidence/reference_runs/seed_5/result.json；optimization_evidence/comparison_summary.json；expert_evidence/QA05_整改证据/QA05_anchor_reverify.json

### QA04 波动指标的 3σ 可分辨性

观察判定：pass；本轮判定：pass
训练seed1..5进入初始化、shuffle和augmentation，B/R固定各自同一方法；Δ8.496≥3σB2.542277，未将Dev或Agent分混入。
审阅依据：workspace/harbor_task/environment/starter/train.py；workspace/reference/train_lt.py；optimization_evidence/comparison_summary.json

### QA05 约束执行实现

观察判定：fail；本轮判定：pass_with_waivers
题面仍声明Agent无出网且工具不可用；当前TOML已移除不支持的禁网字段，仅HF_HUB_OFFLINE与custom-readout seccomp不等于整个Agent禁网。属已批准unsupported_network_policy_transition，非宣称已落实网络隔离。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/task.toml；workspace/harbor_task/tests/sandbox_readout.py；workspace/harbor_task/environment/public_eval/run_round.sh
- 题面仍声明Agent无出网且工具不可用；当前TOML已移除不支持的禁网字段，仅HF_HUB_OFFLINE与custom-readout seccomp不等于整个Agent禁网。属已批准unsupported_network_policy_transition，非宣称已落实网络隔离。；处理：waived
  依据：workspace/harbor_task/instruction.md；workspace/harbor_task/task.toml；workspace/harbor_task/tests/sandbox_readout.py；workspace/harbor_task/environment/public_eval/run_round.sh
  豁免原因：unsupported_network_policy_transition；format-repair-policy.md 白名单 unsupported_network_policy_transition：本包task.toml已删除no-network/白名单，题面仍称无出网；本条只免删除不支持网络策略后的防护迁移缺口，不声称HF_HUB_OFFLINE或读出seccomp等价Agent禁网。

### QA06 Verifier 入口、分数与错误处理

观察判定：pass；本轮判定：pass
/tests/test.sh调用grader，finite数值reward.json优先及reward.txt；CandidateError写-1，infra写0/status ERROR且rc2。
审阅依据：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/grader.py

### QA07 instruction 中的 Hidden 信息泄露

观察判定：pass；本轮判定：pass
仅审题面：未披露Hidden标签、逐样本答案或可恢复映射；B统计不构成测试答案。
审阅依据：workspace/harbor_task/instruction.md

### QA08 instruction 中的参考解信息泄露

观察判定：pass；本轮判定：pass
仅审题面：无Reference代码、算法配方或参考解成绩；接口与质量门是必要合同说明。
审阅依据：workspace/harbor_task/instruction.md

### QA09 结果清理与原子写入

观察判定：pass；本轮判定：pass
clear_outputs清旧reward/detail，mkstemp写入后os.replace原子替换，奖励文件chmod0644。
审阅依据：workspace/harbor_task/tests/grader.py

### QA10 冻结面保护或恢复实现

观察判定：pass；本轮判定：pass
可信标签/锚点/骨干来自独立Verifier镜像；候选仅weights_only权重及受控readout，后者chroot降权且无private；非root只读公开面有实现。
审阅依据：workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/submission_contract.py；workspace/harbor_task/tests/sandbox_readout.py；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile

### QA11 instruction 八项内容

观察判定：pass；本轮判定：pass
目标、环境、指标、范围、禁止、提交、流程、完成条件均有实质内容；7200s wrapper覆盖train/产物/Dev，不接受无界运行；禁网落实差异由QA05单列。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/task.toml；workspace/harbor_task/environment/public_eval/run_round.sh；workspace/harbor_task/tests/submission_contract.py

### QA12 Git 清理

观察判定：pass；本轮判定：pass
清点题包无.git目录；本工作区的受保护.git不属于题包。
审阅依据：workspace/harbor_task/instruction.md

### QA13 Baseline 与参考解提升

观察判定：pass；本轮判定：pass
全部正式5对同seed同协议且同向提升；B合理非平凡、R75.600，质量门及重载记录完整，Seed研究分未参与。
审阅依据：optimization_evidence/comparison_summary.json；workspace/harbor_task/environment/starter/train.py；workspace/reference/train_lt.py；optimization_evidence/baseline_runs/seed_1/result.json；optimization_evidence/baseline_runs/seed_2/result.json；optimization_evidence/baseline_runs/seed_3/result.json；optimization_evidence/baseline_runs/seed_4/result.json；optimization_evidence/baseline_runs/seed_5/result.json；optimization_evidence/reference_runs/seed_1/result.json；optimization_evidence/reference_runs/seed_2/result.json；optimization_evidence/reference_runs/seed_3/result.json；optimization_evidence/reference_runs/seed_4/result.json；optimization_evidence/reference_runs/seed_5/result.json

### QA14 合法改进空间

观察判定：pass；本轮判定：pass
目标/采样/辅助训练/读出接口开放，可从代码设计非数值搜索方法；训练损失变更与两轨方法尝试提供可发现方向；R距U4.4>3σB。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/environment/starter/train.py；workspace/reference/train_lt.py；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json

### QA15 评分资源需求估算

观察判定：manual；本轮判定：pass_with_waivers
Agent1×H20/L20/20CPU，Verifier0GPU/8CPU；估计完整代表轮6000s含训练、产物、Dev及Hidden重载，历史3080Ti不改标目标实测；换卡影响仅有推断。
审阅依据：workspace/harbor_task/task.toml；expert_evidence/专家作业说明文档.md；optimization_evidence/reference_runs/seed_5/result.json；expert_evidence/runtime_forensics_20261025/README.md；workspace/harbor_task/tests/submission_contract.py
- 历史RTX3080Ti未改标；目标H20/L20估算无实际验证，未见当前明确超限。；处理：waived
  依据：workspace/harbor_task/task.toml；expert_evidence/专家作业说明文档.md；optimization_evidence/reference_runs/seed_5/result.json；expert_evidence/runtime_forensics_20261025/README.md；workspace/harbor_task/tests/submission_contract.py
  豁免原因：legacy_hardware_record_difference；白名单 legacy_hardware_record_difference：原正式十次均标RTX3080Ti，当前只把内场交付配置改为H20/L20；已有299.2s训练和CPU重放规模可作6000s代表轮推断，无新卡实测且未冒充。仅免换卡影响证明差异。

### QA16 轨迹实际迭代时长

观察判定：manual；本轮判定：pass_with_waivers
现有窗口37831/37810s，逐调用合计37829/37810；Seed最后45s无新增轮应扣，得37765；内部安装/API/阻塞未分类，不能据墙钟证明各≥10h有效研究。训练题不适用7h。
审阅依据：expert_evidence/runtime_forensics_20261025/README.md；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json
- 现有窗口37831/37810s，逐调用合计37829/37810；Seed最后45s无新增轮应扣，得37765；内部安装/API/阻塞未分类，不能据墙钟证明各≥10h有效研究。训练题不适用7h。；处理：waived
  依据：expert_evidence/runtime_forensics_20261025/README.md；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json
  豁免原因：legacy_research_duration_gap；白名单 legacy_research_duration_gap：两轨实际窗口与timing已读，合计37829/37810s及Seed最后45s未增轮已说明；内部排队/安装未细分，净有效秒数未知。本批免旧研究时长/有效证明，不回填10h、不触发训练题7h例外。

### QA17 Harbor Harness 兼容性

观察判定：fail；本轮判定：pass_with_waivers
由H01–H06派生：历史NOP版本不同、当前Trial未跑；镜像准备/root/seccomp/移交由平台验证；不将静态路径通过说成实跑。
审阅依据：workspace/harbor_task/task.toml；expert_evidence/nop_trial/README.md
Harbor逐项派生：H01=pass；H02=pass_with_waivers；H03=pass_with_waivers；H04=pass；H05=pass_with_waivers；H06=pass_with_waivers

### QA18 轨迹、日志与分析

观察判定：manual；本轮判定：pass_with_waivers
两轨84/47轮及所交原始JSONL、索引、源码/复验均已读。独立目录模型有自述/启动器支持；原始Prompt及最高档证明不齐。Seed多成员旧分无完整权重且已撤回得分主张，仅研究记录，不用作正式B/R。
审阅依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/reverify/track_seed_artifacts/trajectory.jsonl；expert_evidence/best_selection.json；expert_evidence/runtime_forensics_20261025/launch_track.sh；expert_evidence/reverify/track_seed_reverify.json
- 实际模型/独立目录据自述/启动器与方法演进支持；最高推理档及完整Prompt快照缺历史证明，不虚称同条件。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/reverify/track_seed_artifacts/trajectory.jsonl；expert_evidence/best_selection.json；expert_evidence/runtime_forensics_20261025/launch_track.sh；expert_evidence/reverify/track_seed_reverify.json
  豁免原因：legacy_runtime_proof_gap；白名单 legacy_runtime_proof_gap：launch_track.sh分别独立CODEX_HOME/task/output及凭据，轨迹实际模型与84/47轮相符；最高推理档与共享HARNESS_PROMPT/AGENT_BRIEF原文未交，仅免历史启动和一致性证明缺口，未确认实质差异。
- Seed旧集成仅保存首成员，当前撤回所有得分主张；只保留研究过程，不作为正式B/R或当前best。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/reverify/track_seed_artifacts/trajectory.jsonl；expert_evidence/best_selection.json；expert_evidence/runtime_forensics_20261025/launch_track.sh；expert_evidence/reverify/track_seed_reverify.json
  豁免原因：legacy_runtime_proof_gap；白名单 legacy_runtime_proof_gap 在既有历史研究证明范围：原Seed集成权重仅保存第1成员，best_selection已is_claimed=false/research_record_only、winner为gpt56；保留原得分unverified且不纳入任何正式B/R或当前best，不把缺权重称作已复算成功，也不要求获免历史研究重跑。
- 已实际对比现有两轨材料，旧版材料仍不足以证明所有历史条件一致；仅此记录缺口豁免，不声称已证实同条件。六维已审：两轨任务均CIFAR10LT、起点67.16、相同公开Dev及训练/读出研究面，启动器独立CODEX_HOME/task/output；build_round_prompt共享HARNESSprompt/BRIEF引用而原文未交，不能认证逐字或全部反馈权限相同。未找到identical_prompt=false或已确认实质差异；driver会话粒度81次对3次是研究行为，不自动等于不同题目反馈。历史同3080Ti/20CPU自述，无目标卡实测。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md；expert_evidence/runtime_forensics_20261025/build_round_prompt.py；expert_evidence/runtime_forensics_20261025/launch_track.sh；expert_evidence/runtime_forensics_20261025/README.md；expert_evidence/任务版本冻结记录_20261008.md
  豁免原因：legacy_runtime_proof_gap；本轮旧题迁移不要求新增Prompt快照、hash或重跑；已读资料中没有已确认的实质条件差异。

### QA19 seed 与有效提升阈值

观察判定：pass；本轮判定：pass
题面声明训练seed{1..5}与有效提升3σB；训练随机、固定模型前向确定，不以单checkpoint确定性取消正式seed检验。
审阅依据：workspace/harbor_task/instruction.md；workspace/harbor_task/environment/starter/train.py；workspace/reference/train_lt.py

### QA20 修改范围、网络与工具策略

观察判定：pass；本轮判定：pass
题面明确可改训练/读出范围、数据/权重来源禁令、网络与平台工具策略；禁网能力另列QA05迁移缺口。
审阅依据：workspace/harbor_task/instruction.md

### QA21 三个 JSON 的填写内容

观察判定：fail；本轮判定：fail
当前最佳方法说明仍有两处实质对应错误：gpt56的README把Seed的5成员仅保存1个缺口写成本目录限制；专家表把winner隐藏reward写1.3179，与83.96及现B/U应得1.307072不符。原B/R与JSON复算值不因此无效。
审阅依据：expert_evidence/best_method/README.md:85-91；expert_evidence/best_method/train.py；expert_evidence/best_method/run_meta.json；expert_evidence/专家作业说明文档.md:123-130；expert_evidence/reverify/track_gpt56_reverify.json；workspace/harbor_task/tests/private/anchors.json；expert_evidence/run_summary.json；expert_evidence/expert_annotation.json；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json
- 当前最佳方法说明仍有两处实质对应错误：gpt56的README把Seed的5成员仅保存1个缺口写成本目录限制；专家表把winner隐藏reward写1.3179，与83.96及现B/U应得1.307072不符。原B/R与JSON复算值不因此无效。；处理：unwaived
  依据：expert_evidence/best_method/README.md:85-91；expert_evidence/best_method/train.py；expert_evidence/best_method/run_meta.json；expert_evidence/专家作业说明文档.md:123-130；expert_evidence/reverify/track_gpt56_reverify.json；workspace/harbor_task/tests/private/anchors.json
  修改方向：仅修正当前说明：best_method/README.md:87-89的5成员缺失说明应归track_seed；专家作业说明文档.md:125的winner隐藏reward应与83.96及现锚点一致为1.3070719603，明确旧口径时另标；不改原始轨迹或正式B/R，不要求重跑历史研究。
  验收：提交当前说明与best_method单模型+18视图代码、run_meta及track_gpt56_reverify.json一致的修订；验证(83.96-67.104)/(80-67.104)=1.3070719603，Seed缺权重说明有明确归属。
- 重算四项8970072d…与run_summary匹配；该字段记录当前v34，不能追溯证明两轨历史输入相同。；处理：waived
  依据：expert_evidence/run_summary.json；workspace/harbor_task/task.toml；expert_evidence/专家作业说明文档.md
  豁免原因：legacy_task_binding_migration；白名单 legacy_task_binding_migration：四项官方工具实算8970072d193260d16a5a26908d4b5d0e8f1d5bb3d200b0585bb515d304c96f48/35文件，与run_summary匹配；说明其仅当前v34返修包绑定，不能补造历史A/B哈希或覆盖两轨条件实质差异。

## Harbor 六项

### H01 任务目录

观察判定：pass；本轮判定：pass
task根四部分齐；私有标签和anchors由tests/镜像预置，grader实际读取；非空Hidden与公开Dev来源分离。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/private/anchors.json；workspace/harbor_task/tests/private/test_labels.npz

### H02 版本与配置

观察判定：fail；本轮判定：pass_with_waivers
题面仍声明Agent无出网且工具不可用；当前TOML已移除不支持的禁网字段，仅HF_HUB_OFFLINE与custom-readout seccomp不等于整个Agent禁网。属已批准unsupported_network_policy_transition，非宣称已落实网络隔离。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md；workspace/harbor_task/tests/sandbox_readout.py
- 题面仍声明Agent无出网且工具不可用；当前TOML已移除不支持的禁网字段，仅HF_HUB_OFFLINE与custom-readout seccomp不等于整个Agent禁网。属已批准unsupported_network_policy_transition，非宣称已落实网络隔离。；处理：waived
  依据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md；workspace/harbor_task/tests/sandbox_readout.py
  豁免原因：unsupported_network_policy_transition；format-repair-policy.md 白名单 unsupported_network_policy_transition：本包task.toml已删除no-network/白名单，题面仍称无出网；本条只免删除不支持网络策略后的防护迁移缺口，不声称HF_HUB_OFFLINE或读出seccomp等价Agent禁网。

### H03 环境与运行路径

观察判定：manual；本轮判定：pass_with_waivers
Agent上下文environment/、Verifier上下文tests/均路径一致，artifacts覆盖/workspace/solution；本地GPU/CPU及chroot子进程，不申请额外工作环境。缺当前内场镜像准备及root/seccomp/移交实测。
审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/sandbox_readout.py
- 有效双Dockerfile/COPY/入口具备；当前内场镜像导入/tag仍由平台准备。；处理：waived
  依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/sandbox_readout.py
  豁免原因：platform_image_preparation_pending；白名单 platform_image_preparation_pending：Agent environment上下文和Verifier tests上下文已有有效Dockerfile、requirements、COPY及绝对入口，内部ICM导入/tag不在包内完成；本条仅免平台镜像准备证明。
- root/chroot/seccomp/实际依赖/产物移交未在当前内场运行核实，不作为作者缺陷。；处理：waived
  依据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/sandbox_readout.py
  豁免原因：platform_execution_verification_pending；白名单 platform_execution_verification_pending：当前代码明确同一Verifier内chroot/降权/seccomp，本地GPU无额外工作环境，static路径无错误；root/seccomp权限、依赖安装、真实移交须平台执行，不能因本轮未跑而记作者静态缺陷。

### H04 测试入口与 reward

观察判定：pass；本轮判定：pass
绝对/tests/test.sh→grader，清理后原子写两种数值reward与detail；合法负数可写，json无字符串。
审阅依据：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/grader.py；expert_evidence/nop_trial/verifier/reward.json

### H05 Job/Trial 调用配置

观察判定：manual；本轮判定：pass_with_waivers
已有NOP config/result为旧task.toml 103cec04，与当前49ee4857不同，agent=nop、separate；当前部署的镜像选择/有效覆盖未实跑，不能作为本版运行证明。
审阅依据：workspace/harbor_task/task.toml；expert_evidence/nop_trial/config.json；expert_evidence/nop_trial/result.json
- 旧Trial参数已审；当前内场有效覆盖/实际镜像选择待平台执行核对。；处理：waived
  依据：workspace/harbor_task/task.toml；expert_evidence/nop_trial/config.json；expert_evidence/nop_trial/result.json
  豁免原因：platform_execution_verification_pending；白名单 platform_execution_verification_pending：已有两份旧NOP调用agent=nop且separate，task.toml103cec04不同于当前49ee4857；只免当前内场有效覆盖和镜像选择的运行验证，旧调用内容已读且非空选、非禁用Verifier。

### H06 NOP 自检记录

观察判定：fail；本轮判定：pass_with_waivers
两份原生旧NOP同次config/result均nop/separate、已结束无exception、reward一致且日志非空；无相同sandbox ID反证，亦无完整物理认证。旧v2 CPU5epoch实际覆盖重放分支但题包hash不同，当前Trial缺失。
审阅依据：expert_evidence/nop_trial/config.json；expert_evidence/nop_trial/result.json；expert_evidence/nop_trial/trial.log；expert_evidence/nop_trial/verifier/reward.json；expert_evidence/nop_trial/verifier/reward.txt；expert_evidence/nop_trial/verifier/test-stdout.txt；expert_evidence/nop_trial/README.md；expert_evidence/nop_trial_v1_superseded/config.json；expert_evidence/nop_trial_v1_superseded/result.json
- 两份原生旧NOP同次config/result均nop/separate、已结束无exception、reward一致且日志非空；无相同sandbox ID反证，亦无完整物理认证。旧v2 CPU5epoch实际覆盖重放分支但题包hash不同，当前Trial缺失。；处理：waived
  依据：expert_evidence/nop_trial/config.json；expert_evidence/nop_trial/result.json；expert_evidence/nop_trial/trial.log；expert_evidence/nop_trial/verifier/reward.json；expert_evidence/nop_trial/verifier/reward.txt；expert_evidence/nop_trial/verifier/test-stdout.txt；expert_evidence/nop_trial/README.md；expert_evidence/nop_trial_v1_superseded/config.json；expert_evidence/nop_trial_v1_superseded/result.json
  豁免原因：legacy_nop_or_current_trial_gap；白名单 legacy_nop_or_current_trial_gap：两份原生历史NOP config/result身份均nop、separate、finish无exception，reward与日志一致；绑定task.toml103cec04不同当前49ee4857，v2是CPU5epoch/可信重放旧分支，v1是旧预测评分分支。本条仅免格式迁移后当前Trial未跑，原记录不改为当前成功。

## 两轨已有内容

### T01 第一条轨迹已有内容

观察判定：manual；本轮判定：pass_with_waivers
ERM→先验调整/BS→Cutout→TTA→正则/学习率→Dev偏置/affine与top1细化；84轮，含标签平滑/EMA等退化与回退。 历史round84自报86.66；选用干净复验86.54（对应round69式单模型18-view/affine），Hidden83.96，reward1.307072；源hash与选优时点差异已有说明。
审阅依据：expert_evidence/trajectory_codex.json；expert_evidence/runtime_forensics_20261025/README.md；expert_evidence/best_selection.json；expert_evidence/reverify/track_gpt56_reverify.json
方法：ERM→先验调整/BS→Cutout→TTA→正则/学习率→Dev偏置/affine与top1细化；84轮，含标签平滑/EMA等退化与回退。
迭代内容：完整审84轮；失败、回退、best与最终选择均有保留。
最终结果：历史round84自报86.66；选用干净复验86.54（对应round69式单模型18-view/affine），Hidden83.96，reward1.307072；源hash与选优时点差异已有说明。
分数采用范围：不使用该轨分数证明G03；正式B/R为optimization_evidence十次训练。winner历史复验范围可用，但非当前内场新复跑。
已读来源：expert_evidence/trajectory_codex.json；expert_evidence/_trajectory_index.json；expert_evidence/专家作业说明文档.md；expert_evidence/runtime_forensics_20261025/build_round_prompt.py；expert_evidence/runtime_forensics_20261025/launch_track.sh
- 所交轨迹可读且属本题，旧启动/最高档/净有效时间证明不足。；处理：waived
  依据：expert_evidence/trajectory_codex.json；expert_evidence/runtime_forensics_20261025/README.md；expert_evidence/best_selection.json；expert_evidence/reverify/track_gpt56_reverify.json
  豁免原因：legacy_runtime_proof_gap；白名单 legacy_runtime_proof_gap：已完整读本轨方法、全部轮次/原JSONL和选择记录；最高档/原始Prompt和净有效计时证明不足，允许保留旧证明差异，不新增sessions、启动快照或补跑义务。

### T02 第二条轨迹已有内容

观察判定：manual；本轮判定：pass_with_waivers
ERM→CB/Focal失败→LA/Mixup/CutMix→多seed集成与TTA→dropout/LS；47轮，原JSONL inner标签缺30/时区归一化有说明，EMA9.98失败保留。 历史round33/34最高86.36属于31/36模型、超当前24 member-view预算，process_record_only；round35式重训85.08只为方法对照，原85.70配置不同且权重不齐无法核对；整轨不主张可复算得分。
审阅依据：expert_evidence/trajectory_seed.json；expert_evidence/runtime_forensics_20261025/README.md；expert_evidence/best_selection.json；expert_evidence/reverify/track_seed_reverify.json
方法：ERM→CB/Focal失败→LA/Mixup/CutMix→多seed集成与TTA→dropout/LS；47轮，原JSONL inner标签缺30/时区归一化有说明，EMA9.98失败保留。
迭代内容：完整审47轮；失败、回退、best与最终选择均有保留。
最终结果：历史round33/34最高86.36属于31/36模型、超当前24 member-view预算，process_record_only；round35式重训85.08只为方法对照，原85.70配置不同且权重不齐无法核对；整轨不主张可复算得分。
分数采用范围：不使用该轨分数证明G03；正式B/R为optimization_evidence十次训练。Seed可复算成绩不主张；85.08方法重训不替代原提交，85.70不与不同配置84.90直接比较。
已读来源：expert_evidence/trajectory_seed.json；expert_evidence/_trajectory_index.json；expert_evidence/reverify/track_seed_artifacts/trajectory.jsonl；expert_evidence/专家作业说明文档.md；expert_evidence/runtime_forensics_20261025/build_round_prompt.py；expert_evidence/runtime_forensics_20261025/launch_track.sh
- 所交轨迹可读且属本题，旧启动/最高档/净有效时间证明不足。；处理：waived
  依据：expert_evidence/trajectory_seed.json；expert_evidence/runtime_forensics_20261025/README.md；expert_evidence/best_selection.json；expert_evidence/reverify/track_seed_reverify.json
  豁免原因：legacy_runtime_proof_gap；白名单 legacy_runtime_proof_gap：已完整读本轨方法、全部轮次/原JSONL和选择记录；最高档/原始Prompt和净有效计时证明不足，允许保留旧证明差异，不新增sessions、启动快照或补跑义务。

## 两轨实际条件对比

对比已完成：是
条件判断：historical_evidence_gap；成对对照有效性：unverified
六维已审：两轨任务均CIFAR10LT、起点67.16、相同公开Dev及训练/读出研究面，启动器独立CODEX_HOME/task/output；build_round_prompt共享HARNESSprompt/BRIEF引用而原文未交，不能认证逐字或全部反馈权限相同。未找到identical_prompt=false或已确认实质差异；driver会话粒度81次对3次是研究行为，不自动等于不同题目反馈。历史同3080Ti/20CPU自述，无目标卡实测。
已对比维度：prompt、task、dev、feedback、constraints、resources
对比依据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/专家作业说明文档.md；expert_evidence/runtime_forensics_20261025/build_round_prompt.py；expert_evidence/runtime_forensics_20261025/launch_track.sh；expert_evidence/runtime_forensics_20261025/README.md；expert_evidence/任务版本冻结记录_20261008.md
质检员内部对比底稿；不要求专家新增字段、Prompt快照、hash或重跑。语义判断须实际阅读原材料，脚本只核验审阅覆盖及判定一致性。

## 当前格式前检 F01–F07（子检查）

format_decision：PASS_WITH_WAIVERS
以下仅为当前格式子检查；整题结论以本报告顶部完整质检结果为准。

- F01 [pass] 当前必需目录、文件与 TOML 接口：当前task四部分、TOML可解析且显式separate；原生资源配置有效表，旧entrypoint/submit仅说明；标准入口/tests/test.sh存在。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md；workspace/harbor_task/tests/test.sh
- F02 [pass] 有效构建或镜像方案、构建上下文及 COPY 来源：双Dockerfile均context内COPY，Agent ARG默认python3.11-slim，依赖声明完整；内部tag/构建由平台准备，不冒充已经运行。
  格式审阅依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile
- F03 [pass] 评分入口、独立依赖声明与固定输出路径：专用tests镜像预置绝对入口、CPUtorch/numpy、私有数据和readout运行时根，数值reward在/logs/verifier。
  格式审阅依据：workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/requirements.txt
- F04 [pass] 提交物 artifacts 移交契约：顶层artifacts=/workspace/solution覆盖grader读取的同一绝对目录；无destination容器重映射误用。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/grader.py
- F05 [pass] 公开 Dev、私有 Hidden 供给与 Agent 隔离：公开Dev/data/starter进入Agent，私有tests仅进入独立Verifier，custom运行时仅小资产/features/logits；未见静态COPY泄漏。
  格式审阅依据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/sandbox_readout.py
- F06 [pass] separate、单容器、无 Compose 与当前目标资源配置：GPU任务Agent1×H20/L20/20CPU，Verifier8CPU/0GPU，separate；直属无Compose/不支持字段；调用仅本地进程，不额外调度GPU环境。
  格式审阅依据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/sandbox_readout.py；workspace/harbor_task/environment/public_eval/run_round.sh
- F07 [pass] 当前评分实现与冻结面无确证故障或作者泄漏造假：当前评分可执行链静态完整，参考数据来自可信镜像，清理/重放/原子reward，未见硬编码伪分或作者泄漏。当前best说明不一致另由QA21保留。
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
NOP：{"status": "manual", "runtime_status": "unverified", "trials": [{"trial_dir": "expert_evidence/nop_trial", "evidence": ["expert_evidence/nop_trial/config.json", "expert_evidence/nop_trial/result.json", "expert_evidence/nop_trial/verifier/reward.json", "expert_evidence/nop_trial/verifier/reward.txt", "expert_evidence/nop_trial/trial.log", "expert_evidence/nop_trial/verifier/test-stdout.txt"], "status": "manual", "summary": "Harbor Trial task.toml hash disagrees with the inspected task", "protected": false}, {"trial_dir": "expert_evidence/nop_trial_v1_superseded", "evidence": ["expert_evidence/nop_trial_v1_superseded/config.json", "expert_evidence/nop_trial_v1_superseded/result.json", "expert_evidence/nop_trial_v1_superseded/verifier/reward.json", "expert_evidence/nop_trial_v1_superseded/verifier/reward.txt", "expert_evidence/nop_trial_v1_superseded/trial.log", "expert_evidence/nop_trial_v1_superseded/verifier/test-stdout.txt"], "status": "manual", "summary": "Harbor Trial task.toml hash disagrees with the inspected task", "protected": false}], "summary": "逐份读取并校验已有 NOP 记录；未启动新的 Trial。"}

原报告与全部详细结果：standard/report.json；不因豁免覆盖原判。

| 来源 | 项目 | 原判 | 本轮处理 | 依据及原因 |
|---|---|---|---|---|
| checks/QA05 | QA05 | fail | pass_with_waivers | 题面仍声明Agent无出网且工具不可用；当前TOML已移除不支持的禁网字段，仅HF_HUB_OFFLINE与custom-readout seccomp不等于整个Agent禁网。属已批准unsupported_network_policy_transition，非宣称已落实网络隔离。 |
| checks/QA15 | QA15 | manual | pass_with_waivers | 缺少：当前成绩的硬件归属/换卡影响尚未确认 |
| checks/QA16 | QA16 | manual | pass_with_waivers | Codex + GPT-5.6 Sol缺少有效时长或排除排队/安装/故障的核算证据；Codex + Seed 2.1 Turbo缺少有效时长或排除排队/安装/故障的核算证据 |
| checks/QA17 | QA17 | fail | derived_from_details | Harbor 子项未通过：H02 版本与配置；H03 环境与运行路径；H05 Job/Trial 调用配置；H06 NOP 自检记录；详细原因与证据保留在 report.json。 |
| checks/QA18 | QA18 | manual | pass_with_waivers | 两轨84/47轮及所交原始JSONL、索引、源码/复验均已读。独立目录模型有自述/启动器支持；原始Prompt及最高档证明不齐。Seed多成员旧分无完整权重且已撤回得分主张，仅研究记录，不用作正式B/R。 |
| checks/QA21 | QA21 | fail | fail | 当前最佳方法说明仍有两处实质对应错误：gpt56的README把Seed的5成员仅保存1个缺口写成本目录限制；专家表把winner隐藏reward写1.3179，与83.96及现B/U应得1.307072不符。原B/R与JSON复算值不因此无效。 |
| harbor/H02 | H02 | fail | pass_with_waivers | 题面仍声明Agent无出网且工具不可用；当前TOML已移除不支持的禁网字段，仅HF_HUB_OFFLINE与custom-readout seccomp不等于整个Agent禁网。属已批准unsupported_network_policy_transition，非宣称已落实网络隔离。；题面仍声明Agent无出网且工具不可用；当前TOML已移除不支持的禁网字段，仅HF_HUB_OFFLINE与custom-readout seccomp不 |
| harbor/H03 | H03 | manual | pass_with_waivers | Agent上下文environment/、Verifier上下文tests/均路径一致，artifacts覆盖/workspace/solution；本地GPU/CPU及chroot子进程，不申请额外工作环境。缺当前内场镜像准备及root/seccomp/移交实测。 |
| harbor/H05 | H05 | manual | pass_with_waivers | 已有NOP config/result为旧task.toml 103cec04，与当前49ee4857不同，agent=nop、separate；当前部署的镜像选择/有效覆盖未实跑，不能作为本版运行证明。 |
| harbor/H06 | H06 | fail | derived_from_details | 两份原生旧NOP同次config/result均nop/separate、已结束无exception、reward一致且日志非空；无相同sandbox ID反证，亦无完整物理认证。旧v2 CPU5epoch实际覆盖重放分支但题包hash不同，当前Trial缺失。 |
| harbor/deployment_contract/0 | H02 | fail | pass_with_waivers | 题面仍声明Agent无出网且工具不可用；当前TOML已移除不支持的禁网字段，仅HF_HUB_OFFLINE与custom-readout seccomp不等于整个Agent禁网。属已批准unsupported_network_policy_transition，非宣称已落实网络隔离。 |
| resources/gaps/0 | QA15 | manual | pass_with_waivers | 当前成绩的硬件归属/换卡影响尚未确认 |
| nop/trials/0 | H06 | manual | pass_with_waivers | Harbor Trial task.toml hash disagrees with the inspected task |
| nop/trials/1 | H06 | manual | pass_with_waivers | Harbor Trial task.toml hash disagrees with the inspected task |
