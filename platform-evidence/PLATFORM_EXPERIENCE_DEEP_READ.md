# 平台群聊分享经验文档逐篇精读报告

日期：2026-11-14  
范围：群聊全量消息中筛出的平台质检/返修经验文档 A 组 9 份。  
方法：`im +chat-messages-list --page-all` 拉全量（通知群 272 条、讨论群 403 条，均 `has_more=false`）→ `drive +inspect` 解析标题/token → `docs +fetch --doc-format markdown` / `sheets +table-get` 落盘 → 逐篇提取原文判据 → 对 `adversarial-engineering-qa-strict` 做脚本级覆盖检索。

本地正文目录：`group_doc_docs/*.md`，机器清单：`group_shared_docs_full_inventory.json`，工作表数据：`group_doc_docs/06_acceptance_triage_20261107.json`。

> 纪律：群聊经验文档是“平台/项目组经验与口径材料”，不是平台对某一题包的最终合规结论。下列「可验证判据」是从原文提炼出的候选检查项；是否进入自动 checker，仍须按当前报告版本和官方 skill 版本做冲突裁决。

---

## 01. AutoResearch 专家终检问题汇总（2026-11-13）

- token：`QZJQdgZlyoDNPFxaPemcEYcPnjg`
- 本地正文：`01_zhongjian_wenti_huizong_20261113.md`
- 群聊语境：2026-11-14 00:19「老师们这是一些问题汇总可以看看」。

### 原文问题族

| 问题族 | 题数 | 原文根因 | 原文返修方向 |
|---|---:|---|---|
| 难度过低（短时间达峰） | 64 | Seed 首版/第二版短时间逼近最高合法分或理论上限，后续增益有限；研究空间退化为小型枚举、查表或固定参数 | 扩大问题规模或有效算法空间；消除闭式捷径/查表路径；仅延长轨迹或调整归一化刻度不算解决 |
| 难度过高／无高分合法解 | 31 | 三轨最高分和 Reference 归一化不超过 0.20 等，涉及锚点失配、质量门不稳、优化空间不足 | 按此前同步的 0.15–0.8 口径处理；仅因 0.15/0.20 下限差异被打回可通过难度项；低于 0.15 不在澄清范围 |
| 失败写成普通 0 分 | 38 | 评分器判题前预写 0，或格式错误、无效候选、超时、执行异常仍发布 0.0，混淆失败与合法 Starter 水平 | 统一错误分类和结果出口；候选违规/格式错误/候选超时返回确定负分（报告要求 ≤−1）；0.0 仅表示合法 Starter；可信环境故障保留独立错误/无分诊断 |
| Verifier 低效／预算失配 | 11 | 独立 case 或训练串行执行，Verifier 耗时过长；GPU 资源配置错误；单 seed 预算、固定训练协议与声明时限不匹配 | 并行化独立 case、修正 GPU 资源、按实际训练成本调整预算/整体评测协议；验证完整 Verifier 能在声明资源和时限内完成 |
| 评分门／合同与防作弊 | 31 | 题面未公开实际评分约束，公开 Dev 与 Hidden 行为不一致，评分器误拒合法实现，资源探针不兼容，公开环境泄露结果表，计时过程可回放 | 同步公开合同与实际评分规则；修正误拒白名单/guard；修复资源探针；移除私有评测结果泄露；隔离计时状态及正式输入；复核合法实现通过、违规路径被正确拒绝 |

### 可验证判据

- `difficulty_low`：是否存在闭式捷径/查表路径；合法方法空间是否退化为固定参数；Reference 是否短时间饱和；仅延长轨迹或改归一化刻度不得算修复。
- `difficulty_high`：Reference 归一化是否 <0.15；0.15–0.20 之间不得仅因旧 0.20 下限打回。
- `failure_zero`：失败、超时、格式错误、可信故障路径不得发布普通 `0.0`；`0.0` 只能对应合法 Starter 水平。
- `verifier_budget`：独立 case 是否并行；单 seed 预算、训练协议、声明时限、GPU/CPU 配置是否可完成完整 Verifier。
- `contract_guard_consistency`：题面公开限制必须和 guard/评分器一致；合法样例 pass，违规样例正确拒绝；公开环境不得有 Hidden/结果表泄露；计时状态不可回放。

