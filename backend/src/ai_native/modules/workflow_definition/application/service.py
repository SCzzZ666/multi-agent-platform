"""workflow_definition 应用用例：创建草稿 / 更新定义 / 发布版本（08 Schema 校验）。"""
from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ai_native.modules.workflow_definition.adapters.orm import (
    RoleCatalogVersion,
    WorkflowDraft,
    WorkflowDraftRevision,
    WorkflowTemplateVersion,
    WorkflowVersion,
)
from ai_native.modules.workflow_definition.domain.validator import is_acyclic, validate_definition
from ai_native.shared_kernel.digest import sha256_hex
from ai_native.shared_kernel.ids import uuid7


def _digest(obj) -> str:
    return "sha256:" + sha256_hex(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8"))


def get_published_template(db: Session, template_key: str) -> WorkflowTemplateVersion | None:
    return db.scalar(
        select(WorkflowTemplateVersion)
        .where(WorkflowTemplateVersion.template_key == template_key, WorkflowTemplateVersion.status == "PUBLISHED")
        .order_by(WorkflowTemplateVersion.version_no.desc())
        .limit(1)
    )


def get_published_role_catalog(db: Session) -> RoleCatalogVersion | None:
    return db.scalar(
        select(RoleCatalogVersion)
        .where(RoleCatalogVersion.status == "PUBLISHED")
        .order_by(RoleCatalogVersion.version_no.desc())
        .limit(1)
    )


def create_workflow(db: Session, project_id, template_key: str, title: str) -> WorkflowDraft:
    template = get_published_template(db, template_key)
    if template is None:
        raise ValueError(f"模板未发布或不存在: {template_key}")
    draft = WorkflowDraft(
        id=uuid7(), project_id=project_id, workflow_key=template_key, title=title,
        template_version_id=template.id, row_version=1, current_revision_no=0,
    )
    db.add(draft)
    db.flush()
    return draft


def put_definition(db: Session, draft: WorkflowDraft, definition: dict, user_id) -> WorkflowDraftRevision:
    ok, errors = validate_definition(definition)
    if not ok:
        raise ValueError(errors)
    ok2, reason = is_acyclic(definition)
    if not ok2:
        raise ValueError([reason])
    rev_no = draft.current_revision_no + 1
    rev = WorkflowDraftRevision(
        id=uuid7(), project_id=draft.project_id, workflow_draft_id=draft.id,
        revision_no=rev_no, definition_json=definition, content_digest=_digest(definition),
        created_by=user_id,
    )
    db.add(rev)
    draft.current_revision_no = rev_no
    draft.row_version += 1
    db.flush()
    return rev


def latest_revision(db: Session, draft: WorkflowDraft) -> WorkflowDraftRevision | None:
    return db.scalar(
        select(WorkflowDraftRevision)
        .where(WorkflowDraftRevision.workflow_draft_id == draft.id)
        .order_by(WorkflowDraftRevision.revision_no.desc())
        .limit(1)
    )


def publish_version(db: Session, draft: WorkflowDraft, user_id) -> WorkflowVersion:
    rev = latest_revision(db, draft)
    if rev is None:
        raise ValueError("草稿无定义，先 PUT draft")
    role_catalog = get_published_role_catalog(db)
    if role_catalog is None:
        raise ValueError("无已发布角色目录")
    version_no = db.scalar(
        select(func.count()).select_from(WorkflowVersion).where(WorkflowVersion.workflow_draft_id == draft.id)
    ) + 1
    definition = rev.definition_json
    version = WorkflowVersion(
        id=uuid7(), project_id=draft.project_id, workflow_draft_id=draft.id,
        version_no=version_no, schema_version="1.0",
        role_catalog_version_id=role_catalog.id, template_version_id=draft.template_version_id,
        definition_json=definition, content_digest=_digest(definition), published_by=user_id,
    )
    db.add(version)
    db.flush()
    return version