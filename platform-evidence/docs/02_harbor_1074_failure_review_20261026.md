<title>Harbor 1074题执行复盘：失败原因、解决办法与验收清单（2026-10-26） 副本</title>

面向：评测项目负责人、题目维护者、平台工程师。数据基线：任务状态表 revision 63，全表1,074条、无分页遗漏；统计单位为题目当前记录，不重复累计历史试跑。本文为失败复盘和修复建议，不代表修复已执行。

逐题状态、原始错误、评分JSON及HDFS证据见[任务状态总表](<lark-doc>)。

# 核心结论

**1,074题中，410题执行与评分流程正常（38.2%），664题存在准备、执行或评分问题（61.8%）。**准备失败322题，是最大的阶段性阻塞；执行问题共268题，其中工作目录检查拦截106题、Agent超时119题；评分阶段失败74题。

修复应先消除镜像、依赖、运行身份、GPU路由和评分协议等系统性阻塞，再针对超时与个案优化。不能把平台Failed、任务零分和Agent失败视为同一件事，也不能把工作目录检查报错直接解释为“题目必须开放写权限”。

**重要限制：**410题“成功”仅指Agent与评分流程正常，不代表分数达到题目通过阈值。116题“已评分（执行异常）”必须保留原分数，但不能计入正常成功。零分、负分、框架默认分数均不得人为改写。

# 统计口径与任务分布

范围为表内源行1-1074，每道题按当前Trial链接统计一次。未将被停止、被替换的原始trial或诊断trial再次累加。任务主键为源记录、源行及完整包SHA256；题号大小写有意义，不能将Auto0013与auto0013等合并。

| 当前任务结果 | 题数 | 解释 |
|-|-|-|
| 执行与评分正常 | 410 | Agent成功、无执行异常、取得有效有限数值评分。 |
| 准备失败 | 322 | 未进入Agent执行与评分。 |
| 执行阶段失败／无评分证据 | 152 | 包括执行终态但缺少已发布原生摘要的23题。 |
| 评分阶段失败 | 74 | 评分文件缺失、产物下载失败或非数值输出。 |
| 已评分但执行异常 | 116 | 仍有rewards，但Agent超时、非零退出或安全拒绝等，不计正常成功。 |
| 合计 | 1,074 | 五类互斥；失败／异常共664题。 |

| 当前归属Trial | 总数 | 正常 | 准备失败 | 执行失败 | 评分失败 | 评分但异常 |
|-|-|-|-|-|-|-|
| 438064644 | 213 | 42 | 62 | 91 | 5 | 13 |
| 438563780 | 43 | 9 | 11 | 18 | 1 | 4 |
| 438627695 | 475 | 218 | 123 | 32 | 32 | 70 |
| 439171143 | 343 | 141 | 126 | 11 | 36 | 29 |
| 合计 | 1,074 | 410 | 322 | 152 | 74 | 116 |

这些分群不是同一题集的受控实验，源包、运行阶段和环境配置不同，因此不能用Trial间成功率差异推断模型优劣或某项配置的因果收益。438627695与439171143已复核为平台Failed，分别于2026-10-25 15:03、2026-10-26 05:09结束，执行中均为0；其他记录按表内已有终态证据汇总。

# 准备阶段：322题阻塞在镜像、软件源、依赖、资产或发布链路

<callout emoji="🍰">
大部分问题跟镜像构建有关：
1. 方案一：~~专家提供镜像image~~

   1. 风险：安全问题
2. 方案二：明确可使用的基础镜像和依赖是哪些，专家在可选的list中决策

   1. 风险：list完备性
3. 方案三：~~内部改写（验证可行）~~

   1. 风险：1. 会修改题目环境，可能偏离作答意图；2. 纯依赖ai（/goal的方式，就变成我们出题；还有一种写质检skill）
</callout>

![图片展示了auto1332的Docker Hub访问问题修复方案及验证结果。方案包括修改Dockerfile、将pip源改为指定URL、将任务镜像地址替换为hub.byted.org等。验证结果中，Trial 440955276正常结束，通过本地包、远端包、准备快照等22个文件验证。交付文件有修复后题包、完整修复说明及镜像地址等。图片与上文准备阶段中322题阻塞问题的解决办法相关，呈现了具体修复措施及验证情况。](<lark-doc>)

