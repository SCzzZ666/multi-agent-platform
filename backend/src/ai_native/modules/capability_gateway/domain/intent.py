"""Invocation 状态机（09 §9.6）：INTENT_RECORDED→DISPATCHING→SUCCEEDED|FAILED|UNKNOWN|NOT_DISPATCHED。

- 未形成有效 Intent 前不得解析凭据/建进程/调 Tool/开宿主写句柄/耗配额。
- UNKNOWN 只通过对账（receipt）走向确定，主 Intent 状态不倒退；
- NON_IDEMPOTENT + UNKNOWN 禁自动重发；READ_ONLY/IDEMPOTENT 按策略可重试。
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
    IDEMPOTENT = "IDEMPOTENT"
    NON_IDEMPOTENT = "NON_IDEMPOTENT"


TERMINAL_STATUSES: frozenset[InvocationStatus] = frozenset(
    {InvocationStatus.SUCCEEDED, InvocationStatus.FAILED, InvocationStatus.NOT_DISPATCHED}
)

_ALLOWED: dict[InvocationStatus, frozenset[InvocationStatus]] = {
    InvocationStatus.INTENT_RECORDED: frozenset({InvocationStatus.DISPATCHING, InvocationStatus.NOT_DISPATCHED}),
    InvocationStatus.DISPATCHING: frozenset({InvocationStatus.SUCCEEDED, InvocationStatus.FAILED, InvocationStatus.UNKNOWN}),
    InvocationStatus.SUCCEEDED: frozenset(),
    InvocationStatus.FAILED: frozenset(),
    InvocationStatus.NOT_DISPATCHED: frozenset(),
    InvocationStatus.UNKNOWN: frozenset(),  # 不倒退；对账经 receipt 走向确定
}


def can_transition(frm: InvocationStatus, to: InvocationStatus) -> bool:
    return to in _ALLOWED.get(frm, frozenset())


def is_terminal(status: InvocationStatus) -> bool:
    return status in TERMINAL_STATUSES


def can_auto_retry(idempotency: IdempotencyClass, status: InvocationStatus) -> bool:
    """是否允许自动重发。NON_IDEMPOTENT 的 UNKNOWN 禁自动重发（09 §9.6）。"""
    if is_terminal(status):
        return False
    if idempotency == IdempotencyClass.NON_IDEMPOTENT and status == InvocationStatus.UNKNOWN:
        return False
    return True