---
name: adversarial-engineering-qa
description: "对代码库、Harbor/AutoResearch 题包及软件交付物做严格工程化质检、独立复检、对抗审查、FAIL 复核和提交前验收；真实分级调用官方 AutoResearch/Baseline Skills，完整保留原 v4 六道闸门和交付物，并叠加双门禁、行为覆盖、有效反例、跨文件契约及机器可校验报告。静态只读与经明确授权的隔离动态验证均可使用。"
agent_created: true
---

# Adversarial Engineering QA

**版本**：v2.4（2026-11-05）
**v2 相对 v1 的实质改动**：新增 Gate C（执行层门禁）——`scripts/check_execution_path.py`
四条静态规则 + `scripts/check_honest_candidate.py` 诚实候选冒烟；判定纪律加入
「Gate C blocking 不可豁免、不得静默降级 manual」；合并规则加入 `remaining_findings` 阻断。
反推依据见 `references/platform-criteria-inference.md`。

**v2.1 相对 v2 的实质改动**：新增「2.6 并行分派协议」——`scripts/plan_gate_dispatch.py`
按证据索引的 shard 切出可独立认领的单元，`scripts/merge_gate_results.py` 做完整性校验与
合并（缺单元一律 INCOMPLETE）。主模型退到编排位（分派 / 合并 / 抽检 / 裁定），
不再串行通读受检代码。实测瓶颈是串行阅读而非脚本（脚本 1.6–18.6 s，读 140 文件是小时级）。

**v2.2 相对 v2.1 的实质改动**：新增「2.7 怎么保证串行读大量文件不丢重点」——
`scripts/build_review_worklist.py` 把「读一遍」变成四类强制槽（文件处置 / 声明绑定 /
热点问答 / 副本对账），`scripts/validate_coverage.py` 机器判覆盖率，
不足 100% 的单元即使自报 PASS 也被降为 INCOMPLETE。副本对账是 0340 QA05 的唯一
发现路径：140 个文件里精准圈出 3 组差异文件。

**v2.3 相对 v2.2 的实质改动**：新增「2.8 官方标准层」——`scripts/qa_official.py`
把 `official/` 里的 21 项（QA01–QA21）+ 3 个内容门 + Harbor 六项接进流水线，
`qa.py` 增加 `official` / `review` / `integrate` 三个阶段，`build_review_worklist.py`
给每个槽标注 `serves`（服务哪几项 QA）。**此前流水线只有对抗层，官方标准层从未被调用**——
实测代价：AutoRe1841 的「NOP 早于题包最后两次修改」这类问题，对抗层完全看不见。

**v2.4 相对 v2.3 的实质改动（2026-11 平台新规接入）**：平台在 2026-10-26 复盘
（rev 1145）、2026-11-02 supplement skill 与 2026-11-03 返修指南中给出四条源包硬规则
与 37 类报错定位表，其中 **B-C02 与内嵌官方层正面翻转**（旧口径要求填写
`docker_image`，新口径禁止）。v2.4 新增：① `scripts/check_platform_rules.py`
机械核对 B-C01–B-C04（§2.9）；② Gate C 追加 6 条执行环境类静态规则
（landlock / home_writability / entrypoint_only_init / artifacts_handoff_mismatch /
submission_dir_pollution / atomic_replace_race，来源为平台八类已确认运行缺陷）；
③ 报告 schema 升 1.1——finding 增加责任归属（`responsible` / `action`）、新增
`platform_checks`（证据三态）与 `three_judgements`（链路 / 成绩可信性 / 是否返修）；
④ `qa.py` 增加 `platform` 阶段；⑤ 内嵌 `official/autoresearch-supplement-platform-audit`
（只读副本，`sync_official_skills.py` 已纳入）；⑥ 错误类台账扩至 E1–E25，
`platform-criteria-inference.md` 记录规则翻转案例与方法升级。

## 目标

证明当前产物在声明的接口、正常路径、失败路径和对抗路径上是否成立，而不只证明文件存在、格式正确或本轮没有改坏。把“变更面回归”和“当前实现正确性”作为两个独立门禁；任一未通过，都不得给出无限定 PASS。

不承诺自动证明全部代码语义正确。静态工具给出可定位证据和语法线索，动态结论只来自实际到达目标行为的运行。

## 先选模式

### 静态只读模式（默认）