### 现有 strict skill 覆盖

- 五类终检汇总关键词在该仓库 0 命中，尚未形成规则台账。
- 最接近：`check_execution_path.py:173-212` 超时归因、`qa_official.py:199-214/229-239/378-385` 对 0.3.10 的分数/3σ/seed 预填；但无「失败普通 0 分」「难度过低/过高」「Verifier 并行预算」「0.15–0.20 口径澄清」独立检查。

---

## 02. Harbor 1074题执行复盘：失败原因、解决办法与验收清单（2026-10-26） 副本

- wiki node：`Gto2wtQ4yiSU5dkC3Hmc5NK7n1c` → docx：`L7zhd09fMoxdNqxzUegc6gFinzx`
- 本地正文：`02_harbor_1074_failure_review_20261026.md`
- 数据基线：状态表 revision 63，1,074 题；正常 410，问题 664；准备失败 322、执行/无评分证据 152、评分失败 74、已评分但执行异常 116。

### 核心原文口径

- 原文明确：「不能把平台 Failed、任务零分和 Agent 失败视为同一件事」；「410 题成功仅指 Agent 与评分流程正常，不代表分数达到通过阈值」；「116 题已评分（执行异常）必须保留原分数，但不能计入正常成功」；「零分、负分、框架默认分数均不得人为改写」。
- 准备阶段 25 个原因族：Docker Hub 不可达 97、APT 403 36、Python 分发/索引/兼容 33、基础镜像引用/授权 23、Git 锁/推送 22、发布包结构或归档损坏 22、wheel 403 14、镜像层上传 13、模型资产链路 13、npm 407 10、manifest/digest 9、构建 context 路径 6 等。
- 工作目录只读与运行目录可写不是同一约束：先读题目声明；只读是设计时修正不适用预检；确需写入只授权规定输出位置；不能递归 chown/chmod 777。
- 评分阶段：72 题 `RewardFileNotFoundError`、1 题 `DownloadVerifierDirError`、1 题非数值 `null`；修复不得补造零分，`null/NaN/Infinity` 不能当有效零分。
- 文末「需加入质检 skill 的 rule」：唯一 `task.toml` 在 `workspace/harbor_task/task.toml`；禁止 `docker_image`，以 `environment/Dockerfile` 为准；依赖禁止非官方源；npm 使用 bnpm（该行在副本中有删除线，需按后续版本裁决）。

### 可验证判据

- 唯一任务根、唯一 `task.toml`、归档 ZIP 完整性、无多任务根。
- 实际 Dockerfile/安装脚本/pip/apt/npm 源可追溯；不擅自关闭签名校验、不删除哈希约束、不把凭据写入镜像/命令日志。
- 运行身份、HOME、临时目录、日志、输出目录按实际 UID/GID 初始化；只读资产与允许写入路径分离。
- reward 文件存在、数值有限、来源对应当前候选；`RewardFileNotFoundError` 与回传失败分开定位。
- 准备/执行/评分/平台异常四类状态互斥，不把平台 Failed、Agent 非零、任务零分混同。

### 现有 strict skill 覆盖

- 有：`check_platform_rules.py:110-155` 唯一 task.toml（v0.5.0 后降 `needs_manual`）；`:63-84,288-337` 非官方源；`:355-420` bnpm；`:235-271` COPY 源；`check_execution_path.py:344-384` Landlock、`:418-451` HOME/tmp/log、`:454-556` artifacts、`:607-638` os.replace/st_nlink、`:563-604` 提交目录污染。
- 缺口：25/9/3 原因族只部分映射；`docker_image` 已降为建议，与复盘「禁止」冲突；credential-not-in-package 仅 prose；`0.5.6-current.1` 口径未进入 strict 版本台账。

---

## 03. 题包运行问题修复说明：错误 / 正确样例（19题） 副本

- wiki node：`Rts6wCkhkiTwy3kMIJDc42XIndc` → docx：`CYFhdxajhoXnjAxHXnucjVj0n6b`
- 本地正文：`03_package_runtime_fix_examples_19.md`
- 原文：覆盖 19 道题、8 类问题；「独立评分器实际产出数值分数即算运行通过；低分、负分或质量门槛未通过，不另判运行失败」；「保持原始评分与状态，不伪造分数、不改变评分规则」。

### 8 类运行问题

