"""workflow_runtime API 路由：建 Run(202) / 查 Run / SSE 事件 / operation。"""
from __future__ import annotations

import json
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ai_native.bootstrap.db import SessionLocal, get_db, project_context
from ai_native.modules.workflow_runtime.application import service

router = APIRouter(tags=["runs"])


@router.post("/projects/{project_id}/workflow-versions/{version_id}/runs", status_code=202)
def start_run(project_id: uuid.UUID, version_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    project_context(db, project_id)
    try:
        run = service.start_run(db, project_id, version_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=e.args[0])
    db.commit()
    return {
        "operation_id": str(run.id),
        "run_id": str(run.id),
        "state": run.state,
        "status": "ACCEPTED",
        "status_url": f"/api/v1/projects/{project_id}/runs/{run.id}",
    }


@router.get("/projects/{project_id}/runs/{run_id}")
def get_run(project_id: uuid.UUID, run_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    project_context(db, project_id)
    run = service.get_run(db, run_id)
    if run is None or str(run.project_id) != str(project_id):
        raise HTTPException(status_code=404, detail="run not found")
    return {
        "id": str(run.id),
        "project_id": str(run.project_id),
        "workflow_version_id": str(run.workflow_version_id),
        "state": run.state,
        "state_version": run.state_version,
        "event_seq": run.event_seq,
        "queued_at": run.queued_at.isoformat() if run.queued_at else None,
    }


@router.get("/projects/{project_id}/runs/{run_id}/events")
def stream_events(project_id: uuid.UUID, run_id: uuid.UUID, db: Session = Depends(get_db)) -> StreamingResponse:
    project_context(db, project_id)
    run = service.get_run(db, run_id)
    if run is None or str(run.project_id) != str(project_id):
        raise HTTPException(status_code=404, detail="run not found")

    def gen():
        after = 0
        while True:
            s = SessionLocal()
            try:
                project_context(s, project_id)
                for ev in service.list_events(s, run_id, after):
                    data = json.dumps({"event_type": ev.event_type, "payload": ev.payload}, ensure_ascii=False)
                    yield f"id: {ev.event_seq}\nevent: {ev.event_type}\ndata: {data}\n\n"
                    after = ev.event_seq
            finally:
                s.close()
            time.sleep(1)

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/operations/{operation_id}")
def get_operation(operation_id: uuid.UUID) -> dict:
    # Operation 是 202 受理回执；权威状态在 project-scoped 的 run 端点
    return {"operation_id": str(operation_id), "status": "ACCEPTED"}