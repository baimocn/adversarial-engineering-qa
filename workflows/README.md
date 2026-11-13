# 编排模型与多题 workflow（strict-qa）

## 先说一个宿主限制

ZCode 的 `agent(name, {model})` 里的 model 是**编译期字面量**，不能在运行时用
`args.judgeA` 动态指定。所以“编排模型问人 → 人选模型”这一步必须由**主会话的编排模型**
完成，而不是写死在一个 workflow 里。两种落地方式：

1. **主会话直接派发**（推荐）：编排模型用 `ListModels` 列出候选，问人选择；
   然后按 `references/strict-panel-prompts.md` 用 Agent 工具逐个派发，模型参数由人选决定。
2. **生成一次性 workflow**：人选完后，把选定的模型字面量写进
   `workflows/strict_single.dwf.ts` 的 `MODELS` 常量，再提交运行。适合同一组模型跑多题。

Python 脚本（`judge_panel.py`、`compare_judgments.py`、`validate_decomposition.py`、
`run_decomposition_checks.py`、`verdict.py`）是确定性的，和宿主无关；workflow 只负责
“派发 + 隔离上下文 + 收集”。

## 启动时问人（编排模型）

```
请选择本次质检使用的模型：
1. 拆题（建议能力最高）
2. 评审 A
3. 评审 B（必须与 A 不同家族）
4. 裁决（建议第三家族）
5. 执行者（找证据/低风险任务，可选）
```

`ListModels` 的输出作为选项；人选写入 `run-config.json`，并由
`scripts/validate_run_config.py` 校验：

```bash
python scripts/validate_run_config.py --config run-config.json --out config-validation.json
```

校验不过就不启动；不允许“同一家族跑两次”冒充双评审。

## 单题 workflow（阶段）

```
0. 校验 run-config
1. 拆题：拆题模型写 decomposition.json
2. 校验拆题：validate_decomposition.py（四条硬规则）
3. CPU 执行：run_decomposition_checks.py（命令/文件/JSON/正则/哈希）
4. 主观项：评审 A、B 隔离各答一次，各写 judgments/<item>/{a,b}.json
5. 比对：compare_judgments.py
   - judged_agree / judged_adjudicated → 进入总判
   - human_required → 裁决模型写 adjudication.json，再比对；仍无效则保留 open
6. 总判：verdict.py（strict）
7. 报告：verdict.json + 证据索引 + 未覆盖清单
```

关键纪律：

- 评审 A/B 的 prompt 不包含对方结论；模型不同家族。
- 每条 judgment 必须带 `path:line+quote` 或 JSON pointer；`panel_lib.py` 先核证据。
- 裁决必须选 A 或 B，并引用原文；选不出就 `unknown`。
- `human_required` 不改写成 pass；strict 下就是 INCOMPLETE。

## 多题 workflow

```
tasks = args.tasks[]   # 每个: taskRoot, packageZip?, workDir
for each task (bounded concurrency):
    单题 workflow（同一份 run-config）
汇总：
    verdict 表：PASS / FAIL / INCOMPLETE / human_required
    同一 criterion 跨题命中次数
    哪些题是 notCovered
```

多题共用同一份 `run-config.json` 和同一份拆题缓存（按题族）；每个题独立 workDir，
互不共享上下文。任一题 FAIL 不阻断其他题；批量报告分别列出。

## 产物

```
<workDir>/
  run-config.json
  decomposition.json
  validation.json
  check-results.json
  judgments/<item>/{a,b,adjudication}.json
  panel.json
  verdict.json
  report.md
```

## 官方层（0.3.10 / 0.5.0）

`strict_verify.py --package-zip <zip>` 会同时跑两层官方内核：

- **0.3.10**：`qa_official.py run` 生成模板 → `qa_official.py review` 本地预填 →
  把预填底稿复制到 out-dir 外，再 `qa_official.py run --standard-review` 让官方
  审计器出正式 decision。仍为 `ERROR/REVIEW_NOT_FINISHED` 时，在 strict verdict 里
  记 `official-0.3.10:auditor = human_required`。
- **0.5.0**：`qa_unified.py prepare` 生成 90 项模板；若
  `<ws>/official-0.5.0/review.json` 已填，`qa_unified.py review` 出正式 decision；
  未填则记 `official-0.5.0:auditor = human_required`。

两层的详细 checks 都保留在 `<ws>/official/` 与 `<ws>/official-0.5.0/` 作为证据；
strict verdict 只吃两层的**聚合 decision**，不把 0.3.10 的本地预填 fail 当成官方 fail
（旧版规则的布局假设可能与当前题包不一致）。

## 和现有 qa.py 的关系

- `qa.py` 仍负责证据索引、worklist、Gate A/B/C、官方层；
- `panel` 阶段读 `judgments/`，`verdict` 阶段把 panel + 对抗层 + 官方层合成五档总判；
- 本目录的 workflow 是“编排层”，不替代 `qa.py` 的确定性检查。
