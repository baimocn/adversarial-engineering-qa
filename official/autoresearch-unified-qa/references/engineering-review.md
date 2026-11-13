# 当前工程六组

0.5.0-current.1。六组是现有编号共享事实，不新增检查或完整动态认证。只按[当前标准](current-standard-policy.md)判断，关键词、广域except、镜像名、单一timeout不能自动判缺陷。

| 组 | 主责 | 必审内容 |
|---|---|---|
| score_paths | H04、QA06/09、F07 | 正常候选、候选违规、可信评分/资产故障、外层中断四路径。 |
| timeout_budget | H04、QA15 | 有效截止、全部实际计时阶段、共享预算与收尾。 |
| resource_alignment | QA15、H03、F06 | Work/Judge各自实际需求、配置、依赖与合法方法。 |
| controls_logs | QA05/20、H03 | 必要控制与fallback、已交日志首因/恢复/影响。 |
| score_scope | H04、CS04 | 本次有效分数、Verifier验证及正式采用范围。 |
| delivery_lineage | QA21、T01/T02 | 当前选定Trial/候选/reward/归档/QC真实身份。 |

## score_paths：四条结果路径

正常候选须规定评测完成并产生真实主分。候选违规须证明确由候选触发，hard gate−10及可执行诊断；不能把可信grader同名异常误罚候选。可信评分器、依赖/私有资产/平台故障须错误状态或无分，失败哨兵与正常reward隔离，不能伪装正常0分或其他完成成绩。环境故障协议的−10与候选惩罚语义不同；负数本身不证明训练reward被污染，读真实状态及消费规则。

中断路径核对signal/非零退出/set-e、子进程终止、清理和结果收集，不能消费旧结果或预写占位。临时中间文件不等于正式成绩。当前有分不证明所有支路正确；确定支路缺陷也不自动使正常已完成成绩无效。只依假想可能性不能宣布全部历史数据无效。

## timeout_budget：有效预算

读实际配置/override/multiplier和计时范围，区分Agent、Dev一次整链、单次Verifier、生命周期截止。按真实串并行/共享deadline覆盖初始化、数据加载、候选计算、seed/重试、kill/grace、清理与提交；不机械相加各timeout最大值，不固定+60秒或Runner案例1800秒。需要指出可触发路径及对正常合法提交的影响，单纯内外等长不足判失败。

## resource_alignment：角色与镜像

Work/Judge分别审，单次候选不用GPU不等于所有合法方法CPU-only。GPU≤8张H20/L20、CPU≤64，Dev完整反馈≤2h及最大合法输入可运行；延续正式单seed≤2h/同候选多seed累计≤8h，按真实并发/共享deadline核算。必要依赖固定预装、实际可用，官方源/npm指定bnpm或已批准替代沿实际安装链核对；CPU误申GPU/无效配置保留具体问题。

50G为当前镜像规范上限，大多数10G以下为建议。仅实际可信size明确超限才判当前规范未满足；源码未给内网镜像size只记平台待验证，不要求专家补内网证明。无必要重型CUDA base按依赖/角色给高优精简建议，不凭镜像名/体积印象判错。

## controls_logs：实际控制

读完所有已交日志，追首因并区分已恢复、无关warning与必要控制失效。Landlock/bwrap/seccomp/设备权限按实际平台支持和fallback核对，公开Dev须能用。chmod失败不证明Agent用了GPU，软报错/fallback不证明约束有效。unknown不单独失败；平台核验能力，不把未测/未交平台日志推给专家。

## score_scope：分数与覆盖

核对最终候选→Verifier输入→原始指标→权威reward。当前选中坏reward解析失败是具体H04缺陷，历史坏记录不误作当前FAIL。已有有效分数可反证本次未评分，诊断标签/正式scope限制与原始完成事实分别写。

一小时超时无分直接退题继续暂停，scored_required旧参数仅观察；缺分不新增FAIL、材料缺口或补跑，无分也不证明Verifier正常。除明确延续的项目G01/G03与平台必需外，其余L1/L2默认建议，不靠新增高级动态证据义务退题。

## delivery_lineage：身份

按当前明确选定正式Trial核对题号/包/候选/分数/QC/归档；不能按最新时间自动选正式记录，不能把hash用途不同当冲突。已有外部表错映射由交付协调处理；没给可选外部台账只记范围。真实错题/错候选/伪造绑定仍按L0处理。

## 内部底稿

使用真实模板填写六组summary/evidence/details及score_paths四分支，发现有具体证据/影响/动作/责任。只读审查不要求新运行/receipt/探针。L0与延续项目/平台阻断事实、其余L1/L2/旧门建议、平台未验证、内部未读/工具问题分开，最终二值结论见[统一输出](unified-report.md)。
