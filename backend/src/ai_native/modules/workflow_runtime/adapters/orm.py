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


class RunLease(Base):
    __tablename__ = "run_lease"
    __table_args__ = {"schema": "platform"}

    run_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.run.id"), primary_key=True)
    lease_owner: Mapped[str] = mapped_column(Text)
    fencing_token: Mapped[int] = mapped_column(BigInteger)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    row_version: Mapped[int] = mapped_column(BigInteger, default=1)


class NodeAttempt(Base):
    __tablename__ = "node_attempt"
    __table_args__ = {"schema": "platform"}

    id: Mapped[object] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[object] = mapped_column(Uuid)
    run_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.run.id"))
    run_plan_version_id: Mapped[object | None] = mapped_column(Uuid, nullable=True)
    node_key: Mapped[str] = mapped_column(Text)
    task_id: Mapped[str] = mapped_column(Text)
    role_ref: Mapped[str] = mapped_column(Text)
    attempt_no: Mapped[int] = mapped_column(Integer)
    rework_round: Mapped[int] = mapped_column(Integer, default=0)
    previous_attempt_id: Mapped[object | None] = mapped_column(Uuid, nullable=True)
    input_envelope_artifact_id: Mapped[object | None] = mapped_column(Uuid, nullable=True)
    input_digest: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_envelope_artifact_id: Mapped[object | None] = mapped_column(Uuid, nullable=True)
    result_digest: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(Text)
    fencing_token: Mapped[int] = mapped_column(BigInteger)
    state_version: Mapped[int] = mapped_column(BigInteger, default=0)
    completion_receipt: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


