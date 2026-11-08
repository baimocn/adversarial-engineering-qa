# auto2768 审计报告

来源表：tblHNtQNFPVwuKiP；记录：recvxeP2AYB9GI；提交事件：124417。
题包 SHA256：`608c25681411083167cdcfb6ca3ae9963212fda9b807d62187d32294805aebe4`。
Skills SHA256：`105b9aa25e8bd309246eb8a01215b47997cfb87c1b8059ee78a6591a3ccb4b60`（均按给定标识记录）。

已读取组合入口、原版规则与案例、平台专项、规则来源兼容边界、平台案例。仅本次指定包与平台目录；外部来源链接未访问。未执行题包或平台操作。

## A：原版增量审计

auto2768：无必须修改。

此结论仅表示已读材料未确认六类必须修改事项，不表示轨迹已通过。

| 类别 | 状态 | 检查与边界 |
|---|---|---|
| A01 | 未执行 | 未提供原始主、子、恢复、重试会话；trace-inventory.json 为 {}，无法建立完整会话到当前候选及权威评分的对应。已有历史 NOP 不能替代当前正式求解轨迹。 |
| A02 | 未执行 | 两份 trajectory JSON 为轮次摘要而非逐消息会话；未执行实际违规轨迹审查，不据摘要断言合规或违规。 |
| A03 | 已检查 | 通读题面与实际评分链：两图测试准确率等权宏平均，按可信 B/U 归一化；单套预测评分、不重训、不三种子聚合及模型仅加载质量门均已明确披露。未确认影响正常合规提交的直接冲突。 |
| A04 | 已检查 | 目标预测实际从 artifacts/<dataset>/test_pred.npy 读取并与私有测试标签比较后进入 reward；训练日志、解释及来源附件不另立优化内容缺失问题。 |
| A05 | 已检查 | 公开数据、starter、Dev 入口的 COPY 资产存在；Dev 默认从 /workspace/data 读取验证标签，输出到可写 solution。无正常调用未恢复失败或正常调用必然失败的直接证据。依赖可安装性未实跑验证。 |
| A06 | 已检查 | 按 Dockerfile/context 确定公开面：仅 public_assets/starter/public_eval；tests/private、校准与参考方法未进入 Agent 镜像。公开 baseline、Dev 标签、seed 不作为泄漏。未证明具体 Hidden/参考解公开可见或成功重建使用；二进制资产未反序列化。 |

会话覆盖：`trace-inventory.json = {}`，实际会话清单为空，`trace_coverage=[]`。没有可核对的消息总数或读取区间；不将轮次摘要当会话。

评分静态链：`/workspace/solution` 移交 → `bash /tests/test.sh` → 可信源码检查与 calibration → 模型加载质量门 → 两图 `test_pred.npy` 对比私有 `y_test` → 两图准确率等权宏平均 → `(x-B)/(U-B)` → reward。题面明确不重训、不从模型重新生成预测，未据此追加来源真实性要求。

难度：未执行判断；仅供参考，不作验收要求。

## B：平台专项

平台静态配置检查已完成；当前平台运行检查未执行，材料未提供，不作运行成功结论。

| 源包规则 | 状态 | 依据 |
|---|---|---|
| B-C01 | 符合 | 完整 evidence-input 文件树仅一份 task.toml，位于指定 workspace/harbor_task/task.toml。 |
| B-C02 | 符合 | 源配置无 docker_image；两侧 Dockerfile 非空，实际 COPY 资产均在各自 context，dockerignore 只排缓存等。源声明选 tests/Dockerfile 专用分支；平台实际选择版本未提供，不能由两份文件推定隔离或构建成功。 |
| B-C03 | 符合 | 当前生效声明使用官方默认 APT、PyPI 与 PyTorch CPU 源；未见非官方依赖源。ARG 可覆盖不是已发生的违规；无平台构建参数，无法确认运行时是否覆盖。 |
| B-C04 | 不适用 | 源包实际构建安装链为 apt/pip，不使用 npm；不要求添加 npm。若使用 npm，应适用 bnpm 指定例外。 |

专用 Verifier 分支：源包包含 tests/Dockerfile，预置入口、可信评分实现及 private，声明 separate 与 artifacts 移交。当前平台版本和实际镜像选择未知；不假定 tests 自动上传，也不以 Dockerfile 数量证明隔离。