- 不导入、不执行待检代码，不安装其依赖，不连接其服务。
- 允许读取文件、解析 AST、运行本 Skill 自带的确定性脚本。
- 对必须依赖运行才能成立的声明，最高记 `manual`；不得凭源码阅读写成行为 PASS。
- 静态证据可以直接证明 FAIL，例如声明路径不存在、返回数量契约确定不一致、声明的保护执行点缺失。

### 授权沙箱动态模式

仅在用户明确授权执行后启用。先记录授权范围，再使用可丢弃副本、非特权用户、最小挂载、无宿主秘密、受控网络和资源限制。不得把宿主个人目录、真实凭据或唯一数据挂载给候选代码。

每次运行动态用例前，加载 `references/behavior-and-adversarial.md`。记录镜像/系统、cwd、完整命令、环境、UID、挂载、网络、退出码和日志。工具缺失或环境未就绪记 `manual`/`INCOMPLETE`，不记 PASS，也不伪装成作者缺陷。

## 核心流程

### 0. 固定对象、权限与输出边界

1. 记录待检文件或目录的绝对路径、大小、SHA-256；解包前检查越界路径、符号链接和特殊文件。
2. 将报告和临时产物放在待检产物之外；不得修改正式包。
3. 多模型/多会话并行质检同一个包时，先运行 `scripts/prepare_review_workspace.py prepare` 建立共享只读工作区，一个包只解压一次；详见 `references/multi-review-workspace.md`。所有质检输出写入各自独立目录，命名含包版本、包任务编号、质检模型名和会话 ID。
4. 写明包含范围、排除范围、排除原因、动态授权范围和时间预算。排除依赖缓存不等于排除交付源码。
5. 结束时重新计算源身份；源在审查期间变化则使旧证据失效，重新固定版本。基于旧包上下文的会话必须用当前包的 task/version/hash 重新绑定工作区，不得继承旧路径、旧报告或旧判级。

### 1. 先建证据清单，再读局部

运行：

```bash
python scripts/collect_evidence.py --root "<待检目录>" --out "<输出目录>/evidence-index"
```

先读 `manifest.json`，再按文件清单和分片完整审查。不得只读模型偶然看到的文件。大项目按分片写简短笔记，保留跨分片引用；不要把整库塞入上下文。

索引中的调用只是 AST 语法线索，不是精确调用图。动态分发、反射、别名、框架注册和隐式控制流必须另行核对。加载 `references/context-and-interfaces.md` 处理跨文件关联和上下文预算。

### 2. 分开建立两个门禁

**Gate A：变更面回归**

- 固定基线与当前版本，列出实际 diff、允许变更面、非预期变化和既有修复回归。
- “逐字节不变”只能证明没有漂移，不能证明基线正确。
- 没有基线且本轮不作回归声明时，记 `not_applicable` 并说明原因；不得伪造回归结论。

**Gate B：当前实现正确性**

- 无论 Gate A 是否通过，都独立检查当前声明、接口、失败分支、安全边界和对抗行为。
- 历史 PASS、作者自证、官方格式检查、NOP 和其他模型结论只能作为待检对象，不能继承为本轮 PASS。

### 2.5 Gate C：执行层门禁（v2 新增）

**查的不是「有没有保护」，是「诚实候选能不能跑出分」。**

背景（2026-10-30，从 11 份官方质检报告反推）：平台 `0.3.10-standard-waiver.5-toolfix.2`
把 QA06 的判据从「入口存在 / 退出码分类 / reward 落地」（结构层）改成
「按真实调用链走一遍，看类型与数量对不对」（执行层）。

证据：QA06 在 `.5` 与 `.5-toolfix.1` 下对 4 个任务全 pass，在 `.5-toolfix.2` 下对
2 个任务全 fail，根因都不是作弊：

- 0340：父进程把动作构造成 `np.ndarray` 传给 `TensorWrapper.step`，而该包装器第一行是
  `self.env.step(action.numpy())` ⇒ 首步 `AttributeError`，被当作候选侧失败计 −1；
- 2001：超时分支 `return` 三元组，调用方按二元组解包 ⇒ `ValueError`。

**这两类在「对抗路径」里永远查不到——它们只在诚实路径上炸。**

运行：

```bash
python scripts/check_execution_path.py --root "<待检目录>" --out "<输出目录>/execution-path.json"
```

输出三档：

| 级别 | 含义 | 处置 |
|---|---|---|
| `blocking` | 确定性代码缺陷（如 numpy 数组喂给要求 tensor 的包装器） | **必须修，不得豁免** |
| `needs_manual` | 题面声明与实现口径不一致（如题面说超时属基础设施、代码把 timeout 归候选） | 必须明确「改题面」或「改实现」，不得沉默 |
| `informational` | 题面绝对声明清单 | 逐条在 `review.json` 绑定证据 |

