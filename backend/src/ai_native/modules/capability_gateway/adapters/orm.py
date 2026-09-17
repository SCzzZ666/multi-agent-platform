"""capability_gateway 的 ORM 映射：approval_request / approval_decision / invocation_intent。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ai_native.bootstrap.db import Base


class ApprovalRequest(Base):
    __tablename__ = "approval_request"
    __table_args__ = {"schema": "platform"}

    id: Mapped[object] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[object] = mapped_column(Uuid)
    run_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.run.id"))
    node_attempt_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.node_attempt.id"))
    action_id: Mapped[object] = mapped_column(Uuid)
    tool_schema_version_id: Mapped[object | None] = mapped_column(Uuid, nullable=True)
    workflow_digest: Mapped[str] = mapped_column(Text)
    schema_digest: Mapped[str] = mapped_column(Text)
    args_digest: Mapped[str] = mapped_column(Text)
    resources_digest: Mapped[str] = mapped_column(Text)
    risk: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    row_version: Mapped[int] = mapped_column(BigInteger, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApprovalDecision(Base):
    __tablename__ = "approval_decision"
    __table_args__ = {"schema": "platform"}

    id: Mapped[object] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[object] = mapped_column(Uuid)
    approval_request_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.approval_request.id"))
    decision: Mapped[str] = mapped_column(Text)
    decided_by: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.app_user.id"))
    idempotency_key: Mapped[str] = mapped_column(Text)
    request_digest: Mapped[str] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())


class InvocationIntent(Base):
    __tablename__ = "invocation_intent"
    __table_args__ = {"schema": "platform"}

    id: Mapped[object] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[object] = mapped_column(Uuid)
    run_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.run.id"))
    node_attempt_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.node_attempt.id"))
    approval_request_id: Mapped[object | None] = mapped_column(Uuid, nullable=True)
    action_id: Mapped[object] = mapped_column(Uuid)
    tool_schema_version_id: Mapped[object | None] = mapped_column(Uuid, nullable=True)
    schema_digest: Mapped[str] = mapped_column(Text)
    args_digest: Mapped[str] = mapped_column(Text)
    resources_digest: Mapped[str] = mapped_column(Text)
    idempotency_class: Mapped[str] = mapped_column(Text)
    provider_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    fencing_token: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(Text)
    dispatch_not_before: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())