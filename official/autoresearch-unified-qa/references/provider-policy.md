# 当前平台事实与静态边界

本页不是另一套验收版本。当前要求见[唯一标准](current-standard-policy.md)；provider仅帮助核对真实底座/版本/能力，未明确可为unknown。

源码静态审查可在unknown下完成。把“源包配置/入口/依赖/私有边界成立”与“目标平台实际支持/启动/隔离/GPU/镜像size/12h稳定性已验证”分开。后者由平台核验，未给证据不要求专家补内网tag或新探针，不单独阻断静态；不能把一般Harbor可解析当内场约束已落实。

有实际MASO/Mido或其他版本依据时读其能力资料；不把旧MASO不支持字段全套给Mido，亦不因unknown放过已有明确配置冲突/正常运行故障。Landlock/bwrap、root/UID、seccomp、network/storage、Compose及额外环境等均按当前目标实际契约；机制名称/镜像名不独自定性；当前额外计算工作环境边界见[容器组织](innerfield-deployment.md#容器组织与gpu使用要求)，保留已分配沙盒内执行和独立Verifier要求。

GPU当前上限≤8张H20/L20、CPU≤64，按Work/Judge实际需求。源包候选含其他卡型不自动违规，实际分配与回退按目标检查；未到卡不冒充到卡。镜像50G上限按可信实际size，缺size仅平台范围；纯CPU不必要重型GPU base可给精简建议。

源包提供实际可用镜像/构建材料与必要资产；平台准备内部发布镜像。源码不填内部tag不失败，已经明确错误引用/缺资产/实际拉取失败仍据控制点处理。正式reward唯一输出及主分所有题按[CS03/04](current-standard-checks.md)检查，无旧批例外。
