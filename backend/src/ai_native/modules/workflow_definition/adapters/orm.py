"""workflow_definition 的 ORM 映射。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_native.bootstrap.db import Base


class RoleCatalogVersion(Base):
    __tablename__ = "role_catalog_version"
    __table_args__ = {"schema": "platform"}

    id: Mapped[object] = mapped_column(Uuid, primary_key=True)
    catalog_key: Mapped[str] = mapped_column(Text)
    version_no: Mapped[int] = mapped_column(Integer)
    content_digest: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WorkflowTemplateVersion(Base):
    __tablename__ = "workflow_template_version"
    __table_args__ = {"schema": "platform"}

    id: Mapped[object] = mapped_column(Uuid, primary_key=True)
    template_key: Mapped[str] = mapped_column(Text)
    version_no: Mapped[int] = mapped_column(Integer)
    fixed_definition_json: Mapped[dict] = mapped_column(JSONB)
    extension_policy_json: Mapped[dict] = mapped_column(JSONB)
    content_digest: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WorkflowDraft(Base):
    __tablename__ = "workflow_draft"
    __table_args__ = {"schema": "platform"}

    id: Mapped[object] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.project.id"))
    workflow_key: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    template_version_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.workflow_template_version.id"))
    row_version: Mapped[int] = mapped_column(default=1)
    current_revision_no: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())


class WorkflowDraftRevision(Base):
    __tablename__ = "workflow_draft_revision"
    __table_args__ = {"schema": "platform"}

    id: Mapped[object] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[object] = mapped_column(Uuid)
    workflow_draft_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.workflow_draft.id"))
    revision_no: Mapped[int] = mapped_column(Integer)
    definition_json: Mapped[dict] = mapped_column(JSONB)
    content_digest: Mapped[str] = mapped_column(Text)
    created_by: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())


class WorkflowVersion(Base):
    __tablename__ = "workflow_version"
    __table_args__ = {"schema": "platform"}

    id: Mapped[object] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[object] = mapped_column(Uuid)
    workflow_draft_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.workflow_draft.id"))
    version_no: Mapped[int] = mapped_column(Integer)
    schema_version: Mapped[str] = mapped_column(Text)
    role_catalog_version_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.role_catalog_version.id"))
    template_version_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.workflow_template_version.id"))
    definition_json: Mapped[dict] = mapped_column(JSONB)
    content_digest: Mapped[str] = mapped_column(Text)
    published_by: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.app_user.id"))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())