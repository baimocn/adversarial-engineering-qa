# 当前交付合同六组

0.5.0-current.1。验收唯一依据为[当前标准](current-standard-policy.md)，来源revision2189及返修意见revision116；不再按831/new1104/人工等级分流。内部worksheet键delivery_contract，可信模块与产物core存储名delivery_contract_review；以真实模板为准。

| 内部组（保留存储名） | 主责 | 当前职责 |
|---|---|---|
| task_contract | QA11 | 目标指标、可改范围、提交结构、实际限制与完成条件。 |
| normalization_anchors | QA02 | Starter0/上界1、方向、实际B/U、正式split/协议及硬件敏感性。 |
| image_dependency_fit | QA15 | Work/Judge真实依赖与资源、合理镜像；50G真实size由平台核验。 |
| infra_capabilities | H03 | 必要内核/隔离依赖、目标平台及fallback，公开Dev可用性。 |
| batch_acceptance | H04 | 已交运行事实、真实候选/评分、无分覆盖及当前错误。 |
| new_intake_protocol | H04 | 名称仅为内部存储兼容；下列四项对所有题默认必查。 |

## 合同与锚点

从实际guard/固定训练器/评分调用反查公开说明，重点执行子限、AST/表达式、import/from import/nonlocal、graph/tensor shape、可交文件和静态Python规则。只报告会影响正常合法方案的差异，不能泛泛要求题面穷举全部内部细节。

沿原始x→实际公式→reward读真实B/U与来源；线性映射(x−B)/(U−B)及方向等价式静态代入0/1。不同split不直接比较，设计常数不冒充另一split重测；固定墙钟/性能锚点目标校准或可比依据，固定steps accuracy不因换卡必重测。只指向受影响结果，不一刀切重跑。

## 所有题统一四项协议

1. Oracle规范入口solution/solve.sh（容器侧/solution/solve.sh），生成正常提交物后独立评分；reference.py实现名/语言不限，不能直接写reward。
2. 核心与影响可复现的必要依赖固定预装，有适用lockfile/锁定材料；不使用latest/浮动分支冒充可复现，不要求专家内网tag。
3. 同次正式reward在json/txt中选一种；JSON有有限主reward，多指标主分明确。不拼不同Trial/seed制造双文件冲突。
4. 候选hard gate拒绝、可执行诊断与−10；先证明是候选违约，不把可信故障当正常候选分数。

真实模板保留new_intake_protocol详情oracle_entry/dependency_lock/formal_reward/gate_penalty；可依据材料记录entry/implementation_paths、locked、output_files/json_main_key及value等内部事实，不给专家新增同名schema。其他详情也按真实模板完整填写；工程/合同内部组不复制checks[].findings规则对象，保留各自模块事实结构。高级附加level_assurance可提供已有证据，模块只列assurance_notes并固定不认证完整等级。

## 运行、能力与高级建议

provider unknown只是平台未指定，不阻断静态；Landlock/bwrap等必要能力及fallback按真实底座，不能靠静态缺证要求专家新smoke。已有当前不可用工具/依赖/约束及正常评分失败仍查，缺运行与已证明失败分开。

一小时超时无分直接退题继续暂停。旧scored_required等参数不选标准，只记已有运行覆盖；无分不证明Verifier正常，也不因此新退题/补跑。当前选中坏reward的原生解析失败是H04真实缺陷，历史坏reward不误作当前；负分、错误状态与平台消费要结合读。

L1公开信息捷径/平凡满分/评分漏洞、L2计时回放/evaltool反推/诱导cheat轨迹都读已有证据、记录建议。只有静态facet名称不能证明动态验证，无动态材料不能认证完整L2；本版不人工选等级，也不因缺高级证据默认拒收。若已独立构成L0私有暴露/真实作弊/错评分则仍按L0阻断。原A六类范围不反写，也不能用其排除主题取消其他L0缺陷。
