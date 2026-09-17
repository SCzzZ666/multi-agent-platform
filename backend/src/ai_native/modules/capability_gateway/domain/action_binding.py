"""ActionBinding 不可变 + 三个摘要（09 §9.4）。

args_digest、resource_scope_digest 分别算；action_digest 由两者及身份/risk/排序后 credential refs 组合
（排除自身与易变字段）。授权一律用服务端重算摘要比对，不信客户端摘要。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ai_native.shared_kernel.jcs import jcs_digest


@dataclass(frozen=True)
class ActionBinding:
    project_id: str
    action_id: str
    tool_key: str
    capability_key: str
    tool_schema_digest: str
    normalized_args: dict
    resource_scopes: dict
    risk: str
    credential_refs: tuple = ()
    run_id: str | None = None
    workflow_version_id: str | None = None
    run_plan_version_id: str | None = None
    node_attempt_id: str | None = None
    args_digest: str = ""
    resource_scope_digest: str = ""
    action_digest: str = ""

    def compute_digests(self) -> "ActionBinding":
        args_digest = jcs_digest(self.normalized_args)
        scope_digest = jcs_digest(self.resource_scopes)
        action_digest = jcs_digest(
            {
                "args_digest": args_digest,
                "scope_digest": scope_digest,
                "identity": {
                    "project_id": self.project_id,
                    "run_id": self.run_id,
                    "workflow_version_id": self.workflow_version_id,
                    "run_plan_version_id": self.run_plan_version_id,
                    "node_attempt_id": self.node_attempt_id,
                },
                "capacity": [self.tool_key, self.capability_key, self.tool_schema_digest],
                "risk": self.risk,
                "credential_refs": sorted(self.credential_refs),
            }
        )
        return ActionBinding(
            **{**self.__dict__, "args_digest": args_digest, "resource_scope_digest": scope_digest, "action_digest": action_digest}
        )

    def verify_digests(self) -> bool:
        """服务端重算比对：三个摘要都一致才算同一动作；任一字段变 → 新 Binding + 新审批。"""
        recomputed = self.compute_digests()
        return (
            recomputed.args_digest == self.args_digest
            and recomputed.resource_scope_digest == self.resource_scope_digest
            and recomputed.action_digest == self.action_digest
        )