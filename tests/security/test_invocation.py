"""InvocationIntent 状态机 + 幂等分类（09 §9.6）。"""
from __future__ import annotations

from ai_native.modules.capability_gateway.domain.invocation import (
    IdempotencyClass,
    InvocationStatus,
    can_transition,
    is_terminal,
    may_auto_retry,
)


def test_recorded_to_dispatching_or_not() -> None:
    assert can_transition(InvocationStatus.INTENT_RECORDED, InvocationStatus.DISPATCHING)
    assert can_transition(InvocationStatus.INTENT_RECORDED, InvocationStatus.NOT_DISPATCHED)


def test_dispatching_to_terminal_or_unknown() -> None:
    assert can_transition(InvocationStatus.DISPATCHING, InvocationStatus.SUCCEEDED)
    assert can_transition(InvocationStatus.DISPATCHING, InvocationStatus.FAILED)
    assert can_transition(InvocationStatus.DISPATCHING, InvocationStatus.UNKNOWN)


def test_unknown_only_to_determined() -> None:
    assert can_transition(InvocationStatus.UNKNOWN, InvocationStatus.SUCCEEDED)
    assert can_transition(InvocationStatus.UNKNOWN, InvocationStatus.FAILED)
    assert not can_transition(InvocationStatus.UNKNOWN, InvocationStatus.DISPATCHING)


def test_terminal_states() -> None:
    for s in (InvocationStatus.SUCCEEDED, InvocationStatus.FAILED, InvocationStatus.NOT_DISPATCHED):
        assert is_terminal(s)


def test_non_idempotent_unknown_cannot_auto_retry() -> None:
    assert not may_auto_retry(InvocationStatus.UNKNOWN, IdempotencyClass.NON_IDEMPOTENT)


def test_idempotent_unknown_can_auto_retry() -> None:
    assert may_auto_retry(InvocationStatus.UNKNOWN, IdempotencyClass.PROVIDER_IDEMPOTENT)
    assert may_auto_retry(InvocationStatus.UNKNOWN, IdempotencyClass.READ_ONLY)


def test_determined_status_no_retry() -> None:
    assert not may_auto_retry(InvocationStatus.SUCCEEDED, IdempotencyClass.PROVIDER_IDEMPOTENT)
    assert not may_auto_retry(InvocationStatus.FAILED, IdempotencyClass.NON_IDEMPOTENT)