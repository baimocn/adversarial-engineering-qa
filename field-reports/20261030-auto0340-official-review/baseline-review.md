# Baseline 合理性检查

总评：在已提供的现行 15k 正式材料范围内合理。当前 Verifier 的静态错误单列为交付阻断，不把它追溯算成历史 Baseline 的不公平，也不以本结论证明当前评分可用。

Starter 为 Agent 可见的 vanilla TD 起点及专家更新骨架；正式 Baseline 来自原样 vanilla TD 路径；主评分 B 为正式 Hidden seeds 1/2/3 均值 0.05325224981673576。Reference 为专家/在线混合的 IQ 隐式奖励目标、χ² 正则与 v0 锚定。没有把旧故障 Baseline 或 Agent 历史 Dev 分另当评分 B。

| 比较维度 | Baseline | Reference | 证据 |
|---|---|---|---|
| 方法/源码 | vanilla TD，use_expert=false | IQ 目标，use_expert=true、use_v0=true | `workspace/harbor_task/solution/tdmpc2/tdmpc2.py`；`workspace/reference/tdmpc2/tdmpc2.py`、`iq.py` |
| 实际训练 | 各 seed 到 15000 步，2326.38–2382.90s | 各 seed 到 15000 步，3969.8–3984.2s（Hidden） | `optimization_evidence/{baseline_runs,reference_runs}/seed_{1,2,3}/train.log`、`result.json` |
| 数据/评价 | Hidden 34 条，30 回合 | 相同 | 六份正式 result；`tests/anchors.json`；`训练证据说明.md` |
| 资源/预算 | RTX 4080 SUPER 历史实测，单轮共同 7200s 预算 | 同卡型/协议；额外专家目标是研究变量 | 正式 result 的 hardware；`task.toml`；未冒充 H20/L20 实测 |
| 随机性/选择 | seeds 1/2/3、final checkpoint | 相同 seed 全集、固定候选版本 | 六份 result、`reload_manifest.json`、`reload.log` |
| 结果 | 0.12450895099148813 / 0.0006893011880796015 / 0.03455849727063954 | 114.67274838561086 / 124.6976967446135 / 127.69176767755877 | 逐 seed 正式 result |

| 项目 | 状态 | 证据与理由 | 最小修复/补证及复验条件 |
|---|---|---|---|
| B01 代表性 | 通过 | vanilla TD 为公开起点和朴素对照；题目允许专家数据利用。没有包内同协议强锚点反证，不因低分或方法简单判不合理。 | 无需指定 SOTA。 |
| B02 实现与训练健全 | 通过 | `common/math.py` 标量分支 `(pred-symlog(target))²`，`_update_vanilla` 有 backward/optimizer 更新；生产 Ensemble 探针 `q_grad_probe_result.json` 首步梯度 0.10552591351901965、第二步早层梯度记录存在。六份训练日志到 15000 步，未发现 Baseline 专属少训练或异常中止；末端 loss 近零本身不证明故障。旧交叉熵/零梯度批明确作废。 | 已有探针仅证明通路，未声称本次重跑或已收敛。 |
| B03 公平预算 | 通过 | 同一 Hidden、15k 步、30 回合、共同单轮资源上限；R 更长训练耗时仍在共同预算内，专家目标/混合 batch 属允许方法变化。 | H20/L20 仅迁移推断，不把历史时间改标。 |
| B04 配置与搜索公平 | 通过 | 两臂共同固定协议；源码与配置原件保留，未发现只给 B 异常超参。Reference 数值差异对应专家方法开关；无证据据此断言搜索不公平。 | 不主张已证明全局最优调参。 |
| B05 随机性公平 | 通过 | seeds 1/2/3 全集逐项配对；train.py 调 set_seed，环境 cfg.seed 生效。六权重逐字节 SHA256 与各自 result 一致，且六哈希不同；各臂方法源码版本固定。 | 原始方法/配置及权重索引继续保留。 |
| B06 基本锚点 | 通过（有限范围） | 原样 Starter 即正式对照，未发现已交同协议 sanity 分数高于 B 而被隐瞒；不编造随机或常数分数。 | 没有额外 sanity 不自动失败。 |
| B07 改进归因 | 通过 | 健康标量损失两侧一致；R 增益来自 IQ 目标与专家利用整体方案。旧故障和旧泄露 Agent 分不计入当前正式对照；没有拿 100k 与 15k 相减。 | 不把整体方案比较说成单项消融结论。 |
| B08 选择披露 | 通过 | `训练证据说明.md`、两臂 README、Reference README、原始源码和 batch 说明披露角色、方法、协议、局限；结构重载与独立推理复评分开。 | 历史修订附件可归档精简，不能覆盖现行原件。 |

六个 Hidden 模型各 27,057,492 字节，已仅通过流式 SHA256 核对，未加载。`reload.log` 自述为结构级重载，不能冒充独立推理复评分。正式三对复算：B=0.05325224981673576，σ_B=0.06399155184515133，R=122.35407093592771，Δ=122.30081868611097，Δ/σ_B=1911.2025753346027，归一化=0.2499614876890265。U=489.3319 有文本逐回合返回值支撑，其均值为489.33189705882353；未反序列化 Hidden 数据。

关键红旗：现行正式 Baseline 未发现直接削弱红旗。两个当前 Verifier 缺陷仍须修复：`evaluate_verify.py:590-599` 将 ndarray 传入要求 Tensor 的包装器；`_code_fp` 把 docstring 纳入冻结指纹，误拒语义相同的 Starter/Reference。详见总报告 QA05/QA06/H04。

专家退回说明：本专项不要求更换 Baseline 或重做历史两轨。请修复当前评分动作接口和冻结比较口径；按总报告的正常候选验收条件验证，不用历史 NOP 替代当前静态问题的修复。

边界：只读源码、JSON、日志、AST 与字节哈希核查，不等于独立复现；未执行、导入提交代码，未运行训练、Verifier、Docker/Harbor或反序列化权重。
