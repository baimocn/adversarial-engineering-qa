# 优化面介绍

APAVA受试者级EEG二分类；开放模型Python接口，可设计时域/频域编码、SSM/注意力/图结构、增广与损失。解析器直接调用Model.forward，不限常量。

可修改：models/模型结构与可执行forward；run.py训练组件、损失/增广/正则；允许预算内batch调整；正式B/R固定同batch16。

固定面：受试者划分与冻结数据管线；Adam lr=1e-4、12epochs、seed41/42/43；正式SWA ep3-12均匀平均；macro-F1 argmax及B/U锚点、20M与1800s训练上限。

指标与质量门：maximize hidden TEST macro-F1；B=0.6492613306723667，U=1；Δ≥3σ_B且归一化[0.15,0.8]；公开Dev n=1413，TEST n=1431。

# Baseline 与 Reference 跑分

Baseline 方法：正式B为BaselineFormer：三尺度Conv(3/5/7)+2层pre-norm Transformer，d64/ff128，76,529参数；Adam1e-4，batch16，12轮，SWA ep3-12。它是未经结构修改Starter的独立完整训练对照；示例脚本batch32不作锚点。

Reference 方法：正式R为MedMamba：原始/差分/频域SSM三支路门控、空间图Mamba与DAG/稀疏损失，d256/ff512/4层，15,955,713参数；dropout0.2、Adam wd0.01；同batch16/12轮/seed/SWA。不是Agent r101最佳方法。

主指标：hidden TEST argmax macro-F1（越高越好）。

| training_seed | Baseline | Reference | 配对改善 | 有效性 |
|---|---:|---:|---:|---|
| 41 | 0.606617679143 | 0.79131616112 | 0.184698481977 | B:是 / R:是 |
| 42 | 0.648612294213 | 0.765370573668 | 0.116758279455 | B:是 / R:是 |
| 43 | 0.692554018661 | 0.787662957075 | 0.0951089384137 | B:是 / R:是 |

汇总：Baseline 均值 0.649261330672，样本标准差 0.0429718460002；Reference 均值 0.781449897288，样本标准差 0.0140443925108。

改善结论：全部三seed逐项正向；Δ=0.13218856661518463；σ_B=0.04297184600022364；3.0761668143σ_B；归一化0.37688620666945666。3–5σ区间可接受，保留复核建议。

质量门：6/6 COMPLETE，全部12轮、2352 update、37476 samples；六份checkpoint大小/SHA与artifact和reload逐一吻合，F1与重载记录一致；固定ep3-12。历史不对称和未达标敏感性未并入正式值。

# 前置内容门槛

| 门槛 | 结论 | 原因 |
|---|---|---|
| G01 方法级优化空间 | 通过 | 模型接口开放可执行结构方法；BaselineTransformer与Reference三支路SSM/图结构差异实质，Reference末轮正则调整不使整题成为纯调参。 |
| G02 Baseline 合理性 | 通过 | 正式Baseline在已交材料范围内合理：完成共同固定预算、训练/推理健全、成对seed完整，未发现人为削弱或挑差B的直接反证。 |
| G03 Reference 提升充分性 | 通过 | 全部有效成对值复算：Δ=0.1321885666=3.0762σ_B，归一化0.376886，剩余headroom0.2185501=5.0859σ_B，满足门槛。 |

复核建议：改善达到 3σ_B 但低于 5σ_B，建议复核稳定性；不单独判失败。

G03 复算：Δ=0.132188566615；σ_B（样本标准差）=0.0429718460002；U=1；归一化分数=0.376886206669。

# 两条轨迹迭代概况

| Agent 轨迹 | 状态 | 打包轮数 | 声明有效轮数 | 有效时长 | 概况与最终结果 |
|---|---|---:|---:|---:|---|
| Codex + GPT-5.6 Sol | 完整 | 260 | 260 | 10.46h | r1-50探索频带、相关性、池化和增广；r51起用单epoch最优替代SWA；r62/68/72稳健空间统计；r94/101软delta边界达到峰值；r133-260逐步退化为增广浮点微调，无后续净提升；轨迹r101单ep11 Dev=0.9781为违约峰值，不能当提交分；当前同代码SWA权重39fe274f…独立既有Dev记录0.9596006381555247，非Hidden。 |
| Codex + Seed 2.1 Turbo | 完整 | 57 | 56 | - | r1-12多尺度卷积、EEG增广与多seed；r15 balanced CE；r20-30 DropPath/SSM/R-Drop/SAM/融合多次失败；r31-50正则与冻结LR；r51-57缩SWA窗、门控读出及频域分支；r44无结果如实null；轨迹r54峰值0.84052，采用SWA ep5-9、lr5e-5/冻结LR，不满足固定lr/SWA协议；r57失败回退r52，摘要保留0.84031，不把0.84052当正式成绩。 |

