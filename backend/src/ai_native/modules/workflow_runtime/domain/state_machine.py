"""Run / NodeAttempt 状态机（06 基线 §14 + 全景手册 5.3）。

只承载转换规则与终态原因，不 import 框架/ORM。终态仅 CANCELLED/FAILED/SUCCEEDED，用 terminal_reason 区分。
"""
from __future__ import annotations

from enum import Enum


class RunState(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    PAUSING = "PAUSING"
    PAUSED = "PAUSED"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    FAILED = "FAILED"
    SUCCEEDED = "SUCCEEDED"


class NodeAttemptState(str, Enum):
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"
    UNKNOWN = "UNKNOWN"


TERMINAL_STATES: frozenset[RunState] = frozenset(
    {RunState.CANCELLED, RunState.FAILED, RunState.SUCCEEDED}
)


class TerminalReason(str, Enum):
    USER_CANCELLED = "USER_CANCELLED"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"
    USER_ENDED_INPUT_WAIT = "USER_ENDED_INPUT_WAIT"
    PLAN_REJECTED = "PLAN_REJECTED"  # → CANCELLED
    SYSTEM_FAILURE = "SYSTEM_FAILURE"
    RECOVERY_ABORTED = "RECOVERY_ABORTED"  # → FAILED
    COMPLETED_SUCCESSFULLY = "COMPLETED_SUCCESSFULLY"  # → SUCCEEDED


_REASON_TO_TERMINAL: dict[TerminalReason, RunState] = {
    TerminalReason.USER_CANCELLED: RunState.CANCELLED,
    TerminalReason.APPROVAL_REJECTED: RunState.CANCELLED,
    TerminalReason.USER_ENDED_INPUT_WAIT: RunState.CANCELLED,
    TerminalReason.PLAN_REJECTED: RunState.CANCELLED,
    TerminalReason.SYSTEM_FAILURE: RunState.FAILED,
    TerminalReason.RECOVERY_ABORTED: RunState.FAILED,
    TerminalReason.COMPLETED_SUCCESSFULLY: RunState.SUCCEEDED,
}

_ALLOWED: dict[RunState, frozenset[RunState]] = {
    RunState.QUEUED: frozenset({RunState.RUNNING, RunState.CANCELLED}),
    RunState.RUNNING: frozenset(
        {
            RunState.WAITING_APPROVAL,
            RunState.PAUSING,
            RunState.CANCELLING,
            RunState.RECOVERY_REQUIRED,
            RunState.FAILED,
            RunState.SUCCEEDED,
        }
    ),
    RunState.WAITING_APPROVAL: frozenset({RunState.RUNNING, RunState.CANCELLED}),
    RunState.PAUSING: frozenset({RunState.PAUSED}),
    RunState.PAUSED: frozenset({RunState.RUNNING, RunState.CANCELLED}),
    RunState.CANCELLING: frozenset({RunState.CANCELLED}),
    RunState.RECOVERY_REQUIRED: frozenset({RunState.RUNNING, RunState.CANCELLED, RunState.FAILED}),
    RunState.CANCELLED: frozenset(),
    RunState.FAILED: frozenset(),
    RunState.SUCCEEDED: frozenset(),
}


def can_transition(frm: RunState, to: RunState) -> bool:
    return to in _ALLOWED.get(frm, frozenset())


def terminal_state_for(reason: TerminalReason) -> RunState:
    return _REASON_TO_TERMINAL[reason]


def is_terminal(state: RunState) -> bool:
    return state in TERMINAL_STATES