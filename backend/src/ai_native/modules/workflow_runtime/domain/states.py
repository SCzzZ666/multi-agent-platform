"""Run 11 态 / NodeAttempt 8 态 / 终态与 terminal_reason（05 5.3 / 12 基线冻结不变式）。

- Run 终态仅 3 种，用 terminal_reason 区分原因（USER_CANCELLED/…→CANCELLED；
  SYSTEM_FAILURE/RECOVERY_ABORTED→FAILED；COMPLETED_SUCCESSFULLY→SUCCEEDED）。
- 本模块是 domain 层：禁止 import FastAPI/Pydantic DTO/SQLAlchemy/psycopg/MAF/供应商 SDK（10 基线 6.2）。
"""
from __future__ import annotations

from enum import StrEnum


class RunState(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_INPUT = "WAITING_INPUT"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    PAUSING = "PAUSING"
    PAUSED = "PAUSED"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    FAILED = "FAILED"
    SUCCEEDED = "SUCCEEDED"


class NodeAttemptState(StrEnum):
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"
    UNKNOWN = "UNKNOWN"


# Run 终态仅 3 个（05 5.3：终态仅 CANCELLED/FAILED/SUCCEEDED）
TERMINAL_RUN_STATES = frozenset({RunState.CANCELLED, RunState.FAILED, RunState.SUCCEEDED})


class RunTerminalReason(StrEnum):
    # → CANCELLED
    USER_CANCELLED = "USER_CANCELLED"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"
    USER_ENDED_INPUT_WAIT = "USER_ENDED_INPUT_WAIT"
    PLAN_REJECTED = "PLAN_REJECTED"
    # → FAILED
    SYSTEM_FAILURE = "SYSTEM_FAILURE"
    RECOVERY_ABORTED = "RECOVERY_ABORTED"
    # → SUCCEEDED
    COMPLETED_SUCCESSFULLY = "COMPLETED_SUCCESSFULLY"


# terminal_reason 必须与最终 Run 终态一致；不一致的 (reason, state) 不得写盘。
REASON_TO_TERMINAL: dict[RunTerminalReason, RunState] = {
    RunTerminalReason.USER_CANCELLED: RunState.CANCELLED,
    RunTerminalReason.APPROVAL_REJECTED: RunState.CANCELLED,
    RunTerminalReason.USER_ENDED_INPUT_WAIT: RunState.CANCELLED,
    RunTerminalReason.PLAN_REJECTED: RunState.CANCELLED,
    RunTerminalReason.SYSTEM_FAILURE: RunState.FAILED,
    RunTerminalReason.RECOVERY_ABORTED: RunState.FAILED,
    RunTerminalReason.COMPLETED_SUCCESSFULLY: RunState.SUCCEEDED,
}