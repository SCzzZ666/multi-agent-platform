"""Run/NodeAttempt 状态机 domain 不变量测试：枚举基数、终态、合法/非法迁移、terminal_reason 匹配。"""
from __future__ import annotations

import pytest

from ai_native.modules.workflow_runtime.domain.states import (
    REASON_TO_TERMINAL,
    TERMINAL_RUN_STATES,
    NodeAttemptState,
    RunState,
    RunTerminalReason,
)
from ai_native.modules.workflow_runtime.domain.transitions import (
    NODE_ATTEMPT_TRANSITIONS,
    RUN_TRANSITIONS,
    InvalidStateTransition,
    assert_node_attempt_transition,
    assert_run_transition,
    is_terminal_run,
)


def test_run_state_enum_has_exactly_11_states() -> None:
    assert len(RunState) == 11
    assert TERMINAL_RUN_STATES == frozenset({RunState.CANCELLED, RunState.FAILED, RunState.SUCCEEDED})


def test_node_attempt_state_enum_has_exactly_8_states() -> None:
    assert len(NodeAttemptState) == 8


def test_run_transition_table_total() -> None:
    # 每个 RunState 都有转移表条目（终态映射到空集），不允许漏状态。
    assert set(RUN_TRANSITIONS) == set(RunState)


def test_node_attempt_transition_table_total() -> None:
    assert set(NODE_ATTEMPT_TRANSITIONS) == set(NodeAttemptState)


@pytest.mark.parametrize(
    "current,target",
    [
        (RunState.QUEUED, RunState.RUNNING),
        (RunState.RUNNING, RunState.WAITING_INPUT),
        (RunState.RUNNING, RunState.WAITING_APPROVAL),
        (RunState.RUNNING, RunState.PAUSING),
        (RunState.RUNNING, RunState.CANCELLING),
        (RunState.RUNNING, RunState.RECOVERY_REQUIRED),
        (RunState.RUNNING, RunState.SUCCEEDED),
        (RunState.RUNNING, RunState.FAILED),
        (RunState.WAITING_INPUT, RunState.RUNNING),
        (RunState.WAITING_INPUT, RunState.CANCELLED),
        (RunState.WAITING_APPROVAL, RunState.RUNNING),
        (RunState.WAITING_APPROVAL, RunState.CANCELLED),
        (RunState.PAUSING, RunState.PAUSED),
        (RunState.PAUSED, RunState.RUNNING),
        (RunState.CANCELLING, RunState.CANCELLED),
    ],
)
def test_legal_run_transitions_do_not_raise(current: RunState, target: RunState) -> None:
    assert_run_transition(current, target)  # 不抛即通过


@pytest.mark.parametrize(
    "current,target",
    [
        (RunState.SUCCEEDED, RunState.RUNNING),  # 终态不可再转
        (RunState.FAILED, RunState.RUNNING),
        (RunState.CANCELLED, RunState.RUNNING),
        (RunState.SUCCEEDED, RunState.FAILED),  # 终态↔终态
        (RunState.QUEUED, RunState.SUCCEEDED),  # 不可跳
        (RunState.RUNNING, RunState.QUEUED),  # 不可回退
        (RunState.CANCELLING, RunState.SUCCEEDED),
    ],
)
def test_illegal_run_transitions_raise(current: RunState, target: RunState) -> None:
    with pytest.raises(InvalidStateTransition):
        assert_run_transition(current, target)


def test_terminal_reason_maps_to_matching_terminal_state() -> None:
    assert REASON_TO_TERMINAL[RunTerminalReason.PLAN_REJECTED] == RunState.CANCELLED
    assert REASON_TO_TERMINAL[RunTerminalReason.RECOVERY_ABORTED] == RunState.FAILED
    assert REASON_TO_TERMINAL[RunTerminalReason.SYSTEM_FAILURE] == RunState.FAILED
    assert REASON_TO_TERMINAL[RunTerminalReason.COMPLETED_SUCCESSFULLY] == RunState.SUCCEEDED
    # 每个 reason 都必须落在一个终态上
    assert set(REASON_TO_TERMINAL.values()) <= set(TERMINAL_RUN_STATES)


def test_is_terminal_run() -> None:
    assert is_terminal_run(RunState.CANCELLED) is True
    assert is_terminal_run(RunState.RUNNING) is False
    assert is_terminal_run("SUCCEEDED") is True


def test_node_attempt_legal_transitions() -> None:
    assert_node_attempt_transition(NodeAttemptState.READY, NodeAttemptState.RUNNING)
    assert_node_attempt_transition(NodeAttemptState.READY, NodeAttemptState.SKIPPED)
    assert_node_attempt_transition(NodeAttemptState.RUNNING, NodeAttemptState.UNKNOWN)
    assert_node_attempt_transition(NodeAttemptState.RUNNING, NodeAttemptState.WAITING_APPROVAL)
    assert_node_attempt_transition(NodeAttemptState.WAITING_APPROVAL, NodeAttemptState.SUCCEEDED)


def test_node_attempt_terminal_and_unknown_do_not_transition() -> None:
    with pytest.raises(InvalidStateTransition):
        assert_node_attempt_transition(NodeAttemptState.SUCCEEDED, NodeAttemptState.RUNNING)
    with pytest.raises(InvalidStateTransition):
        # UNKNOWN 不倒退（对账只追加确定结论，不覆盖原状态）
        assert_node_attempt_transition(NodeAttemptState.UNKNOWN, NodeAttemptState.FAILED)


def test_transition_accepts_str() -> None:
    assert_run_transition("QUEUED", "RUNNING")
    assert is_terminal_run("SUCCEEDED") is True


def test_unknown_state_value_raises() -> None:
    with pytest.raises(ValueError):
        assert_run_transition("NOT_A_STATE", "RUNNING")