"""Skill 目录应用用例：导入候选 → 发布固定版本 → 目录查询 → 退役（热加载边界）。

不可变：每次发布/候选都追加新 skill_version（version_no++），不覆盖旧版本；
热加载边界：只影响后续解析，已发布版本与运行中 Run 固定原 skill_version_id。
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ai_native.modules.catalog_registry.adapters.orm import Skill, SkillVersion
from ai_native.modules.catalog_registry.domain.skill import SkillPackage, package_digest
from ai_native.shared_kernel.ids import uuid7

VALIDATION_CANDIDATE = "CANDIDATE"
VALIDATION_PUBLISHED = "PUBLISHED"


def _get_or_create_skill(db: Session, project_id, package: SkillPackage) -> Skill:
    skill = db.scalar(
        select(Skill).where(Skill.project_id == project_id, Skill.skill_key == package.skill_key)
    )
    if skill is None:
        skill = Skill(id=uuid7(), project_id=project_id, skill_key=package.skill_key,
                      name=package.name, status="HIDDEN")
        db.add(skill)
        db.flush()
    return skill


def _next_version_no(db: Session, skill_id) -> int:
    return (db.scalar(select(func.coalesce(func.max(SkillVersion.version_no), 0)).where(SkillVersion.skill_id == skill_id)) or 0) + 1


def _manifest(package: SkillPackage) -> dict:
    return {
        "name": package.name,
        "description": package.description,
        "instructions": package.body,
        "scripts": sorted(package.scripts),
        "references": sorted(package.references),
        "assets": sorted(package.assets),
    }


def resolve_skill_version(db: Session, skill_version_id) -> dict | None:
    """skill 节点装载固定版本：返回 {name, description, instructions, version_no}。"""
    sv = db.get(SkillVersion, skill_version_id)
    if sv is None:
        return None
    m = sv.manifest or {}
    return {
        "name": m.get("name", ""),
        "description": m.get("description", ""),
        "instructions": m.get("instructions", ""),
        "version_no": sv.version_no,
    }


def import_skill(db: Session, project_id, package: SkillPackage) -> SkillVersion:
    """导入 → 不可变候选包 → 静态检查 → CANDIDATE 候选版本（不发布）。"""
    skill = _get_or_create_skill(db, project_id, package)
    manifest = _manifest(package)
    sv = SkillVersion(
        id=uuid7(), project_id=project_id, skill_id=skill.id,
        version_no=_next_version_no(db, skill.id),
        package_digest=package_digest(manifest), manifest=manifest,
        validation_status=VALIDATION_CANDIDATE,
    )
    db.add(sv)
    db.flush()
    return sv


def publish_skill_version(db: Session, project_id, package: SkillPackage) -> SkillVersion:
    """Validator 独立验证 + Approval 后：追加不可变 PUBLISHED 固定版本。"""
    skill = _get_or_create_skill(db, project_id, package)
    manifest = _manifest(package)
    sv = SkillVersion(
        id=uuid7(), project_id=project_id, skill_id=skill.id,
        version_no=_next_version_no(db, skill.id),
        package_digest=package_digest(manifest), manifest=manifest,
        validation_status=VALIDATION_PUBLISHED,
    )
    db.add(sv)
    db.flush()
    return sv


def list_skills(db: Session, project_id) -> list[dict]:
    """目录查询：只退检索不删历史（retired 仍可查其历史版本）。"""
    skills = list(db.scalars(select(Skill).where(Skill.project_id == project_id).order_by(Skill.skill_key)))
    out = []
    for s in skills:
        published = db.scalar(
            select(SkillVersion).where(SkillVersion.skill_id == s.id, SkillVersion.validation_status == VALIDATION_PUBLISHED)
            .order_by(SkillVersion.version_no.desc()).limit(1)
        )
        out.append({
            "id": str(s.id), "skill_key": s.skill_key, "name": s.name, "status": s.status,
            "published_version_no": published.version_no if published else None,
        })
    return out


def retire_skill(db: Session, skill_id):
    """retire 只退检索、不删历史；历史 SkillVersion 保留。"""
    skill = db.get(Skill, skill_id)
    if skill is not None:
        skill.status = "RETIRED"
    return skill


def refresh_catalog(db: Session, project_id, packages: list[SkillPackage]):
    """目录刷新：只为后续 Draft/Run 解析新版本；运行中版本不漂移。"""
    return [import_skill(db, project_id, p) for p in packages]