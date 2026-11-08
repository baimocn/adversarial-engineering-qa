# 仅格式前检子报告

不代表整题质检结论；完整三门、21项、Harbor六项、两轨与豁免结论请看 report.*。

# 旧题格式返修检查

本轮结论：FAIL
阶段：format_repair

本批只审当前格式与核心交付语义；历史记录与平台实跑事项不作为本轮门槛。
平台运行状态：not_executed；本次未运行模型、题目代码、Docker 或 Harbor。


## 本轮七项核心检查

- F01 [pass] 当前必需目录、文件与 TOML 接口：当前三目录/TOML结构有效，显式separate和artifacts；未依赖旧resources。
  审阅证据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md
- F02 [pass] 有效构建或镜像方案、构建上下文及 COPY 来源：Agent和Verifier采用各自Dockerfile/context；COPY来源存在，模型/数据仅当前沙盒本地运行。
  审阅证据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/environment/starter/exp/exp_classification.py
- F03 [pass] 评分入口、独立依赖声明与固定输出路径：test.sh及独立requirements/可信数据管线完整，固定/logs/verifier输出。
  审阅证据：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/tests/requirements.txt
- F04 [pass] 提交物 artifacts 移交契约：artifacts源/workspace/solution与评分读取绝对路径一致。
  审阅证据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/test.sh
- F05 [pass] 公开 Dev、私有 Hidden 供给与 Agent 隔离：公开Dev评价与19受试者在Agent；私有TEST经已有注入契约及NOP日志支持，fail-closed，不把空README当实际数据。
  审阅证据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；expert_evidence/nop_trial_native/verifier/test-stdout.txt
- F06 [pass] separate、单容器、无 Compose 与当前目标资源配置：当前H20/L20、Verifier0GPU、separate无Compose/未支持资源字段；网络防护迁移缺口独立按H02白名单处理。
  审阅证据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile
- F07 [fail] 当前评分实现与冻结面无确证故障或作者泄漏造假：当前评分器仍用旧B=.644488，新正式汇总B=.644707676857，主分数锚点与正式来源有确定静态冲突；并非历史换卡验证缺口。
  审阅证据：workspace/harbor_task/tests/evaluate_verify.py；optimization_evidence/comparison_summary.json
  整改：统一合法正式Baseline及评分器锚点，修正混用旧/新成绩的汇总。
  验收：正式B代入reward为0，U=1为1，题面/公式/正式汇总一致。

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
