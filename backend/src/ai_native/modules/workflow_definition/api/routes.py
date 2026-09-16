"""workflow_definition API 路由。"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ai_native.bootstrap.db import get_db, project_context
from ai_native.modules.identity_project.api.routes import get_current_user
from ai_native.modules.identity_project.application import service as identity_service
from ai_native.modules.workflow_definition.application import service
from ai_native.modules.workflow_definition.adapters.orm import WorkflowDraft

router = APIRouter(tags=["workflows"])


class WorkflowCreate(BaseModel):
    template_key: str
    title: str = Field(min_length=1, max_length=200)


class DraftPut(BaseModel):
    definition: dict


def _get_draft_or_404(db: Session, project_id: uuid.UUID, workflow_id: uuid.UUID) -> WorkflowDraft:
    project_context(db, project_id)
    draft = db.get(WorkflowDraft, workflow_id)
    if draft is None or str(draft.project_id) != str(project_id):
        raise HTTPException(status_code=404, detail="workflow not found")
    return draft


@router.post("/projects/{project_id}/workflows", status_code=201)
def create_workflow(project_id: uuid.UUID, body: WorkflowCreate, db: Session = Depends(get_db)) -> dict:
    # 项目必须存在
    if identity_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")
    project_context(db, project_id)
    try:
        draft = service.create_workflow(db, project_id, body.template_key, body.title)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=e.args[0])
    db.commit()
    return {"workflow_id": str(draft.id), "template_key": draft.workflow_key, "current_revision_no": draft.current_revision_no}


@router.put("/projects/{project_id}/workflows/{workflow_id}/draft")
def put_draft(project_id: uuid.UUID, workflow_id: uuid.UUID, body: DraftPut,
              user=Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    draft = _get_draft_or_404(db, project_id, workflow_id)
    try:
        rev = service.put_definition(db, draft, body.definition, user.id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=e.args[0])
    db.commit()
    return {"workflow_id": str(draft.id), "revision_no": rev.revision_no}


@router.post("/projects/{project_id}/workflows/{workflow_id}/publish", status_code=201)
def publish(project_id: uuid.UUID, workflow_id: uuid.UUID,
            user=Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    draft = _get_draft_or_404(db, project_id, workflow_id)
    try:
        version = service.publish_version(db, draft, user.id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=e.args[0])
    db.commit()
    return {"workflow_version_id": str(version.id), "version_no": version.version_no}


@router.get("/projects/{project_id}/workflows/{workflow_id}/draft")
def get_draft(project_id: uuid.UUID, workflow_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    draft = _get_draft_or_404(db, project_id, workflow_id)
    rev = service.latest_revision(db, draft)
    return {
        "workflow_id": str(draft.id),
        "template_key": draft.workflow_key,
        "current_revision_no": draft.current_revision_no,
        "definition": rev.definition_json if rev else None,
    }