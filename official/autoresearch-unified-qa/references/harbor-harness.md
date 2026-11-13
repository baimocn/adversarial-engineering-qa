# 当前Harbor与Oracle审阅

以[当前标准](current-standard-policy.md)审当前题面/配置/代码与已有证据。原生Harbor在实际指定底座可运行是目标，源码质检不冒充本次已跑平台。

| ID | 当前职责 |
|---|---|
| H01 | 任务结构、实体资产、可调用solution/solve.sh Oracle入口；实现文件名/语言不限，不固定额外外层根目录。 |
| H02 | 实际有效配置、Agent/Judge资源、artifacts传递及唯一可识别任务；unknown不单独失败。 |
| H03 | separate独立sandbox、真实镜像/构建/依赖/权限和私有边界；不按关键词或无平台证据假定失败；[额外计算工作环境边界](innerfield-deployment.md#容器组织与gpu使用要求)仍适用。 |
| H04 | 真实评分入口、候选→指标→主reward、四种结果路径、失败状态与有效预算。四协议所有题检查。 |
| H05 | 实际选择镜像分支与tests供给；复用初始镜像或专用Verifier均可，自带依赖且不依赖Agent临时状态。 |

识别实际分支：继承初始Solver镜像后向独立sandbox上传私有tests，或tests/Dockerfile专用构建，或显式Verifier镜像/认可适配装配。核对context/COPY/ignore和入口实际来源；两份Dockerfile不是统一必交，镜像相同不证明sandbox相同。公开Dev保留，Hidden/Reference不入Work，不允许COPY后删除泄漏层。

Oracle是默认必查入口，不直接写分；tests/test.sh或目标认可等价评分入口产生唯一正式reward，JSON主reward明确。源码已有入口/依赖/构建路径实错可判，内网发布/实际到卡/启动/12h稳定性与镜像size由平台核验，unknown不拖住正常静态审查。

H04/QA17只聚合当前必需的具体缺陷，不能传播旧child FAIL、高级科学门、固定路径/双模型/字段要求或平台未知。NOP不恢复；单纯一小时超时无分不直接退题。原算法A与本表各自完整审，排除范围不互相覆盖。
