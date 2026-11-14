<title>题包运行问题修复说明：错误 / 正确样例（19题） 副本</title>

本文供外部专家修复题包的运行兼容性问题，覆盖 19 道题、8 类问题。每类按“遇到的问题—错误示例 / 正确示例—错误原因—修正后应达到”说明。

示例中的脚本、目录、UID 和流程均为脱敏结构示意，请替换为本题原有实现；不是统一目录规范，也不是已经验证的可执行补丁。仅保留通用系统目录及题包内相对路径。

运行验收口径：独立评分器实际产出数值分数即算运行通过；低分、负分或质量门槛未通过，不另判运行失败。保持原始评分与状态，不伪造分数、不改变评分规则。以下是已确认的题包缺陷修复说明，不代表 19 题按此口径全部未通过。

修复边界：Sandbox 负责平台级任务隔离、资源分配与运行环境约束；题包在平台提供的环境中准备必要输入，直接执行原有训练、公开评估和独立评分入口，不重复实现一套 Sandbox 或资源管理器。题包仅修复自身环境、入口、资产与产物交付问题，并保留原输入/产物校验、评分数据访问边界和科学评分；不修改平台或宿主内核。

# 训练或评分强依赖不可用的 Landlock

涉及题目：10454、10393、10481、10715、10771、10820。

遇到的问题：可信训练或评分进程在载入候选方法前，就因 Landlock 不可用退出。常见错误为 landlock_unavailable、Function not implemented、ENOSYS；后续“缺模型”可能只是训练未启动的结果。

<table><colgroup><col/><col/></colgroup><thead><tr><th vertical-align="top">错误示例</th><th vertical-align="top">正确示例</th></tr></thead><tbody><tr><td vertical-align="top"><pre caption="&#xA;" lang="text" wrap="false"><code>训练 / 评分启动<br/>  → 强制检查 Landlock ABI<br/>  → 当前环境不可用<br/>  → 直接抛错退出<br/><br/>候选方法尚未载入；<br/>训练或评分无法继续。</code></pre></td><td vertical-align="top"><pre caption="&#xA;" lang="text" wrap="false"><code>平台：提供已隔离且资源已配置的环境<br/><br/>题包正式入口：<br/>  → 准备必要依赖和输入<br/>  → 直接执行原有训练 / 公开评估<br/>  → 在独立评分环境执行原评分入口<br/>  → 写出数值评分及原始状态<br/><br/>不因缺少 Landlock 阻断运行；<br/>不要求题包再实现一套 Sandbox。</code></pre></td></tr></tbody></table>

错误原因：把特定内核能力作为题包启动前提，而执行环境不提供该能力；不能因此认定候选算法有问题。

请修正：移除把 Landlock 可用性作为训练、公开评估和独立评分启动前提的逻辑，使用平台已经提供的隔离与资源配置，直接执行正式入口。保留题包原有输入、产物及评分数据权限校验；不把新建 chroot、seccomp 或用户隔离实现作为统一交付要求。

修正后应达到：在平台现有 Sandbox 内，即使不提供 Landlock，正式训练 / 公开评估及独立评分仍能执行并出分；按“出分即运行通过”验收，不要求额外建设隔离层。

边界说明：平台隔离不同任务或运行环境，不自动证明同一个评分环境中候选代码无法读取私有评分材料。如果原检查还承担此类应用内权限保护，应核对现有候选/评分运行约定，保留必要的数据权限校验；不能把“直接执行”理解成删除所有保护，也不因此要求专家自行重建平台隔离。

# HOME、临时目录或日志目录不可写

涉及题目：10058、10873、10597、10844。

遇到的问题：非 root 用户缺少存在且可写的 HOME，或临时目录被改成仅属主可写，导致 Agent 初始化、后台工具、PID 文件或日志创建失败。常见错误为 mkdir Permission denied、background command Permission denied。

