# adversarial-engineering-qa

一套对 Harbor/AutoResearch 题包做质检的 skill。它把"让模型读代码找问题"变成一条流水线，脚本先跑机械检查，agent 分片读热点，红队独立攻击，最后合并出一份机器可校验的报告。

这个 skill 从三十多轮真实质检里长出来。每一版背后都有一次被打脸。第二轮质检放过了 1841 的 5 项清单失配，交叉审计才发现检查器把 revision_log 里的历史哈希当成了当前声明；2604 的 reward 双写藏在变量赋值加循环镜像里，行级扫描看不见，逼出了 D-C03 的强特征。规则也反复翻烧饼，`docker_image` 从要求到禁止再到"旧规则建议"，B-C01/B-C02 降了三次级。如果平台规则变了，先看 `references/platform-criteria-inference.md` 里的反转记录，再决定要不要改判据。

> **征集失败报告**。仓库开了 [field-reports/](field-reports/) 目录，专门收你用这套 skill 质检后得到的失败或存疑报告。历次校准全都来自真实误报，我们自己的包越跑越"顺"，反而难再撞出新的判据缺口；你的报告就是下一个回归用例的来源。提交方式见该目录的 README，脱敏后一报告一文件即可。

**当前版本 v2.5.1（2026-11-07）**

## 它解决什么问题

质检题包时最容易出三类事故，skill 各有一层防线。

1. **串行读代码丢重点**。一个模型通读 140 个文件，实测要小时级，而且读完也说不出哪里重点看过。v2.1 把主模型退到编排位，`plan_gate_dispatch.py` 按证据索引切分片，agent 认领执行，`merge_gate_results.py` 做合并。缺任何一个单元，整题判 INCOMPLETE。
2. **覆盖率自报不可信**。agent 说"我读完了"不算数。v2.2 用 `build_review_worklist.py` 强制四类槽位（文件处置、声明绑定、热点问答、副本对账），`validate_coverage.py` 机器判覆盖率，不满 100% 的单元即使自报 PASS 也降为 INCOMPLETE。副本对账这一槽在 0340 上是 QA05 的唯一发现路径，140 个文件里圈出 3 组差异文件。
3. **只有对抗层看不见官方判据**。v2.3 之前流水线没有官方标准层，AutoRe1841"NOP 早于题包最后两次修改"这类问题，对抗层完全看不见。现在 `qa_official.py` 把 21 项 QA + Harbor 六项接进流水线。

## 两条流水线

**快速机械检查**，不需要 agent，几秒出结果。

```bash
# 平台源包硬规则 B-C01 至 B-C04
python scripts/check_platform_rules.py --root <提交包根> --out <outdir>/platform-rules.json

# 交付契约 D-C01 至 D-C04（reward 写入链 / 清单哈希复算 / 二选一 / Oracle 入口）
python scripts/check_delivery_contract.py --root <提交包根> --out <outdir>/delivery-contract.json

# 执行层门禁 Gate C-1（10 条静态规则：tensor_api_mismatch、return_arity_mismatch、
# landlock_dependency、home_writability、artifacts_handoff_mismatch 等）
python scripts/check_execution_path.py --root <harbor_task> --out <outdir>/execution-path.json

# 诚实候选冒烟（Gate C-2）
python scripts/check_honest_candidate.py --help
```

**完整七步流水线**，状态机支持断点续跑。

```bash
python scripts/qa.py init  --task-dir <harbor_task> --zip <submission.zip> --workspace <ws>
python scripts/qa.py run   --workspace <ws>   # 全量；或 --stage evidence|plan|worklist|scripts|platform|check|merge|official|review|integrate
python scripts/qa.py status --workspace <ws>
```

十阶段里 `platform` 一站会同时跑平台规则、交付契约、Gate C 三组脚本；`check/merge` 负责覆盖率校验与合并；`official/review/integrate` 出官方底稿和终稿。

**机器可校验报告**。

```bash
python scripts/validate_review.py --review <outdir>/adversarial_review.json
```

报告不是自由文本。schema 1.1 强制三判断分离（链路 / 成绩可信性 / 是否返修）、每条 finding 带责任归属（`responsible` / `action`）、平台检查项带证据三态。validator 会拒绝重复 JSON 键和凭空出现的 PASS。

**自测**。

```bash
python -m unittest discover -s tests   # 94 用例
```

## 判级纪律（最容易踩的坑）

- **blocking 不可豁免、不得静默降级 manual**。降级必须写明理由与证据范围。
- **不继承旧判级**。上一轮的 FAIL/PASS 只作待检声明，每条要用当前字节重新验证。我们见过修复报告声称"已修复"但字节没动的案例，也见过检查器自己误报把好包判死的案例，两个方向都会发生。
- **修复诚信和修复完整性是两回事**。第三波修复 35 条声明零造假，但五包仍全军覆没，因为修复只覆盖被点名的路径，没做相邻路径的封闭性验证。审修复时先问"这个修法堵住了所有入口吗"，再问"声明属实吗"。
- **可信侧故障不等于候选分数**。Verifier 自己的资产坏了、门禁自己崩了，不能记成候选 −10。2768 的私有资产共用 try/except、0340 的 hard_gate 无兜底崩溃，都是这条纪律的真实案例。

## 版本里程碑

