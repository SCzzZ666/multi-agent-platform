"""Worker 侧用例：领 Run（租约/fencing）→ 投影节点与事件 → 终态（不写 DAG 推进）。

Edge 路由/条件/并行/汇合/HITL 归 MAF；本模块只做命令领取、租约、宿主、恢复协调与事实投影。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_native.modules.operations_events.application.service import append_audit, emit_event
from ai_native.modules.workflow_runtime.adapters.orm import NodeAttempt, Run, RunLease
from ai_native.modules.workflow_runtime.domain.state_machine import (
    NodeAttemptState,
    RunState,
    TerminalReason,
    can_transition,
)
from ai_native.shared_kernel.digest import sha256_hex
from ai_native.shared_kernel.ids import uuid7


def _emit(db: Session, run: Run, event_type: str, payload: dict):
    seq = int(run.event_seq or 0) + 1
    run.event_seq = seq
    return emit_event(
        db, run_id=run.id, project_id=run.project_id, event_seq=seq,
        state_version=run.state_version or 0, event_type=event_type,
        payload=payload, aggregate_id=run.id,
    )


def claim_next_run(db: Session, *, worker_id: str = "worker-1", lease_seconds: int = 60) -> Run | None:
    """SKIP LOCKED 领一个 QUEUED Run，建租约加 fencing，转 RUNNING。"""
    run = db.scalar(
        select(Run)
        .where(Run.state == RunState.QUEUED.value)
        .order_by(Run.queued_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if run is None:
        return None
    now = datetime.now(timezone.utc)
    if not can_transition(RunState.QUEUED, RunState.RUNNING):
        raise RuntimeError("QUEUED→RUNNING 非法转换")
    db.add(
        RunLease(
            run_id=run.id, lease_owner=worker_id, fencing_token=1,
            heartbeat_at=now, expires_at=now + timedelta(seconds=lease_seconds), row_version=1,
        )
    )
    run.state = RunState.RUNNING.value
    run.started_at = now
    run.state_version = (run.state_version or 0) + 1
    _emit(db, run, "RUN_STARTED", {"worker_id": worker_id})
    append_audit(
        db, project_id=run.project_id, event_type="RUN_CLAIMED",
        actor={"kind": "worker", "worker_id": worker_id},
        subject={"run_id": str(run.id)}, payload={"state": run.state},
    )
    db.flush()
    return run


def project_node(db: Session, run: Run, node: dict) -> None:
    """投影一个已执行成功的节点 → NodeAttempt(SUCCEEDED) + 事件。"""
    receipt = (
        "sha256:"
        + sha256_hex(f"{run.id}:{node['node_key']}:{node['role_ref']}".encode("utf-8"))
    )
    db.add(
        NodeAttempt(
            id=uuid7(), project_id=run.project_id, run_id=run.id,
            node_key=node["node_key"], task_id=node["node_key"], role_ref=node["role_ref"],
            attempt_no=1, rework_round=0, state=NodeAttemptState.SUCCEEDED.value,
            fencing_token=1, state_version=0, completion_receipt=receipt,
            ended_at=datetime.now(timezone.utc),
        )
    )
    _emit(db, run, "NODE_SUCCEEDED", {"node_key": node["node_key"], "role_ref": node["role_ref"]})


def complete_run(db: Session, run: Run) -> None:
    if not can_transition(RunState(run.state), RunState.SUCCEEDED):
        raise RuntimeError(f"{run.state}→SUCCEEDED 非法转换")
    run.state = RunState.SUCCEEDED.value
    run.ended_at = datetime.now(timezone.utc)
    run.state_version = (run.state_version or 0) + 1
    _emit(db, run, "RUN_COMPLETED", {"terminal_reason": TerminalReason.COMPLETED_SUCCESSFULLY.value})
    append_audit(
        db, project_id=run.project_id, event_type="RUN_SUCCEEDED",
        actor={"kind": "system"}, subject={"run_id": str(run.id)},
        payload={"state": RunState.SUCCEEDED.value},
    )


def fail_run(db: Session, run: Run, error: str) -> None:
    run.state = RunState.FAILED.value
    run.ended_at = datetime.now(timezone.utc)
    run.state_version = (run.state_version or 0) + 1
    _emit(db, run, "RUN_FAILED", {"terminal_reason": TerminalReason.SYSTEM_FAILURE.value, "error": error})
    append_audit(
        db, project_id=run.project_id, event_type="RUN_FAILED",
        actor={"kind": "system"}, subject={"run_id": str(run.id)},
        payload={"state": RunState.FAILED.value, "error": error},
    )