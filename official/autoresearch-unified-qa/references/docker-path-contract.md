# 当前构建与路径核对

按[当前标准](current-standard-policy.md)和真实Runner/配置选择构建路径，不把旧teaching-task-root或某固定context当另一套门。

从实际Dockerfile/镜像、context、COPY/ADD、ignore、入口脚本和artifacts沿链核对：必要资产存在、未排除；公开Dev可达；私有tests/Hidden/Reference不入Work任何镜像层；Oracle与评分入口真实可调用。相对路径按实际工作目录解析，绝对提交物路径与Judge读取一致。动态表达式须读真实说明/代码，不能靠猜测通过。

继承初始镜像后上传tests、专用评分构建或已发布镜像均按目标实际分支。Verifier独立sandbox和依赖保留，不取Agent结束时临时包/缓存。缺第二Dockerfile、等价根布局或无内网发布tag不单独退题。明确COPY缺资产、错误context、私有暴露或提交未覆盖实际评分路径按L0具体判。

unknown目标仅平台范围，不要求专家新Docker探针；读完已有运行反证，不把静态构建分析说成本次运行成功。