1. 训练或评分强依赖不可用的 Landlock：移除 `landlock_unavailable/ENOSYS` 作为启动前提，但不能删除应用内必要的数据权限校验。
2. HOME、临时目录或日志目录不可写：按实际非 root UID 初始化 HOME/cache/log/workdir；`/tmp`、`/var/tmp` 兼容 1777；不能全员可写。
3. 仅依赖镜像 ENTRYPOINT 启动服务或生成资产：正式入口显式接入准备、完整性、服务就绪；不能假设平台执行 ENTRYPOINT。
4. 固定共享 UID 与过低 `RLIMIT_NPROC` 冲突：避免无关任务共用进程计数预算，保留降权与资源限制。
5. 模型、训练及验证资产未交付：`MANIFEST` 或「运行时挂载」一句话不够；需真实资产、版本、摘要、受控交付说明。
6. 未声明候选产物，独立评分收到空目录：artifacts 声明、源目录、移交范围、评分端路径、SHA256 一致。
7. 公开评估生成额外文件污染严格提交目录：`__pycache__`/pyc/MUJOCO_LOG.TXT 等；可信导入禁写 bytecode，cwd 指向评估输出目录。
8. 原子发布与单链接文件检查发生竞态：`os.replace` 后旧 fd `st_nlink=0` 的合法瞬态，应有界重开，保留 nofollow/普通文件/单链接/大小/完整读取校验。

### 可验证判据

- 运行出分与科研低分/负分区分；可信评分器输出数值即可判「运行通过」。
- Landlock、HOME、ENTRYPOINT、UID/NPROC、资产、artifacts、目录污染、原子发布竞态各有一条正例/反例探针。
- 不通过简单关闭白名单、删除安全检查、手工删除污染文件、无限重试来掩盖正式流程问题。

### 现有 strict skill 覆盖

- 已实现 6 条静态规则：`check_execution_path.py:344-638`。
- 未实现：共享 UID/NPROC、模型资产完整性、MUJOCO_LOG.TXT 具体污染、超时收尾余量、Verifier 串行/预算失配；模型资产仅在台账 prose，MUJOCO/NPROC 关键词近乎缺失。

---

## 04. AutoResearch 题包返修指南：算法要求与平台常见报错

- token：`M8eDdvbHMo9JGAxdvGUcVzUUn8M`
- 本地正文：`04_repair_guide_algorithm_platform_errors.md`

### 要求调整表

- 单题源包只保留 `workspace/harbor_task/task.toml`；历史配置另归档或改说明材料。
- 专家交 Dockerfile，平台准备内部镜像；源 `task.toml` 删除有效 `docker_image` 项；交齐 environment/Dockerfile、context、依赖、资产。
- pip/APT 使用官方源；npm 使用 `https://bnpm.byted.org`；构建代理/认证失败交平台，不把凭据写进题包。
- GPU 题实际 H20/L20；CPU 不增加 GPU；候选列表可含其他型号，但须支持并实际选用 H20/L20；历史卡型标签保留。
- Work/Verifier 两侧独立 sandbox，不强制两份 Dockerfile；复用 Solver 镜像可省略 tests/Dockerfile，但评分依赖须预装，私有 tests 交给新 Verifier。
- 作者校准（3σ、Reference 区间、10h 研究）不得写成 Solver 完成义务；题目算法本身使用 3σ 不按关键词删除。

### 题面/公开评测/评分逻辑常见缺陷

- 题面和实际接口不一致；公开 Dev 或承诺工具不能用；要求优化的产物没有参与评分；最终候选与成绩对不上；私有内容能被 Agent 获得或重建；已有记录证明保护边界被绕过。
- 参考解、Hidden 私有边界和真实评分必须保留；不能为了跑通删评分、交 Hidden、只验证模型文件非空、写默认 0 分代替失败原因。

### 25/9/3 报错码

- P01–P25：Docker Hub/APT/pip/镜像授权/Git lock/包结构/wheel/镜像上传/资产/npm/manifest/COPY/APT 首因/版本缺失/ResolutionImpossible/prepare 脚本/证书临时目录/fixture/权限/bootstrap/sudoers/429/UID/sudo 资产/依赖哈希。
- E01–E09：工作目录可写性、HOME/缓存/日志、Agent 超时、非零退出、LLMRefusal、缺摘要、healthcheck、cgroup、沙箱任务消失。
- S01–S03：reward 文件缺失、Verifier 目录下载失败、reward null/NaN/Infinity。

