"""catalog_registry 的 ORM 映射：skill / skill_version（Skill 目录）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_native.bootstrap.db import Base


class Skill(Base):
    __tablename__ = "skill"
    __table_args__ = {"schema": "platform"}

    id: Mapped[object] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.project.id"))
    skill_key: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="HIDDEN")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())


class SkillVersion(Base):
    __tablename__ = "skill_version"
    __table_args__ = {"schema": "platform"}

    id: Mapped[object] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[object] = mapped_column(Uuid)
    skill_id: Mapped[object] = mapped_column(Uuid, ForeignKey("platform.skill.id"))
    version_no: Mapped[int] = mapped_column(Integer)
    package_digest: Mapped[str] = mapped_column(Text)
    manifest: Mapped[dict] = mapped_column(JSONB)
    validation_status: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())