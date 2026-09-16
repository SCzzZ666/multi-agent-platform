# design-contracts（只读）

本目录文件为 `document_modified/` 冻结基线的**只读拷贝**，供 `tools/contract_codegen` 消费。
唯一事实源仍在 `document_modified/` 下。

规则（CODEBASE-BL D10-14）：

- 禁止手改本目录任何合同文件正文；
- 若源合同更新，须重新拷贝并记录源摘要、生成器版本与时间；
- CI 必须校验「生成物 ↔ 源摘要」一致，漂移即失败，不自动覆盖；
- 生成物不能反向成为业务事实源。

## 目录布局说明（与来源目录镜像）

本目录按源工作区的目录结构镜像放置：

```text
design-contracts/
├── 07_API接口/
│   ├── openapi.yaml
│   ├── problem-details.schema.json
│   ├── event-envelope.schema.json
│   └── error-catalog.json
├── 08_WorkflowDefinition/
│   └── workflow-definition.schema.json
└── 09_权限审批和本地执行安全/
    ├── resource-scope.schema.json
    ├── capability-dispatch-security.schema.json
    ├── local-execution-patch-security.schema.json
    └── security-diagnostic-catalog.json
```

原因：`openapi.yaml` 内部的 `$ref` 使用**相对文件路径**
（`./problem-details.schema.json`、`../08_WorkflowDefinition/workflow-definition.schema.json`）。
若按扁平布局拷贝，这些相对引用会断裂（`../08_WorkflowDefinition` 不复存在）。
镜像源目录结构可让引用在原位闭合，且不改变任何合同正文。