### 可验证判据

- `task.toml` 唯一、无有效 `docker_image`、配置与实际资源/镜像/artifacts 一致。
- `instruction.md`、公开 Dev、guard、评分器读取路径、最终产物、reward 形成同一条链；合法实现可跑通，违规路径可拒绝。
- Solver 题面不含作者校准义务；3σ 留在专家材料/optimization_evidence。
- 失败码按最早首因定位；不凭最后一行猜根因；无效值不能改成 0。

### 现有 strict skill 覆盖

- 部分覆盖：唯一 task.toml、源规则、COPY、D-C01/D-C03/D-C04、Gate C 六类。
- 冲突/缺口：GPU 卡型无脚本；`docker_image` strict 已降 needs_manual；`provider unknown`、二态 PASS/FAIL、90 项/六组仅官方 vendored 未接入；`0.5.6-current.1` 未纳入。

---

## 05. Skill修改清单与格式说明

- token：`ZK2ddy4YRozlWxxd6QUcx8KPnGe`
- 本地正文：`05_skill_modification_list_format_notes.md`

### 新 skill 口径

- 统一入口 `scripts/audit_current.py`；删除活动流程中的 mode、intake_cohort、target-level、provider 选择。
- 四项规则默认生效：Oracle 位置与入口、全量依赖锁定、正式 reward 二选一、候选 hard gate −10；不再因未填 `new_1104` 跳过。
- provider 未知不阻断源码审阅；未知只表示目标平台未验证，不等于专家漏交字段。
- 最终结果二态：通过/不通过；删除初始未审模板的 `unreviewed`。
- 保留 90 项、工程六组、交付合同六组；发现失败仍完成其余可安全审阅内容；全量阅读记录绑定文件哈希与阅读区间。
- 原严格要求延续：G01 方法空间、G02 Baseline、G03 全 seed/3σ/Reference 区间、2h/8h、依赖源规则。
- QA06/H04/QA17/F07 可引用同一事实；同一根因只改一次；专家返修、平台处理、双方协作、质检端错误分开。

### 四项交付要求

1. `solution/solve.sh` 调 `solution/` 内参考实现，生成正常提交物；Oracle 不直接写 reward；私有参考解不提前暴露给 Agent。
2. 依赖版本锁全：直接、传递、运行时依赖覆盖，实际构建采用；只锁几项或交 `lock.json` 配置不算。
3. 正式 reward 只选一种：`/logs/verifier/reward.json` 或 `reward.txt`；JSON 主 reward 必须有限数值；诊断另放 `result.json`/日志；不能双写。
4. 候选 hard gate 确定 −10：题面、公开反馈、正式评分协议同步；区分候选违约、可信评分器/资产/依赖故障、平台中断；可信故障不能伪装候选 0 分或正常 reward。

### 仍保留的实质检查

- QA06/H04 分别检查成功候选、候选拒绝、可信故障、外层中断；不能仅凭负分断言历史数据无效。
- QA02/QA13 核对 Starter→0、U→1、方向、公式、正式 B/U；换卡时核锚点可比性。
- QA15 公开 Dev ≤2h、正式单 seed ≤2h、同候选多 seed 累计 ≤8h；按真实串并行和共享 deadline 核算。
- QA18/A 完整阅读全部已交实验、主/子/恢复/重试会话及分数记录；未交原生 session 不得认证动态行为。
- G01–G03 可执行方法空间、Baseline 五维、G03 3σ 与 Reference [0.15,0.8]；静态通过不等于 Docker/Harbor 实跑成功。

### 现有 strict skill 覆盖

- `strict_verify.py:119-144` 只取 0.5.0 `audit_current.py` 聚合 decision；`qa_unified.py:39-103` 是 prepare/review 薄封装。
- 90 项、工程六组、交付合同六组、provider unknown、最终二态主要存在于 `official/autoresearch-unified-qa/references/*` 与 `current-check-map.json`；多数官方模块未接入 strict 自有 `scripts/*.py`。
- strict `verdict.py` 仍是多档（PASS/FAIL/INCOMPLETE/PASS_WITH_OPEN + 五类 category），与「最终二态」冲突。
- `−10` 在 strict 仍主要留 review；D-C03 只查 reward 双写，未把四类失败码和可信故障写入可执行 gate。