<table><colgroup><col/><col/></colgroup><thead><tr><th vertical-align="top">错误示例</th><th vertical-align="top">正确示例</th></tr></thead><tbody><tr><td vertical-align="top"><pre caption="&#xA;" lang="text" wrap="false"><code>容器运行用户：非 root<br/><br/>HOME 未设置，或指向不存在目录<br/>缓存 / 日志目录由 root 持有且不可写<br/>/tmp、/var/tmp 权限为 0755<br/><br/>结果：<br/>初始化用户目录或启动后台工具失败。</code></pre></td><td vertical-align="top"><pre caption="&#xA;" lang="text" wrap="false"><code>构建时明确题包实际运行 UID<br/>为该用户创建 HOME、缓存和日志目录<br/>目录归属与运行用户一致<br/>/tmp、/var/tmp 使用兼容的 1777 权限<br/>最终 WORKDIR 为候选用户可写目录<br/><br/>验证：以同一非 root 用户创建文件，<br/>实际启动 Agent、后台工具及公开入口。</code></pre></td></tr></tbody></table>

错误原因：构建期 root 能写，不代表运行期候选用户能写；复制只读 Starter 后，仅修改文件属主也不一定恢复写权限。

请修正：在题包镜像内补齐实际用户、HOME、必要子目录、日志和工作目录的初始化；候选可写目录与评分私有目录分别设置权限。不要把全部目录改成全员可写。

修正后应达到：从全新环境以实际运行 UID 正常启动，缓存、日志和后台工具均可写；不依赖手工 chmod 或历史容器中的残留目录。

10844 需单独保留另一处问题：可信 NumPy / OpenBLAS 在导入候选前出现线程创建或模块加载失败。目前仅凭进程上限数值不能确定原因，也不能断言修复临时目录即可解决它；需保留完整子进程错误日志，在同版本环境继续复现。

# 仅依赖镜像 ENTRYPOINT 启动服务或生成资产

涉及题目：10429、10590。

遇到的问题：正式训练依赖后台评分服务或公开资产，但这些准备动作只写在镜像 ENTRYPOINT；实际平台直接启动指定命令，未触发该 ENTRYPOINT。表现为 socket 无法连接，或 candidate_payload.pt 等文件不存在。

<table><colgroup><col/><col/></colgroup><thead><tr><th vertical-align="top">错误示例</th><th vertical-align="top">正确示例</th></tr></thead><tbody><tr><td vertical-align="top"><pre caption="&#xA;" lang="text" wrap="false"><code>Dockerfile：<br/>ENTRYPOINT ["./boot_service.sh"]<br/><br/>boot_service.sh：<br/>启动评分服务 / 生成公开资产<br/><br/>solve.sh：<br/>直接连接服务 / 读取资产<br/><br/>若平台未执行 ENTRYPOINT：<br/>训练在准备阶段失败。</code></pre></td><td vertical-align="top"><pre caption="&#xA;" lang="text" wrap="false"><code>题包正式入口：<br/>  → 显式执行受控准备步骤<br/>  → 核对资产版本与完整性<br/>  → 检查所需服务已就绪<br/>  → 再执行原有训练 / 公开评分<br/><br/>例如包内包含：<br/>public_eval/prepare.py<br/>public_eval/healthcheck.py<br/>solution/solve.sh<br/><br/>准备动作与权限边界随题包交付。</code></pre></td></tr></tbody></table>

错误原因：镜像启动假设没有写进实际可执行的题包入口；仅有 Dockerfile 中的 ENTRYPOINT 不能保证目标平台会执行。

请修正：把准备、健康检查和资产验证接入正式入口，不依赖执行端额外打补丁。可信服务必须保持固定权限边界，不能向候选开放私有数据或任意 root 命令。

修正后应达到：目标平台不执行隐式 ENTRYPOINT 时，正式入口仍可完成准备、训练和评分；重复启动与失败退出的行为明确。

# 固定共享 UID 与过低进程上限冲突

涉及题目：10611、10741。

遇到的问题：评分器给候选设置 RLIMIT_NPROC=16，再切换到固定共享 UID，创建 Python worker 时返回 EAGAIN / Resource temporarily unavailable；此时尚未执行候选算法。