**与 Gate A/B 的关系**：Gate A 证明「没改坏」，Gate B 证明「当前对」，Gate C 证明
「真的能跑」。三者独立，任一 FAIL 即 FAIL；**Gate C 的 blocking 不可豁免**——
它属于当前实现缺陷，不是「证明差异」。

#### 2.5.1 Gate C-1：静态形态扫描（`check_execution_path.py`）

四条规则，全部来自真实打回报告，不是假设的攻防形态：

| 规则 | 查什么 | 来源 |
|---|---|---|
| `tensor_api_mismatch` | numpy 数组喂给「内部对参数调 `.numpy()`」的包装器 | 0340 QA06 |
| `return_arity_mismatch` | 函数一律返回 N 元组，调用点按 M≠N 个解包 | 2001 QA06（3 返 2 收，活到 v37） |
| `timeout_attribution_mismatch` | 题面说超时属基础设施，`_INFRA*` 前缀表不含 timeout | 0340 QA11 |
| `absolute_claim` | 题面绝对声明清单 → 强制逐条绑定证据 | 0340 QA05/QA11 都是「题面写了、实现没做」 |

#### 2.5.2 Gate C-2：诚实候选冒烟（`check_honest_candidate.py`）

**这是本节最重要的一条：拿题目自带的 starter / reference 原样当候选，跑一遍，必须拿到分。**

```bash
# 常规入口（自动探测 tests/ 下带 --solution_dir 的脚本）
python scripts/check_honest_candidate.py \
  --task-dir "<harbor_task>" --candidate "<reference 或 starter>" \
  --out "<输出目录>/execution-honest.json"

# 协议型评测器（如 policy_only 收发 JSON 行）
python scripts/check_honest_candidate.py \
  --task-dir "<harbor_task>" --candidate "<dir>" \
  --stdin-file payload.jsonl \
  --cmd "{py} -B {entry} --mode policy_only --solution_dir {candidate} --data_root {task_dir} --out {out} --ckpt {ckpt}" \
  --ckpt "<权重>" --out "<输出目录>/execution-honest.json"
```

判定：解析到崩溃签名 ⇒ `blocking`；未见崩溃但取不到分 ⇒ `needs_manual`（不假装通过）；
崩在未归类异常 ⇒ `unclassified_crash`，同样 blocking。

崩溃签名与真实缺陷的对应关系：

| 签名 | 归因 | 真实案例 |
|---|---|---|
| `frozen_method_tampered` | `fingerprint_false_positive` — 指纹把诚实候选判成篡改 | 0340 QA05（docstring 进了 `co_consts`） |
| `'numpy.ndarray' object has no attribute 'numpy'` | `tensor_api_mismatch` | 0340 QA06 |
| `too many/not enough values to unpack` | `return_contract_mismatch` | 2001 QA06 |
| `mat1 and mat2 must have the same dtype` | `dtype_mismatch` | 0340 v25.5.2（float64 输入 vs float32 权重） |

> **为什么必须用 reference 而不只是 starter**：0340 的 QA05 里，`starter` 与可信副本
> 指纹一致，只有 `workspace/reference`（在 `harbor_task` 之外）的 docstring 不同。
> 只跑 starter 会得到假绿。**两个都跑。**

### 2.6 并行分派协议（主模型 = 编排者）

**先认清瓶颈在哪。** 实测（0340，140 文件 / 96 py）：

| 环节 | 耗时 |
|---|---|
| `collect_evidence.py` | 1.4 s |
| `check_execution_path.py` | 1.6 s |
| `check_honest_candidate.py`（单候选冒烟） | 18.6 s |
| **主模型串行读 140 个文件 + 逐条推理** | **小时级** |

**慢的不是脚本，是串行阅读。** 所以并行要并的是「阅读与推理面」，不是「脚本」。
把 `check_execution_path.py`、`merge_gate_results.py` 这类确定性脚本也丢给子代理，
只会增加调度开销——它们本来就秒级。

#### 2.6.1 三个角色，边界不许混

