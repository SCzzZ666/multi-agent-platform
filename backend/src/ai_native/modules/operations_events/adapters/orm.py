"""operations_events 的 ORM 映射：RunEvent / EventOutbox / AuditEvent。

RunEvent 从 workflow_runtime 迁到本模块（10 基线：operations_events 拥有 Operation/RunEvent/outbox/审计）。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_native.bootstrap.db import Base


class RunEvent(Base):
    __tablename__ = "run_event"
    __table_args__ = {"schema": "platform"}

    id: Mapped[object] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[object] = mapped_column(Uuid)
    run_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.run.id"))
    event_seq: Mapped[int] = mapped_column(BigInteger)
    event_type: Mapped[str] = mapped_column(Text)
    state_version: Mapped[int] = mapped_column(BigInteger, default=0)
    actor: Mapped[dict] = mapped_column(JSONB)
    correlation_id: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB)
    payload_digest: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())


class EventOutbox(Base):
    __tablename__ = "event_outbox"
    __table_args__ = {"schema": "platform"}

    id: Mapped[object] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.project.id"))
    aggregate_type: Mapped[str] = mapped_column(Text)
    aggregate_id: Mapped[object] = mapped_column(Uuid)
    event_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.run_event.id"))
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error_code: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_event"
    __table_args__ = {"schema": "platform"}

    id: Mapped[object] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.project.id"))
    audit_seq: Mapped[int] = mapped_column(BigInteger)
    event_type: Mapped[str] = mapped_column(Text)
    actor: Mapped[dict] = mapped_column(JSONB)
    subject: Mapped[dict] = mapped_column(JSONB)
    previous_digest: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_digest: Mapped[str] = mapped_column(Text)
    payload_digest: Mapped[str] = mapped_column(Text)
    trace_id: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())