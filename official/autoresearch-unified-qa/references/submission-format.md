# 当前交付结构与证据

以原生Harbor和[当前标准](current-standard-policy.md)检查，不限定额外workspace/harbor_task外层，也不因等价结构拒收。

```text
tasks/<task-id>/
  task.toml
  instruction.md
  environment/        # Work公开资产/Starter/必要依赖
  solution/solve.sh   # Oracle入口，语言/实现文件可等价
  tests/test.sh       # 独立Judge入口/私有资产供给
```

只认可实际Runner选择、构建context/COPY/ignore和提交契约。Oracle所有题必查，不给Agent；tests可上传独立sandbox或专用镜像预置，不一律要求第二Dockerfile。公开Dev留Work，私有tests/Hidden/Reference不能进入其镜像层；必要实体数据与依赖预置可用，锁定版本。

manifests/evidence等来源建议附件不是额外必交schema。已有方法、正式协议结果、模型/重载、轨迹或原始日志完整读取并核对真实关系；不强制optimization_evidence固定树、八字段、四hash或两轨文件名。正式协议已声明全部seed/重复必须完整审，不能挑轮、空日志/模型冒充成功。

提交物范围按题面，控制大小与类型，不把整工作区/下载缓存/无关checkpoint移交；候选与Judge读取内容真实对应。已有hash比较用途一致，不因不同种类hash不等同认错。

更多文件/旧布局/等价命名是精简建议，只有导致当前实体资产缺失、不可调用、错评分、私有暴露或身份造假才按L0处理。50G actual size与12h稳定性由平台验证，源码缺内网证明不独自失败。NOP不要求。