<table><colgroup><col/><col/></colgroup><thead><tr><th vertical-align="top">错误示例</th><th vertical-align="top">正确示例</th></tr></thead><tbody><tr><td vertical-align="top"><pre caption="&#xA;" lang="text" wrap="false"><code>多个任务共用相同候选 UID<br/><br/>评分器：<br/>  设置 NPROC = 16<br/>  切换到共享 UID<br/>  启动 Python worker<br/><br/>结果：同 UID 的进程计数已触限，<br/>worker 还没运行就启动失败。</code></pre></td><td vertical-align="top"><pre caption="&#xA;" lang="text" wrap="false"><code>采用经目标环境核验的任务身份方案<br/>避免无关任务共用同一进程计数预算<br/><br/>保留：<br/>  原候选进程上限<br/>  CPU / 内存 / 文件资源限制<br/>  用户降权及私有数据保护<br/><br/>验证：单任务与批量并发时，<br/>可信 worker 均能启动并出分。</code></pre></td></tr></tbody></table>

错误原因：进程限制可能按 UID 的已有进程合计生效，而非只按当前题包内子进程计数。已有对照检查支持共享 UID 与低上限的兼容冲突，不能直接认定为 GPU 不够。

请修正：在题包内选择可验证的任务身份与进程预算方案，保留原限制；不要用全局提限或取消降权解决。并额外核对候选用户的最终工作目录是否可写。

修正后应达到：并发条件下不再在 exec 阶段报 EAGAIN，且原有隔离和资源限制仍有效。

# 模型、训练及验证资产未交付

涉及题目：10646。

遇到的问题：代码要求加载 Qwen2.5-7B 等基座及训练 / 验证数据，但交付物只有清单说明，没有实际资产，也没有可执行的受控交付或挂载说明。训练前即报 FileNotFoundError，后续 checkpoint 缺失是结果。

<table><colgroup><col/><col/></colgroup><thead><tr><th vertical-align="top">错误示例</th><th vertical-align="top">正确示例</th></tr></thead><tbody><tr><td vertical-align="top"><pre caption="&#xA;" lang="text" wrap="false"><code>task_package/<br/>  solution/solve.sh<br/>  assets/<br/>    MANIFEST.md<br/><br/>MANIFEST 只写“运行时由外部挂载”<br/>模型、配置及训练数据未交付<br/>也未说明由谁、以何种方式准备<br/><br/>结果：模型加载阶段失败。</code></pre></td><td vertical-align="top"><pre caption="&#xA;" lang="text" wrap="false"><code>task_package/<br/>  solution/solve.sh<br/>  assets/<br/>    MANIFEST.json<br/>    model/  # 原版本完整模型文件<br/>    train/  # 原训练数据<br/>    dev/    # 原开发数据<br/><br/>或提供获授权的单独交付方式，<br/>注明固定版本、摘要、放置位置<br/>以及正式入口的准备步骤。</code></pre></td></tr></tbody></table>

错误原因：描述“应当挂载”不能代替真实文件和受支持的准备步骤。仅把代码路径改成另一处目录，也不能补齐缺失资产。

请提供：原基座名称与版本、权重和配置 / 分词器文件清单、真实 Train / Dev 数据、文件摘要及受控交付说明。受限数据只进入约定角色，不公开给候选。不能自行换小模型或用合成数据代替。

修正后应达到：从干净环境按交付说明准备资产，正式训练能读取真实输入、生成 checkpoint，并交给独立评分器计算分数。缺料时由材料提供方补齐，不能要求专家凭空补造。

# 未声明候选产物，独立评分收到空目录

涉及题目：1151。

遇到的问题：Agent 运行目录已有 method.py、solve.sh，但题包未正确声明需要移交的候选产物；独立评分环境收到空目录，报 expected method.py and solve.sh; got []。

<table><colgroup><col/><col/></colgroup><thead><tr><th vertical-align="top">错误示例</th><th vertical-align="top">正确示例</th></tr></thead><tbody><tr><td vertical-align="top"><pre caption="&#xA;" lang="text" wrap="false"><code>Agent 运行后：<br/>solution/<br/>  method.py<br/>  solve.sh<br/><br/>题包运行配置：<br/>未声明以上候选产物及来源<br/><br/>独立评分收到：<br/>solution/<br/>  # 空目录</code></pre></td><td vertical-align="top"><pre caption="&#xA;" lang="text" wrap="false"><code>Agent 运行后：<br/>solution/<br/>  method.py<br/>  solve.sh<br/><br/>题包运行配置：<br/>按执行器正式格式声明候选产物<br/>明确来源目录及评分端读取位置<br/><br/>移交前后核对：<br/>文件清单一致，SHA256 一致。</code></pre></td></tr></tbody></table>

