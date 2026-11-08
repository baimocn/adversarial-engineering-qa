# 仅格式前检子报告

不代表整题质检结论；完整三门、21项、Harbor六项、两轨与豁免结论请看 report.*。

# 旧题格式返修检查

本轮结论：FAIL
阶段：format_repair

本批只审当前格式与核心交付语义；历史记录与平台实跑事项不作为本轮门槛。
平台运行状态：not_executed；本次未运行模型、题目代码、Docker 或 Harbor。


## 本轮七项核心检查

- F01 [pass] 当前必需目录、文件与 TOML 接口：任务根和三目录、task.toml原生接口完整。
  审阅证据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md
- F02 [pass] 有效构建或镜像方案、构建上下文及 COPY 来源：两侧Dockerfile分别使用environment/tests上下文，COPY来源齐全。
  审阅证据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile
- F03 [pass] 评分入口、独立依赖声明与固定输出路径：评分入口绝对/tests/test.sh，numpy独立依赖，reward固定/logs/verifier；sleep CMD仅存活。
  审阅证据：workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/grader.py
- F04 [pass] 提交物 artifacts 移交契约：顶层artifacts覆盖/workspace/solution，Verifier按原绝对路径读取。
  审阅证据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/grader.py
- F05 [fail] 公开 Dev、私有 Hidden 供给与 Agent 隔离：task.toml dev_score_command将--out设为/workspace/results.json；Agent Dockerfile使/workspace root所有0755并切换USER agent，仅/workspace/solution属于agent。evaluate.py无条件open该输出，配置命令在默认身份下不可写并退出失败。
  审阅证据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/environment/public_eval/evaluate.py
  整改：将配置的Dev输出改到Agent可写目录，例如/workspace/solution/results.json，并同步任何引用；或在镜像中仅准备所需可写输出位置。
  验收：task.toml命令、镜像权限与evaluate.py实际写路径静态一致；无需通过放宽公开/私有冻结面权限修复。
- F06 [pass] separate、单容器、无 Compose 与当前目标资源配置：显式separate、两侧CPU16/GPU0；无正式Compose和不支持字段；源码无另起工作环境要求。
  审阅证据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh
- F07 [fail] 当前评分实现与冻结面无确证故障或作者泄漏造假：instruction §3要求模型可加载，§6要求模型产物；grader仅读取test_pred.npy，既不检查model.pt存在也不重载。源码AST检查不证明模型可加载，缺模型仍可进入正常评分。
  审阅证据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/contract_guard.py；workspace/harbor_task/environment/public_eval/protocol.json
  整改：在独立可信Verifier实施模型存在及可加载质量门并使用与题面一致的安全重载接口；同步准备独立依赖。
  验收：可信评分调用链中可定位的模型检查/加载与失败分支，明确模型和预测对应路径。

## 平台后续事项（不阻断本轮）

- 字节内部准备、构建或导入镜像并配置实际 ICM tag；本轮不要求专家补内部镜像运行记录。
- 平台实际构建和启动，核对依赖、基础镜像 digest 及 bash/解释器；静态推断不能冒充运行结果。
- 平台核对 root、seccomp、网络及实际分配的沙盒权限设置。
- 平台后续执行当前版本 Harbor Trial/NOP、独立 Verifier 和 reward 收集；其缺口不作为本轮专家返修门槛。
- 平台实际核对提交物移交及目标 H20/L20（GPU 题）运行；本轮不重算历史资源或成绩。
- 移除不支持的禁网字段后，新的联网或外部查表防护尚未落实，列为平台迁移事项，不要求本批专家新增防护实现或补跑；当前确证 Hidden 暴露或假 reward 仍属当前核心缺陷。

## 本轮不复查的历史事项

- 历史运行字段、资源差异和旧卡记录
- 历史轨迹八字段、状态、时间及行为重审
- 历史运行时长、方法轮次和最高推理档记录
- 旧题包指纹、哈希和旧版本重新绑定
- 历史 Baseline/Reference 成绩重跑与换卡复验
- 旧版未要求的当前 Trial/NOP 记录
