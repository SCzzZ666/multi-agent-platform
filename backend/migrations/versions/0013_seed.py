r"""迁移第⑫步：8 角色 + 三模板策略种子数据 + 合同版本行（依赖 Python 生成 uuid7 / sha256）。

注：模板 fixed_definition_json 此处只落共享治理骨架，完整专业 DAG 在 11 基线（Day2/3/4）按
TemplateResolver 展开；发布校验（08 schema）在 R3 主线接入时执行。
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def _uuid7() -> str:
    ts = int(time.time() * 1000) & 0xFFFFFFFFFFFF
    b = bytearray(uuid.uuid4().bytes)
    b[:6] = ts.to_bytes(6, "big")
    b[6] = (b[6] & 0x0F) | 0x70
    b[8] = (b[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(b)))


def _sha256(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


ROLES = [
    ("planner", "规划者", "唯一协调规划：目标理解、任务拆分、模板内规划、返工重规划"),
    ("architect", "架构师", "模块、领域、数据、API 与技术方案设计"),
    ("engineer", "工程师", "在隔离工作副本实现并生成 Patch，不直接回写宿主"),
    ("researcher", "研究员", "文献、来源、假设与实验设计"),
    ("analyst", "分析师", "固定数据快照分析、复现与可视化"),
    ("writer", "撰写者", "基于已验证制品形成交付/研究报告"),
    ("skill_maintainer", "技能维护者", "导入、规范化和版本化 Skill 候选包"),
    ("validator", "验证者", "独立质量门与定向返工，不修改被验证制品"),
]

_TEMPLATES = [
    ("software_factory", "软件工厂", {"max_professional_nodes": 12, "allowed_expert_roles": ["engineer"]}),
    ("skills", "Skills", {"max_professional_nodes": 8, "allowed_expert_roles": ["skill_maintainer"]}),
    ("ai4s", "AI4S", {"max_professional_nodes": 16, "allowed_expert_roles": ["researcher", "analyst"]}),
]


def _skeleton(template_key: str, name: str) -> dict:
    nodes = [
        {"node_key": "normalize", "name": "输入标准化", "kind": "transform", "region": "FIXED_CONTROL", "role_ref": "planner", "activation_mode": "ALL_INBOUND"},
        {"node_key": "planner", "name": "规划", "kind": "agent", "region": "FIXED_CONTROL", "role_ref": "planner", "activation_mode": "ALL_INBOUND"},
        {"node_key": "validate_plan", "name": "确定性计划校验", "kind": "transform", "region": "FIXED_CONTROL", "role_ref": "planner", "activation_mode": "ALL_INBOUND"},
        {"node_key": "route_plan", "name": "计划路由", "kind": "condition", "region": "FIXED_CONTROL", "role_ref": "planner", "activation_mode": "ALL_INBOUND", "routes": ["EXECUTE", "HOLD_FOR_USER", "REJECT"]},
        {"node_key": "validator", "name": "独立质量门", "kind": "agent", "region": "FIXED_CONTROL", "role_ref": "validator", "activation_mode": "ALL_INBOUND"},
    ]
    edges = [
        {"source": "normalize", "target": "planner"},
        {"source": "planner", "target": "validate_plan"},
        {"source": "validate_plan", "target": "route_plan"},
    ]
    return {
        "schema_version": "1.0",
        "workflow_key": template_key,
        "name": name,
        "entry_node_key": "normalize",
        "output_node_keys": ["validator"],
        "nodes": nodes,
        "edges": edges,
    }


def upgrade() -> None:
    cat_id = _uuid7()
    roles_payload = json.dumps(
        [{"role_id": r[0], "name": r[1], "responsibility": r[2]} for r in ROLES],
        ensure_ascii=False, sort_keys=True,
    )
    cat_digest = _sha256(roles_payload)
    op.execute(
        "INSERT INTO platform.role_catalog_version "
        "(id, catalog_key, version_no, content_digest, status, published_at) "
        f"VALUES ('{cat_id}','roles',1,'{cat_digest}','PUBLISHED', now())"
    )
    for role_id, name, resp in ROLES:
        profile = json.dumps({"role_id": role_id, "name": name, "model_policy_ref": None}, ensure_ascii=False)
        capc = json.dumps({}, ensure_ascii=False)
        op.execute(
            "INSERT INTO platform.role_definition "
            "(catalog_version_id, role_id, name, responsibility, capability_ceiling, profile_json) "
            f"VALUES ('{cat_id}', $txt${role_id}$txt$, $txt${name}$txt$, $txt${resp}$txt$, $json${capc}$json$, $json${profile}$json$)"
        )

    for template_key, name, policy in _TEMPLATES:
        fixed = _skeleton(template_key, name)
        fixed_json = json.dumps(fixed, ensure_ascii=False, sort_keys=True)
        policy_json = json.dumps(policy, ensure_ascii=False, sort_keys=True)
        digest = _sha256(fixed_json)
        op.execute(
            "INSERT INTO platform.workflow_template_version "
            "(id, template_key, version_no, fixed_definition_json, extension_policy_json, content_digest, status, published_at) "
            f"VALUES ('{_uuid7()}', $txt${template_key}$txt$, 1, $json${fixed_json}$json$, $json${policy_json}$json$, '{digest}', 'PUBLISHED', now())"
        )


def downgrade() -> None:
    pass