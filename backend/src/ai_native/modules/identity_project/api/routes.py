"""identity_project API 路由（挂到 /api/v1 下）。"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ai_native.bootstrap.db import get_db
from ai_native.modules.identity_project.adapters.orm import AppUser, Project
from ai_native.modules.identity_project.application import service

router = APIRouter(tags=["projects"])

# 本地会话认证首发（10 基线 13.2）：dev 固定身份；生产 Profile 拒载测试身份
DEV_SUBJECT = "local:dev"


def get_current_user(db: Session = Depends(get_db)) -> AppUser:
    return service.ensure_user(db, DEV_SUBJECT, "本地开发用户")


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


def _out(p: Project) -> dict:
    return {
        "id": str(p.id),
        "name": p.name,
        "status": p.status,
        "row_version": p.row_version,
    }


@router.post("/projects", status_code=201)
def create_project(body: ProjectCreate, user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    p = service.create_project(db, user, body.name)
    db.commit()
    return _out(p)


@router.get("/projects")
def list_projects(user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"items": [_out(p) for p in service.list_projects(db, user.id)]}


@router.get("/projects/{project_id}")
def get_project(project_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    p = service.get_project(db, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="project not found")
    return _out(p)