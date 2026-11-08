# Baseline 合理性检查

总评：在已提供材料范围内合理。

角色：Starter=普通GCN+损坏标签交叉熵；正式Baseline=未经修改Starter三seed独立运行；主评分B=正式隐藏测试宏均值61.8833；额外sanity=干净训练标签oracle（上限锚点，不是替代Baseline）。

对照：同两图/划分/噪声标签、GCN骨干和Adam；B200步，R500步为披露的共同7200秒内日程变量。两者分别验证选点、独立重载；没有将公开Dev分数当隐藏TEST。

| 项 | 状态 | 主张 → 证据 → 比较结论 | 最小修复/复验 |
|---|---|---|---|
|B01|通过|Starter角色与来源见instruction §2、expert_annotation、GCN_Predictor；朴素GCN适用于带噪标签研究，无包内同预算强锚点证明其不具代表性。|无Baseline专项返修；保留原证据。|
|B02|通过|Base_Predictor实际backward/Adam更新；逐行读取12份training.jsonl，B每图200步/R500步，均epoch_budget_exhausted；B最佳8/39、7/4、6/5，后期val回落，没有只训练占位或错误加载证据。|无Baseline专项返修；保留原证据。|
|B03|通过|instruction §4与protocol_decisions允许共同7200秒内自选日程；两侧CPU；B约56–59秒/R426–494秒，重载日志另计后仍远低上限。日程差被披露，不宣称等成本单因素创新。|无Baseline专项返修；保留原证据。|
|B04|通过|config/gcn冻结lr0.01/wd0.0005，R沿用同Adam/骨干；验证集选点。历史失败开发三组完整保留，未发现B异常学习率或只挑失常配置。|无Baseline专项返修；保留原证据。|
|B05|通过|formal_test_scoring_declared三seed完整同集合逐项成对；setup_seed进入实际Python/numpy/torch。12个checkpoint哈希相异且逐一与artifact/训练结果/评分索引吻合，未将一个模型复制充独立训练。|无Baseline专项返修；保留原证据。|
|B06|通过|同协议Starter即正式B；初始公开Dev59.7与seed3000验证结果吻合。oracle75.1333使用干净train标签，属于不同信息条件上限，不能强迫其成为B。未提供额外随机锚点，不捏造分数。|无Baseline专项返修；保留原证据。|
|B07|通过|修复R的同类锚点只来自train noisy-label双路LP，损失和辅助对比变化在允许范围；同Frozen资产/指标，validation只选点，旧v7泄漏R明确失效并未混入正式六run。|无Baseline专项返修；保留原证据。|
|B08|通过|专家作业说明文档、训练证据说明及protocol_decisions披露来源、角色、200/500日程、全部seed及限制；无新增物理隔离或目标卡认证要求。|无Baseline专项返修；保留原证据。|



全部正式成对TEST：3000 B60.05/R70.25；3001 B62.6/R71.4；3002 B63/R69.95。

均值 B=61.8833333333 R=70.5333333333；样本σ_B=1.6002603955 σ_R=0.7653975002；Δ=8.65，Δ/σ_B=5.4053702913；U=75.1333归一化=0.6528318310，U100对照=0.2269348491。

关键红旗：未发现直接Baseline不公平红旗。U在结果后替换已披露，100预声明口径也达标，保留这一选择限制。

专家退回说明：Baseline专项无需替换SOTA或重训。整题当前Dev写路径权限、单轮时限实施与模型加载质量门问题见总报告，它们不被Baseline合理性覆盖。

边界：只读审源码、配置、逐epoch文本、模型文件大小/SHA与重载记录；未执行或导入提交代码，未反序列化权重，未独立复现。
