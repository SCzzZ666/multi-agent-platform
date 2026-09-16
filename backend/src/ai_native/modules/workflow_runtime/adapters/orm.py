"""workflow_runtime 的 ORM 映射（run 核心对象）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_native.bootstrap.db import Base


class RunSnapshot(Base):
    __tablename__ = "run_snapshot"
    __table_args__ = {"schema": "platform"}

    id: Mapped[object] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.project.id"))
    workflow_version_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.workflow_version.id"))
    source_snapshot: Mapped[dict] = mapped_column(JSONB)
    model_config_snapshot: Mapped[dict] = mapped_column(JSONB)
    prompt_snapshot: Mapped[dict] = mapped_column(JSONB)
    capability_snapshot: Mapped[dict] = mapped_column(JSONB)
    content_digest: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())


class Run(Base):
    __tablename__ = "run"
    __table_args__ = {"schema": "platform"}

    id: Mapped[object] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.project.id"))
    workflow_version_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.workflow_version.id"))
    run_snapshot_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.run_snapshot.id"))
    state: Mapped[str] = mapped_column(Text)
    state_version: Mapped[int] = mapped_column(BigInteger, default=0)
    event_seq: Mapped[int] = mapped_column(BigInteger, default=0)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    max_wall_seconds: Mapped[int] = mapped_column(Integer)
    max_cost_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    used_cost_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    cancel_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
    active_plan_version_id: Mapped[object | None] = mapped_column(Uuid, nullable=True)
    row_version: Mapped[int] = mapped_column(BigInteger, default=1)


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