| 角色 | 做 | **不做** |
|---|---|---|
| **编排者**（主模型） | 建证据索引 → 生成分派计划 → 派发 → 合并 → 裁定 → 抽检 | **不亲自通读受检代码**（那是并行要消掉的部分） |
| **执行者**（子代理） | 只认领**一个**单元，按 `acceptance` 做完，写 `result.json` | 不碰其他单元；不改结论口径；不给自己加豁免 |
| **合并方**（脚本） | 校验完整性、按规则合成总判 | 不做语义判断 |

#### 2.6.2 标准流程

```bash
# ① 建索引（只做一次）
python scripts/collect_evidence.py --root "<任务>" --out "<outdir>/evidence-index"

# ② 生成分派计划（切分来自 manifest，不靠模型临时决定）
python scripts/plan_gate_dispatch.py \
  --task-dir "<任务>" --evidence-dir "<outdir>/evidence-index" \
  --out "<outdir>/plan.json" [--baseline <基线>] [--max-units 8]

# ③ 按 parallel_group 派发：同组并发，组号小的先跑
#    每个执行者拿到的完整上下文 = plan.units[i] + 共享只读工作区 + acceptance

# ④ 收齐后合并（缺任一单元 ⇒ INCOMPLETE，不会被当成通过）
python scripts/merge_gate_results.py \
  --plan "<outdir>/plan.json" --results-dir "<outdir>" --out "<outdir>/gates/merged.json"
```

#### 2.6.3 执行者契约（派发时必须原样给出）

每个执行者的提示必须包含这五项，缺一项结果不可采信：

1. **单元 id 与 gate**（如 `B.shard-0001` / `B`）——决定它只能往哪写；
2. **输入清单**（shard 路径 + 文件数）——限定阅读范围，不许扩到别人的片；
3. **`acceptance` 原文**——从 plan 里原样贴，不许改写或精简；
4. **输出路径与 schema**（`unit_id` / `gate` / `status` / `findings` / `reason`）；
5. **禁止事项**：不得把「属于其他 shard」当作不看的理由；跨片疑点写 `cross_refs`。

#### 2.6.4 编排者的不可下放职责

这几条**不能交给执行者**，否则等于放弃裁定权：

- **总判**：只由 `merge_gate_results.py` 的规则产出，不由任何执行者的自述决定；
- **抽检**：随机抽 ≥2 条执行者的 `blocking` finding，编排者亲自复核原文；抽检不成立则整份结果作废；
- **Gate C 的 blocking**：执行者报 PASS 但 findings 里有 blocking ⇒ 合并脚本判自相矛盾并计 FAIL；
- **源身份**：开工前与收尾各算一次；源在审查期间变了，全部单元结果作废重跑。

#### 2.6.5 不支持和降级

宿主没有子代理能力时，**同一份 plan 由主模型串行执行**，仍然走 `merge_gate_results.py`。
保证完全一致，只是墙钟更长。**不得因为不能并行就跳过分片、跳过合并校验。**

#### 2.6.6 成本实话

并行**只缩短墙钟，不减少总工作量**；总 token 通常高于串行（每个执行者都要读自己的上下文）。
文件数少于 ~40、或只有单 shard 时，并行收益为负，直接用串行。

### 2.7 怎么保证「串行读大量文件」不丢重点

**先说结论：语义正确性无法保证；能保证的只有程序完整性。** 把这两件事分开，才不会自欺。

| 能机械保证 | 不能保证 |
|---|---|
| 每个文件都被处置过（读了/略读/跳过 + 理由） | 读到的地方都理解了 |
| 每条高风险声明都绑定到实现位置或明确「无实现」 | 绑定关系判断正确 |
| 每个热点函数都回答了固定问题 | 答案是真话 |
| 每组同源副本的差异都被解释过 | 解释是善意的 |

程序完整性不能证明结论对，但它**消灭了「压根没看」这一类漏检**——0340 的 QA05/QA06
正是这一类：两行接口错配躺在那里，五路复核谁都没往那个方向看。

#### 2.7.1 四类抓手（全部由 `build_review_worklist.py` 生成）

| 抓手 | 来源 | 强制项 |
|---|---|---|
| **文件处置槽** | `manifest.files` | 每文件必须填 `disposition` + `reason` |
| **声明绑定槽** | shard 的 `declarations`，按风险打分 | `must_bind=true` 必须绑 `file:line` 或 `no_implementation` |
| **热点问答槽** | `symbols.json`，按函数体哈希**全局去重** | 每个热点回答固定问题 |
| **副本对账槽** | 同相对路径在多树下成组，`sha256` 不同即成组 | `mirror_notes` 必须逐组说明差异是否有意 |

