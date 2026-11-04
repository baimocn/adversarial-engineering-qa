# 并行分派模板（可直接复制）

配合 `SKILL.md` §2.6 使用。所有占位符用 `<...>` 标出，派发前必须逐项填实，不许留空。

---

## 一、编排者开工清单

按顺序执行，**不要跳步**（跳过 ② 就会变成「模型临时决定看哪些文件」，覆盖范围不可复现）：

```
[ ] ① collect_evidence.py 建索引
[ ] ② plan_gate_dispatch.py 出 plan.json
[ ] ③ 记录 source_digest（开工身份）
[ ] ④ 按 parallel_group 派发（同组并发，组号小的先）
[ ] ⑤ 收结果 → merge_gate_results.py
[ ] ⑥ 抽检 ≥2 条 blocking finding
[ ] ⑦ 重算 source_digest，与 ③ 比对
[ ] ⑧ 出报告
```

③ 和 ⑦ 不一致 ⇒ 全部单元结果作废，重跑。**没有例外。**

---

## 二、执行者提示模板

> 复制下面整段，替换 `<...>`。**不要精简、不要改写 acceptance。**

```
你是本次质检的执行者，只负责一个单元。除这个单元外的任何内容都不属于你的职责。

## 你的单元
- unit_id: <B.shard-0001>
- gate: <B>
- kind: <code_review>

## 输入范围（只准看这些）
- shard 清单: <outdir>/evidence-index/shards/<shard-0001>.json
- 文件数: <50>
- 共享只读工作区: <task-dir>（不得修改其中任何文件）

## 接受标准（逐条满足，缺一条判 INCOMPLETE）
<把 plan.units[i].acceptance 原样贴在这里，不许改写>

## 输出
- 路径: <outdir>/gates/<B.shard-0001>.json
- schema:
{
  "unit_id": "<B.shard-0001>",
  "gate": "<B>",
  "status": "PASS | FAIL | INCOMPLETE | not_applicable",
  "findings": [
    {"severity": "blocking | major | minor | info",
     "summary": "<一句话说清是什么缺陷>",
     "evidence": "<file:line + 证据类型（静态读码/脚本输出/运行结果）>"}
  ],
  "cross_refs": ["<跨片疑点，指向哪个 shard 的哪个文件>"],
  "reason": "<status 不是 PASS 时必须写清楚为什么>"
}

## 禁止
- 不得把「属于其他 shard」当作不看的理由（跨片疑点写 cross_refs）
- 不得给自己加豁免、不得把 blocking 写成 major
- 不得修改共享工作区里的任何文件
- 不得声称跑过你没真跑的命令
```

---

## 三、编排者抽检模板

抽检不是抽查格式，是**抽查事实**。每条至少做一件事：

```
finding: <执行者报的原文>
声称证据: <file:line>

抽检动作（三选一，必须真做）：
  A. 打开该 file:line，确认代码确实如所述
  B. 复跑该脚本，确认 rc 与输出与执行者一致
  C. 构造最小反例，确认该缺陷可复现

抽检结论: 成立 / 不成立
若不成立 ⇒ 该执行者的整份结果作废（不是只删这一条）。
```

**为什么整份作废**：一条证据造假说明它的判断链不可信，其余条目无法单独取信。

---

## 四、合并后必看的三个字段

```json
{
  "decision": "...",      // 只认这个，不认任何执行者的自述
  "missing": [...],       // 非空 ⇒ INCOMPLETE，先把漏跑的单元补齐
  "errors": [...]         // 非空 ⇒ 至少有一条单元结果不可采信
}
```

`decision` 为 PASS 但 `errors` 非空 ⇒ **不许交**。这说明合并层发现过矛盾（如 blocking 报 PASS）。
