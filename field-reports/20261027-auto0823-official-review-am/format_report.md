# 仅格式前检子报告

不代表整题质检结论；完整三门、21项、Harbor六项、两轨与豁免结论请看 report.*。

# 旧题格式返修检查

本轮结论：PASS_WITH_WAIVERS
阶段：format_repair

本批只审当前格式与核心交付语义；历史记录与平台实跑事项不作为本轮门槛。
平台运行状态：not_executed；本次未运行模型、题目代码、Docker 或 Harbor。


## 本轮七项核心检查

- F01 [pass] 当前必需目录、文件与 TOML 接口：当前task四部分、TOML可解析且显式separate；原生资源配置有效表，旧entrypoint/submit仅说明；标准入口/tests/test.sh存在。
  审阅证据：workspace/harbor_task/task.toml；workspace/harbor_task/instruction.md；workspace/harbor_task/tests/test.sh
- F02 [pass] 有效构建或镜像方案、构建上下文及 COPY 来源：双Dockerfile均context内COPY，Agent ARG默认python3.11-slim，依赖声明完整；内部tag/构建由平台准备，不冒充已经运行。
  审阅证据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile
- F03 [pass] 评分入口、独立依赖声明与固定输出路径：专用tests镜像预置绝对入口、CPUtorch/numpy、私有数据和readout运行时根，数值reward在/logs/verifier。
  审阅证据：workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/requirements.txt
- F04 [pass] 提交物 artifacts 移交契约：顶层artifacts=/workspace/solution覆盖grader读取的同一绝对目录；无destination容器重映射误用。
  审阅证据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/grader.py
- F05 [pass] 公开 Dev、私有 Hidden 供给与 Agent 隔离：公开Dev/data/starter进入Agent，私有tests仅进入独立Verifier，custom运行时仅小资产/features/logits；未见静态COPY泄漏。
  审阅证据：workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/sandbox_readout.py
- F06 [pass] separate、单容器、无 Compose 与当前目标资源配置：GPU任务Agent1×H20/L20/20CPU，Verifier8CPU/0GPU，separate；直属无Compose/不支持字段；调用仅本地进程，不额外调度GPU环境。
  审阅证据：workspace/harbor_task/task.toml；workspace/harbor_task/tests/sandbox_readout.py；workspace/harbor_task/environment/public_eval/run_round.sh
- F07 [pass] 当前评分实现与冻结面无确证故障或作者泄漏造假：当前评分可执行链静态完整，参考数据来自可信镜像，清理/重放/原子reward，未见硬编码伪分或作者泄漏。当前best说明不一致另由QA21保留。
  审阅证据：workspace/harbor_task/tests/grader.py；workspace/harbor_task/tests/submission_contract.py；workspace/harbor_task/tests/sandbox_readout.py

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
