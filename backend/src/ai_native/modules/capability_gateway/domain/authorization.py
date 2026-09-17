"""九层权限交集（09 §9.2，PDP 确定性策略，失败关闭）。

任一交集层缺失/失效/漂移/不可比 → DENY；Approval 不参与并集扩权，只把
「已通过 8 层、但策略要求审批」的 APPROVAL_REQUIRED 抬到 ALLOW，永远不能让 DENY 变 ALLOW。
"""
from __future__ import annotations

from enum import Enum

# 8 个基础交集层（不含运行期 Approval，后者由策略决定是否需要）
BASE_LAYERS = (
    "subject_project_membership",   # 主体—项目关系
    "project_policy_and_workspace",  # Project 当前策略 ∩ WorkspaceGrant
    "role_capability_ceiling",       # RoleCatalog 角色上限
    "workflow_node_declaration",     # WorkflowVersion 节点声明
    "active_plan_declaration",       # 活动 RunPlanVersion 任务声明
    "skill_version_cap",             # SkillVersion 上限（用时）
    "tool_schema_snapshot",          # Tool Schema Snapshot 与当前暴露状态
    "runtime_security_egress",       # 当前运行时安全与数据外发策略
)


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"


def decide(
    layers: dict[str, bool],
    *,
    approval_required: bool = False,
    valid_approval: bool = False,
) -> Decision:
    """失败关闭的单调权限交集。layers 缺键视为 False（宁可拒绝）。"""
    for name in BASE_LAYERS:
        if not layers.get(name, False):
            return Decision.DENY
    if approval_required and not valid_approval:
        return Decision.APPROVAL_REQUIRED
    return Decision.ALLOW