风险打分规则（写死在脚本里，不靠模型判断）：

```
+3  绝对声明（不可/无法/必须/仅/只/不会/一律/禁止）
+3  数量声明（N 秒 / N GB / N 核 / gpu）
+3  安全边界（隔离/只读/隐藏/沙箱/权限/降权/root）
+2  失败路径（超时/重试/失败/异常/崩溃）
+2  校验口径（指纹/hash/sha256/校验/verify/check）
+2  评分链（评分/reward/score/分数/奖励）
```

#### 2.7.2 副本对账为什么单列一条

0340 的 QA05 是**唯一一条只有副本对账才能发现**的缺陷：

```
starter  _estimate_value_iq  ─┐
                              ├─ 方法体一字不差，只有 docstring 不同
trusted  _estimate_value_iq  ─┘
运行时指纹把 docstring 算进 co_consts ⇒ 诚实候选被判「篡改」⇒ −1
```

逐文件阅读时，两份代码「看起来一样」，注意力不会停在 docstring 上。
机器做 sha256 比较，一眼就跳出来。实测 140 个文件里，这条规则精准圈出 **3 组**
（`tdmpc2/config.yaml`、`tdmpc2/tdmpc2.py`、`trainer/online_trainer.py`）——
正是历史出事的那三个文件。

#### 2.7.3 三档强度（默认 standard）

| 档 | 覆盖 | 0340 实测题量 |
|---|---|---|
| `light` | 只问高危函数，每处 2 问；必修声明 ≤15/片 | 76 问 |
| `standard` | 高危全问 3 问；环境样板只问 1 问（形状/dtype） | 127 问 |
| `strict` | 全问，必修声明不设上限 | 127 问 + 299 条必修 |

```bash
python scripts/build_review_worklist.py --evidence-dir <ev> --task-dir <task> \
  --all --outdir <outdir>/worklist --intensity standard
python scripts/validate_coverage.py --worklist <filled.json> \
  --result <unit result.json> --out <outdir>/coverage-<shard>.json
```

`validate_coverage.py` 返回 `coverage_pct`；**未达 100% 的单元，即使自报 PASS，
`merge_gate_results.py` 也会降为 INCOMPLETE**。

#### 2.7.4 天花板（必须写进结论）

程序完整性到顶之后，剩下的风险是「看了但没看懂」。这一层只能靠：

1. **第二路独立红队**（§6），且必须用**不同的入口**——不是同一份清单再答一遍；
2. **抽检**：随机抽 ≥2 条 blocking，编排者亲自复核原文；
3. **承认不确定**：拿不准的写 `unverifiable` 并说明缺什么，不要凑一个 `holds`。

> **不要把 `coverage_pct=100%` 当成「质量已保证」。** 它只说明「该看的都看了」，
> 不说明「看对了」。任何报告里出现「覆盖率 100% 故结论可靠」这类推论，一律判为
> 论据不足。

### 2.8 官方标准层（QA01–QA21 + G01–G03 + Harbor 六项）

**本 skill 有两层，编号互不相通。别把一层做完当成全部做完。**

| 层 | 查什么 | 入口 |
|---|---|---|
| **对抗层**（Gate A/B/C） | 候选能不能作弊、诚实候选能不能跑通 | `check_execution_path.py` / `check_honest_candidate.py` / worklist |
| **标准层**（官方 21 项） | 题包作为**交付物**是否合格：题面泄露、评分公式、锚点可分辨性、NOP、四项指纹、资源时长、轨迹 | `official/autoresearch-task-qa-legacy-waiver/scripts/audit_standard_with_waivers.py` |

实测代价（AutoRe1841，2026-10-31）：只跑对抗层时得到「FAIL，1 条阻断」，
看起来挺完整；补跑官方层才发现 **NOP 记录早于题包最后两次修改**（NOP 10-16，
`task.toml`/`frozen_manifest.json` 10-23），以及题面声称的分数域与实现不符。
**这两类问题对抗层根本不看。**

#### 2.8.1 三个阶段

```bash
python scripts/qa.py init --task-dir <harbor_task> --zip <submission.zip> --workspace <ws>
python scripts/qa.py run  --workspace <ws> --stage official    # 跑原版审计，拿 21 项判据 + 指纹
python scripts/qa.py run  --workspace <ws> --stage review      # 生成 review.json 底稿
python scripts/qa.py run  --workspace <ws> --stage integrate   # 两层合成总判
```