| 阶段 | 状态 | 观察与覆盖限制 |
|---|---|---|
| 准备 | 材料未提供 | platform-evidence 为空；当前包构建步骤、实际参数、镜像 digest/选用配置未提供。本次不执行构建。包内历史本地 Trial 设置结束记录不等于当前平台准备成功。 |
| 执行 | 材料未提供 | 当前平台 Agent/子会话/恢复重试、实际身份挂载和候选移交材料未提供。本次未执行；历史 nop 非求解会话，不能替代当前 Agent。 |
| 评分 | 材料未提供 | 当前正式候选→Verifier 输入→原始指标→平台 reward→回传链未提供。历史 nop 已归档 reward=0.0，但为无提交 FORMAT_ERROR、grader rc=1；非当前有效正式评分，不将零分与非零退出或超时等同。 |

历史原始结果：原生本地 `auto2768-nop-20261008T163026Z` 的 result 采用 reward **0.0**，exception_info 为 null；完整评分 stdout 明确 `INVALID / FORMAT_ERROR`、缺 cora 预测、grader rc=1。它是无提交分支，不是当前有效正式成绩。另有历史 Docker 模拟 reward **-0.1383622641509434**、退出 0，保持原值；不冒充原生 Trial 或当前评分。

已确认当前问题：无；findings 为空。准备 25、执行 9、评分 3 原因族均仅按已有材料检查，未从日志缺失推断当前故障。

### 处理清单

- 专家需返修：无。
- 平台需处理：无已确认必须修改项。覆盖所缺材料为当前包的构建完整日志与实际配置、Agent 全会话/候选移交记录、Verifier stdout/stderr、原始指标、权威 reward 和归档回执；最小获取方式为平台提供本 Trial 既有导出，非要求专家补跑。
- 仅记录：历史 NOP 无提交的 0.0 与退出 1；历史模拟原分及其适用边界。

## 证据位置（相对报告根目录）

- `evidence-input/workspace/harbor_task/task.toml`，L17-L61：唯一任务源配置；artifacts 为 /workspace/solution，separate 声明，无有效 docker_image 项。
- `evidence-input/workspace/harbor_task/environment/Dockerfile`，L5-L47：官方基础镜像；公开资产、starter、public_eval 分别复制；agent 身份与 solution 写权限明确，不复制 tests/reference/expert_evidence。
- `evidence-input/workspace/harbor_task/tests/Dockerfile`，L3-L34：专用 tests context 预置 grader、可信 guard/policy/calibration、私有标签及入口，独立准备评分依赖。COPY 源文件均存在且未被 dockerignore 排除。
- `evidence-input/workspace/harbor_task/tests/grader.py`，L108-L187：先静态检查与可信校准，再加载模型质量门及两图预测，和私有 y_test 比较，宏平均并归一化写 reward。
- `evidence-input/workspace/harbor_task/tests/contract_guard.py`，L856-L997：注册表与完整 scaffold profile 检查，静态源码数据流和配置校验；不执行候选模块。
- `evidence-input/expert_evidence/repair/harbor/native_nop_trial/native_trial/verifier/test-stdout.txt`，L1-L8：历史 NOP 缺少 cora/test_pred.npy；INVALID/FORMAT_ERROR，reward 0.0，grader rc=1。
- `evidence-input/expert_evidence/repair/harbor/native_nop_trial/native_trial/result.json`，字段 trial_name、task_checksum、verifier_result、exception_info：历史 trial auto2768-nop-20261008T163026Z；权威归档 rewards.reward=0.0，exception_info=null。

## 覆盖限制

- 原始会话清单 trace-inventory.json 实际内容为 {}，没有列出的会话或消息总数；trace_coverage=[]，不伪造 total_messages/read_ranges/complete。A01/A02 未执行。
- 包内 trajectory_codex.json、trajectory_seed.json 只有 rounds 等摘要字段，训练 training.jsonl 和旧 events 不能充当完整主/子/恢复/重试工具会话；无法作轨迹通过结论。
- platform-evidence 目录为空；未提供当前平台准备、执行和评分材料。历史本地探针与 Trial 只能证明各自记录范围，不能替代当前包、当前候选或平台运行。
- 静态审查不执行题包、构建、Harbor、Verifier、训练、安装或下载；未反序列化 .pt 模型或图资产，不能实证二进制内容与声明一致，不能证明网络可达或依赖完整兼容。
- 当前题包 SHA256 与 Skills SHA256 按用户和模板记录；未提供原始压缩包供重算，未将解压目录哈希冒充包哈希。
- 未取得可信的当前候选完整评分链，难度跳过，仅供参考，不作验收要求。
- 材料缺失仅限制本次覆盖；不产生专家补历史双轨、NOP、3σ、时限或校准义务，不自设全局待核验验收结论。