---

## 06. AutoResearch 交付验收与专家返修分流｜20261107

- token：`DkE5sSPIWhwgT6tGaKgc1u6vnIf`
- 本地数据：`06_acceptance_triage_20261107.json`
- 4 个工作表：`专家返修` 86 行、`无需返修` 738 行、`运营处理` 1 行、`待与算法确认返修意见` 14 行。字段：`题号/专家/题目/当前分类/处理负责人/问题类别/问题说明/处理建议/证据性质/处理进度/备注/返修核实意见`。

### 专家返修表问题类别统计

| 类别 | 数量 |
|---|---:|
| CPU / CUDA 镜像选型 | 28 |
| 异常 reward 契约 | 19 |
| 超时收尾余量 | 12 |
| 异常 reward 契约；超时收尾余量 | 5 |
| GPU 设备权限设置 | 4 |
| CPU / CUDA 镜像选型；超时收尾余量 | 1 |
| CPU / CUDA 镜像选型；异常 reward 契约 | 1 |
| 其余 19 类（公开数据可重建 Hidden、未公开限制、换卡/计时锚点、Judge 吞异常、表达式解析器拒字面量、代码裁剪与题面冲突等） | 各 1 |

### 典型原文判据

- 公开数据与切分信息可用于重建私有评测输入：公开 manifest 保留 train/dev 哈希与顺序、private 为同序列连续切片、重建任务标签是输入自身；应更换独立评测池或不可还原切分，并用 Solver 可见材料复核不能逐项恢复正式私有输入。
- 异常 reward 契约：外壳对所有非零退出且无 reward 的情形写 −1 并统一标 `E_TIMEOUT`；应只对明确候选违规发布惩罚值，可信资产/运行环境/解释器/判题器故障保留诊断并不发布数值 reward。
- 超时收尾余量：内层耗时达到外层 Verifier 7200s 边界，未预留停止进程、读取指标、写入并回传 reward 的余量；应使用共享绝对截止时间，按启动/清理/日志回传实测开销留余量。
- CPU/CUDA 镜像：Work/Judge 均配置 CPU 却用 CUDA/NVIDIA 基础镜像；改用匹配数值栈的 CPU 镜像和依赖，固定版本后复核基线/参考；不能声称该次分数必然无效。

### 可验证判据

- 从「问题类别 + 问题说明 + 处理建议 + 证据性质」抽取为静态规则：镜像选型、异常 reward、超时余量、GPU 权限、公开数据可重建 Hidden、未公开限制、换卡/计时锚点、Judge 吞异常、题面-实现不一致。
- 分流表和文档口径要分版本：这是 2026-11-07 分流材料，不能直接覆盖 11-13 终检汇总或 11-14 当前平台 PASS 报告。

### 现有 strict skill 覆盖

- `异常 reward` 部分对应 D-C03（双写）和 prose；`超时收尾余量` 在 vendor engineering review 但未接线；`CPU/CUDA 镜像选型`、`GPU 设备权限`、`公开数据可重建 Hidden` 无可执行实现；`MUJOCO_LOG.TXT`/`NPROC` 关键词缺失。

---

## 07. 返修记录豁免清单与质检口径

- token：`NkNrdZmmQowbPZxpVbdcFjzhnKe`
- 本地正文：`07_waiver_list_qa_scope.md`

### 核心口径

- 「按原 v0.3.10 完整检查，再逐原因豁免」；当前版本 `0.3.10-standard-waiver.5`；原标准 NOP、三门控、21 项、Harbor 六项、轨迹行为/分数、资源时长、四项指纹全部保留；七项格式前检不能代替完整质检。
- 豁免不等于取消检查：原检查和已有记录照常逐项核验，报告同时保留原判、证据、具体豁免及最终状态；历史缺 NOP、缺新版字段可免补跑/补造，但不能写成已运行/已达标/检查通过。
- 检查顺序：清点完整当前包和已有证据 → 三门控 → QA01–QA21/H01–H06 每项记录内容和证据 → 阅读两轨实际内容并比较研究条件 → 逐问题应用豁免 → 回读完整报告。
- 逐项表列出 G01–G03、QA01–QA21、H01–H06、T01/T02 的「可免/无需新增」与「仍须处理」边界。
- 结论：`PASS_WITH_WAIVERS` 或 `FAIL`；`format_report` 只是格式子报告；平台 Harbor 实跑另行完成。