`official` 阶段**必然返回 ERROR / REVIEW_NOT_FINISHED**——这是设计如此：
官方脚本要求 21 项逐条审明，不填底稿就不给结论。

#### 2.8.2 三档判定，manual 不许自动转 pass

| 档 | 含义 | 谁给结论 |
|---|---|---|
| `mechanical` | 规则可判（数值、布尔、文件存在） | 脚本，附证据 |
| `manual` | 需读语义 | **质检员**；脚本只预填证据并写明「还缺什么」 |
| `blocked` | 前置缺失 | 不猜，直接报缺什么 |

官方脚本里写死了一条：`STANDARD_MANUAL_REVIEW_NOT_FINISHED`——
「原 manual 仍需质检员审明，**不能自动转为作者失败**」。
对称地，**也不能自动转成通过**。任何把 manual 批量改写成 pass 的做法都是作弊。

#### 2.8.3 实测：21 项里有多少能机械判

AutoRe1841 一次 `review` 的分布：**pass 5 / fail 1 / manual 15**。

| 能机械判（有客观条件） | 只能人工 |
|---|---|
| QA04 3σ 可分辨性（`delta_in_sigmas ≥ 3`）<br>QA09 清理与原子写（`rm -f` + `os.replace`）<br>QA12 Git 清理（树内无 `.git`）<br>QA13 B/R 提升（R mean > B mean）<br>QA19 seed 与阈值（≥3 seed 且 ≥3σ） | QA01 八章节与泄露<br>QA05 约束执行<br>QA07/QA08 题面泄露<br>QA11 题面八项<br>QA14 改进空间<br>QA16 轨迹时长<br>QA18 轨迹分析<br>QA20 范围与网络 |

**15/21 仍需人读**——这个比例本身就是结论：标准层不可自动化，只能自动化「找证据」那一半。

#### 2.8.4 槽位与 QA 项的对应

`build_review_worklist.py` 给每个槽加了 `serves` 字段，标明它服务哪几项：

```
instruction.md              → QA01 QA05 QA07 QA08 QA11 QA14 QA20
tests/grader.py             → QA02 QA06 QA10 QA21
tests/test.sh               → QA06 QA09 QA21
tests/hidden_assets/anchors.json → QA02 QA04 QA19
task.toml                   → QA15 QA17 QA20
frozen_manifest.json        → QA10 QA14 QA21
```

答一个槽之前先看 `serves`，就知道这个答案会被哪一项引用；反过来某项全是 manual 时，
顺着 `serves` 能查出「缺的是哪个文件的哪一段没读」。

### 2.9 平台源包硬规则（B-C01–B-C04，2026-11 新规；v2.4 新增）

**这四条不在 QA01–QA21 的任何一项里**（官方层 2026-10-23 版早于它们），必须单独跑：

```bash
python scripts/check_platform_rules.py --root "<提交包根或任务目录>" \
  --out "<输出目录>/platform-rules.json"
```

| 编号 | 查什么 | 判定档 |
|---|---|---|
| B-C01 | 只保留一份 `task.toml` 于 `workspace/harbor_task/`；历史配置另归档或改成说明材料 | mechanical |
| B-C02 | 专家源 `task.toml` 禁配 `docker_image`；`environment/Dockerfile` 及 COPY/ADD 构建上下文完整 | mechanical |
| B-C03 | 依赖用发行版/生态官方源——只扫**执行载体**（Dockerfile/安装脚本/包管理配置），README 里的 URL 不算生效 | mechanical / needs_manual |
| B-C04 | npm 实际生效 registry 为 `https://bnpm.byted.org`——命令行 `--registry` 覆盖 `.npmrc`；未用 npm 记不适用 | mechanical / needs_manual |

全部机械判（mechanical）。supplement 的案例边界已编码进实现：注释里的字段名不算配置、
说明文档不算生效包源、`.npmrc` 写 bnpm 被命令行覆盖仍判不符合。

**⚠️ 规则冲突批注（不得静默处理）**：内嵌官方层（`0.3.10-standard-waiver.5`）的
`innerfield-deployment.md` / `submission-format.md` / `harbor-harness.md` 仍写着
「按平台要求**填写** `docker_image`」——该口径已被 2026-10-26 复盘（rev 1145）与
2026-11-03 返修指南**翻转**。处置：

