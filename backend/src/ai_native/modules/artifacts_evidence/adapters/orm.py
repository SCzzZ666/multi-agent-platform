"""artifacts_evidence 的 ORM 映射。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ai_native.bootstrap.db import Base


class Artifact(Base):
    __tablename__ = "artifact"
    __table_args__ = {"schema": "platform"}

    id: Mapped[object] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.project.id"))
    run_id: Mapped[object | None] = mapped_column(Uuid, ForeignKey("platform.run.id"), nullable=True)
    artifact_type: Mapped[str] = mapped_column(Text)
    media_type: Mapped[str] = mapped_column(Text)
    object_ref: Mapped[str] = mapped_column(Text)
    content_digest: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sensitivity: Mapped[str] = mapped_column(Text, default="INTERNAL")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)