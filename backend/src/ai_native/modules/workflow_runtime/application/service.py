"""workflow_runtime 应用用例：建 Run（快照+命令+事件同事务）→ 事件投影。"""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_native.modules.workflow_definition.adapters.orm import WorkflowVersion
from ai_native.modules.workflow_runtime.adapters.orm import Run, RunEvent, RunSnapshot
from ai_native.shared_kernel.digest import sha256_hex
from ai_native.shared_kernel.ids import uuid7


def _digest(obj) -> str:
    return "sha256:" + sha256_hex(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8"))


TERMINAL_STATES = {"CANCELLED", "FAILED", "SUCCEEDED"}


def start_run(db: Session, project_id, workflow_version_id, snapshot: dict | None = None) -> Run:
    version = db.get(WorkflowVersion, workflow_version_id)
    if version is None or str(version.project_id) != str(project_id):
        raise ValueError("workflow version not found in project")
    snap = snapshot or {}
    payloads = {
        "source": snap.get("source", {}),
        "model_config": snap.get("model_config", {}),
        "prompt": snap.get("prompt", {}),
        "capability": snap.get("capability", {}),
    }
    snap_row = RunSnapshot(
        id=uuid7(), project_id=project_id, workflow_version_id=workflow_version_id,
        source_snapshot=payloads["source"], model_config_snapshot=payloads["model_config"],
        prompt_snapshot=payloads["prompt"], capability_snapshot=payloads["capability"],
        content_digest=_digest(payloads),
    )
    db.add(snap_row)
    db.flush()
    run = Run(
        id=uuid7(), project_id=project_id, workflow_version_id=workflow_version_id,
        run_snapshot_id=snap_row.id, state="QUEUED", state_version=0, event_seq=0,
        priority=100, max_wall_seconds=3600,
    )
    db.add(run)
    db.flush()
    emit_event(db, run, "RUN_CREATED", {"workflow_version_id": str(workflow_version_id)})
    return run


def emit_event(db: Session, run: Run, event_type: str, payload: dict) -> RunEvent:
    seq = (run.event_seq or 0) + 1
    run.event_seq = seq
    ev = RunEvent(
        id=uuid7(), project_id=run.project_id, run_id=run.id, event_seq=seq,
        event_type=event_type, state_version=run.state_version or 0,
        actor={}, correlation_id=str(uuid7()), payload=payload, payload_digest=_digest(payload),
    )
    db.add(ev)
    return ev


def get_run(db: Session, run_id) -> Run | None:
    return db.get(Run, run_id)


def list_events(db: Session, run_id, after_seq: int = 0) -> list[RunEvent]:
    return list(
        db.scalars(
            select(RunEvent)
            .where(RunEvent.run_id == run_id, RunEvent.event_seq > after_seq)
            .order_by(RunEvent.event_seq)
        )
    )