截至任务状态表 revision 63，322题准备失败均已有表内原因标签。此前249条“原生准备失败（见原始准备错误）”通用记录已细分为38个具体标签；合并历史同义标签后，本节按25个可执行修复原因族展示，合计322题。

本轮细化只同步归因和修复建议，未重跑任务、未修改权限或源包、未实施平台修复。表内计数是互斥题目数；“主要子类与证据状态”中的错误码说明用于定位，不重复相加。

<table><colgroup><col/><col/><col/><col/><col/></colgroup><thead><tr><th vertical-align="top">修复原因族</th><th vertical-align="top">题数</th><th vertical-align="top">主要子类与证据状态</th><th vertical-align="top">解决办法</th><th>补充说明</th></tr></thead><tbody><tr><td vertical-align="top">Docker Hub网络不可达</td><td vertical-align="top">97</td><td vertical-align="top">本轮细化70条，历史同义标签27条；错误均指向registry-1.docker.io连接失败或Errno 101 Network is unreachable。</td><td vertical-align="top">将agent和verifier依赖镜像同步到可访问的内部仓库并锁定digest；分别用准备环境与实际构建身份验证拉取。必须访问外网时，按授权修复出口路由或代理。</td><td>「task.toml里面的docker_image配置了本地镜像」<br/>解法：删除这一行<br/>打回专家返修，删除<br/><b>另外需要放入质检Skill要求</b>。<img name="image.png" alt="图片展示了在MASO / Harbor准备流程中，有和没有docker_image配置时的准备方式。有docker_image时，使用指定的预构建镜像，不从对应Dockerfile重建；没有docker_image时，根据对应Dockerfile和构建上下文准备镜像。该图片与文档中关于Harbor 1074题执行复盘的内容相关，用于说明在不同配置情况下MASO / Harbor准备流程的镜像准备方式，辅助理解题目的失败原因及解决办法。" mime="image/png" scale="1.000000" src="FC22bs6oioXVcYxAclqcMR49nie"/><img name="image.png" alt="图片展示的是一个配置文件中的环境设置部分。其中，用红色框突出显示的“docker_image = “runtimefix-a3-agent:20261022””一行是关键内容，表明docker_image的值为“runtimefix-a3-agent:20261022”。该图片与文档中“task.toml里面的docker_image配置了本地镜像”相关，是对此配置的直观呈现，为后续删除这一行以解决镜像相关问题提供参考。" mime="image/png" scale="1.000000" src="H0SmbewTJoxnsxx9a9ZcU8crnVM"/><img name="image.png" alt="图片展示的是一个配置文件中的环境设置部分，其中“docker_image”参数被红色框突出显示。其值为“project21-agent:21.1.2”，表明任务中使用的Docker镜像名称及版本。该图片与文档中“task.toml里面的docker_image配置了本地镜像”内容相关，是问题出现时的配置情况，为后续问题分析和解决提供关键信息。" mime="image/png" scale="1.000000" src="IckcbJzp1o4AumxiuwoccchYnzb"/></td></tr><tr><td vertical-align="top">APT软件源索引或安装包下载403</td><td vertical-align="top">36</td><td vertical-align="top">软件源InRelease访问被拒26条，安装包下载被拒10条。后续“not signed”是索引下载失败的连带结果。</td><td vertical-align="top">修复构建身份可访问的APT镜像源、出口和授权策略，使用可复现源快照；不得用trusted=yes、关闭签名校验或允许不安全仓库掩盖403。</td><td>打回专家返修？使用指定依赖？<br/>解法：找字节可使用的源<br/>风险：限流、司内/外资源不一致<br/>todo：找出哪些apt源异常，让专家替换<img name="image.png" alt="图片展示的是一个错误提示信息，内容为“当前APT源找不到固定的sudo=1.9.15p5-3ubuntu5.24.04.3和ca-certificates=20260601~24.04.1，安装退出100。”该信息被蓝色边框突出显示，位于文档中“准备阶段：322题阻塞在镜像、软件源、依赖、资产或发布链路”部分，是对322题在执行过程中因APT源问题导致安装失败这一情况的说明，为后续查找问题原因、解决办法提供关键信息。" mime="image/png" scale="1.000000" src="A4SnbSFmnof5zZxzExjc2DT0nyf"/></td></tr><tr><td vertical-align="top">Python分发、索引或环境兼容性</td><td vertical-align="top">33</td><td vertical-align="top">19条已确认需求解析失败但索引或兼容性首因待核；14条已明确为无匹配分发、PyArrow/NumPy不兼容、缺少z3模块或索引配置不匹配。</td><td vertical-align="top">在相同基础镜像核对Python版本、CPU/CUDA架构、pip索引和完整pip日志；提供经校验的内部源或离线wheelhouse。不得仅凭“from versions: none”断言版本从未发布，也不直接删除版本约束。</td><td>打回专家返修？使用指定依赖？<img name="image.png" alt="图片展示的是逐题复核结论，内容为运行owl_prepare_assets.py导入pyarrow时报错，ImportError: pyarrow requires NumPy 2.0 or newer, found 1.26.4；模型/公开资产准备在依赖导入阶段已失败。该图片与文档中准备阶段322题阻塞问题相关，表明在准备阶段，模型/公开资产准备在依赖导入阶段因pyarrow依赖问题导致失败，需解决此问题以推进后续工作。" mime="image/png" scale="1.000000" src="UYRQb1iT7oZwh6xZnITchj8Dnuf"/></td></tr><tr><td vertical-align="top">基础镜像引用或拉取授权</td><td vertical-align="top">23</td><td vertical-align="top">pull access denied、insufficient_scope，或短镜像名被解析到docker.io/library；引用错误与授权不足需分开验证。</td><td vertical-align="top">核对完整仓库、tag、digest、平台架构和实际工作负载身份；补齐最小拉取权限后验证manifest。不要把所有404都归为权限问题。</td><td>打回专家返修？使用合法可访问镜像</td></tr><tr><td vertical-align="top">Git仓库访问、锁与推送</td><td vertical-align="top">22</td><td vertical-align="top">index.lock冲突12、push超过300秒6、git-pull失败2、Codebase访问失败1、构建分支幂等冲突1；其中2条pull失败仍需区分授权与网络首因。</td><td vertical-align="top">使用每任务隔离的干净clone和构建分支；先确认无活跃Git进程再处理本次专用锁。用实际身份核对git ls-remote、HTTP状态、推送对象大小和远端接收结果，做有界幂等重试。</td><td>尝试重试<br/>重试无效让maso解决</td></tr><tr><td vertical-align="top">发布包结构或归档损坏</td><td vertical-align="top">22</td><td vertical-align="top">任务根目录不唯一13、未找到任务根目录4、原始包不是有效ZIP 4、RAR数据损坏或截断1。</td><td vertical-align="top">按真实格式解包，校验task.toml、instruction.md和唯一任务根目录；重新下载或补发损坏归档。不得随机选择候选根目录或借用相近题号资产；源包修改必须生成新SHA256和修订记录。</td><td>打回专家返修<br/>「任务根目录」要求：只允许一份task.toml，且文件位置为 workspace/harbor_task/task.toml</td></tr><tr><td vertical-align="top">Python wheel下载拒绝或代理错误</td><td vertical-align="top">14</td><td vertical-align="top">已解析到具体wheel后下载返回403共13条，另有PyPI代理源站DNS错误530一条；这不是单纯缺版本。</td><td vertical-align="top">核对具体下载域名、代理、出口和访问策略，用授权内部源或校验过的离线wheel提供同一资产；保留哈希、TLS和包完整性校验。</td><td>打回专家返修？使用标准版本依赖</td></tr><tr><td vertical-align="top">镜像层上传会话失效</td><td vertical-align="top">13</td><td vertical-align="top">builder到registry提交阶段报blob upload unknown，部分上传PUT返回404。</td><td vertical-align="top">检查上传会话生命周期、registry状态、代理和并发；重新建立会话后有界重试，最终用新工作负载回读manifest和digest。</td><td>尝试重试</td></tr><tr><td vertical-align="top">模型或公开资产下载链路</td><td vertical-align="top">13</td><td vertical-align="top">模型或公开资产429限流10条，TLS证书链失败1条，308重定向未正确处理1条，Agent依赖资产获取超时1条；超时题的具体资产链路仍待补。</td><td vertical-align="top">建立内部资产缓存和授权token，降低共享出口并发并实施退避；修正TLS信任链与重定向处理。受保护资产只在授权作用域下载，不绕过校验。</td><td>尝试重试</td></tr><tr><td vertical-align="top">npm代理认证失败407</td><td vertical-align="top">10</td><td vertical-align="top">npm下载阶段返回407 Proxy Authentication Required；失败点是包管理代理认证，不是Codex进程本身启动失败。</td><td vertical-align="top">修复构建身份的代理认证或改用可访问的内部npm源；验证npm registry元数据和tarball均可读，不在命令或镜像中写入长期凭据。</td><td>看具体的报错，oncall</td></tr><tr><td vertical-align="top">镜像manifest、digest或代理异常</td><td vertical-align="top">9</td><td vertical-align="top">digest无法解析5、镜像代理manifest异常2、ECR blob请求401一条、构建成员镜像manifest发布缺失一条。</td><td vertical-align="top">同时核对源registry与代理的manifest媒体类型、架构、digest和认证；从可信源同步为内部不可变镜像。不得仅凭代理not found判定上游镜像不存在。</td><td>打回专家返修？<br/>变成质检skill枚举</td></tr><tr><td vertical-align="top">构建上下文资产路径缺失</td><td vertical-align="top">6</td><td vertical-align="top">BuildKit计算COPY或cache key时发现指定路径not found。</td><td vertical-align="top">核对授权源包、构建context根目录、COPY路径、.dockerignore和资产manifest；缺失资产补齐后重算哈希。不得创建空目录或把hidden_assets暴露给Agent。</td><td>打回专家返修</td></tr><tr><td vertical-align="top">APT安装命令失败，首因待补</td><td vertical-align="top">5</td><td vertical-align="top">历史标签仅记录APT安装退出100，当前摘录没有第一条致命错误。</td><td vertical-align="top">补拉对应ByteBuild失败步骤完整stdout/stderr，并与Dockerfile行号对齐；先确认403、缺版本、临时目录或协议中的首因，再选择修复。</td><td>尝试重试</td></tr><tr><td vertical-align="top">APT固定版本缺失</td><td vertical-align="top">4</td><td vertical-align="top">sudo、ca-certificates等固定版本在当前源中不可得。</td><td vertical-align="top">核对发行版、updates/security源和源快照，用apt-cache policy验证版本；采用经验证的可复现版本集合，不取消全部版本锁定。</td><td>尝试重试</td></tr><tr><td vertical-align="top">Python依赖约束冲突</td><td vertical-align="top">2</td><td vertical-align="top">ResolutionImpossible或requirements与constraints不兼容。</td><td vertical-align="top">用完整解析报告定位冲突依赖对，统一为有解且经过测试的版本集；不盲目升级全部依赖或删除约束。</td><td>Agent尝试修改题包</td></tr><tr><td vertical-align="top">准备脚本或资产校验失败，首因待补</td><td vertical-align="top">2</td><td vertical-align="top">历史标签记录prepare_image.py public退出1、uv sync或资产校验退出2，但缺少首个失败子命令。</td><td vertical-align="top">补齐traceback和命令stderr，区分依赖解析、公开资产下载和校验失败；不得删除资产校验来换取构建成功。</td><td>打回专家返修</td></tr><tr><td vertical-align="top">APT证书包配置临时目录缺失</td><td vertical-align="top">2</td><td vertical-align="top">配置ca-certificates时所需临时目录不存在或不可用。</td><td vertical-align="top">调整Dockerfile步骤顺序和目录创建权限，确保APT或证书脚本运行前临时目录存在且属主正确；修复后验证证书链。</td><td>打回专家返修</td></tr><tr><td vertical-align="top">评分资产或锚点不一致</td><td vertical-align="top">2</td><td vertical-align="top">评分锚点与fixture映射哈希不一致1条，评分初始化目标hidden_assets目录缺失1条。</td><td vertical-align="top">由授权verifier维护者核对资产manifest、锚点哈希、fixture映射和隔离复制步骤；不能删除校验、创建空目录或向Agent暴露隐藏资产。</td><td>打回专家返修</td></tr><tr><td vertical-align="top">源包路径访问被拒</td><td vertical-align="top">1</td><td vertical-align="top">准备进程访问包内environment/starter/solve.sh时报Permission denied。</td><td vertical-align="top">核对准备工作负载身份、解包后文件及父目录模式；在授权隔离副本中处理只读源文件，不递归chown或chmod原资产。</td><td>打回专家返修</td></tr><tr><td vertical-align="top">bootstrap解释器无法启动</td><td vertical-align="top">1</td><td vertical-align="top">/opt/runtime/bin/python调用bootstrap.py失败，现象指向解释器路径或启动契约。</td><td vertical-align="top">核对解释器文件、动态链接依赖、PATH和bootstrap脚本权限，验证原启动契约；不随意替换运行时或提升到root。</td><td>打回专家返修</td></tr><tr><td vertical-align="top">sudoers规则语法错误</td><td vertical-align="top">1</td><td vertical-align="top">visudo或sudoers校验明确失败。</td><td vertical-align="top">按最小授权修正规则并用visudo -cf校验；保留命令范围和身份限制，不开放无约束sudo。</td><td>打回专家返修</td></tr><tr><td vertical-align="top">Docker Hub请求限流429</td><td vertical-align="top">1</td><td vertical-align="top">manifest HEAD请求明确返回429 Too Many Requests。</td><td vertical-align="top">使用授权缓存或内部同步镜像，降低重复manifest请求，按限流响应退避；不通过提高并发掩盖限流。</td><td>打回专家返修</td></tr><tr><td vertical-align="top">创建用户时UID 1000冲突</td><td vertical-align="top">1</td><td vertical-align="top">useradd或等价初始化步骤发现UID 1000已被占用。</td><td vertical-align="top">核对基础镜像既有用户和题目要求的运行UID；按契约改用明确UID或调整创建步骤，避免UID变化破坏只读资产权限。</td><td>打回专家返修</td></tr><tr><td vertical-align="top">sudo资产下载源全部失败，HTTP状态待补</td><td vertical-align="top">1</td><td vertical-align="top">已确认锁定sudo资产的所有下载源均失败，但现有摘录没有保留具体HTTP状态。</td><td vertical-align="top">补记录各源请求URL、HTTP状态、代理和DNS结果；确认是授权、网络还是源不可用后再修复，不放宽sudo资产约束。</td><td>打回专家返修</td></tr><tr><td vertical-align="top">Python依赖包哈希校验失败</td><td vertical-align="top">1</td><td vertical-align="top">下载包与requirements声明哈希不一致。</td><td vertical-align="top">隔离下载物，核对锁文件、预期wheel、缓存和镜像来源；仅在验证可信资产后更新正确哈希，不删除--require-hashes。</td><td>打回专家返修</td></tr></tbody></table>

