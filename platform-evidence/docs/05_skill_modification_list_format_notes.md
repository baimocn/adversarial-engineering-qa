<title>Skill修改清单与格式说明</title>

# 修改

| 修改项 | 本版处理 | 对使用者的影响 |
|-|-|-|
| 统一标准入口 | 新入口scripts/audit_current.py；删除活动流程中的mode、intake_cohort、target-level和provider选择。四个旧完整入口的命令行也转到当前入口。 | 直接指定本版Skill和题包；不用再说明哪批、用哪个版本或申请哪条豁免。 |
| 四项规则默认生效 | Oracle位置与入口、全量依赖锁定、正式reward二选一、候选hard gate −10，对所有题都检查。 | 不再因为未填写new_1104而跳过。具体返修见下一节。 |
| provider未知不阻断源码审阅 | 统一检查Harbor任务契约；MASO/Mido实际能力据已有明确证据核对。未知只表示目标平台未验证，不等于专家漏交字段。 | 不再因provider=unknown输出review，也不要求专家补内部平台名称、内网tag或到卡证明。已有真实平台故障仍报告具体原因与责任。 |
| 最终结果二态 | 正式报告及专家说明只输出通过或不通过；删除最终JSON中的初始未审模板。 | 不再把空底稿或模板中的unreviewed当成另一份结论。工具、读取错误由质检端处理，不冒充专家缺陷。 |
| 全部检查继续执行 | 保留90项、工程六组、交付合同六组；发现失败仍完成其余可安全审阅内容。全量阅读记录绑定文件哈希与实际阅读区间。 | 保留轨迹、候选身份、原始分数、异常路径及科学质量审查；没有缩成几项格式检查。 |
| 原严格要求延续 | 保留G01方法空间、G02合理Baseline、G03同协议全seed／3σ／Reference区间，以及原正式评测2h／多seed8h和适用依赖源规则。 | 算法等级与项目加严来源分别注明；不借等级重映射放宽原项目检查，也不扩大成全部L1/L2新实验义务。 |
| 问题合并与归责 | QA06、H04、QA17、F07可引用同一事实；专家返修按根因合并，保留关联项与定位。 | 同一缺陷只改一次；专家返修、平台处理、双方协作和质检端错误分开。 |

# 需要对齐的四项交付要求

以下路径均相对实际Harbor任务根。外层项目目录可以保留；需修正实际入口、读取路径和装配关系。

| 要求 | 需要怎么改 | 验收要看什么 |
|-|-|-|
| 参考解放在solution/ | 提供solution/solve.sh，调用solution/内的参考实现，生成正常提交物；reference.py只是示例名，method.py或其他语言实现也可以。参考解不得提前暴露给Agent。 | 入口及实现实体存在，调用链和输出路径正确；Oracle不直接写正式reward。 |
| 依赖版本锁全 | 提供覆盖必要直接、传递及运行时依赖的锁定材料，并让实际构建采用；必要工具、数据、库在解题前准备好。只锁几项核心包，或仅交名为lock.json的Harbor配置，不等于依赖锁全。 | 沿实际Work/Judge构建链检查版本和锁文件是否被使用。不可变固化环境须有真实依赖绑定，不能拿无关历史镜像代替当前构建输入。 |
| 正式reward只选一种 | 每次正式评分仅输出/logs/verifier/reward.json或reward.txt。使用JSON时，主reward必须是有限数值；其他诊断另放result.json或日志。 | 核对实际写入与读取链及旧文件清理；不能同时发布两种reward，也不能用只有accuracy等诊断指标的对象代替主分。历史凭证保留原貌，不改写历史成绩。 |
| 候选hard gate确定−10 | 已明确由候选触发的约束拒绝，统一返回−10并给可执行诊断；同步题面、公开反馈和正式评分协议。 | 区分候选违约、可信评分器／资产／依赖故障和平台中断。可信故障不能伪装成候选0分或正常reward，也不能把所有异常和无分一律罚−10。 |

Work与Judge始终是两个全新独立sandbox。可以复用同一个预置镜像，也可以使用专用评分镜像；不因Dockerfile数量相同就推断未隔离。公开Dev保留，私有tests／Hidden及Reference只按相应阶段安全装配。源码由专家提供，平台负责内部镜像构建、发布及实际拉取验证。

## Oracle参考解：需要补齐的目录与入口

