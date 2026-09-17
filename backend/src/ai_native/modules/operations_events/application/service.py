"""operations_events 应用用例：RunEvent + outbox 同事务至少一次发布、SSE 游标、审计摘要链。"""
from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ai_native.modules.operations_events.adapters.orm import AuditEvent, EventOutbox, RunEvent
from ai_native.shared_kernel.digest import sha256_hex
from ai_native.shared_kernel.ids import uuid7


def _digest(obj) -> str:
    return "sha256:" + sha256_hex(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8"))


def emit_event(
    db: Session,
    *,
    run_id,
    project_id,
    event_seq: int,
    state_version: int,
    event_type: str,
    payload: dict,
    aggregate_id=None,
) -> RunEvent:
    """写 RunEvent + event_outbox（同事务，至少一次发布）。与业务事实同事务提交。"""
    ev = RunEvent(
        id=uuid7(), project_id=project_id, run_id=run_id, event_seq=event_seq,
        event_type=event_type, state_version=state_version, actor={},
        correlation_id=str(uuid7()), payload=payload, payload_digest=_digest(payload),
    )
    db.add(ev)
    db.flush()
    outbox = EventOutbox(
        id=uuid7(), project_id=project_id, aggregate_type="run",
        aggregate_id=aggregate_id or run_id, event_id=ev.id,
    )
    db.add(outbox)
    return ev


def list_events(db: Session, run_id, after_seq: int = 0) -> list[RunEvent]:
    return list(
        db.scalars(
            select(RunEvent)
            .where(RunEvent.run_id == run_id, RunEvent.event_seq > after_seq)
            .order_by(RunEvent.event_seq)
        )
    )


def append_audit(db: Session, *, project_id, event_type: str, actor: dict, subject: dict, payload: dict, trace_id: str | None = None) -> AuditEvent:
    """审计追加写，按 project 建序号 + 摘要链（只追加、不覆盖）。"""
    prev = db.scalar(
        select(AuditEvent.event_digest)
        .where(AuditEvent.project_id == project_id)
        .order_by(AuditEvent.audit_seq.desc())
        .limit(1)
    )
    seq = (db.scalar(select(func.coalesce(func.max(AuditEvent.audit_seq), 0)).where(AuditEvent.project_id == project_id)) or 0) + 1
    material = json.dumps(
        {"event_type": event_type, "actor": actor, "subject": subject, "payload": payload, "previous": prev},
        sort_keys=True, ensure_ascii=False,
    )
    ev = AuditEvent(
        id=uuid7(), project_id=project_id, audit_seq=seq, event_type=event_type,
        actor=actor, subject=subject, previous_digest=prev,
        event_digest="sha256:" + sha256_hex(material.encode("utf-8")),
        payload_digest=_digest(payload), trace_id=trace_id or str(uuid7()),
    )
    db.add(ev)
    return ev