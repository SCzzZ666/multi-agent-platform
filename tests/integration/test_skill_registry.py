"""Skill 目录（不可变版本 + 热加载边界 + 退役只退检索）：真实 PG。"""
from __future__ import annotations

import uuid as _uuid

from sqlalchemy import select

from fastapi.testclient import TestClient

from ai_native.bootstrap.db import SessionLocal, project_context
from ai_native.entrypoints.api import app
from ai_native.modules.catalog_registry.adapters.orm import SkillVersion
from ai_native.modules.catalog_registry.application import skill_service
from ai_native.modules.catalog_registry.domain.skill import SkillPackage


def _pkg():
    return SkillPackage(skill_key="code-review", name="代码审查", description="静态审查",
                        body="审查步骤", scripts={"scripts/check.sh": "echo ok"})


def test_registry_import_publish_list_retire() -> None:
    c = TestClient(app)
    pid = c.post("/api/v1/projects", json={"name": f"sk-{_uuid.uuid4().hex[:6]}"}).json()["id"]
    pid_u = _uuid.UUID(pid)
    db = SessionLocal()

    project_context(db, pid_u)
    cand = skill_service.import_skill(db, pid_u, _pkg())
    assert cand.validation_status == "CANDIDATE" and cand.version_no == 1
    pub = skill_service.publish_skill_version(db, pid_u, _pkg())
    assert pub.validation_status == "PUBLISHED" and pub.version_no == 2
    db.commit()

    project_context(db, pid_u)
    listing = skill_service.list_skills(db, pid_u)
    assert len(listing) == 1 and listing[0]["published_version_no"] == 2
    skill_id = listing[0]["id"]

    project_context(db, pid_u)
    skill_service.retire_skill(db, _uuid.UUID(skill_id))
    db.commit()

    project_context(db, pid_u)
    assert skill_service.list_skills(db, pid_u)[0]["status"] == "RETIRED"
    # 历史版本不可变：CANDIDATE(1) + PUBLISHED(2) 都在
    versions = list(db.scalars(select(SkillVersion.version_no).where(SkillVersion.project_id == pid_u).order_by(SkillVersion.version_no)))
    assert versions == [1, 2]
    db.close()


def test_hot_reload_appends_new_version_not_mutate() -> None:
    c = TestClient(app)
    pid = c.post("/api/v1/projects", json={"name": f"sk-{_uuid.uuid4().hex[:6]}"}).json()["id"]
    pid_u = _uuid.UUID(pid)
    db = SessionLocal()

    project_context(db, pid_u)
    v1 = skill_service.publish_skill_version(db, pid_u, _pkg())
    db.commit()

    # 目录刷新后再发布同 key → 追加新版本 v2，不覆盖 v1
    project_context(db, pid_u)
    v2 = skill_service.publish_skill_version(db, pid_u, _pkg())
    db.commit()

    assert v1.version_no == 1 and v2.version_no == 2 and v1.id != v2.id
    project_context(db, pid_u)
    nos = list(db.scalars(select(SkillVersion.version_no).where(SkillVersion.project_id == pid_u).order_by(SkillVersion.version_no)))
    assert nos == [1, 2]
    db.close()