## 细化后的关键结论与证据边界

- **归因覆盖：**249条通用标签已更新为38个具体表内标签；与历史73条已有标签记录合并并归并同义写法后，形成上表25个修复原因族。所有322题仍保持准备失败状态，没有进入执行或评分。
- **证据强度：**本轮细化的249条中，156条由原始准备错误直接确认，70条由补充ByteBuild日志直接确认；补充读取覆盖93道题关联的98份ByteBuild日志。其余23条已确认失败步骤或失败需求，但底层首因仍需补证。
- **仍待补底层首因的23条：**19条为pip分发索引或Python兼容性，2条为ICM git-pull授权或网络，1条为Agent依赖资产获取超时，1条为sudo资产下载源HTTP状态不明。它们不是“无原因”，不能用跳过校验或盲目改版本处理。
- **APT边界：**InRelease或安装包403之后出现的“not signed”是下载失败连带结果，不应关闭签名校验；只有APT退出100而没有首条错误的5条历史记录仍需补日志。
- **包管理边界：**npm 407应修代理认证或内部npm源；pip “from versions: none”不能单独证明包版本从未发布；wheel下载403、PyPI代理DNS错误和哈希不匹配应分别处理。
- **资产与缓存边界：**HuggingFace等公开资产429主要按共享出口限流处理，应内部缓存、授权token、降并发并退避；buildcache not found是无害缓存未命中，不是终止原因。hidden_assets和评分锚点只能由授权verifier维护者修复。

