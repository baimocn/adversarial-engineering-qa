# 拆题缓存

拆题由编排模型在启动时用 `ListModels` 问人选择“最强模型”，产物经
`scripts/validate_decomposition.py` 校验后缓存在这里：

```
criteria/decompositions/<task-family>.json
```

缓存带 `task_family`、`generated_by`（模型）、`rubric_sha256`、`validated_at`。
同一题族后续运行直接复用；题面/合同变了才重拆。缓存不是证据，只是把
“怎么验”固定下来；真正的结论仍来自 `scripts/verdict.py`。
