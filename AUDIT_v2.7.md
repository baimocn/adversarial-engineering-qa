# v2.7 当前标准重构审计（2026-11-14）

## 目标

按「有冲突的以最新标准为准」重构 skill：以群聊最新官方包和平台最新反馈报告为有效规则，旧 0.3.10/V4/豁免口径退出当前 gate。

## 权威来源

| 层级 | 来源 | 结论 |
|---|---|---|
| 规则底座 | `autoresearch-unified-qa-v0.5.0-current.1_20261107.zip` | 群聊 11-07 最新官方 skill；sha256 `5359339439dba1d62211e7ff1be125f0ee505c26c3059b2378a4bbcb92cb6698`；message `om_x100b61df8b04fca8c4789cf0ce43750` |
| 覆盖口径 | 飞书 2768 四轮报告 + 最终 PASS | `0.5.6-current.1`，`implementation_patch=read-recovery-fix-20261113-v1`，90 checks / 50 evaluated，最终 PASS 对应 v30 包 |
| 历史材料 | V4 教程、0.3.10 豁免清单、格式前检 v1.2.1 | 仅归档/参考，不进入当前 gate |

## 冲突裁决

| 冲突 | 旧口径 | 当前生效 | 证据 |
|---|---|---|---|
| hard gate | `-1` | `-10` | 0.5.0 `current-standard-policy.md:13`；0.5.6 report/grader |
| docker_image | V4/前检示例允许或要求 | 专家源 task.toml 不硬编码；Dockerfile/context + 平台镜像配置 | 11-07 返修指南；Harbor 1074 复盘；0.5.6 overlay |
| 最终结论 | PASS_WITH_WAIVERS / INCOMPLETE / PASS_WITH_OPEN | 外部二态 PASS/FAIL；内部不完整记 QA_NOT_FINISHED | 0.5.0 当前标准；Skill修改清单 |
| NOP | 每次返修补同 trial NOP | NOP 不恢复 | 0.5.0 `current-standard-checks.md:3` |
| 两轨/八字段/10h/四项指纹 | V4 恢复为硬门 | 不恢复；G03 全 seed 配对仍保留 | 0.5.0 `current-standard-policy.md:35` |
| 检查数 | 0.3.10 21 项 | 0.5.0 90 项 / 0.5.6 90 checks、50 evaluated | standard-coverage / report.json |
| best_method adapter | 旧 `weights_only=False` 历史 adapter | 恢复 Starter `weights_only=True` 冻结 adapter；同步哈希与验证范围 | 0.5.6 H04 报告与最终 PASS |

## 重构内容

1. `config/rule_versions.json`
   - 定义 `legacy-0.3.10-v4`、`official-0.5.0-current.1`、`platform-0.5.6-current.1-report`、`current-20261114` 四层。
   - 当前 profile 明确继承、supersedes 与 conflict_resolution。
2. `scripts/current_standard_gate.py`
   - 单包机械门禁，二态 PASS/FAIL。
   - 覆盖：唯一 task.toml、无 expert docker_image、separate/artifacts、单一 reward、`-10` hard gate、可信故障无分、公开合同 nonlocal/staged 白名单、guard 一致性、Oracle source/artifact handoff、best_method 冻结 adapter、G03 source binding、版本冲突裁决、platform_scope 声明。
3. `scripts/verdict.py`
   - 外部二态 PASS/FAIL；内部 open/unknown 记 `QA_NOT_FINISHED`。
   - `--legacy-incomplete` / `--non-strict` 仅用于旧编排兼容，不作为当前作者结论。
4. `scripts/strict_verify.py`
   - 增加 `--legacy-incomplete` 透传；默认使用当前标准 verdict。
5. `scripts/check_autoresearch_integration.py`
   - 修复直接执行时 `validate_review` 导入路径；子进程 help probe 显式 UTF-8 解码。
6. `tests/`
   - 新增 `test_current_standard_gate.py`：v30 good 基线 + 9 个 bad/good 消融。
   - 更新 `test_verdict.py`、`test_strict_verify.py`：二态与 QA_NOT_FINISHED，保留 legacy 兼容测试。
   - 修复 `test_scripts.py` 对 `None` stdout/stderr 的拼接与 UTF-8 解码。
7. `README.md` / `SKILL.md`
   - 版本升级到 v2.7.0；给出当前入口和 legacy 边界。

## 核心机制消融验证

| 规则 | bad 消融 | good 基线 | 结果 |
|---|---|---|---|
| hard gate `-10` | `HARD_GATE=-1.0` | v30 `HARD_GATE=-10.0` | bad FAIL / good PASS |
| reward 二选一 | 增加 `reward.txt` 发布函数 | 仅 `reward.json`，显式清理旧 reward | bad FAIL / good PASS |
| docker_image | task.toml 新增 active docker_image | 无 active docker_image | bad FAIL / good PASS |
| nonlocal 披露 | instruction 删除全部 nonlocal 文本 | 四处公开合同披露 | bad FAIL / good PASS |
| staged 白名单 | protocol 放宽为 numpy | exact whitelist | bad FAIL / good PASS |
| Oracle H02 | solve.sh 去掉 assembler | 训练前 assemble + SOLUTION_DIR/run.sh | bad FAIL / good PASS |
| best_method H04 | 复制 v29 `weights_only=False` adapter | v30 Starter frozen adapter | bad FAIL / good PASS |
| source binding | selection data.py hash 改为 0*64 | 真实 sha256 同步 | bad FAIL / good PASS |
| G03 provenance | 追加旧 blanket claim | role-specific binding | bad FAIL / good PASS |

## 全量验证

命令：

```bash
python -I -m unittest discover -s tests -p 'test_*.py'
```

结果：`Ran 141 tests`，`OK (skipped=1)`。跳过项为原始官方分发包不在本机，非失败。

对已获平台 PASS 的 v30 包：

```bash
python -I scripts/current_standard_gate.py --root <v30_tree> --out current_standard_gate.json
```

结果：`decision=PASS`，`pass=22`，`fail=0`。

## 边界

- 当前 gate 是静态源码/证据门禁，不执行 Docker/Harbor/Hidden，不声称平台实跑。
- 0.5.0 官方 90 项模板和 vendored 模块未全部改写为本地 gate；本重构先用版本目录、二态 verdict 和当前报告已证实的机械项解决冲突，避免把旧 prose 机械回灌。
- 平台后续若发布 0.5.7+，应先更新 `rule_versions.json` 的 profile 与冲突裁决，再改 `current_standard_gate.py`；不得直接改脚本硬编码绕过版本轴。