# 轨迹可信性与题包绑定

Codex + GPT-5.6 Sol：分数无效；Codex + Seed 2.1 Turbo：分数无效

| 轨迹 | 所交内容审查 | 分数与当前包对应 | 审查范围 | run_summary 哈希 |
|---|---|---|---|---|
| Codex + GPT-5.6 Sol | 不通过 | 无效 | 仅审查已交轮次/方法摘要；未提供工具调用或sessions，结论限于这些材料。 | run_summary 的四项题包哈希与当前包一致。 |
| Codex + Seed 2.1 Turbo | 不通过 | 无效 | 仅审查已交轮次/方法摘要；未提供工具调用或sessions，结论限于这些材料。 | run_summary 的四项题包哈希与当前包一致。 |

- Codex + GPT-5.6 Sol：存在作弊/违规 / 已确认：仅指已确认固定协议违约的历史方法/成绩，不推测主观动机；正式作者B/R另有独立全seed证据且未采用这些分数。；受影响分数无效；影响轮次 [51, 62, 68, 72, 94, 101]；证据 expert_evidence/trajectory_codex.json；workspace/harbor_task/instruction.md；expert_evidence/专家作业说明文档.md
  修复：保留无效分数、归属与采用范围；当前SWA合规结果单列。；验收：已有记录分层，不把违规峰值当正式B/R或合规提交成绩。

- Codex + Seed 2.1 Turbo：存在作弊/违规 / 已确认：仅指已确认固定协议违约的历史方法/成绩，不推测主观动机；正式作者B/R另有独立全seed证据且未采用这些分数。；受影响分数无效；影响轮次 [1, 2, 31, 36, 51, 52, 54, 57]；证据 expert_evidence/trajectory_seed.json；workspace/harbor_task/instruction.md；expert_evidence/专家作业说明文档.md
  修复：保留无效分数、归属与采用范围；当前SWA合规结果单列。；验收：已有记录分层，不把违规峰值当正式B/R或合规提交成绩。

# QA15 资源证据

缺少：当前成绩的硬件归属/换卡影响尚未确认

| 运行 | 计时范围 | 记录耗时（秒） | GPU 数量/型号 | 分配 CPU 核 |
|---|---|---:|---|---:|

资源需求估算：完整一轮约 6000 秒，1 张 GPU，16 核 CPU；正式Reference每seed全流水线约1322-1329s，CPU TEST重评最慢403.4s；3×(1329+403.4)=5197.2s，取6000s留余量，GPU峰值约14.5GB，目标卡推断而非实测。

计时口径：覆盖最保守三seed训练+SWA+重载及CPU评测，不把整条10h研究计为评分时间。

# 目标部署能力

配置范围：innerfield-maso-v1

当前交付符合内场能力检查；Solver/Verifier 仍须不同 sandbox。

任务硬件与成绩对应：gpu / unverified；当前成绩的硬件归属/换卡影响尚未确认
证据：expert_evidence/g02_support/matched_control/preflight.json；expert_evidence/g02_support/improved_method_runs/reference_seed41/preflight.json；workspace/harbor_task/task.toml

# 格式对齐建议

三目录职责基本明确；轻量result字段由等价worker/config/原日志、artifact/reload补足，不因缺新版同名schema否定原记录；现行八字段齐全。历史Ref摘录不可单独运行，但正式完整源码另已交；best SWA输入链未全交付，仅引用既有原环境重算，未声称本包可重建。