典型证据可回查：[auto1815依赖解析日志](<internal-log>)、[AutoRe0187 APT构建日志](<internal-log>)、[auto1941镜像层上传日志](<internal-log>)。本轮补充证据还包括表内记录的其他ByteBuild链接；具体题号、日志来源和证据摘录已保留在任务状态总表。

# 执行阶段：系统性拦截与Agent异常分开处理

本节覆盖152题执行阶段失败及116题已评分但执行异常，共268题。以下按表内原因标签合并，类别互斥；GPU和环境变量问题在“缺少摘要”23题内进一步说明，不重复计数。

<table><colgroup><col/><col/><col/><col/><col/></colgroup><thead><tr><th vertical-align="top">原因族</th><th vertical-align="top">题数</th><th vertical-align="top">证据边界</th><th vertical-align="top">解决办法</th><th>补充说明</th></tr></thead><tbody><tr><td vertical-align="top">工作目录可写性检查拦截</td><td vertical-align="top">106</td><td vertical-align="top">例如auto0850、auto0926；非root Agent面对root:root、755目录，启动前检查报错。</td><td vertical-align="top">先确认题目是否要求只读。只读是设计时修正不适用的预检并保持权限；确需写入时仅授权规定的输出位置。</td><td>尝试改写前置校验器配置。初步验证可解决问题<img name="image.png" alt="这是一段与Harbor 1074题执行相关的配置调整说明代码及注释内容。内容分为环境配置代码、配置修改说明、命令行指令及注意事项几个部分，核心是在triall的job-config.json文件中修改环境配置，将“workdir_access”设为“off”，同时提供了通过harbor run命令指定该配置的方式，还说明了修改后的相关限制与操作要求，用于解决Agent异常相关的问题，是对应文档中执行阶段处理系统性拦截与Agent异常问题的具体配置操作内容。" mime="image/png" scale="1.000000" src="HEgnbKLspof0VEx5r7PcKndnnrg"/><img name="image.png" alt="图片展示了Harbor 1074题执行复盘中关于Agent超时问题的代码及说明。代码部分在runner为每个题目生成sandbox配置时加入配置项，位置在trial内置的streaming_pipeline.py中。下方说明了check、off的含义，即检查cmd是否可写、不检查等。图片与上下文紧密相关，是对Agent超时问题解决办法的详细说明，帮助理解问题原因及解决措施。" mime="image/png" scale="1.000000" src="R3AobUw67oNCfox3MSac9BqAn3g"/><img name="image.png" alt="图片展示的是Harbor 1074题执行复盘中关于Agent超时的记录。显示截至2026年10月26日21:14，trial 440031833仍在运行。原生准备、已结束执行、已评分等状态信息均有呈现，如AutoRe1843、AutoRe1851已评分但失败，reward=0；AutoRe0770 Agent原生执行成功但任务为unscored，没有reward等。图片与上下文紧密相关，直观呈现了Agent超时问题的执行状态及部分结果。" mime="image/png" scale="1.000000" src="ZN3lbOtZ2oOEh6xFOSUcDgynnph"/></td></tr><tr><td vertical-align="top">HOME／临时目录／日志权限</td><td vertical-align="top">4</td><td vertical-align="top">例如AutoRe0291、AutoRe0176；HOME指向不可写路径，PID或日志创建失败。</td><td vertical-align="top">在实际挂载后核对UID/GID与HOME，提供独立可写运行目录和本次专用PID路径；不改题目只读资产。</td><td>打回专家返修</td></tr><tr><td vertical-align="top">Agent超时</td><td vertical-align="top">119</td><td vertical-align="top">记录3600秒截止；包含有评分与无评分两种结局。尚不能把等待、计算和无效循环混为一因。</td><td vertical-align="top">按轨迹拆分模型等待、工具、训练／搜索和重试耗时，设置分级预算与提前保存；确需更长预算时单独授权并标注评测口径变化。</td><td>任务设定1小时超时，部分符合预期，状态改为「成功（Agent超时）」。<br/>其余尝试重试</td></tr><tr><td vertical-align="top">其他非零Agent退出</td><td vertical-align="top">8</td><td vertical-align="top">NonZeroAgentExitCodeError；非零退出只是现象，具体原因需读stderr。</td><td vertical-align="top">检查首次非零命令、依赖与输出路径，验证Agent启动契约；不默认归为权限问题，不提升到root掩盖错误。</td><td>尝试重试</td></tr><tr><td vertical-align="top">Agent安全拒绝</td><td vertical-align="top">5</td><td vertical-align="top">例如auto2709记录LLMRefusalError及安全风险提示。</td><td vertical-align="top">核对任务授权、目标范围和模型平台适用政策；适用的授权渠道或支持流程由负责人处理。不得改写提示词绕过安全限制。</td><td>尝试重试？ 算法确认<img name="image.png" alt="这张图片展示了一段程序执行的错误日志内容，核心是Agent调用相关的报错信息，提示检测到存在网络安全风险的内容，需要重新发起请求。日志中包含多条技术相关的代码与参数信息，如训练相关的日志内容、异常错误的定位信息，还记录了具体的错误类型为MLSafetyError，并有对该错误的详细解释，同时也标注了调用异常的相关组件路径、命令行执行参数等细节，用于排查和定位执行过程中触发的网络安全拦截问题。" mime="image/png" scale="1.000000" src="Zb5Ab5dgTohuSlxa7v8cnUpvnwe"/></td></tr><tr><td vertical-align="top">执行已结束但未发布原生摘要</td><td vertical-align="top">23</td><td vertical-align="top">438627695占19题，439171143占4题；不是仍在运行。</td><td vertical-align="top">保留已有日志和错误证据；修正已知启动契约问题，同时补齐退出码、终态文件和归档回执。不能凭缺失摘要补分。</td><td>打回专家返修。没有评分结果</td></tr><tr><td vertical-align="top">环境健康检查失败</td><td vertical-align="top">1</td><td vertical-align="top">AutoRe0664：连续3次检查test -S /run/public-eval.sock失败。</td><td vertical-align="top">检查服务启动日志、socket创建与可见挂载、启动顺序和合理就绪时限；不能简单删掉healthcheck。</td><td>尝试重试。MASO 环境检查的问题</td></tr><tr><td vertical-align="top">环境创建／cgroup资源设置失败</td><td vertical-align="top">1</td><td vertical-align="top">Auto0203：CgroupCreationFailed，cpu.cfs_quota_us写入invalid argument。</td><td vertical-align="top">核对任务资源请求与沙箱后端支持范围，携请求ID和资源参数找平台确认；不能自行缩减题目资源需求。</td><td>尝试重试。16核及以下的能正常跑，24核异常，不确定是不是平台的偶现问题</td></tr><tr><td vertical-align="top">其他沙箱异常</td><td vertical-align="top">1</td><td vertical-align="top">表内记录沙箱运行任务不存在；需结合环境生命周期日志定位。</td><td vertical-align="top">核对会话创建、任务ID、清理与重试边界，避免复用已删除会话；先补证据再重跑。</td><td>尝试重试</td></tr></tbody></table>