### 可验证判据

- 每个 check 必须有 original status、evidence、waiver reason、final status 四层字段；不得用一项总豁免覆盖 QA17/H06/G03。
- 旧轨迹字段缺失、旧 NOP 缺失、旧指纹不匹配可分别豁免，但当前入口、依赖、Hidden 来源、移交路径、真实内容矛盾仍失败。
- 报告必须回读；未审完不能凭格式通过给总 PASS。

### 现有 strict skill 覆盖

- `qa_official.py` 对 21 项有预填（大量 manual），`SKILL.md:395-407` 自述官方层 15/21 仍需人读；`strict_verify.py` 只取官方聚合 decision；`SKILL.md:405-407` 有 manual 不得自动转 pass 的纪律。
- 缺口：完整逐项 waiver ledger、同 trial config/result/reward/log、原始判/豁免/终判三层结构在 strict 自有脚本未形成强校验；`PASS_WITH_WAIVERS` 与 0.5.0 二态 PASS/FAIL 冲突。

---

## 08. AutoResearch 返修格式自检与完整包交付规范（2026-10-20）

- token：`QRGqd3E4xoKsSTxk8X3ckVsanDf`
- 本地正文：`08_format_self_check_delivery_spec_20261020.md`

### 核心口径

- `check_package.py v1.2.1`：只读检查本地目录/ZIP/TAR/TAR.GZ；不上传、不运行提交代码、不拉/构建镜像；Python ≥3.11 标准库即可。
- 前检尺度：明确错误阻断，不确定提醒；`ERROR` 修复后重检，`WARN` 不阻断；输入读取失败/超预算返回「检查未完成」，不算通过，也不作为平台格式不合格。
- 完整包三类目录：`workspace/`、`expert_evidence/`、`optimization_evidence/`；不能只交 harbor_task、修改文件或补丁。
- 提交一次同版本 NOP 记录（config/result/reward/log）；两条轨迹每轮八字段；公开 Dev 与 Hidden 材料；训练型交模型/重载证据；单容器、独立 sandbox、Verifier 自备评分依赖。
- CPU 配置示例中仍出现 `docker_image`，但正文又说明专家提交 Dockerfile、内部镜像由字节侧构建；这是版本冲突点，后续 11 月文档明确删除有效 `docker_image`。
- 脚本检查范围：三目录、任务根、TOML 语法/类型/separate、镜像来源、Compose 四类文件、GPU/资源、不支持约束、COPY/ADD 缺源/越界、artifacts。
- 正式目录禁止 `docker-compose.yaml/yml`、`compose.yaml/yml`；GPU H20/L20；CPU 题 `--task-kind cpu`；报告 `PASS/PASS_WITH_WARNINGS/FAIL/检查未完成`。

### 可验证判据

- 三目录完整；唯一任务根；`instruction.md`/`task.toml` 非空；environment/tests 存在；无 Compose 直属文件。
- TOML 显式 separate；GPU/CPU 资源合法；COPY/ADD 源真实存在且在当前 context；无越界复制私有材料给 Agent；artifacts 路径与评分读取一致。
- `WARN` 与 `ERROR` 分开；检查未完成不得当通过；格式前检不得冒充完整质检或平台实跑。

### 现有 strict skill 覆盖

- 与 strict 的 `check_platform_rules.py`、`check_delivery_contract.py` 部分重合；但 strict 对 `docker_image` 已降 needs_manual、对 Compose/官方源/COPY/上下文已有实现；对「检查未完成不得判通过」「完整包三目录」没有完整官方 checker 接线。
- 注意：该文档示例中的 `docker_image` 与 11 月禁令冲突；应按时间和平台当前版本裁决，不能把旧示例当当前合规结论。

---

## 09. AutoResearch 专家线下标注教程 V4 副本

- wiki node：`B6Jgw94Z2inUUKkwIcfcERKtnNe` → docx：`Tjk8dXrItoOZV0xeSL7ct3Dunmf`
- 本地正文：`09_expert_annotation_tutorial_v4.md`
- 精读范围：全文目录 + 判据相关章节（1–140、245–605、734–1030），附录 PCA 示例未作为通用规则吸收。

