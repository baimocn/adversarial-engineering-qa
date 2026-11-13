# 2+1 低幻觉评审协议（strict-qa，v2.6）

适用对象：方法创新性、轨迹真实性、题面是否“讲清楚”——没有客观 oracle、只能靠模型判断的项。

目标：**模型只做执行者，结论由固定规则算。** 两个模型一致才过；不一致交裁决；裁决也拿不出可核证据才交人。

## 1. 两评审

- 两个**不同家族**的模型，隔离上下文，同一证据包、同一问题。
- 每条输出：

```json
{
  "schema": "judgment/1",
  "item_id": "method_novelty",
  "model": "provider/model",
  "verdict": "pass | fail | unknown",
  "confidence": 80,
  "evidence": [
    {"path": "optimization_evidence/comparison_summary.json", "pointer": "/statistics/delta"},
    {"path": "instruction.md", "line": 42, "quote": "原文片段"}
  ],
  "rationale": "一句话"
}
```

证据只接受三种：`line + quote`、`pointer`（JSON Pointer）、`value`（文件内字符串）。`panel_lib.py` 先核证据是否存在、是否支持结论；核不过的票作废。

## 2. 一致 / 不一致

```bash
python scripts/judge_panel.py compare --root <task-root> \
  --judgment-a a.json --judgment-b b.json \
  [--adjudication adj.json] --out panel.json
```

| 情况 | 结果 |
|---|---|
| 两票 verdict 相同、证据都有效、且不是 unknown | `judged_agree` → 按该 verdict |
| 两票不同，或任一方证据无效 | 需要裁决 |
| 提供了有效裁决 | `judged_adjudicated` → 按裁决 verdict |
| 裁决缺失/无效/verdict=unknown | `human_required` → unknown |

裁决格式：

```json
{
  "schema": "adjudication/1",
  "item_id": "method_novelty",
  "model": "provider/model",
  "winner": "A | B",
  "verdict": "pass | fail | unknown",
  "evidence": [{"path": "...", "line": 1, "quote": "..."}],
  "reason": "为什么选 A/B，必须引用原文"
}
```

裁决必须选边，且 verdict 必须等于被选方的 verdict；否则无效。

## 3. 批量

目录布局：

```
<ws>/judgments/<item_id>/a.json
<ws>/judgments/<item_id>/b.json
<ws>/judgments/<item_id>/adjudication.json   # 可选
```

```bash
python scripts/compare_judgments.py --root <task-root> \
  --dir <ws>/judgments --out <ws>/gates/panel.json
```

`qa.py` 的 `panel` 阶段自动调用；没有 `judgments/` 时跳过。

## 4. 拆题

拆题由编排模型在启动时用 `ListModels` 问人选“最强模型”，人选写入 `run-config.json`。
拆题产物：

```json
{
  "schema": "decomposition/1",
  "task_family": "harbor",
  "requirements": [{"id": "R1", "text": "...", "source": "instruction.md:42"}],
  "checks": [{
    "id": "C1",
    "requirement_id": "R1",
    "question": "是否拒绝 NPZ 容器？",
    "answer_space": ["pass", "fail", "unknown"],
    "verifier": {"kind": "command", "command": "python",
                 "args": ["-I", "probes/npz_candidate/probe.py"],
                 "assert": {"exit_code": 0}}
  }]
}
```

校验：

```bash
python scripts/validate_decomposition.py --spec decomposition.json \
  --root <task-root> --out validation.json
```

四条硬规则：有限答案（含 unknown）、可执行验证、需求溯源、每条需求至少一个检查。
不满足就退回重拆；拆好的缓存到 `criteria/decompositions/<题族>.json`，人工批一次后复用。

## 5. 总判

```bash
python scripts/verdict.py --results check-results.json --out verdict.json [--non-strict]
```

| 类别 | 含义 | strict 下 |
|---|---|---|
| `verified` | 脚本/CPU 检查 | pass/fail 直接生效 |
| `judged_agree` | 两评审一致 + 证据有效 | 按 verdict 生效 |
| `judged_adjudicated` | 裁决选边 + 证据有效 | 按裁决生效 |
| `human_required` | 裁决也拿不出证据 | INCOMPLETE |
| `unknown` | 没有可执行检查 | INCOMPLETE |

规则：任一 fail → FAIL；任一 open → INCOMPLETE；全 pass → PASS；空结果 → INCOMPLETE。
`--non-strict` 把 open 降为 `PASS_WITH_OPEN`，不用于送检。

## 6. 模型角色配置

`config/models.example.json` 只是示例；真实选择由编排模型在启动时问人，写入 `run-config.json`：

```json
{
  "decomposer": ["<provider/model>$max"],
  "judges": [["<provider/modelA>$max", "<provider/modelB>$max"]],
  "adjudicator": ["<provider/modelC>$max"],
  "executor": ["<provider/modelD>$high"]
}
```

要求：评审 A/B 不同家族；裁决模型不与 A/B 同家族；拆题用当前可选模型里能力最高的。