## 工作目录只读与运行目录可写不是同一约束

表内较早记录有“改镜像目录归属／workdir_access=chown”的通用建议；后续复核与用户约束明确指出工作目录对Agent只读可能是题目设计。**本文采用条件式修复，不把历史通用建议当成统一执行指令。**

1. 先阅读题目声明，确认只读资产、允许写入目录、最终交付路径与Agent用户。保留原始UID/GID、目录mode和挂载属性证据。
2. 若工作目录按设计只读：仅在运行器确实支持且评测负责人确认后关闭／调整不适用的可写性预检（如workdir_access=off），保持实际文件权限不变。单独保证HOME、日志、缓存、临时文件及题目允许的输出位置可写。
3. 若题目明确允许或需要写入某个输出目录：修复镜像USER／WORKDIR与该输出目录的契约，检查运行时挂载是否覆盖镜像权限。只对授权目录和正确UID/GID操作，不能递归chown整题资产或chmod 777。
4. 验收同时证明：Agent以原指定身份启动、只读路径仍拒绝写入、允许的输出路径可写、日志与结果可保存、verifier协议和题目要求未变。

## 缺少摘要的23题：18题GPU路由、1题环境变量、4题待补证据

以下18题属于Trial 438627695，表内保留的此前batch.log均显示“ValueError: device_type does not satisfy the task GPU requirements”：auto2089、auto2666、auto0539、AutoRe1221、AutoRe1228、auto0538、AutoRe1220、auto0537、auto0290、AutoRe1229、AutoRe1402、AutoRe0288、AutoRe0389、auto0592、AutoRe1225、AutoRe1150、AutoRe0594、AutoRe1404。