错误原因：候选存在于 Agent 环境，不代表已交到独立评分环境；评分端空目录不能直接归为 Agent 没写代码。

请修正：使用执行器正式支持的产物声明，核对源目录、移交范围和评分端路径。配置字段须按实际格式填写，不能直接把此处说明当成可执行配置。

修正后应达到：真实 Agent 生成的候选原样到达独立评分器，摘要一致，评分器能载入并出分；同时验证只读 Starter 复制后候选仍具备必要写权限。

# 公开评估生成额外文件，污染严格提交目录

涉及题目：10326、1006。

遇到的问题：正式公开评估导入候选后生成 \_\_pycache\_\_ / pyc，或 MuJoCo 在候选目录写出 MUJOCO_LOG.TXT；独立评分随后按严格文件白名单拒绝该目录。

<table><colgroup><col/><col/></colgroup><thead><tr><th vertical-align="top">错误示例</th><th vertical-align="top">正确示例</th></tr></thead><tbody><tr><td vertical-align="top"><pre caption="&#xA;" lang="text" wrap="false"><code>公开评估前：<br/>solution/<br/>  method.py<br/>  solve.sh<br/><br/>公开评估后：<br/>solution/<br/>  method.py<br/>  solve.sh<br/>  __pycache__/<br/>  MUJOCO_LOG.TXT<br/><br/>独立评分：额外文件，拒绝。</code></pre></td><td vertical-align="top"><pre caption="&#xA;" lang="text" wrap="false"><code>候选目录保持原白名单：<br/>solution/<br/>  method.py<br/>  solve.sh<br/><br/>公开评估：<br/>  导入候选时禁写 bytecode<br/>  可信进程的 cwd 指向评估输出目录<br/>  日志、缓存与候选产物分开存放<br/><br/>公开运行后直接移交，目录仍合规。</code></pre></td></tr></tbody></table>

错误原因：额外文件由题包自身的可信公开流程产生，而非必然是候选自行违规；公开评估与独立评分对目录的约定互相冲突。

请修正：让可信导入、训练和评估日志不污染候选目录；保留原文件白名单，不能简单关闭检查。不要靠移交前手工删除文件掩盖正式流程中的问题。

修正后应达到：按“公开评估 → 立即移交 → 独立评分”的实际顺序运行，以及超时收尾后移交，均不新增违规文件并可出分。

# 原子发布与单链接文件检查发生竞态

涉及题目：10609。

遇到的问题：官方发布器使用 os.replace 原子替换文件；可信读取器先打开旧文件，再检查 st_nlink==1。恰在两步之间替换时，旧 inode 的链接数变为 0，正常发布也被误判。

<table><colgroup><col/><col/></colgroup><thead><tr><th vertical-align="top">错误示例</th><th vertical-align="top">正确示例</th></tr></thead><tbody><tr><td vertical-align="top"><pre caption="&#xA;" lang="text" wrap="false"><code>读取器：open("result.bin")<br/>发布器：os.replace(new, "result.bin")<br/>读取器：fstat(已打开的旧 fd)<br/>        → st_nlink = 0<br/>        → 判为非法文件<br/><br/>结果：<br/>Artifact must be a bounded<br/>single-link ordinary file</code></pre></td><td vertical-align="top"><pre caption="&#xA;" lang="text" wrap="false"><code>识别正常替换造成的短暂竞态<br/>必要时有界重开当前路径<br/>每次重新校验：<br/>  不跟随符号链接<br/>  普通文件、单链接<br/>  文件大小上限及完整读取<br/><br/>并发发布可成功；<br/>符号链接、硬链接、FIFO、超限文件<br/>仍然被拒绝。</code></pre></td></tr></tbody></table>

错误原因：把原子发布造成的合法瞬态，当成了恶意文件形态。已有隔离并发复现支持这一原因。

请修正：使发布与可信读取约定一致，只处理被证实的替换瞬态；不要移除单链接、大小、nofollow 等安全检查，也不能无限重试。

修正后应达到：重复并发发布 / 读取稳定出分，负向样例仍按原约定拒绝；修复版须重新构建并在目标环境验证。