"""九层权限交集（失败关闭的单调交集）—— 09 基线 9.2。

每层只能收窄：任一缺失/失效/漂移/不可比即 DENY；Approval 不提权，只能对已在交集内的
确定动作加人工确认（APPROVAL_REQUIRED ≠ ALLOW）。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

LAYER_NAMES: tuple[str, ...] = (
    "subject_project",          # 主体—项目关系
    "project_policy_workspace",  # Project 策略 + WorkspaceGrant
    "role_ceiling",             # RoleCatalog 角色上限
    "workflow_node_declaration",  # WorkflowVersion 节点声明
    "runplan_task",             # 活动 RunPlanVersion 任务声明
    "skill_version",            # SkillVersion 上限
    "tool_schema_snapshot",     # Tool Schema Snapshot 与当前暴露状态
    "runtime_egress_policy",    # 运行时安全与数据外发策略
    "effective_approval",       # 有效 Approval（策略要求时）
)


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"


@dataclass(frozen=True)
class LayerResult:
    layer: str
    decision: str  # ALLOW / DENY / APPROVAL_REQUIRED
    reason: str = ""


@dataclass(frozen=True)
class PolicyDecision:
    decision: Decision
    diagnostics: tuple[str, ...] = ()


def evaluate(layers: dict[str, LayerResult]) -> PolicyDecision:
    """九层交集：缺失层级 → DENY（失败关闭）；任一层 DENY → DENY；
    存在 APPROVAL_REQUIRED → APPROVAL_REQUIRED；否则 ALLOW。"""
    missing = [n for n in LAYER_NAMES if n not in layers]
    if missing:
        return PolicyDecision(Decision.DENY, (f"缺失层级: {missing}",))
    for name in LAYER_NAMES:
        r = layers[name]
        if r.decision == Decision.DENY.value:
            return PolicyDecision(Decision.DENY, (f"{name}: {r.reason}",))
    if any(layers[n].decision == Decision.APPROVAL_REQUIRED.value for n in LAYER_NAMES):
        return PolicyDecision(Decision.APPROVAL_REQUIRED, ())
    return PolicyDecision(Decision.ALLOW, ())