这证明当时原生CLI环境初始化存在device_type与题目GPU约束不兼容，并不证明18题“都没有分配GPU”或属于配额不足。修复时逐题核对gpus、gpu_types、device_type、CPU/GPU环境管理器路由及实际沙箱设备；维持题目原始CPU/GPU和资源约束，先完成环境创建与探测，再允许Agent执行。

同Trial的Auto0107记录缺少LLM_API_KEY（environment.env阶段）。应通过授权的密钥注入／环境文件契约补齐所需变量；只验证是否存在及作用域，禁止把密钥明文写入表格、文档、命令日志或题目包。

Trial 439171143的auto1043、auto1199、auto1287、auto1676只有协调器执行终态，无已发布摘要和可用原始执行错误，具体根因仍未确认。优先补batch.log、complete.json、原生result与上传错误，而不是重启旧trial来探测。

18题GPU和1题环境变量的依据是表内明确标为“此前快照”的日志，不是本次重新读取结束后的容器文件；本轮最终日志确认它们已结束但没有发布摘要。复跑前仍需独立复现启动契约并补完整终态证据。

# 评分阶段：74题需要修复协议或产物回传

| 原因 | 题数 | 已记录现象 | 修复与验收 | 补充说明 |
|-|-|-|-|-|
| 评分文件缺失 | 72 | RewardFileNotFoundError／verifier评分文件缺失，未找到reward.txt或reward.json。 | 核对verifier退出码、stdout/stderr和实际输出路径；区分脚本未生成、路径不符与回传失败。由真实计算生成协议有效评分，不能补造零分。 | 打回专家返修 |
| verifier目录下载失败 | 1 | Auto0268：DownloadVerifierDirError。 | 若沙箱内产物已存在，查目录挂载、下载／传输及会话存活期；验收本地与归档产物一致，不只验证脚本退出0。 | 环境被回收，尝试重试 |
| 非数值评分null | 1 | 表内记录verifier输出非数值null。 | 核对评分异常分支和JSON序列化；正常分支返回有限数值，失败分支明确报错。null、NaN、Infinity不能当有效零分。 | 打回专家返修 |