1. B-C02 以 `check_platform_rules.py`（新口径）为准；旧口径判据不得再引用；
2. review 中显式记录冲突：「官方副本口径已过期，以 2026-11-03 平台规则为准」；
3. 不修改官方副本本体；官方热更新仍走 `sync_official_skills.py --apply` 显式同步；
4. 引用任何规则时**连日期版本一起引**（见 `references/platform-criteria-inference.md` §6）。

**执行环境类缺陷（Gate C 新增 6 条）**：平台八类已确认运行缺陷中可静态定位的形态
已进 `check_execution_path.py`——`landlock_dependency`（无条件 import Landlock
⇒ blocking）、`home_writability`（非 root USER + 硬编码 `/root/` ⇒ blocking；
UID 未知 ⇒ needs_manual）、`artifacts_handoff_mismatch`（题面提交路径与 artifacts
不一致 ⇒ blocking；声明无引用 ⇒ needs_manual）、`submission_dir_pollution`
（公开评测写提交目录 ⇒ blocking）、`entrypoint_only_init` / `atomic_replace_race`
（informational / needs_manual）。进程上限、资产版本核验等静态判不了的记
`needs_manual`，不猜。

**三个判断分开 + 证据三态**（对齐 supplement 1.0.1）：凡涉及平台材料的结论，
`review.json` 填 `three_judgements`（运行链路情况 / 成绩可信性 / 作者是否需要返修——
三者独立，平台故障不自动生成作者返修项）与 `platform_checks`（每条带
`evidence_state`: verified / materials_missing / not_run）；不设全局「待核验」结论；
「没有日志」不得写成「没有运行」或「运行失败」。findings 的 `responsible`
（author / platform / unresolved）与 `action`（author_fix / platform_fix /
record_only）不得互相矛盾。

### 3. 建立声明—实现—行为链

对每条关键声明记录：声明原文及位置、被描述对象、实现位置、配置/调用方、需要的证据等级、行为覆盖和最终状态。至少覆盖：

- 对外命令、入口参数、输入输出和错误契约；
- producer → consumer → config → docs 的完整链；
- 正常、异常、超时、空输入、非法输入、资源边界和降级路径；
- 权限、文件系统、网络、进程和环境隔离；
- “不可绕过”“完整可复现”“不会影响评分”等绝对声明。

Python 项目运行：

```bash
python scripts/check_return_contracts.py --root "<待检目录>" --out "<输出目录>/return-contracts.json"
```

该检查是合同候选扫描，不替代人工确认。返回数量不一致可直接定位到定义、各返回点和解包调用点。

### 4. 填行为覆盖矩阵

为每个公开接口列出所有语义分支，而不只列测试名称。每个 PASS 绑定实际覆盖记录；未运行的分支列入 `untested_branches`。

公开命令必须在声明的实际 cwd、文件布局和环境里**逐字原样执行**。用等价命令、另换 cwd、预置未声明文件或人工补参数得到成功，不能证明声明命令可用。

NOP、早退、缺权重、空数据或 `n_test=0` 只能证明实际到达的分支。必须记录覆盖分母，不能继承为全链路证明。

### 5. 让每个反例先证明“到达目标”

每个攻击或负向测试分别证明：

1. 攻击代码已进入目标逻辑；
2. 防御机制被实际触发或观察；
3. 去掉/替换防御后对照会改变结果；
4. 判定 oracle 检查目标性质，而不是只检查“最终失败”。

语法错误、导入错误、依赖缺失、无关崩溃、目标前超时和 `reward=-1` 等通用失败不得直接作为防御 PASS。核心机制需做 ablation；无法动态验证时记 `manual`。

进程分离、`python -I`、独立进程组、容器、文件系统权限和网络命名空间是不同边界，不得互相替代。

### 6. 至少保留一路独立红队

高风险提交至少安排一路不读取旧报告、不看包内结论的独立审查，从当前产物和声明出发重建攻击面。其他路线可做数值、格式、归属和口径复核，但不能全部共享同一旧结论。

无法获得独立路线时，在覆盖限制中明示；不得把同一模型的多次复述计为多路独立验证。

### 7. 先出机器可校验报告，再给结论

以 `assets/review_template.json` 创建 `review.json`，以 `references/report-schema.json` 为结构唯一权威。加载 `references/review-contract.md` 填判定和证据。

```bash
python scripts/validate_review.py --review "<输出目录>/review.json"
```

`review.json` 是机器判定权威，`report.md` 是人读摘要；两者结论必须一致。验证器报错时先修报告或补证据，不得绕过校验直接宣布完成。

## 判定纪律

