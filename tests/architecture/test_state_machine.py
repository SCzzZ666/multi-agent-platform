"""Run / NodeAttempt 状态机转换规则 + 终态原因（06 基线 §14）。"""
from __future__ import annotations

from ai_native.modules.workflow_runtime.domain.state_machine import (
    RunState,
    TerminalReason,
    can_transition,
    is_terminal,
    terminal_state_for,
)


def test_queued_to_running() -> None:
    assert can_transition(RunState.QUEUED, RunState.RUNNING)


def test_running_to_succeeded_and_failed() -> None:
    assert can_transition(RunState.RUNNING, RunState.SUCCEEDED)
    assert can_transition(RunState.RUNNING, RunState.FAILED)
    assert can_transition(RunState.RUNNING, RunState.RECOVERY_REQUIRED)


def test_terminal_states_have_no_outgoing() -> None:
    for s in (RunState.CANCELLED, RunState.FAILED, RunState.SUCCEEDED):
        assert not can_transition(s, RunState.RUNNING)
        assert is_terminal(s)


def test_terminal_reason_mapping() -> None:
    assert terminal_state_for(TerminalReason.COMPLETED_SUCCESSFULLY) == RunState.SUCCEEDED
    assert terminal_state_for(TerminalReason.PLAN_REJECTED) == RunState.CANCELLED
    assert terminal_state_for(TerminalReason.APPROVAL_REJECTED) == RunState.CANCELLED
    assert terminal_state_for(TerminalReason.SYSTEM_FAILURE) == RunState.FAILED


def test_running_to_waiting_approval() -> None:
    assert can_transition(RunState.RUNNING, RunState.WAITING_APPROVAL)


def test_non_terminal() -> None:
    assert not is_terminal(RunState.QUEUED)
    assert not is_terminal(RunState.RUNNING)


def test_waiting_approval_transitions() -> None:
    # 审批通过 → RUNNING(重新校验);拒绝 → CANCELLED;不得直接跳 SUCCEEDED(06 §14.5)
    assert can_transition(RunState.WAITING_APPROVAL, RunState.RUNNING)
    assert can_transition(RunState.WAITING_APPROVAL, RunState.CANCELLED)
    assert not can_transition(RunState.WAITING_APPROVAL, RunState.SUCCEEDED)