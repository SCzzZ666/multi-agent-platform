"""workflow_runtime 领域不变式：Run/NodeAttempt 状态机（不依赖框架）。"""
from .states import (
    REASON_TO_TERMINAL,
    TERMINAL_RUN_STATES,
    NodeAttemptState,
    RunState,
    RunTerminalReason,
)
from .transitions import (
    NODE_ATTEMPT_TRANSITIONS,
    RUN_TRANSITIONS,
    InvalidStateTransition,
    assert_node_attempt_transition,
    assert_run_transition,
    is_terminal_run,
)

__all__ = [
    "REASON_TO_TERMINAL",
    "TERMINAL_RUN_STATES",
    "NodeAttemptState",
    "RunState",
    "RunTerminalReason",
    "NODE_ATTEMPT_TRANSITIONS",
    "RUN_TRANSITIONS",
    "InvalidStateTransition",
    "assert_node_attempt_transition",
    "assert_run_transition",
    "is_terminal_run",
]