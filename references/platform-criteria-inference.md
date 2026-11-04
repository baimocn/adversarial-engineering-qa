# 平台判据反推方法（2026-10-30）

> 本文记录 **怎么在拿不到平台 skill 源码的情况下，反推出它的判定口径**。
> 结论会过期（平台一升级就变），方法不会。下次被新版本打回，照第 2 节重跑一遍即可。

---

## 1. 为什么必须反推

平台不提供最新 skill 源码（防作弊），而本地内嵌副本是 `0.3.10-standard-waiver.5`。
平台实际执行的是 `0.3.10-standard-waiver.5-toolfix.2`。

两者差异（由两份 `skills-revision.json` 逐文件哈希比对得到）：

**新增 2 个文件**
- `PIPELINE_TOOLFIX_2.json`
- `references/reviewer-closure.md`

**改动 9 个文件**
```
scripts/audit_standard_with_waivers.py
scripts/audit_legacy_task.py
scripts/audit_format_repair.py
scripts/implementation_review.py
scripts/trajectory_review.py
scripts/task_fingerprint.py
autoresearch-task-qa-legacy-waiver/SKILL.md
tests/test_audit_standard_with_waivers.py
tests/test_task_fingerprint.py
```

**核心脚本全被换过。** 用旧副本自检「通过」，与平台判定没有任何关系。

---

## 2. 反推流程（可复用）

### 2.1 收集样本

每份打回报告 zip 里固定有三样，缺一样都要问平台要：

| 文件 | 用途 |
|---|---|
| `pipeline-status.json` | `skill_version` / `skill_content_sha256` / `effective_decision` |
| `skills-revision.json` | `files` 逐文件哈希 → 判断版本间改了哪些脚本 |
| `standard-waiver/standard/report.json` | 21 项 `checks` 的 `title` + `summary` + `status` |

### 2.2 建样本表

按 `(task_fingerprint, skill_version)` 去重，把每份的 21 项 `checks` 拉平成表。
本次共得 **11 个独立样本**，覆盖 4 个任务（0340 / 2001 / 0823 / 2768）、3 个版本：

```
0.3.10-standard-waiver.5            ×3
0.3.10-standard-waiver.5-toolfix.1 ×6
0.3.10-standard-waiver.5-toolfix.2 ×2
```

### 2.3 找「同号换靶」

**这是整个方法的关键。** 不要只看谁 fail，要看 **同一个编号在不同版本下 `title`/`summary` 说的是不是同一件事**。

实例 —— QA05：

| 版本 | 任务 | 实际查什么 |
|---|---|---|
| `.5` | 0340 | `build_eval_cfg` 直接读候选 config、import 候选 TDMPC2 |
| `.5` | 2001 | 20M 参数量门 + 1800s timeout 有没有真执行 |
| `toolfix.1` | 0823 | `run_round.sh` 直接取 `ROUND_BUDGET_SEC`，没校验 ≤7200 |
| `toolfix.1` | 2768 | 单轮 7200 秒仅声明而未执行 |
| `toolfix.2` | 0340 | **docstring 导致运行时指纹误判 starter/reference** |
| `toolfix.2` | 2001 | **「子进程不可触及 Hidden」的声明与调用链不符** |

同一编号，靶子从「配置边界」→「参数上界」→「指纹口径」。
**按旧 findings 修完，新版本会拿另一个问题再报同一个编号——这不是修错了，是编号背后的判据换了。**

### 2.4 找「跨任务集体翻转」

单个任务的 fail 可能是个案；**同一项在多个无关任务上同时由 pass 翻 fail，只可能是判据变了**。

QA06 实测分布：

| 版本 | fail | pass |
|---|---|---|
| `.5` | 0 | 3 |
| `toolfix.1` | 0 | 4 |
| `toolfix.2` | **2** | 0 |

`toolfix.2` 只有 2 个样本，两个都 fail，且根因都是「评分链跑不通」：
- 0340：`np.ndarray` 传给 `TensorWrapper.step`，包装器调 `action.numpy()`
- 2001：超时分支 3 返、调用方 2 收

### 2.5 归纳判据深度

```
.5          →  结构层：文件在不在、字段全不全、声明写没写
toolfix.1   →  参数层：声明 vs 脚本里的实际取值（BUDGET、7200）
toolfix.2   →  执行层：按真实调用链走一遍，看类型/数量/顺序会不会崩
```

**这三层是递进的：上一层的「全 pass」在下一层毫无意义。**

---

## 3. 本次反推出的结论

### 3.1 平台真正在查的是「诚实候选能不能出分」

`toolfix.2` 对 0340 报出的 3 条剩余 fail，**没有一条是「候选能作弊」**：

| 项 | 缺陷 | 后果 |
|---|---|---|
| QA05 | 静态 G6 剥 docstring，运行时 `_code_fp` 没剥 | starter/reference 被判篡改 ⇒ −1 |
| QA06 | `np.ndarray` 喂给调 `.numpy()` 的包装器 | 首步 `AttributeError` ⇒ −1 |
| QA11 | 题面说超时属基础设施，`_INFRA_FAULT_PREFIXES` 不含 timeout | 归候选 −1 |

而此前 8 轮迭代、五路对抗复核，查的全是「候选怎么作弊」。