- **Gate C 有 `blocking` ⇒ 一律 FAIL，且不可豁免**：这是「诚实候选跑不通」，不是「证明差异」。
- **不得静默降级**：凡 Gate C 已给出确定结论的项，不得改记 `manual` 绕过；
  静态模式下仍可判 FAIL 的项（路径缺失、数量契约不一致、声明的保护点不存在），一律判 FAIL。
- `PASS`：Gate A/B/C 均通过，所有强制声明和反例均有足够证据，且校验器通过。
- `FAIL`：任一当前实现、接口、约束或证据真实性存在不可豁免缺陷。发现 FAIL 不阻止继续完成其余审查。
- `INCOMPLETE`：证据不足、动态能力未授权、工具缺失、范围未覆盖或人工复核未完成。不得把 INCOMPLETE 写成“基本通过”。
- `PASS_WITH_WAIVERS`：只能出现在独立豁免层；先保留原标准 FAIL，再给适用政策、reason code 和不可豁免边界。当前实现缺陷不得用历史迁移豁免遮盖。
- 所有“未发现”“全部”“一致”都必须附实际扫描数、逐条判读数和未覆盖范围。

## AutoResearch / Harbor 官方分级调用

处理 AutoResearch 题包时，先加载 `references/autoresearch-integration.md`，再开始任何题包判级。必须实际完成四层，而不是只写“兼容官方”：

1. 用 `scripts/check_autoresearch_integration.py contract` 探测并核验内嵌官方 `official/autoresearch-task-qa-legacy-waiver`、`official/autoresearch-baseline-quality` 和 CLI 合同；官方 Skill 已内嵌到本 Skill 根目录 `official/`，默认以相对路径调用，不依赖绝对路径；
2. 按官方 `SKILL.md` 阅读 18 份 references，真实运行 `official/autoresearch-task-qa-legacy-waiver/scripts/audit_standard_with_waivers.py` 的收集和带双 review 终稿入口，保留原标准层与豁免层；
3. 按逐字保留的 `references/autoresearch-v4-original.md` 完成六道闸门、十三张命名底稿、最终八步输出和 18 条收尾核验卡；
4. 再执行本 Skill 的 Gate A/B、E15–E20、行为/反例矩阵和独立红队，取各层最严格结论。

官方 Skill 本体只读，不允许在质检过程中修改。官方热更新通过 `scripts/sync_official_skills.py --apply` 显式同步内嵌副本；同步后需人工复核兼容合同，不得静默接受新规则。

2026-11 起，`official/` 另含只读内嵌副本 `autoresearch-supplement-platform-audit`（1.0.1：原版六类增量审计 + 平台专项 B 模块），同步机制相同。题包质检流程在四层之外补两步：**先跑 `qa.py run --stage platform`（B-C01–B-C04 机械核对，见 §2.9）；平台日志可用时，按 supplement B 模块的原因族（B-P/B-E/B-S）做三阶段链路诊断，产出按其原文的三判断分离、责任三标记、证据三态与处理清单**——A 部分六类与其排除项按原文逐字执行，B 的结论独立保留，不倒灌为 A 的新增类别，不改写官方原判。以 `references/autoresearch-v4-coverage.json` 为覆盖清单权威，生成并填写 `autoresearch_coverage.json`。将官方逐项底稿保存为 `review.json`，将本 Skill 对抗报告保存为 `adversarial_review.json` 并设置 `domain="autoresearch_harbor"`。最终运行 `check_autoresearch_integration.py validate` 核对官方实际调用、全部覆盖 ID、交付文件 SHA-256 和分层 decision；缺官方、缺覆盖或缺交付时不得 PASS。不得修改官方 Skill 本体，不得让历史豁免覆盖当前实现缺陷。

## 收尾硬问

1. 当前源哈希是否与开工一致？
2. 文件清单是否完整，排除项是否可能藏有交付代码？
3. Gate A 通过是否被错误当成 Gate B 通过？
4. 每条 PASS 是否有声明、实现和行为证据，而非只有 README？
5. 公开命令是否原样、同 cwd、同布局执行？
6. 每个攻击是否到达目标并有有效对照，还是只在目标前崩溃？
7. NOP/早退实际覆盖了哪些分支，哪些仍未覆盖？
8. 最薄弱环节、未核对类别和独立红队限制是否写进终稿？
9. B-C01–B-C04 是否机械核对过？与官方内嵌副本的口径冲突（如 docker_image 翻转）
   是否在 review 中显式记录？平台材料的结论是否三判断分离、证据三态标注？