- `optimization_evidence/_derive`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/_retired`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_41/config.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_41/events.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_41/reload.stderr.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_41/reload.stdout.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_41/reload_execution.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_41/reload_resources.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_41/reload_worker.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_41/swa.stderr.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_41/swa.stdout.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_41/swa_execution.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_41/swa_inputs.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_41/swa_resources.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_41/swa_worker.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_41/train.stderr.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_41/train.stdout.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_41/train_execution.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_41/train_resources.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_41/train_worker.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_42/config.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_42/events.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_42/reload.stderr.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_42/reload.stdout.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_42/reload_execution.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_42/reload_resources.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_42/reload_worker.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_42/swa.stderr.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_42/swa.stdout.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_42/swa_execution.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_42/swa_inputs.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_42/swa_resources.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_42/swa_worker.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_42/train.stderr.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_42/train.stdout.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_42/train_execution.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_42/train_resources.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_42/train_worker.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_43/config.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_43/events.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_43/reload.stderr.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_43/reload.stdout.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_43/reload_execution.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_43/reload_resources.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_43/reload_worker.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_43/swa.stderr.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_43/swa.stdout.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_43/swa_execution.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_43/swa_inputs.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_43/swa_resources.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_43/swa_worker.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_43/train.stderr.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_43/train.stdout.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_43/train_execution.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_43/train_resources.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/baseline_runs/seed_43/train_worker.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/budget_ledger.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/learning_curves.csv`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/learning_curves.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/README.md`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_41/config.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_41/events.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_41/reload.stderr.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_41/reload.stdout.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_41/reload_execution.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_41/reload_resources.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_41/reload_worker.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_41/swa.pth`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_41/swa.stderr.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_41/swa.stdout.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_41/swa_execution.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_41/swa_inputs.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_41/swa_resources.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_41/swa_worker.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_41/train.stderr.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_41/train.stdout.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_41/train_execution.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_41/train_resources.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_41/train_worker.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_42/config.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_42/events.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_42/reload.stderr.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_42/reload.stdout.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_42/reload_execution.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_42/reload_resources.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_42/reload_worker.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_42/swa.pth`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_42/swa.stderr.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_42/swa.stdout.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_42/swa_execution.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_42/swa_inputs.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_42/swa_resources.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_42/swa_worker.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_42/train.stderr.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_42/train.stdout.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_42/train_execution.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_42/train_resources.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_42/train_worker.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_43/config.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_43/events.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_43/reload.stderr.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_43/reload.stdout.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_43/reload_execution.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_43/reload_resources.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_43/reload_worker.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_43/swa.pth`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_43/swa.stderr.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_43/swa.stdout.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_43/swa_execution.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_43/swa_inputs.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_43/swa_resources.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_43/swa_worker.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_43/train.stderr.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_43/train.stdout.log`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_43/train_execution.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_43/train_resources.jsonl`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `optimization_evidence/reference_runs/seed_43/train_worker.json`（可保留的额外项）：规范外附加材料；多交不构成格式失败。
- `expert_evidence/`（可保留的额外项）：保留有效历史证据，已退役说明与现行采用范围清晰标注。
- `workspace/reference/ref_code/`（旧布局/打包杂项）：明确指向g02_support/improved_method_source完整正式入口，避免将历史摘录当可独立复现目录。

说明：额外材料仅作精简或归位建议，不因多交而单独判错。

# 质检结论：不通过

产物：evidence-input｜通过 13 项｜不通过 5 项｜未完成 3 项｜跳过/不适用 0 项

前置三门：通过 3 项｜不通过 0 项｜待核验 0 项；全部复核完成：否。

口径：只读检查及已有证据复核；QA07/08 查 instruction；QA18 审所交轨迹及提供的 sessions，QA21 单独核对 run_summary 的四项题包哈希；QA15 允许根据日志、轨迹和B/R实现估算资源。QA16 两条各至少 10h；仅无训练且单轮很短、例外证据完整时可各至少 7h。排队、安装与故障不计有效迭代时长。未执行提交代码、未独立复跑或反序列化模型。

Harbor 格式/接口：不通过；已提交 NOP 的运行或任务版本关联待核实。

