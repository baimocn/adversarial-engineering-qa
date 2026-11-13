# 唯一当前验收标准

适用0.5.0-current.1。来源：[Xpert题目交付标准](https://bytedance.us.larkoffice.com/docx/FiordpU92o4vwPxYYJ6upVdYsWe) revision2189（含等级评论c1）；[质检Skill返修意见](https://bytedance.larkoffice.com/docx/Ka7odrrStoScBjxKgUtcHYNcnvg) revision116；既有项目/平台要求及本轮“其他标准就不降了”裁定，来源边界见[来源表](source-alignment.md)。用户本轮要求四协议默认、单一当前标准、无豁免/人工选版本、最终只有通过或不通过；不是撤销已执行的项目G与平台规范。此前明确暂停的一小时超时无分退题口径继续有效。来源不是执行rollout或修改远端文档的授权。

## 默认必需：未分级题目规范与L0

- 原生Harbor格式、有效任务配置、可调用的solution/solve.sh Oracle入口及独立Judge；参考实现文件名、语言、组织不限，不能要求固定reference.py。
- Work/Judge全新独立sandbox，任务在已分配环境内计算、不依赖自行部署或调用额外计算工作环境；公开Dev与必要数据/工具可用；私有tests/Hidden/Reference不得进Work，不能先COPY后删除掩盖镜像层泄漏。冻结evaluator/guard/metric/baseline/数据绑定由可信版本恢复或放于Agent不可写环境。
- 必要实体文件与数据存在，数据优先打入镜像，也可在构造sandbox时通过可信上传预置；必要依赖在构建期固定并预装，有适用lockfile，不能以解题阶段临时Volume Mount/数据挂载或下载来补齐基础数据与依赖。50G为镜像规范上限，大多数10G以下是建议；无实际镜像size不能猜FAIL，当前实际超限按控制方修复。
- 题面目标、输入输出、主指标/公式/方向、允许修改面、提交结构和完成条件与真实guard/评分一致。实际执行子限、AST/import/nonlocal、shape/图结构等影响合法方案的限制须公开；不把所有实现细节复写成题面。
- 合法Starter、本次候选→Verifier实际输入→原始指标→正式reward对应；Starter映射0、声明理论/设计上界映射1，分数方向正确，不能用错误B/U或别的split实测冒充当前正式标定。
- 声明实际卡型/卡数/显存、CPU、内存、磁盘、单次运行时长及timeout；最大合法提交在约定资源/时间内可评。GPU不超过8张H20/L20、CPU不超过64核，public Dev一次完整反馈不超过2h。预算按真实调用、并发/共享deadline及收尾判断，不能机械相加timeout。硬件敏感性能/固定墙钟锚点须目标环境校准或有可比依据；固定steps accuracy不因换卡必重测。
- 正式reward只输出reward.json或reward.txt一种；JSON有有限数值主reward，多指标主分明确。候选hard gate明确拒绝、可执行诊断及−10；环境/可信评分故障须错误状态/无分，不得作为候选正常0分或其他完成成绩。失败协议的−10哨兵不得混入正常训练reward；仅看负分数值不足以判错。
- rollout证据证明可解及可提升；自动交卷/超时退出时Solver主Agent responses至少51，主动正常完成不套轮数门。工具、实验轮次和子Agent不计主响应。
- 实际泄漏、作弊、错候选和评分伪造不允许。普通下载/允许修改、未成功的访问请求不自动等于真实作弊；具体静态私有暴露仍可构成包内缺陷。
- 集合至少覆盖五类是批次L0要求，不是每题五类；只有明确给出集合才统计，不让单题补其他类型。

## 统一保留的既有项目与平台必需

下列要求沿用上一正式包的项目/平台规则，未假称算法L0，也不需要人工选择版本或等级：

- G01须有真实可执行的方法研究空间；只允许固定任务的一组学习率、轮数或loss权重等字面量而不能表达方法，按method_space整改。参数若编码可组合程序/结构/策略，或研究HPO算法本身，按真实语义判断；Reference只改数值不能独自证明整题纯调参。
- G03保留正式同候选、同协议全seed配对与Reference归一化[0.15,0.8]；随机评估至少3次，协议声明更多则全部核对。Baseline原始指标样本标准差σ_B用n−1分母，改善方向统一为正，须Δ≥3σ_B；σ_B=0仍须Δ>0。3σ至5σ可接受，5σ只表强证据；headroom不足记录风险，不加一刀切门，确定性评估不恢复统一5%。完整解释见[G三项](research-quality.md)。
- 正式单seed≤2h，同一候选正式多seed累计≤8h；public Dev一次完整反馈≤2h是另一个整链要求。按真实串并行、共享deadline和收尾核算，不机械相加配置timeout。
- B-C03非npm依赖使用生态官方源；B-C04实际使用npm时生效registry为指定bnpm。已有批准替代源和等效配置可接受；无npm不适用，不把模型资产/内部镜像仓库当包管理源。按实际生效安装链归责，不索取新的内网证明。

G02继续完整审训练充分性、方法代表性、预算可比、实现正确和选择完整五维；有证据证明明显不合理/过弱、故障或不公平的正式对照仍不通过，不要求SOTA，不凭少epochs或模型印象判错。

## 完整记录、其余默认非阻断的L1/L2

L1：稳定评测、全部禁令可识别执行、calibration.json投递形式、不易几轮满分、公开信息恢复私有标签捷径、平凡满分与评分漏洞。L2：除既有G03校准以外的高级方案区分度、实质多方案/反馈/复测、饱和过早、计时回放/evaltool推断和诱导cheat rollout；批次更多类型/比例要求亦是高级要求。

这些都要阅读已有证据、计算可计算量并保留建议及覆盖限制，但不因未达到其余高级要求默认拒收。若同一事实已独立违反L0（如实际泄漏、坏评分、假候选）或上列延续项目必需，按对应来源阻断，不能以高级标签掩盖。没有诱导rollout不能认证完整L2，也不新开实验。父项只汇总当前必需事实，不传播未校验的旧FAIL或其余高级建议。

旧固定两模型/最高推理档、两条各10h/7h、八字段/四hash和特定目录不恢复；G03的既有随机校准次数与正式全seed不因此取消，不能挑轮或伪造。无历史豁免意味着统一执行当前规范与明确延续要求，不再选择旧批免责。

## 静态、平台与暂停口径

provider=unknown只表示目标平台未指定，不单独阻断静态审阅；平台核验实际内核/隔离/镜像size/启动/12h稳定性。已有真实当前故障仍据控制点报告，不把未知当故障，也不把静态成立写成实机通过。运行阶段所用发布镜像及实际推送/拉取由平台完成核验；源码阶段不向专家索取内网tag、推送证明、到卡探针或新平台证明。

“一小时超时无分直接不通过”继续暂缓。scored_required等旧参数即使保留解析兼容，也只作已有运行观察，不能单凭缺分生成FAIL、材料缺口或补跑义务。无分不证明Verifier；当前选中坏reward原生解析失败、确定入口/评分缺陷、错候选等独立问题仍查。NOP不恢复。

## 判定与返修

最终只有通过/不通过。默认必需条件均已在本次静态/已交证据范围审完且无实质未满足则通过；有当前必需缺陷则不通过，写具体证据、影响、最小动作与作者/平台责任。内部工具/底稿/未读完导致检查不能收尾时仍不宣称通过，明确“质检未完成”及质检方动作，不退成专家缺陷。允许的动态未验证、高级建议、unknown或单纯一小时无分不单独使题不通过。

90编号及当前映射见[覆盖表](standard-coverage.md)。同根因只整改一次，父项只聚合当前blocking事实；旧状态保留追溯，不参与当前总判。

## 固定finding规则枚举

checks[].findings只填rule、reason、remediation、evidence、responsibility（author/platform/coordination）；等级和blocking由可信脚本按下表算，Agent不得任填level或decision。内部读取/缺已有资料/工具问题走inspection issue，不包装成专家真实finding。

| rule枚举 | 等级 | 当前适用事实 |
|---|---|---|
| harbor_format | L0 | 真实Harbor格式/有效配置/入口。 |
| oracle | L0 | 规范Oracle可调用及生成正常提交物。 |
| dependency_lock | L0 | 必要依赖固定预装及适用lockfile。 |
| reward_protocol | L0 | 唯一正式reward、JSON主reward及有效数值。 |
| hard_gate | L0 | 候选违规拒绝、actionable诊断及−10。 |
| task_contract | L0 | 公开合法方案与真实限制/目标/指标一致。 |
| artifact_binding | L0 | 当前候选/读取/指标/分数/归档真实对应，实际伪造不能映射高级建议。 |
| public_dev | L0 | 承诺公开Dev与工具真实可用。 |
| private_boundary | L0 | 私有材料/Reference不可见与冻结边界，真实泄漏/作弊不降级。 |
| resource_limit | L0 | 当前资源上限/最大合法提交/Dev2h的具体不满足。 |
| normalization | L0 | 实际公式、方向、Starter0/上界1与正确B/U。 |
| solver_turns | L0 | 指定自动交卷/超时退出主Agent至少51响应。 |
| solvability | L0 | 任务可解且可提升的真实证据，不恢复1h无分退题门。 |
| baseline_health | L0 | 非法Starter；五维证据确证明显不合理、故障、不公平或假记录的正式对照，不要求SOTA。 |
| runtime_failure | L0 | 当前确定准备/执行/评分故障或实际操纵，具体影响与责任。 |
| data_assets | L0 | 必需实体资产缺失/损坏。 |
| image_size | L0 | 仅有可信已有实际size证明超过50G；无size用platform_scope。 |
| runtime_stability | L0 | 已有正常非破坏性执行确证不满足12h环境要求；无实测用platform_scope。 |
| collection_diversity | L0 | 仅给定题目集合的至少五类覆盖，不套每题。 |
| method_space | L1；项目必需 | 既有G01真实可执行的方法空间，纯固定任务字面量调参不能表达方法。 |
| constraint_enforcement | L1 | 全部文字禁令可执行的高级覆盖。 |
| score_stability | L1 | 重复评测稳定性及calibration.json形式。 |
| shortcut_resistance | L1 | 可证明捷径/平凡满分/理论评分漏洞，独立真实L0暴露另归L0。 |
| reference_calibration | L2；项目必需 | 既有G03正式全seed配对、随机≥3次、Baseline样本3σ及Reference[.15,.8]；不扩展5σ/headroom硬门。 |
| research_iteration | L2 | 实质多方案、反馈复测、早饱和。 |
| adversarial_rollout | L2 | 计时回放/evaltool推断/诱导run的高级证据；真实作弊另归L0。 |
| platform_scope | scope | unknown、未测平台能力/12h/实际size与动态范围。 |
| legacy_schema | scope | 旧固定字段/hash/目录/模型等无当前默认依据。 |
| third_party_source | scope；平台必需 | 延续B-C03官方依赖源、B-C04实际npm指定bnpm；已有批准替代源可接受。 |
| research_duration | scope | 旧固定两轨10h/7h研究时长。 |

L0及明确延续的项目/平台必需具证据的当前缺陷阻断；可信脚本的PROJECT_REQUIRED为method_space、reference_calibration、third_party_source，等级标签不改写。其余L1/L2/scope为非阻断记录；仍需完成全部阅读和90行。精确ID与路由数据为[current-check-map.json](current-check-map.json)，可读表见[standard-coverage.md](standard-coverage.md)，同源生成。
