"""ActionBinding 三摘要（09 §9.4）：args / resource_scope / action。

摘要顺序：按 Tool Schema 类型检查/规范化 → scope 规范化 → RFC8785 JCS → SHA-256。
action_digest 由身份/risk/credential_refs + args_digest + scope_digest 组合（排除自身）。
"""
from __future__ import annotations

from ai_native.modules.capability_gateway.domain.scopes import ResourceScope
from ai_native.shared_kernel.jcs import jcs_digest


def compute_binding_digests(
    *,
    project_id: str,
    run_id: str,
    workflow_version_id: str,
    run_plan_version_id: str,
    node_attempt_id: str,
    action_id: str,
    tool_key: str,
    capability_key: str,
    tool_schema_digest: str,
    normalized_args: dict,
    resource_scopes: list[ResourceScope],
    risk_level: str,
    credential_refs: list[str],
) -> dict[str, str]:
    args_digest = jcs_digest(normalized_args)
    resource_scope_digest = jcs_digest([s.to_dict() for s in resource_scopes])
    action_digest = jcs_digest(
        {
            "project_id": project_id,
            "run_id": run_id,
            "workflow_version_id": workflow_version_id,
            "run_plan_version_id": run_plan_version_id,
            "node_attempt_id": node_attempt_id,
            "action_id": action_id,
            "tool_key": tool_key,
            "capability_key": capability_key,
            "tool_schema_digest": tool_schema_digest,
            "args_digest": args_digest,
            "resource_scope_digest": resource_scope_digest,
            "risk_level": risk_level,
            "credential_refs": sorted(credential_refs),
        }
    )
    return {
        "args_digest": args_digest,
        "resource_scope_digest": resource_scope_digest,
        "action_digest": action_digest,
    }