"""workflow_runtime 应用用例：建 Run（快照+命令+事件+outbox+审计同事务）→ 状态投影。

事件/outbox/审计统一走 operations_events 模块（单一事件事实源）。
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ai_native.modules.operations_events.application.service import append_audit, emit_event
from ai_native.modules.workflow_definition.adapters.orm import WorkflowVersion
from ai_native.modules.workflow_runtime.adapters.orm import Run, RunSnapshot
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
    # 事件（run_event + event_outbox 同事务）+ 审计
    seq = int(run.event_seq or 0) + 1
    run.event_seq = seq
    emit_event(
        db, run_id=run.id, project_id=run.project_id, event_seq=seq,
        state_version=run.state_version or 0, event_type="RUN_CREATED",
        payload={"workflow_version_id": str(workflow_version_id)}, aggregate_id=run.id,
    )
    append_audit(
        db, project_id=project_id, event_type="RUN_STARTED", actor={"kind": "system"},
        subject={"run_id": str(run.id), "workflow_version_id": str(workflow_version_id)},
        payload={"state": "QUEUED"},
    )
    return run


def get_run(db: Session, run_id) -> Run | None:
    return db.get(Run, run_id)