### 3.2 由此得到的判定纪律

1. **对抗路径的「全绿」不能证明交付可用。** 它只证明「已知攻击形态都被拦」。
2. **诚实路径必须单独验。** 判据只有一句：starter 和 reference 原样提交，能出分。
3. **静态能判的不得降级成 `manual`。** 0340 的 QA06 静态就能判（类型流向），一旦降级就不阻断。
4. **`remaining_findings` 非空 ⇒ FAIL。** 豁免层 `decision` 字段可能被上游写错；真正决定能不能交的，是「还有没有未被 `accepted` 覆盖的 fail」。

---

## 4. 反推的边界（不夸大）

- `toolfix.2` 只有 2 个样本，我只能确定 **QA05 / QA06 / QA11** 三项的新判据；
  剩下 18 项在 `toolfix.2` 下长什么样，样本不足。
- 补样本最省的办法：**任何一次提交都会产生一份完整 21 项报告**，哪怕还是 FAIL。
  攒到 4 个任务就能覆盖大部分项。
- 判据会继续变。本文所有结论都带版本号，**引用时必须连版本一起引**。

---

## 5. 版本敏感度提醒

`skills-revision.json` 的 `files` 哈希是最可靠的版本信号：

```
skill_content_sha256 = be1781172a052efe…  → .5（本地内嵌的旧版）
skill_content_sha256 = ea2ebcf9f8b0e052…  → .5-toolfix.2（平台当前）
```

**每拿回一份报告，先读这两个字段再看 findings。** 版本没变，findings 才有累积意义；
版本变了，前面的结论要重新验。

---

## 6. 2026-11 新证据：判据不只是换靶，还会**翻转**

> 本节是 §2 方法的一次升级验证：平台在 2026-10-26（Harbor 1074 题复盘 rev 1145）、
> 2026-11-02（`autoresearch-supplement-platform-audit` 1.0.1）与 2026-11-03（返修指南）
> 给出的新规则里，出现了**同一字段方向翻转**——「同号换靶」的最强形态。
> 规则来源今后一律**连日期版本一起引**，并按下表核对方向。

### 6.1 docker_image：要求 → 禁止（判据倒置）

| 版本口径 | 对 task.toml 的 docker_image |
|---|---|
| `0.3.10-standard-waiver.5`（2026-10-23，本地内嵌） | **必须填写**：innerfield-deployment.md「按平台要求填写 docker_image」、submission-format.md「预构建镜像并填写 docker_image」，且明写「不新增缺 docker_image 即自动失败的门槛」 |
| 复盘 rev 1145 / supplement 1.0.1 / 返修指南（2026-10-26 之后） | **禁止配置**：专家源包不配 docker_image，以 `environment/Dockerfile` 为准；平台构建内部镜像并写入**平台生成的**运行配置，专家无需回填 |

后果：拿旧内嵌层质检，会把**符合新规则的包判 fail**（缺 docker_image）、把**违规包判
pass**（配了 docker_image）。supplement 的 PLATFORM_EVAL_CASES 明确把这两种写成
「不应出现的判断」。处置：机械核对以 `check_platform_rules.py`（B-C02）为准；冲突在
review 显式记录「官方副本口径已过期，以 2026-11 平台规则为准」，不静默沿用旧规则，
也不修改官方副本本体。

### 6.2 3σ：从「写进题面」到「迁出 Solver 题面」

| 版本口径 | 题面里的 3σ |
|---|---|
| 旧标注文档 | 「题面写明有效提升阈值（如 3σ）」 |
| 返修指南（2026-11-03） | 作者校准义务（达到 3σ 才完成、进入 Reference 校准区间、跑满作者研究时长）**从 Solver 题面/完成条件/选优说明迁出**；作者侧 B/R 校准证据保留；题目算法自身合理使用 3σ（异常检测、统计规则）不按关键词删除 |

注意与补充六类审计的边界：原版补充审计把「题面中的 Baseline/Reference 校准流程、3σ」
列为**不报告**项（那是「题面-执行一致性」六类的排除），而迁移规则是**另一条独立要求**
——两者不冲突，但朴素合并会互相搅扰。

### 6.3 其余新规速览（同批给出，同样带版本引用）

- **四条源包硬规则** B-C01–B-C04：唯一 task.toml；禁配 docker_image；依赖用发行版官方源；npm 走 `bnpm.byted.org`。全部静态可判，已实现于 `check_platform_rules.py`。
- **镜像装配三分支**：显式 `verifier.environment.docker_image` → `tests/Dockerfile` → 继承 Solver 镜像。两份 Dockerfile 不证明隔离，一份不证明不合规；地址相同不等于自动上传 tests。
- **37 类平台报错定位表**（P01–P25 / E01–E09 / S01–S03）：用于平台日志诊断，按**第一条致命错误**定位，warning/缓存未命中/已恢复重试不当根因。

### 6.4 方法升级

§2 的反推流程原样可用，但补一条：**当平台随报告给出显式规则文档（复盘/返修指南/
supplement skill）时，显式规则优先于反推结论**——反推是在拿不到源码时的替代手段，
不是与官方口径对赌的工具。反推结论必须标注「截至 rev 1145 / 2026-11-03」，
显式规则更新时立即复核本文全部结论。