| 版本 | 日期 | 实质改动 |
|---|---|---|
| v2.5.1 | 2026-11-07 | D-C03 三轮校准，变量赋值 + for-in 循环镜像的间接双写从行级扫描升级为强特征（成对赋值 / 双扩展循环 → needs_manual）；注释行与 re.compile 模式行不计入字面量；B-C03 范围分级（expert_evidence/ 证据侧非官方源 → needs_manual，environment//tests/ 下仍 blocking）。六修复版全量重跑无误报 |
| v2.5 | 2026-11-07 | unified-qa v0.5.0 接入，B-C01/B-C02 第三次反转降为旧规则建议；D-C03（正式 reward 二选一）、D-C04（Oracle 规范入口）机械化；对应 2604 reward 双写实测缺口 |
| v2.4.1 | 2026-11-06 | 1074 复盘副本接入，B-C04 bnpm 规则被平台划掉 → 降 needs_manual；新增 D-C01（reward_file 写入链，72 题 RewardFileNotFoundError 来源）、D-C02（清单哈希全量复算） |
| v2.4 | 2026-11-05 | 2026-11 平台新规，B-C01 至 B-C04 机械核对；Gate C 追加 6 条执行环境规则（landlock / home_writability / entrypoint_only_init / artifacts_handoff_mismatch / submission_dir_pollution / atomic_replace_race）；报告 schema 1.1；错误台账 E1 至 E25 |
| v2.3 | 2026-11 | 官方标准层接入（QA01 至 QA21 + Harbor 六项），qa.py 增加 official/review/integrate |
| v2.2 | 2026-11 | 四类强制槽位 worklist + 机器判覆盖率 |
| v2.1 | 2026-11 | 并行分派协议，编排者 + 分片执行者 + 合并校验 |
| v2.0 | 2026-11 | Gate C 执行层门禁（诚实候选冒烟） |

完整变更记录与规则反转的反推依据在 `SKILL.md` 与 `references/platform-criteria-inference.md`。

## 仓库结构

```
SKILL.md            Skill 主文档：流程、门禁纪律、判定规则、每版改动依据
scripts/            确定性脚本：qa.py 状态机、证据索引、Gate C、平台硬规则、
                    交付契约、覆盖率、合并、官方底稿、校验器
references/         规则契约：review 契约、判据反推（含平台规则反转记录）、
                    分派提示词模板、报告 schema
official/           内嵌只读官方副本（task-qa / baseline-quality /
                    supplement-platform-audit，SHA256 锁定）
field-reports/      他人质检失败/存疑报告收集处（脱敏后一报告一文件，
                    可复现的误报会转成回归用例）
assets/             review.json 模板
tests/              unittest 自测（94 用例，含各检查器的误报回归）
```

## 欢迎提 PR

这套 skill 在持续被打脸中进化，欢迎任何方向的改进。

- **检查器误报 / 漏报**，附上触发用例（最小可复现的包结构或文件片段最好），我们用它做回归测试。历次校准都来自真实误报，比如 revision_log 历史键、for-in 镜像双写。
- **新规则接入**，平台规则在变（docker_image 翻转过三次，bnpm 规则被划掉过）。如果你有新的平台副本或复盘材料，提 issue 先讨论判据，再动代码。
- **报告 schema / worklist 槽位**，如果你用这套 skill 质检出了别的问题类型，说明现有槽位有盲区，欢迎加槽或改 schema。
- **性能**，脚本单次 1.6 到 18.6 秒，瓶颈从来在阅读而非脚本；但如果你的包更大，欢迎报数据。

### 你的质检报告怎么变成 PR

用这套 skill 跑出了一份失败/存疑的报告，觉得判错了？按下面的路径来提。哪一层不满意，就查哪一层的证据，PR 里对应贴出来。

**第一步，先分清报告里的四种状态**，它们对应不同的复核路径。

| 状态 | 含义 | 你要给的东西 |
|---|---|---|
| `fail` | 检查器判定违规，机械判据 | 复跑命令 + JSON 输出；认为判错就给反例 |
| `needs_manual` | 检查器抓到强特征但不敢定论 | 你的实际落点证据（比如 reward 实际只写一个文件） |
| `platform_scope` | 需要 GPU/Docker/实机，脚本管不了 | 不用提 PR，登记平台待办即可 |
| `informational` | 仅供参考 | 不需要处理 |

**第二步，按缺陷类型准备材料**。

- **机械检查层（B-C/D-C/Gate C-1）判错**。这是最适合 PR 的一类，材料三样。① 复跑命令（`python scripts/check_xxx.py --root <你的包> --out out.json`）；② 完整 JSON 输出；③ 最小复现包，把触发误报的文件结构剥到最小，写清哪几个文件、哪几行让判据命中了。历次校准都这么来的，D-C02 把 revision_log 里的历史哈希当当前声明，D-C03 行级扫描看不见变量赋值加循环镜像的双写，都是有人贴出实际包结构后修掉的。
- **Gate C-2 冒烟 / 官方层 QA 判错**。这类带语义判断，先开 issue。贴 `adversarial_review.json` 里对应的 finding（id、severity、evidence 三样），说明你认为哪条证据不成立、正确答案是什么。判据对齐后再进代码。
- **合并/覆盖率问题**（该 PASS 被判 INCOMPLETE、coverage 不足 100% 的争议）。贴 `state.json` 的十阶段状态和 `coverage/` 目录下对应分片的 JSON，指认哪个单元被漏算或误判。

**第三步，注意脱敏**。你的报告 JSON 里有包的本机绝对路径（`root`、`task_toml` 字段）和题包内容。提 PR 前把路径改成占位符（`<package-root>`），私有题包内容只贴触发判据的最小片段，别整包上传。

**第四步，如果修复方对判级不服**（觉得我们把好包判死了），别在 PR 里争论，直接给反例。我们收过"修复报告声称已修复但字节没动"的包，也出过"检查器误报把好包判死"的事故，两个方向都真实发生过。判断标准只有一个，当前字节加复跑输出。

提 PR 前请跑 `python -m unittest discover -s tests`，94 个用例全过再提交。改动检查器判据的 PR，请同时给出"会误伤的真实包"反例，或者说明为什么不会。
