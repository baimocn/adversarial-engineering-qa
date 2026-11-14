# 平台群聊分享经验文档精读索引（脱敏版）

本文件是逐篇精读报告的公共副本索引；完整本地精读报告位于 `qa_compare/group_doc_docs/PLATFORM_EXPERIENCE_DEEP_READ.md`。公共副本保留判据、版本冲突与覆盖结论，移除内部日志链接、一次性登录参数、附件 token 与个人标识。

## 已精读材料

| # | 标题 | 主要经验 | 当前归类 |
|---:|---|---|---|
| 1 | AutoResearch 专家终检问题汇总（2026-11-13） | 终检五类：难度过低 64、难度过高 31、失败写普通 0 分 38、Verifier 低效/预算失配 11、评分门/合同与防作弊 31 | platform_scope / advisory catalog；其中「失败 0」沉淀为 mechanical |
| 2 | Harbor 1074题执行复盘 | 1074 题中 664 有准备/执行/评分问题；25/9/3 原因族；不能混同平台 Failed、零分、Agent 失败 | current_mechanical partial；其余 runtime scope |
| 3 | 题包运行问题修复说明：错误 / 正确样例（19题） | 8 类运行兼容性：Landlock、HOME、ENTRYPOINT、UID/NPROC、资产、artifacts、提交污染、原子发布竞态 | current_mechanical partial / ablation / platform_scope |
| 4 | AutoResearch 题包返修指南 | 单 task.toml、Dockerfile/context、官方源、GPU、独立 Verifier、题面-评分链、P/E/S 报错码 | current_mechanical partial |
| 5 | Skill修改清单与格式说明 | 0.5.0 四项默认、90 项/六组、最终二态、provider unknown、reward 二选一、-10 hard gate | current_mechanical base |
| 6 | 交付验收与专家返修分流｜20261107 | 86 条返修：CPU/CUDA 镜像 28、异常 reward 19、超时余量 12、GPU 权限 4 等 | advisory catalog |
| 7 | 返修记录豁免清单与质检口径 | 0.3.10 先原标准全审再逐项豁免；PASS_WITH_WAIVERS；NOP 必交 | legacy_archived |
| 8 | 返修格式自检与完整包交付规范 | check_package v1.2.1；三目录、TOML、Compose、GPU、COPY、artifacts | legacy_archived / 部分格式规则保留 |
| 9 | 专家线下标注教程 V4 | 公开 Dev/Hidden、独立 Verifier、G01–G03、3σ/5σ、八字段、四项指纹、best_method | legacy_archived；best_method 冻结 adapter 被 0.5.6 报告重新激活 |

## 版本冲突裁决

| 冲突 | 最新生效口径 |
|---|---|
| hard gate `-1` vs `-10` | `-10` |
| `docker_image` 示例 vs 11 月禁令 vs strict 降级 | 专家源 `task.toml` 不硬编码，平台负责镜像选择；Dockerfile/context 静态可核 |
| 最终多档 / PASS_WITH_WAIVERS vs 二态 | 对外 PASS/FAIL，内部 `QA_NOT_FINISHED` 仅诊断 |
| NOP 每次返修补交 | NOP 不恢复 |
| 两轨 10h/八字段/四项指纹硬门 | 不恢复；G03 全 seed 配对与真实提升保留 |
| 0.3.10 21 项 vs 0.5.0 90 项 vs 0.5.6 报告 | 0.5.0 规则底座 + 0.5.6 平台报告覆盖口径 |

## 覆盖差异结论

- 可执行覆盖：B-C01–B-C04、D-C01–D-C04、Gate C 六类运行规则、0.3.10 21 项预填、当前 gate 的 12 条机械规则。
- 仅归档/平台范围：GPU 实卡、Docker/Harbor 实跑、Hidden、Verifier 预算、难度类、公开数据可重建 Hidden、超时收尾、Judge 吞异常、模型资产完整性等。
- Legacy 不回灌：`-1`、NOP 每次补交、PASS_WITH_WAIVERS、两轨 10h/八字段/四项指纹硬门、V4 docker_image 示例。
- 核心机制准入条件：每条当前机械规则必须有 bad/good 双向消融；消融不过不进 gate。

## 边界

平台经验材料只说明「平台/项目组说过什么」，不替代平台对具体题包的最终报告；静态 gate 的 PASS 也不是 Docker/Harbor/Hidden 实跑证明。后续平台版本变化时，先更新 `config/rule_versions.json` 与 `config/rule_catalog.json`，再改执行器。
