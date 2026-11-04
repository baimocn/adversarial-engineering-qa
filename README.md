# adversarial-engineering-qa

对代码库、Harbor/AutoResearch 题包及软件交付物做严格工程化质检、独立复检、对抗审查、
FAIL 复核和提交前验收的 Skill。真实分级调用官方 AutoResearch/Baseline Skills，
完整保留原 v4 六道闸门与交付物，并叠加双门禁、Gate C 执行层门禁、行为覆盖、
有效反例、跨文件契约及机器可校验报告。

**当前版本：v2.4（2026-11-05）**

## 结构

```
SKILL.md            Skill 主文档（流程、门禁纪律、判定规则）
scripts/            确定性脚本：证据索引、Gate C、平台硬规则、覆盖率、合并、校验器
references/         规则契约：review 契约、AutoResearch 分级调用、v4 原文、判据反推
official/           内嵌只读官方副本（task-qa / baseline-quality / supplement-platform-audit）
assets/             review.json 模板
tests/              unittest 自测（75 用例）
```

## 快速开始

```bash
# 平台源包硬规则（B-C01–B-C04，2026-11 新规）
python scripts/check_platform_rules.py --root <提交包根> --out <outdir>/platform-rules.json

# 全流水线（状态机：evidence → plan → worklist → scripts → platform → check → merge → official → review → integrate）
python scripts/qa.py init    --task-dir <harbor_task> --zip <submission.zip> --workspace <ws>
python scripts/qa.py run     --workspace <ws>
python scripts/qa.py status  --workspace <ws>

# 机器可校验报告
python scripts/validate_review.py --review <outdir>/adversarial_review.json

# 自测
python -m unittest discover -s tests
```

## 版本里程碑

| 版本 | 实质改动 |
|---|---|
| v2.4 | 2026-11 平台新规：B-C01–B-C04 机械核对（docker_image 判据翻转）、Gate C 追加 6 条执行环境类规则、报告 schema 1.1（责任归属/证据三态/三判断分离）、内嵌 supplement-platform-audit、错误类台账扩至 E1–E25 |
| v2.3 | 接入官方标准层（QA01–QA21 + Harbor 六项），qa.py 增加 official/review/integrate |
| v2.2 | 四类强制槽位 worklist + 机器判覆盖率 |
| v2.1 | 并行分派协议（主模型 = 编排者） |
| v2.0 | Gate C 执行层门禁（诚实候选冒烟） |

完整变更记录与反推依据见 `SKILL.md` 与 `references/platform-criteria-inference.md`。
