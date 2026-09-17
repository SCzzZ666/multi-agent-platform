"""ActionBinding（不可变）+ 三个摘要（09 基线 9.4：RFC8785 JCS → SHA-256）。

摘要顺序：Tool Schema 类型检查/默认值/拒未知字段 → scope 规范化 → JCS → SHA-256。
args_digest、resource_scope_digest 分别算；action_digest 由两者 + tool_schema_digest +
风险 + 排序后 credential_refs + 身份 组合得出。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ai_native.shared_kernel.jcs import jcs_sha256


@dataclass(frozen=True)
class ActionBinding:
    action_id: str
    project_id: str
    run_id: str | None
    workflow_version_id: str | None
    run_plan_version_id: str | None
    node_attempt_id: str | None
    tool_key: str
    capability_key: str
    tool_schema_digest: str
    normalized_args: dict
    resource_scopes: dict
    risk: str
    credential_refs: tuple[str, ...] = ()
    args_digest: str = ""
    resource_scope_digest: str = ""
    action_digest: str = ""

    @classmethod
    def build(
        cls,
        *,
        action_id: str,
        project_id: str,
        tool_key: str,
        capability_key: str,
        tool_schema_digest: str,
        normalized_args: dict,
        resource_scopes: dict,
        risk: str,
        credential_refs: tuple[str, ...] = (),
        run_id: str | None = None,
        workflow_version_id: str | None = None,
        run_plan_version_id: str | None = None,
        node_attempt_id: str | None = None,
    ) -> "ActionBinding":
        args_digest = jcs_sha256(normalized_args)
        scope_digest = jcs_sha256(resource_scopes)
        action_digest = jcs_sha256(
            {
                "args_digest": args_digest,
                "resource_scope_digest": scope_digest,
                "tool_schema_digest": tool_schema_digest,
                "risk": risk,
                "credential_refs": sorted(credential_refs),
                "project_id": project_id,
                "tool_key": tool_key,
                "capability_key": capability_key,
            }
        )
        return cls(
            action_id=action_id, project_id=project_id, run_id=run_id,
            workflow_version_id=workflow_version_id, run_plan_version_id=run_plan_version_id,
            node_attempt_id=node_attempt_id, tool_key=tool_key, capability_key=capability_key,
            tool_schema_digest=tool_schema_digest, normalized_args=normalized_args,
            resource_scopes=resource_scopes, risk=risk, credential_refs=credential_refs,
            args_digest=args_digest, resource_scope_digest=scope_digest, action_digest=action_digest,
        )