### 关键原文口径

- 教程 V4 对应审阅 Skill 0.3.10；内场 GPU 优先 H20、接受 L20；CPU 题不增加 GPU；原题其他卡型需调整题目/配置并核对换卡影响，历史记录保留真实卡型。
- 公开 Dev 数据和评分脚本必须保留给 Agent；最终私有评分材料留独立 Verifier；不强制固定 `tests/hidden_assets/` 目录，但空目录或「平台会注入」不算完成。
- Solver/Verifier 必须不同 sandbox，可复用 Solver 镜像；Verifier 依赖须在所用镜像准备，不能继承 Agent 临时装包/缓存/未移交文件。
- 两条轨迹每轮八字段；失败也保留，未出分记 null 并说明原因；两轨有效时长默认 10h，非训练短迭代例外 7h；两条不相加。
- QA21 四项指纹：`run_summary.json.task_binding.hash_profile` + `task_content_sha256`，范围固定 environment/、task.toml、tests/、instruction.md。
- NOP 自检：同次 Trial 的 config/result/reward/log；平台已有匹配记录可复用；格式自检通过仅表示可进入下一步，最终仍需 AIDP 实跑。
- G01/G02/G03：真实方法接口、合理 Baseline、Reference [0.15,0.8]、3σ/5σ、全部 seed 配对；不能改锚点 U 制造达标；Reference 使用与 Baseline 同协议同 seed 的全部有效运行聚合值。
- `task.toml` 示例含 `docker_image`，但后续 11 月文档/复盘要求删除；V4 自身属于旧 0.3.10 教程，与 0.5.x 当前规则存在版本冲突。
- 评分：连续、单调、不裁剪；B→0、U→1；允分 >1；U≠B；多目标写权重/单位/聚合/缺失值；Reference 归一化 0.15–0.8。
- 错误与 Hard Gate：旧教程写「非作弊 Hard Gate 返回 −1；格式错误、超时、资源超限、基础设施错误仍不同失败类型，不能全折算 −1，也不能伪装 0 分」；当前 0.5.x/平台报告已改为 −10 作为候选违约哨兵，需版本化区分。
- 数据隔离：Hidden、Reference、optimization_evidence/、已汇总 expert_evidence/ 不进 Agent 镜像/缓存/Git；Agent 只移交 artifacts 指定最终候选；Verifier 从干净结果目录出分；候选不能读私有标签、改写评分器、伪造结果。
- `best_method/`：唯一最终方法，不含 Reference/Hidden/评分日志/run ID/审核材料/密钥；能在干净任务快照中重新运行并成功出分；提交前专家自查覆盖题面、镜像、轨迹、指纹、NOP、GPU、Hidden、Verifier 出分、冻结面恢复等 30+ 项。

### 可验证判据

- 指纹算法必须按四项冻结输入计算，并记录 hash_profile；修改题包后不静默替换评分公式或允许修改范围。
- seed 实际进入随机过程；同方法跨 seed 除 seed 外代码/配置不变；重复训练与固定模型随机评测区分；全部有效成对运行聚合，不取最好一次。
- `expert_annotation.json` 仅机读标注，不写运行日志/审核结论；`run_summary.json` 记两轨有效时长、task_binding、自验状态；`trajectory_*.json` 每轮八字段；`best_method/` 唯一且可重跑。
- 所有题面限制由环境/评分程序实际执行；超时能中断相应工作；warning/联网降级不当约束生效；正式运行不依赖 Compose。
- 评分函数、reference 区间、3σ、模型重载、Verifier 单命令出分、失败分类、原子写、冻结面恢复均有可检查证据。

### 现有 strict skill 覆盖

- 0.3.10 预填层：`qa_official.py:199-214` qa02 公式/锚点、`:229-239` qa04 3σ、`:283-290` qa10 冻结重载、`:303-312` qa13 B/R、`:348-353` qa16 时长、`:373-375` qa18、`:378-385` qa19 seeds、`:393-401` qa21 指纹 manual。
- strict 自有 `qa.py`/`strict_verify.py` 并行跑 0.3.10/0.5.0 聚合 decision，但很多官方模块未接线；`task_fingerprint.py` 在 vendored official 中未纳入 strict 自有 scripts。
- 版本冲突：V4 的 `−1`、docker_image 示例、NOP 必交、两轨 10h/八字段/四指纹与 0.5.0「最终二态、provider unknown 不阻断、NOP 不恢复、旧固定轨迹/格式不恢复」冲突；当前平台 0.5.6-current.1 报告又更新为 90 checks/50 evaluated 口径，strict 仓库中 `0.5.6-current.1` 完全缺失。

