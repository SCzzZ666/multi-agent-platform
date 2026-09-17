"""九层权限交集 PDP（确定性、失败关闭）→ ALLOW / DENY / APPROVAL_REQUIRED。

主链（09 §9.1）：主体-项目关系 → 单调权限交集（每层只能收窄）→ 决策。
任一非成员/任一交集层缺失/交集为空/候选未被子集覆盖 均 DENY；
HIGH/CRITICAL 风险或缺有效审批 → APPROVAL_REQUIRED。Approval 不提权。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ai_native.modules.capability_gateway.domain.scopes import ResourceScope, covers, intersect


class Effect(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"


@dataclass(frozen=True)
class AuthorizationDecision:
    effect: Effect
    reason_codes: tuple[str, ...] = ()
    required_approval_kind: str | None = None

    def to_dict(self) -> dict:
        d = {"effect": self.effect.value, "reason_codes": list(self.reason_codes)}
        if self.required_approval_kind:
            d["required_approval_kind"] = self.required_approval_kind
        return d


_LAYER_NAMES = (
    "PROJECT_POLICY", "ROLE_CEILING", "NODE_DECLARATION", "RUN_PLAN",
    "SKILL_CEILING", "TOOL_SCHEMA_SNAPSHOT", "RUNTIME_POLICY",
)


def decide(
    *,
    member: bool,
    project_scopes: list[ResourceScope],
    role_scopes: list[ResourceScope],
    node_scopes: list[ResourceScope],
    plan_scopes: list[ResourceScope],
    tool_scopes: list[ResourceScope],
    runtime_scopes: list[ResourceScope],
    skill_scopes: list[ResourceScope] | None = None,
    candidate_scopes: list[ResourceScope],
    risk_level: str,
    has_valid_approval: bool = False,
) -> AuthorizationDecision:
    if not member:
        return AuthorizationDecision(Effect.DENY, ("SUBJECT_NOT_MEMBER",))
    layers = [project_scopes, role_scopes, node_scopes, plan_scopes, skill_scopes or [], tool_scopes, runtime_scopes]
    missing = [_LAYER_NAMES[i] for i, s in enumerate(layers) if not s]
    if missing:
        return AuthorizationDecision(Effect.DENY, tuple(n + "_MISSING" for n in missing))

    # 单调交集：任一不可比即失败关闭
    inter = list(layers[0])
    for scopes in layers[1:]:
        narrowed = []
        for s in scopes:
            for i in inter:
                r = intersect(s, i)
                if r is not None:
                    narrowed.append(r)
        inter = narrowed
        if not inter:
            return AuthorizationDecision(Effect.DENY, ("INTERSECTION_EMPTY",))

    for c in candidate_scopes:
        if not any(covers(i, c) for i in inter):
            return AuthorizationDecision(Effect.DENY, ("SCOPE_NOT_GRANTED",))

    if risk_level in ("HIGH", "CRITICAL") and not has_valid_approval:
        return AuthorizationDecision(Effect.APPROVAL_REQUIRED, ("APPROVAL_REQUIRED",), required_approval_kind="CAPABILITY")
    return AuthorizationDecision(Effect.ALLOW, ())