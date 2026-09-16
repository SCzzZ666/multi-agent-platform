"""identity_project 应用用例。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_native.modules.identity_project.adapters.orm import AppUser, Project
from ai_native.shared_kernel.ids import uuid7


def ensure_user(db: Session, subject: str, display_name: str) -> AppUser:
    user = db.scalar(select(AppUser).where(AppUser.subject == subject))
    if user is None:
        user = AppUser(id=uuid7(), subject=subject, display_name=display_name)
        db.add(user)
        db.flush()
    return user


def create_project(db: Session, owner: AppUser, name: str) -> Project:
    project = Project(id=uuid7(), name=name, status="ACTIVE", owner_user_id=owner.id, row_version=1)
    db.add(project)
    db.flush()
    return project


def get_project(db: Session, project_id) -> Project | None:
    return db.get(Project, project_id)


def list_projects(db: Session, owner_id) -> list[Project]:
    return list(db.scalars(select(Project).where(Project.owner_user_id == owner_id).order_by(Project.created_at)))