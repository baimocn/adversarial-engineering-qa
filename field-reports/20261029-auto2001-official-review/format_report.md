# 仅格式前检子报告

不代表整题质检结论；完整三门、21项、Harbor六项、两轨与豁免结论请看 report.*。

# 旧题格式返修检查

本轮结论：FAIL
阶段：format_repair

本批只审当前格式与核心交付语义；历史记录与平台实跑事项不作为本轮门槛。
平台运行状态：not_executed；本次未运行模型、题目代码、Docker 或 Harbor。


## 本轮七项核心检查

- F01 [pass] 当前必需目录、文件与 TOML 接口：三目录、选定task根及TOML接口存在。
  审阅证据：workspace/harbor_task/instruction.md；workspace/harbor_task/task.toml
- F02 [pass] 有效构建或镜像方案、构建上下文及 COPY 来源：双Dockerfile按各自context，COPY来源完整；ICM镜像准备是平台事项。
  审阅证据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile
- F03 [fail] 评分入口、独立依赖声明与固定输出路径：当前评分器超时分支返回3项，调用接收2项，约定的失败reward处理有确定静态错误。
  审阅证据：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/evaluate_verify.py
  整改：统一推理函数所有分支返回二元组，并由可信主进程处理超时与失败输出。
  验收：源码所有返回分支与调用方参数个数一致；平台后续验证超时能产生约定有限reward或明确约定的失败状态。
- F04 [pass] 提交物 artifacts 移交契约：顶层artifacts含/workspace/solution，与Verifier消费目录一致。
  审阅证据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/test.sh
- F05 [pass] 公开 Dev、私有 Hidden 供给与 Agent 隔离：公开Dev和训练/验证数据供Agent；Hidden仅tests注入契约并有历史日志调用，不COPY进Agent。
  审阅证据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/hidden_assets/inject_contract.json；workspace/harbor_task/tests/test.sh；expert_evidence/nop_trial_native/verifier/test-stdout.txt
- F06 [pass] separate、单容器、无 Compose 与当前目标资源配置：separate、无正式Compose；本沙盒本地进程；AgentH20/L20单卡、VerifierCPU0GPU。
  审阅证据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/evaluate_verify.py
- F07 [fail] 当前评分实现与冻结面无确证故障或作者泄漏造假：评分器存在确定超时错误；题面公开Dev单命令路径与镜像实际布局不一致。
  审阅证据：workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/instruction.md；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/task.toml
  整改：将题面和submit命令统一为明确cwd与绝对solution/data路径，例如从/workspace调用solution/evaluate.py并指定/workspace/solution。
  验收：题面、配置和镜像布局形成同一有效路径链，公开Dev可通过所声明命令找到模型、权重和公开数据。

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