---

## 覆盖差异总表（结论）

| 平台经验族 | strict 可执行覆盖 | 结论 |
|---|---|---|
| 唯一 task.toml / 官方源 / COPY context / bnpm / Compose | 有 `check_platform_rules.py`，部分规则已降 needs_manual | 覆盖但口径降级；与 11 月禁令冲突 |
| D-C01–D-C04：formal reward、双写、Oracle entry/COPY solution | 有 `check_delivery_contract.py` 与测试 | 覆盖较强；但调用链/输出同源仍留 review |
| Gate C 运行经验六类：Landlock、HOME、ENTRYPOINT、artifacts、污染、原子发布竞态 | 有 `check_execution_path.py` | 覆盖 6/20 类左右 |
| reward 有限数值、四类失败码、−10、0.0 Starter、可信故障不伪装 | 主要 prose / field-reports / platform report | 大缺口 |
| 90 项、工程六组、交付合同六组、provider unknown、最终二态 | 文档+薄封装；官方模块多数未接线 | 大缺口，且 strict verdict 多档冲突 |
| best_method frozen_ast / data.py contract_policy / 不放宽可信 policy | strict 自有 0 命中 | 当前平台 H04/v30 经验催生的新判据，完全未吸收 |
| 终检五类：难度过低/过高、普通 0、Verifier 预算、评分门防作弊 | 0 命中 | 完全未吸收 |
| 四项指纹、八字段、10h/7h、NOP、PASS_WITH_WAIVERS | 旧 0.3.10 预填/prose；0.5.0 不恢复 | 版本冲突需裁决，不能机械回灌 |
| GPU H20/L20、旧卡结果不冒充、CPU/CUDA 镜像选型、GPU 设备权限 | 仅 prose / 分流表 / vendored 文档 | 无可执行 gate |
| 公开数据可重建 Hidden、超时收尾余量、Verifier 串行低效/预算失配 | 仅 prose | 无可执行 gate |

## 第一性原理审查与建议（不直接改代码）

1. **版本轴必须先于规则轴**。同一仓库同时存在 0.3.10 V4、0.5.0 current、0.5.6-current.1 平台报告；`-1/-10`、`docker_image`、NOP、PASS_WITH_WAIVERS、90/21 项、两轨 10h 等冲突都来自版本混用。建议先建立 `rule_version` 矩阵（source doc + share date + skill version + supersedes），再决定 checker 接入哪一层。
2. **机制层分三类**：A 机械可证（sha、AST、文件、TOML、reward 文件、COPY）、B 需要受控消融（合法/违规样例、guard 行为、failure path）、C 只能平台实跑（镜像拉取、GPU、Harbor、Hidden）。当前 strict skill 最大问题是把 B/C 的 prose 当成 A 的「已覆盖」，以及把 A 写进模型评审自由裁量。
3. **消融实验应成为新规则准入条件**：每条新增判据必须准备 bad/good 双向最小样例；例如 `failure_zero` 应有「失败写 0.0 被拒 / Starter 0.0 放行」，`best_method frozen_ast` 应有「weights_only=False 被 FIXED_CONTRACT / True 放行」，`contract_boundary` 应有「nonlocal 被拒且已披露 / 合法命名函数放行」。
4. **奥卡姆剃刀**：不要把 9 份文档全部塞进一个万能 checker。按「当前版本、可机械判定、反例可构造、与平台最终 PASS 报告一致」四个条件裁剪；历史教程只进 archive/reference，不进当前 gate。
5. **高内聚低耦合**：建议拆为 `rule_catalog`（文档/版本/证据）、`mechanical_checks`（A）、`ablation_cases`（B）、`platform_scope`（C，只标 unverified 不判分）四层；`strict_verify` 只负责编排和 verdict，不在脚本里硬编码互相冲突的旧规则。