| 检查项 | 是否通过 | 原因 |
|---|---|---|
| QA01 八章节与题面信息泄露 | 通过 | 题面含目标、环境、指标、修改范围、边界、提交、流程、完成条件；未披露MedMamba论文/源码或参考方法答案。 |
| QA02 评分公式与 0/1 锚点 | 通过 | 评分器使用未裁剪连续归一化(F1-B)/(1-B)，正向单调；B三seed均值代入0，U=1代入1。 |
| QA03 参考解分数与复现材料 | 通过 | 三正式Reference有完整方法源码、可识别入口run.py及冻结脚本/原日志/模型索引与重载，归一化0.376886。workspace/reference/ref_code是已标明的历史核心摘录，不作为独立正式入口。 |
| QA04 波动指标的 3σ 可分辨性 | 通过 | seed41/42/43进入Python/NumPy/Torch/CUDA随机初始化；同一B/R方法版本各seed独立重训，六hash互异；样本σ_B复算3.0762σ。 |
| QA05 约束执行实现 | 不通过 | 有冻结面SHA、参数量前置门、1800s训练wrapper与1200s推理计时；但题面把Python子进程宣称为候选不可触及Hidden/评分文件的边界，与当前调用链不符。禁网迁移另按白名单。 |
| QA06 Verifier 入口、分数与错误处理 | 不通过 | test.sh与可信主进程有正式reward及无权重/超参数处理；超时分支返回3项而调用接收2项，导致约定的失败reward路径失效。 |
| QA07 instruction 中的 Hidden 信息泄露 | 通过 | 题面只列测试受试者ID及不可访问规则，没有测试特征、真实标签或可恢复答案。 |
| QA08 instruction 中的参考解信息泄露 | 通过 | 题面没有参考实现、具体参考配置/成绩或直接解法；允许SSM/注意力等一般方法类不等于泄露答案。 |
| QA09 结果清理与原子写入 | 通过 | test.sh评分前删除已有reward与临时文件；write_reward使用O_EXCL唯一临时名、fsync与os.replace原子写出并回读。 |
| QA10 冻结面保护或恢复实现 | 通过 | 评分数据管线从tests自带可信副本加载，不导入候选数据管线；候选冻结面以TRUSTED_HASHES前后校验，有可识别保护逻辑。此项通过不认证完整进程/文件隔离。 |
| QA11 instruction 八项内容 | 不通过 | 八部分实质内容齐全；公开Dev命令与镜像路径不一致，且不可触及评分/Hidden文件的绝对声明超出-I子进程实际边界。 |
| QA12 Git 清理 | 通过 | 1076普通文件清单中无.git路径；未据外部Git仓库或包内旧结论推定完成。 |
| QA13 Baseline 与参考解提升 | 通过 | 六正式运行全部同batch16/12轮/SWA，成对seed完整，模型哈希及独立重载匹配，全部正向且3.0762σ；无效旧Agent峰值不作正式B/R。 |
| QA14 合法改进空间 | 通过 | R均值0.78145未饱和，剩余0.21855；可在开放forward设计题面未直接给出的受试者不变表示/频谱统计与时序模块联合方法，现有r101结构为实际方法空间证据。 |
| QA15 评分资源需求估算 | 待补充核验 | 缺少：当前成绩的硬件归属/换卡影响尚未确认 |
| QA16 轨迹实际迭代时长 | 待补充核验 | Codex + Seed 2.1 Turbo缺少有效时长或排除排队/安装/故障的核算证据 |
| QA17 Harbor Harness 兼容性 | 不通过 | Harbor 子项未通过：H03 环境与运行路径；H04 测试入口与 reward；H06 NOP 自检记录；详细原因与证据保留在 report.json。 |
| QA18 轨迹、日志与分析 | 不通过 | 两条轨迹的八字段证据未通过：rounds[43].status='no_result' 为自定义状态；需人工确认成功/失败含义及对应分数、失败原因和最佳标记。 |
| QA19 seed 与有效提升阈值 | 通过 | 题面明确41/42/43、Δ≥3σ_B与归一化[0.15,0.8]；按随机训练评估审查，不因固定推理seed误作确定性不适用。 |
| QA20 修改范围、网络与工具策略 | 通过 | 题面列出可改范围、禁止外部资源和按平台默认工具策略；规则文字齐全。禁网实际执行缺口在QA05迁移原因记录。 |
| QA21 三个 JSON 的填写内容 | 待补充核验 | 两条轨迹的八字段证据未通过：rounds[43].status='no_result' 为自定义状态；需人工确认成功/失败含义及对应分数、失败原因和最佳标记。 |

# 退回专家说明

QA05 约束执行实现（不通过）：有冻结面SHA、参数量前置门、1800s训练wrapper与1200s推理计时；但题面把Python子进程宣称为候选不可触及Hidden/评分文件的边界，与当前调用链不符。禁网迁移另按白名单。
证据：workspace/harbor_task/instruction.md；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/tests/infer_candidate.py；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/environment/starter/scripts/APAVA_Subject.sh
请修改/补充：仅修复本项已定位问题；历史缺口按本批政策处理，不要求新增平台证明或全部重跑。
复检验收材料：复核所引实际内容、对应修正和既有证据；动态平台事项由平台完成。

QA06 Verifier 入口、分数与错误处理（不通过）：test.sh与可信主进程有正式reward及无权重/超参数处理；超时分支返回3项而调用接收2项，导致约定的失败reward路径失效。
证据：workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/tests/test.sh
请修改/补充：仅修复本项已定位问题；历史缺口按本批政策处理，不要求新增平台证明或全部重跑。
复检验收材料：复核所引实际内容、对应修正和既有证据；动态平台事项由平台完成。

QA11 instruction 八项内容（不通过）：八部分实质内容齐全；公开Dev命令与镜像路径不一致，且不可触及评分/Hidden文件的绝对声明超出-I子进程实际边界。
证据：workspace/harbor_task/instruction.md；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/task.toml；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/tests/infer_candidate.py
请修改/补充：仅修复本项已定位问题；历史缺口按本批政策处理，不要求新增平台证明或全部重跑。
复检验收材料：复核所引实际内容、对应修正和既有证据；动态平台事项由平台完成。

