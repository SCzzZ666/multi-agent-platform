"""计划路由 Condition 映射（确定性，模型不得自由路由）。

映射（05/12 基线）：VALID → EXECUTE；NEEDS_INPUT → HOLD_FOR_USER；INVALID → REJECT。
REJECT 语义：结束计划路径并形成 CANCELLED + PLAN_REJECTED，不新增其他 Run 终态。
"""
from __future__ import annotations

from .plans import PlanVerdict

EXECUTE = "EXECUTE"
HOLD_FOR_USER = "HOLD_FOR_USER"
REJECT = "REJECT"

_ROUTE = {
    PlanVerdict.VALID: EXECUTE,
    PlanVerdict.NEEDS_INPUT: HOLD_FOR_USER,
    PlanVerdict.INVALID: REJECT,
}


def plan_route(verdict: PlanVerdict) -> str:
    return _ROUTE[verdict]