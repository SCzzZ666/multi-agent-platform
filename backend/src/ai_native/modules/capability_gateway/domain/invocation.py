"""InvocationIntent 状态机 + 幂等分类（09 §9.6）。

状态只允许未知→确定，不倒退；NON_IDEMPOTENT 的 UNKNOWN 禁自动重发。
"""
from __future__ import annotations

from enum import Enum


class InvocationStatus(str, Enum):
    INTENT_RECORDED = "INTENT_RECORDED"
    DISPATCHING = "DISPATCHING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    NOT_DISPATCHED = "NOT_DISPATCHED"


class IdempotencyClass(str, Enum):
    READ_ONLY = "READ_ONLY"
    PLATFORM_IDEMPOTENT = "PLATFORM_IDEMPOTENT"
    PROVIDER_IDEMPOTENT = "PROVIDER_IDEMPOTENT"
    NON_IDEMPOTENT = "NON_IDEMPOTENT"


_ALLOWED: dict[InvocationStatus, frozenset[InvocationStatus]] = {
    InvocationStatus.INTENT_RECORDED: frozenset({InvocationStatus.DISPATCHING, InvocationStatus.NOT_DISPATCHED}),
    InvocationStatus.DISPATCHING: frozenset({InvocationStatus.SUCCEEDED, InvocationStatus.FAILED, InvocationStatus.UNKNOWN}),
    InvocationStatus.UNKNOWN: frozenset({InvocationStatus.SUCCEEDED, InvocationStatus.FAILED}),  # 对账：未知→确定
    InvocationStatus.SUCCEEDED: frozenset(),
    InvocationStatus.FAILED: frozenset(),
    InvocationStatus.NOT_DISPATCHED: frozenset(),
}


def can_transition(frm: InvocationStatus, to: InvocationStatus) -> bool:
    return to in _ALLOWED.get(frm, frozenset())


def is_terminal(status: InvocationStatus) -> bool:
    return status in (InvocationStatus.SUCCEEDED, InvocationStatus.FAILED, InvocationStatus.NOT_DISPATCHED)


def may_auto_retry(status: InvocationStatus, idempotency: IdempotencyClass) -> bool:
    """UNKNOWN 只对幂等/只读类允许自动重发；NON_IDEMPOTENT 的 UNKNOWN 禁自动重发、转对账。"""
    if status != InvocationStatus.UNKNOWN:
        return False
    return idempotency in (IdempotencyClass.READ_ONLY, IdempotencyClass.PLATFORM_IDEMPOTENT, IdempotencyClass.PROVIDER_IDEMPOTENT)