**已有参考实现的题目，主要补交付结构和入口接线，无需为此从头重新设计算法或重做历史长轨迹。**把已有参考解接入标准Oracle流程；只新建空脚本、改文件名或直接输出分数，不能完成这项返修。

```text
harbor_task/
├── task.toml
├── instruction.md
├── environment/             # Agent公开环境，保留Starter与公开Dev
│   └── Dockerfile
├── solution/                # 私有Oracle材料，不提前暴露给被测Agent
│   ├── solve.sh             # 标准Oracle执行入口
│   └── method.py            # 复用已有参考实现，文件名和语言可调整
└── tests/                   # 独立Judge使用
    └── test.sh              # 读取正常提交物，计算并输出正式reward
```

**执行顺序：**Oracle模式下，Harbor将题包solution/上传到/solution，执行/solution/solve.sh；该脚本调用参考实现，将正常提交物放到题面及artifacts约定的位置；平台再移交给全新独立Verifier，由tests/test.sh评分。普通模型Agent解题时不上传这份私有Oracle材料，也不把它COPY进公开Work镜像。需核对实际COPY、挂载和访问权限；仅命名为solution/不代表已经隔离。

下面仅演示“提交method.py方法代码”的任务：已有参考方法可通过Oracle入口安装到/workspace/solution/method.py，再由Verifier按原协议运行。若提交的是数据、模型或其他文件，应按本题契约生成对应产物，不能照抄这个代码类示例。

```bash
#!/usr/bin/env bash
set -euo pipefail
oracle_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p /workspace/solution
cp -- "$oracle_dir/method.py" /workspace/solution/method.py
# 不在此写reward；保留题目原有的公开Dev入口和其他必需提交文件。
```

## 两个solve.sh不要混用

| 位置 | 用途 | 返修动作 |
|-|-|-|
| 题包solution/solve.sh；Oracle运行时为/solution/solve.sh | 私有参考解入口，生成正常提交物。 | 新增或适配此入口，并将其所调用的参考实现放在题包solution/内。 |
| Agent运行时/workspace/solution/solve.sh（若原题已有） |  |  |

这里的题包solution/与Agent运行时/workspace/solution不是同一份目录。前者存放私有参考材料，后者存放最终候选提交；不能因目录同名就将私有参考解预置给被测Agent。solution/应新增在选定Harbor任务根下，例如为workspace/harbor_task/solution/，不要误放在完整提交包外层。



# 哪些实质检查仍然保留

| 检查重点 | 本版继续怎么审 |
|-|-|
| QA06／H04：评分结果路径 | 分别检查成功候选、候选拒绝、可信故障和外层中断；结合错误发生位置、结果状态及实际读取规则判断。不能仅凭负分断言所有历史数据无效，也不能用一次正常出分掩盖确定支路缺陷。 |
| QA02／QA13：真实锚点与比较 | 核对Starter→0、上界→1、方向、公式和正式B/U；性能或固定墙钟任务换卡时核对锚点可比性。不能用旧卡结果冒充目标卡实测；固定steps精度任务不因卡名不同就一律重跑。 |
| QA15：时限与资源 | 公开Dev一次完整反馈≤2h；保留正式单seed≤2h、同候选多seed累计≤8h原适用范围。按真实串并行、共享deadline和收尾核算，不机械叠加timeout，也不要求Agent和Verifier时限必须不同。 |
| QA18／A：实际轨迹与会话 | 完整阅读全部已交实验、主／子／恢复／重试会话及分数记录。实验次数不等于主Agent响应次数；真实泄漏、作弊、错候选和假分仍阻断。未交原生会话不能凭台账数字认证动态行为。 |
| G01–G03：研究质量 | 检查可执行方法空间及Baseline五维合理性。沿用G03正式配对、随机评估至少3次、Baseline样本σ及Δ≥3σ、Reference归一化[0.15,0.8]；不把作者校准写成Solver题面的完成义务。 |
| 静态审阅与平台验证 | 静态通过不等于Docker／Harbor实际运行成功；内核能力、实际选卡、镜像大小和长期稳定性保留真实验证范围。未知不是故障，已有明确故障也不会因未知而免查。 |



<figure view-type="Card"><source name="autoresearch-unified-qa-v0.5.0-current.1_20261107.zip" mime="application/zip" size="449771" token="<attachment-token>"/></figure>