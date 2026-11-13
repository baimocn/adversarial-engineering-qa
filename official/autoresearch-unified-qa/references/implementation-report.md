# 当前内部审阅结构

唯一活动底稿由audit_current.py准备，形状为checks[90]、engineering、delivery_contract、coverage；以本次真实模板为准。本文件不要求专家填内部字段，旧组件schema不增加当前必交材料。

每个check有唯一id、具体审阅summary、真实evidence及findings；findings说明当前规则依据、影响、最小动作和责任，等级/blocking由可信脚本推导。method_space、reference_calibration、third_party_source虽非算法L0，作为延续项目/平台必需参与总判；其余L1/L2与无当前来源旧要求记建议，父项不传播未核验旧FAIL。review_completed与最终二值结论分开，内部错误owner=inspection不发成专家返修。

证据路径相对source_root，落真实可读材料内；有行号/JSON字段时位置须存在且支持语义，不拿存在证明真实性。接受大JSON/JSONL、等价载体及已有会话，但必须实际完整读。自动清单和关键词只做观察，不能自动定违规。

engineering六组见[工程规范](engineering-review.md)，delivery_contract六组见[合同规范](delivery-contract-review.md)，90项与非阻断边界见[覆盖表](standard-coverage.md)。coverage保留应读来源、真实范围、未跑/平台未知与内部障碍，不伪造完成标志。
