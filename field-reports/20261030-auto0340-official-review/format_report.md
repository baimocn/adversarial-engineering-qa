# 仅格式前检子报告

不代表整题质检结论；完整三门、21项、Harbor六项、两轨与豁免结论请看 report.*。

# 旧题格式返修检查

本轮结论：FAIL
阶段：format_repair

本批只审当前格式与核心交付语义；历史记录与平台实跑事项不作为本轮门槛。
平台运行状态：not_executed；本次未运行模型、题目代码、Docker 或 Harbor。


## 本轮七项核心检查

- F01 [pass] 当前必需目录、文件与 TOML 接口：三目录与任务根完整，TOML可解析，核心接口存在。
  审阅证据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md
- F02 [pass] 有效构建或镜像方案、构建上下文及 COPY 来源：Agent context=environment、Verifier context=tests，COPY来源均在各自context；有效源构建方案存在，ICM镜像由平台准备。
  审阅证据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile
- F03 [pass] 评分入口、独立依赖声明与固定输出路径：评分入口/tests/test.sh及独立依赖在位，reward固定/logs/verifier路径；实际逻辑故障列F07。
  审阅证据：workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/requirements.txt
- F04 [pass] 提交物 artifacts 移交契约：顶层artifacts覆盖/workspace/solution，与评分读取路径一致。
  审阅证据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/test.sh
- F05 [pass] 公开 Dev、私有 Hidden 供给与 Agent 隔离：公开Dev/data随Agent，Hidden仅tests专用镜像；真实文件/manifest非占位；不反序列化数据。
  审阅证据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/hidden_assets/dataset/hidden_manifest.json
- F06 [pass] separate、单容器、无 Compose 与当前目标资源配置：separate、双方单容器、无正式Compose文件，目标H20/L20和CPU数合法；启动/训练调用不创建额外工作环境。
  审阅证据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/environment/public_eval/eval_dev.py
- F07 [fail] 当前评分实现与冻结面无确证故障或作者泄漏造假：当前评分有两项确证静态故障：动作ndarray与TensorWrapper契约冲突，以及运行时docstring指纹误拒合规Starter/Reference。
  审阅证据：workspace/harbor_task/tests/evaluate_verify.py:590-599；workspace/harbor_task/tests/trusted_env/envs/__init__.py:80-83；workspace/harbor_task/tests/trusted_env/envs/wrappers/tensor.py:36-40；workspace/harbor_task/tests/evaluate_verify.py:720-740；workspace/harbor_task/tests/evaluate_verify.py:805-831；workspace/harbor_task/tests/evaluate_verify.py:927-945；workspace/harbor_task/tests/hard_gate.py:603-632；workspace/harbor_task/environment/starter/tdmpc2/tdmpc2.py:146-168；workspace/harbor_task/tests/trusted_env/trusted_tdmpc2.py
  整改：统一父进程动作与 TensorWrapper 接口，例如校验后转 CPU float32 Tensor 再 step；将评测器自身接口异常与候选违规分开归因。 统一静态与运行时冻结比较的语义范围，排除仅 docstring 差异；保留对可执行代码变化的拒绝。
  验收：提交修正后的真实源码；复验时用原样 Starter 和 Reference 各走正常动作的完整入口，确认冻结检查通过、环境至少完成一个完整回合并产出真实 reward；另确认实际改写冻结代码仍拒绝。本次不执行候选或 Verifier，也不要求重做历史两轨。

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
