"""operations_events API：SSE 事件流（游标/重连去重）+ Operation 回执。"""
from __future__ import annotations

import json
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ai_native.bootstrap.db import SessionLocal, get_db, project_context
from ai_native.modules.operations_events.application import service
from ai_native.modules.workflow_runtime.adapters.orm import Run

router = APIRouter(tags=["operations-events"])


@router.get("/projects/{project_id}/runs/{run_id}/events")
def stream_events(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    after_sequence: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """SSE：单 Run、id=event_seq；`after_sequence` 作重连游标（去重）。"""
    project_context(db, project_id)
    run = db.get(Run, run_id)
    if run is None or str(run.project_id) != str(project_id):
        raise HTTPException(status_code=404, detail="run not found")

    def gen():
        after = after_sequence
        while True:
            s = SessionLocal()
            try:
                project_context(s, project_id)
                for ev in service.list_events(s, run_id, after):
                    data = json.dumps(
                        {"event_type": ev.event_type, "sequence": ev.event_seq, "payload": ev.payload},
                        ensure_ascii=False,
                    )
                    yield f"id: {ev.event_seq}\nevent: {ev.event_type}\ndata: {data}\n\n"
                    after = ev.event_seq
            finally:
                s.close()
            time.sleep(1)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.get("/operations/{operation_id}")
def get_operation(operation_id: uuid.UUID) -> dict:
    """Operation = 202 受理回执；权威状态在 project-scoped run 端点（status_url 指向）。"""
    return {"operation_id": str(operation_id), "status": "ACCEPTED"}