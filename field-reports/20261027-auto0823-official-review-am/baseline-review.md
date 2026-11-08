# Baseline 合理性检查

总评：**在已提供材料范围内合理**。只读审查，不是独立训练或重载认证。

Starter 为 `workspace/harbor_task/environment/starter/train.py` 的全量 ERM/CE；正式 Baseline 是该方法的 5 次独立种子训练；主评分 B 是对应 Hidden 平均准确率 67.104。不是随机模型、欠采样弱对照或 Agent 搜索最佳。Reference 为 `workspace/reference/train_lt.py --loss logit_adj --tau 1.0`，训练损失加入类别先验；BNS/IP-DPP 文件为未采用的备选。

| 条件 | Baseline | Reference | 依据 |
|---|---|---|---|
| 数据 | CIFAR10LT IF100，9929 train /5000 public val /10000 hidden test | 同左 | 两边 result.json 的 protocol；两个训练源码 |
| 架构/初始化 | 固定三 stage ResNetCIFAR，width64，随机初始化 | 同左 | starter/models/resnet.py；train_lt.py |
| 正式变量 | 标准 CE，全量数据，无重采样 | CE(logits+log prior,y)，τ1 | 两训练源码及日志 loss=logit_adj |
| 优化/预算 | SGD lr0.1、momentum0.9、wd5e-4，batch128，100epoch余弦；单轮7200s | 同左 | 10份 result.json；10份原始 run.log |
| 实际训练量 | 5次均到100/100，末loss 0.0033–0.0042，181.5–186.6s | 5次均到100/100，末loss 0.0032–0.0038，172.3–299.2s | 每seed run.log 与 execution.wall_seconds |
| 最终模型 | 最后一轮，独立权重文件 | 同左 | torch.save位置；10份 artifact.json / reload.log |
| 训练随机种子 | 1,2,3,4,5，实际进入模型初始化、shuffle、augmentation | 相同集合、同样生效 | torch.manual_seed / np.random.seed / Generator |
| 选择规则 | 未修改起点，无挑差seed | 固定logit_adj τ1跨全部seed | comparison_summary；训练证据说明 |
| 历史硬件 | 1×RTX3080Ti、配额20CPU | 同左 | result.json / 专家说明；非目标H20/L20实测 |
| 版本与来源 | retained树 aa98f559…；train.py 853f651d…与包内相同 | reference树53d24d74…；入口cc3530ef…及starter依赖 | source_provenance/manifest.json；reference_dependency_manifest.json；remote_forensics |

| 项目 | 状态 | 证据与理由 | 最小修复/补证及复验条件 |
|---|---|---|---|
| B01 代表性 | 通过 | 全量ERM为可解释、非平凡的naive正式对照，起点与锚点映射清楚。包内随机均衡欠采样约61.27反而更弱，作者没有以其作B；无预算可行同协议更强锚点足以证明该选择不当。 | 无；不要求换SOTA。 |
| B02 实现与训练健全 | 通过 | 输入标签对应，CE、zero_grad/backward/step及最终模型推理路径正常；原始日志显示双方实际100epoch正常完成，非仅配置声明。10个模型均11153922字节，现场字节SHA与artifact相符，10份重载记录Dev差0。 | 无；没有加载权重。 |
| B03 公平预算 | 通过 | 双方相同数据、模型、100epoch与单轮预算，只有损失差异。NR_s5耗时299.2s而不是其余约173s，但训练量不变且远低上限。历史硬件相同，未将旧分改标目标卡。 | 目标卡证明差异由QA15逐原因豁免，不重训历史B/R。 |
| B04 配置与搜索公平 | 通过 | 相同SGD等默认配置；Reference的损失选择及失败IP-DPP/BNS/CB方向已披露。没有证据表明只给B异常学习率、早停或故障配置；不要求双方搜索次数机械相等。 | 无。 |
| B05 随机性公平 | 通过 | 所有正式1–5种子逐项成对，种子实际生效；每侧固定候选方法，10份权重哈希均不同。warn_only的CuBLAS非确定警告不被当作全评估确定。 | 无；固定checkpoint前向与独立随机训练分开。 |
| B06 基本锚点 | 通过 | 两轨未改Starter首轮Dev均67.16，与Baseline seed1一致；训练证据说明列较弱欠采样61.27、CB63.31等探索，未见B低于适用包内基本锚点。Dev探索数不可冒充Hidden正式对照。 | 无，不编造随机/常数分数。 |
| B07 改进归因 | 通过 | 固定数据、骨干、优化与预算，仅引入训练损失先验修正。公开Dev拟合属于Agent研究，不混入正式R。当前NR_s5采用现存预测复算链75.69，旧75.68留档，当前十对主值/统计/分组已统一。 | 无，不将历史Agent集成成绩用于B/R正证。 |
| B08 选择披露 | 通过 | 训练证据说明§2/6、源码溯源及原记录说明了选择理由、失败备选、旧卡与argv/cwd限制；没有只用巨大提升代替对照说明。 | 无；不额外要求进程级认证、第三方时间戳。 |

正式 Hidden 成对值：

| seed | B | R | 改善 |
|---|---:|---:|---:|
| 1 | 66.59 | 76.94 | 10.35 |
| 2 | 66.10 | 72.60 | 6.50 |
| 3 | 66.96 | 75.40 | 8.44 |
| 4 | 67.62 | 77.37 | 9.75 |
| 5 | 68.25 | 75.69 | 7.44 |

B均值67.104、样本σB=0.8474255129508454；R均值75.600、样本σR=1.869264561264673；Δ=8.496=10.02566σB，3σB=2.542277；U=80时归一化0.658808933。保留历史75.68订正原件，不把历史留档误作两套同时生效结果。已有Hidden复算记录和QA05锚点重放记录支持原值；本次只复算文本数字和文件哈希。

关键红旗：未发现Baseline直接故障、无依据缩减训练、挑seed或实质预算不公平。U=80有300epoch探针支持，但材料的mtime表明U回填晚于训练、早于结果整理，不证明严格预注册；第三方预注册不是原标准新增必需材料。历史源码argv/cwd缺失亦不自动推断B无效。

专家退回说明：Baseline专项无需返修。总报告另列当前best说明的事实对应错误，既不影响本专项，也不能用Baseline通过掩盖。边界：文件字节/日志/源码内部一致不等于本次独立复现；未执行提交代码、加载模型或复评分。
