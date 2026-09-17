"""Run / NodeAttempt 状态转移表（domain 纯逻辑，无 I/O、无框架）。

- Run 以 05 5.3 的 11 态 + 终态仅 3 种为权威；PAUSING→PAUSED、PAUSED→RUNNING、CANCELLING→CANCELLED
  为基线显式边；RECOVERY_REQUIRED→{RUNNING,CANCELLED,FAILED} 为恢复语义推断，块2 落地 PG Checkpoint
  时按真实恢复路径校准。
- NodeAttempt 8 态基线只给枚举、未显式给转移表；此处是保守语义约束（终态/UNKNOWN 不倒退），
  六类节点 MAF 事件投影落地（Day2 块2）时再收紧。
- 每次状态转换必须同时校验 current_state + state_version（乐观锁）+ fencing_token；后两者在
  application/adapter 落库时执行，本模块只判定「状态图是否允许」。
"""
from __future__ import annotations

from .states import TERMINAL_RUN_STATES, NodeAttemptState, RunState

# 合法 Run 迁移（键 = from，值 = 允许的 to）；终态映射到空集。
RUN_TRANSITIONS: dict[RunState, frozenset[RunState]] = {
    RunState.QUEUED: frozenset({RunState.RUNNING}),
    RunState.RUNNING: frozenset({
        RunState.WAITING_INPUT,
        RunState.WAITING_APPROVAL,
        RunState.PAUSING,
        RunState.CANCELLING,
        RunState.RECOVERY_REQUIRED,
        RunState.FAILED,
        RunState.SUCCEEDED,
    }),
    RunState.WAITING_INPUT: frozenset({RunState.RUNNING, RunState.CANCELLED}),
    RunState.WAITING_APPROVAL: frozenset({RunState.RUNNING, RunState.CANCELLED}),
    RunState.PAUSING: frozenset({RunState.PAUSED}),
    RunState.PAUSED: frozenset({RunState.RUNNING}),
    RunState.CANCELLING: frozenset({RunState.CANCELLED}),
    # 恢复语义：续跑 / 用户放弃 / 恢复失败（出边待块2 校准）
    RunState.RECOVERY_REQUIRED: frozenset({RunState.RUNNING, RunState.CANCELLED, RunState.FAILED}),
    RunState.CANCELLED: frozenset(),
    RunState.FAILED: frozenset(),
    RunState.SUCCEEDED: frozenset(),
}

# NodeAttempt 保守迁移（8 态；SUCCEEDED/FAILED/CANCELLED/SKIPPED/UNKNOWN 不可再迁，状态不倒退）。
NODE_ATTEMPT_TRANSITIONS: dict[NodeAttemptState, frozenset[NodeAttemptState]] = {
    NodeAttemptState.READY: frozenset(
        {NodeAttemptState.RUNNING, NodeAttemptState.CANCELLED, NodeAttemptState.SKIPPED}
    ),
    NodeAttemptState.RUNNING: frozenset({
        NodeAttemptState.WAITING_APPROVAL,
        NodeAttemptState.SUCCEEDED,
        NodeAttemptState.FAILED,
        NodeAttemptState.CANCELLED,
        NodeAttemptState.UNKNOWN,
    }),
    NodeAttemptState.WAITING_APPROVAL: frozenset(
        {
            NodeAttemptState.RUNNING,
            NodeAttemptState.SUCCEEDED,
            NodeAttemptState.FAILED,
            NodeAttemptState.CANCELLED,
        }
    ),
    NodeAttemptState.SUCCEEDED: frozenset(),
    NodeAttemptState.FAILED: frozenset(),
    NodeAttemptState.CANCELLED: frozenset(),
    NodeAttemptState.SKIPPED: frozenset(),
    NodeAttemptState.UNKNOWN: frozenset(),
}


class InvalidStateTransition(RuntimeError):
    """非法状态迁移（domain 不变式被破坏）。"""

    def __init__(self, kind: str, current: RunState | NodeAttemptState, target: RunState | NodeAttemptState) -> None:
        self.kind = kind
        self.current = current
        self.target = target
        super().__init__(f"{kind}: 非法迁移 {current.value} -> {target.value}")


def assert_run_transition(current: RunState | str, target: RunState | str) -> None:
    cur = RunState(current)
    tgt = RunState(target)
    if tgt not in RUN_TRANSITIONS[cur]:
        raise InvalidStateTransition("Run", cur, tgt)


def assert_node_attempt_transition(current: NodeAttemptState | str, target: NodeAttemptState | str) -> None:
    cur = NodeAttemptState(current)
    tgt = NodeAttemptState(target)
    if tgt not in NODE_ATTEMPT_TRANSITIONS[cur]:
        raise InvalidStateTransition("NodeAttempt", cur, tgt)


def is_terminal_run(state: RunState | str) -> bool:
    return RunState(state) in TERMINAL_RUN_STATES