QA15 评分资源需求估算（待补充核验）：缺少：当前成绩的硬件归属/换卡影响尚未确认
证据：workspace/harbor_task/task.toml；expert_evidence/w1_recompute/w1_recompute_report.json；optimization_evidence/baseline_runs/seed_41/result.json；optimization_evidence/baseline_runs/seed_42/result.json；optimization_evidence/baseline_runs/seed_43/result.json；optimization_evidence/reference_runs/seed_41/result.json；optimization_evidence/reference_runs/seed_42/result.json；optimization_evidence/reference_runs/seed_43/result.json；expert_evidence/run_summary.json；expert_evidence/g02_support/matched_control/preflight.json；expert_evidence/g02_support/improved_method_runs/reference_seed41/preflight.json
请修改/补充：按任务性质核对当前Solver/Verifier资源。换卡只复核受影响的成绩或耗时，并引用已有配置、说明或运行记录；旧测量保留原硬件标签。
复检验收材料：CPU题不申请GPU；GPU题的实际目标卡型为H20/L20；受影响正式分数有目标硬件对应依据，不能只改型号沿用旧分。

QA16 轨迹实际迭代时长（待补充核验）：Codex + Seed 2.1 Turbo缺少有效时长或排除排队/安装/故障的核算证据
证据：expert_evidence/run_summary.json；expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json
请修改/补充：为Codex + Seed 2.1 Turbo补一张时长表：研究起止、排队/安装/API失联/故障区间、仍正常运行的训练重叠及有效秒数。可引用已交轨迹和日志片段；不强制提交完整timer或sessions。
复检验收材料：可复算的两轨起止/扣除表，与轨迹时间相符；默认每轨≥36000有效秒。最终复验、收集和明确故障不计，健康训练并发只计一次。

QA17 Harbor Harness 兼容性（不通过）：Harbor 子项未通过：H03 环境与运行路径；H04 测试入口与 reward；H06 NOP 自检记录；详细原因与证据保留在 report.json。
证据：workspace/harbor_task/task.toml；workspace/harbor_task/environment/Dockerfile；workspace/harbor_task/tests/Dockerfile；workspace/harbor_task/tests/test.sh；workspace/harbor_task/tests/hidden_assets/inject_contract.json；expert_evidence/nop_trial_native/verifier/test-stdout.txt；expert_evidence/run_summary.json；workspace/harbor_task/tests/evaluate_verify.py；workspace/harbor_task/tests/infer_candidate.py；expert_evidence/nop_trial_native/config.json；expert_evidence/nop_trial_native/result.json；expert_evidence/nop_trial_native/trial.log；expert_evidence/nop_trial_native/verifier/reward.json；expert_evidence/nop_trial_native/verifier/reward.txt；expert_evidence/nop_trial_native/task_identity_binding.md
请修改/补充：仅修复本项已定位问题；历史缺口按本批政策处理，不要求新增平台证明或全部重跑。
复检验收材料：复核所引实际内容、对应修正和既有证据；动态平台事项由平台完成。

QA18 轨迹、日志与分析（不通过）：两条轨迹的八字段证据未通过：rounds[43].status='no_result' 为自定义状态；需人工确认成功/失败含义及对应分数、失败原因和最佳标记。
证据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/专家作业说明文档.md；expert_evidence/score_patch_record.json；expert_evidence/best_method_manifest.json
请修改/补充：补齐两条真实轨迹，每轮八字段须完整有效；保留失败原因，不补造分数、时间或轮次。自定义状态需说明其语义。
复检验收材料：overview.source_path 指向两份可读取轨迹，轮次及八字段符合教程，并与运行摘要和最佳方法记录一致。

QA21 三个 JSON 的填写内容（待补充核验）：两条轨迹的八字段证据未通过：rounds[43].status='no_result' 为自定义状态；需人工确认成功/失败含义及对应分数、失败原因和最佳标记。
证据：expert_evidence/trajectory_codex.json；expert_evidence/trajectory_seed.json；expert_evidence/run_summary.json；expert_evidence/expert_annotation.json；expert_evidence/best_method_manifest.json；expert_evidence/swa_dev_measurement.json
请修改/补充：补齐两条真实轨迹，每轮八字段须完整有效；保留失败原因，不补造分数、时间或轮次。自定义状态需说明其语义。
复检验收材料：overview.source_path 指向两份可读取轨迹，轮次及八字段符合教程，并与运行摘要和最佳方法记录一致。