所有修复均保持题目评分逻辑、阈值、公开／受保护资产边界不变。Agent已有有效输出时，可先评估是否支持“仅修复评分／回传并独立复评分”，避免无谓重跑Agent；如平台不支持或输出不完整，必须记录新的评估版本与重跑原因。

# 需加入质检skill的rule

1. 不允许项目中有多个task.toml。只能有一份 workspace/harbor_task/task.toml
2. task.toml 里禁止配置docker_image，以 workspace/harbor_task/environment/Dockfile 为准

![图片展示了MASO / Harbor准备流程中关于配置有docker_image和没有docker_image时的准备方式。有docker_image时，使用指定的预构建镜像，不从对应Dockerfile重建；没有docker_image时，根据对应Dockerfile和构建上下文准备镜像。该图片与文档中Harbor 1074题执行复盘内容相关，用于说明在不同配置情况下MASO / Harbor准备流程的镜像准备方式。](<lark-doc>)

![这张图展示了task.toml文件中\[environment\]配置块的部分内容，其中被红色框线突出标注的内容为“docker_image = "runtimefix-a3-agent:20261022"”。结合该文档的任务要求上下文，这份文档中明确要求task.toml文件禁止配置docker_image，需以workspace/harbor_task/environment/Dockfile中的相关内容为准，这张图呈现的就是不符合该要求的错误配置项，是本次复盘提及的失败原因对应的违规配置示例。](<lark-doc>)

1. 所有依赖禁止使用非官方源（比如清华源），不自行设置镜像源，默认使用官方源

![图片展示了Harbor 1074题执行复盘中关于官方源解决部分依赖下载问题的实测结果。表格中列出AutoRe0590、AutoRe0354、Auto0403三个题包，分别说明了其完整题目环境镜像构建成功、APT依赖层构建成功、换官方源仍失败的情况。其中，Auto0403失败是因为scipy==1.18.1要求Python ≥3.12，原镜像是Python 3.11.12，需调整版本或Python环境。该图片与文档中关于官方源解决依赖下载问题的复盘内容紧密相关。](<lark-doc>)

1. ~~如使用npm包，Dockfile里的依赖镜像源必须改为~~ [~~https://bnpm.byted.org~~](https://bnpm.byted.org/) 

```Dockerfile
npm config set registry https://bnpm.byted.org
```