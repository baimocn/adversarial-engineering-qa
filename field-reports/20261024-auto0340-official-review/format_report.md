# 仅格式前检子报告

不代表整题质检结论；完整三门、21项、Harbor六项、两轨与豁免结论请看 report.*。

# 旧题格式返修检查

本轮结论：FAIL
阶段：format_repair

本批只审当前格式与核心交付语义；历史记录与平台实跑事项不作为本轮门槛。
平台运行状态：not_executed；本次未运行模型、题目代码、Docker 或 Harbor。


## 本轮七项核心检查

- F01 [pass] 当前必需目录、文件与 TOML 接口：三目录与必需任务文件、TOML环境/独立Verifier接口可定位。
  审阅证据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md
- F02 [pass] 有效构建或镜像方案、构建上下文及 COPY 来源：两套本地Dockerfile/context与COPY来源一致；内部镜像准备属平台后续。
  审阅证据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile
- F03 [pass] 评分入口、独立依赖声明与固定输出路径：专用Verifier预置/test.sh评分入口、独立依赖与固定reward路径齐全；运行资源错误另列F06/H03。
  审阅证据：workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/evaluate_verify.py
- F04 [pass] 提交物 artifacts 移交契约：顶层artifacts整体移交/workspace/solution，与test.sh读取一致。
  审阅证据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/test.sh
- F05 [pass] 公开 Dev、私有 Hidden 供给与 Agent 隔离：公开66条已进Agent，Hidden真实资产私留专家侧并有明确安全注入路径及已有NOP分支证据。
  审阅证据：workspace/harbor_task/environment/Dockerfile；expert_evidence/hidden_set/README.md；expert_evidence/nop_trial/trial.log；expert_evidence/repair/dataset_resplit_20261021/resplit_report.json
- F06 [fail] separate、单容器、无 Compose 与当前目标资源配置：显式separate和单容器成立，但Verifier配置0GPU，实际train.py断言CUDA且TDMPC2强制cuda，当前资源配置不满足运行需求。
  审阅证据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/starter/tdmpc2/train.py:47-49；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:61-64
  整改：修复实际CUDA资源配置、健康Q更新和候选推理权限边界，保持题面/协议一致。
  验收：相应源码/配置静态链闭合；真实零初始化Q梯度控制及健康正式B/R。
- F07 [fail] 当前评分实现与冻结面无确证故障或作者泄漏造假：真实零初始化Q与预测端symlog导致Baseline仍无Q学习梯度；root父进程导入候选代码使可信冻结面保护失效。
  审阅证据：workspace/harbor_task/environment/starter/tdmpc2/common/math.py:5-29；workspace/harbor_task/environment/starter/tdmpc2/common/math.py:71-77；workspace/harbor_task/environment/starter/tdmpc2/common/world_model.py:30-34；workspace/harbor_task/environment/starter/tdmpc2/common/init.py:4-22；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:293-312；expert_evidence/repair/value_loss_ablation/README.md；expert_evidence/repair/value_loss_ablation/ablation_fixed.json；workspace/harbor_task/tests/evaluate_verify.py:205-245；workspace/harbor_task/tests/Dockerfile
  整改：修复实际CUDA资源配置、健康Q更新和候选推理权限边界，保持题面/协议一致。
  验收：相应源码/配置静态链闭合；真实零初始化Q梯度控制及健康正式B/R。

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
