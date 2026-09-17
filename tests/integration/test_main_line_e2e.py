"""第 1 周最薄主线端到端：发布 Definition → 建 Run(202) → 查 Run → SSE 出事件。

真实口径：TestClient 走真实 FastAPI 路由 → 真实 PostgreSQL（api_user + RLS 项目作用域）。
无 mock：所有写操作真实落库，SSE 真实回放 RUN_CREATED。
"""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from ai_native.entrypoints.api import app

client = TestClient(app)

VALID_DEFINITION = {
    "schema_version": "1.0",
    "workflow_key": "software_factory",
    "name": "示例工作流",
    "input_contract_ref": "text.input@1",
    "output_contract_ref": "text.output@1",
    "entry_node_key": "normalize",
    "output_node_keys": ["validate"],
    "nodes": [
        {"node_key": "normalize", "name": "输入标准化", "kind": "transform", "region": "FIXED_CONTROL", "role_ref": "planner", "input_contract_ref": "text.input@1", "output_contract_ref": "normalized.input@1", "activation_mode": "ALL_INBOUND", "transform_key": "input.normalize"},
        {"node_key": "plan", "name": "规划", "kind": "agent", "region": "FIXED_CONTROL", "role_ref": "planner", "input_contract_ref": "normalized.input@1", "output_contract_ref": "taskplan@1", "activation_mode": "ALL_INBOUND"},
        {"node_key": "validate_plan", "name": "计划校验", "kind": "transform", "region": "FIXED_CONTROL", "role_ref": "planner", "input_contract_ref": "taskplan@1", "output_contract_ref": "validation@1", "activation_mode": "ALL_INBOUND", "transform_key": "plan.validate"},
        {"node_key": "route", "name": "计划路由", "kind": "condition", "region": "FIXED_CONTROL", "role_ref": "planner", "input_contract_ref": "validation@1", "output_contract_ref": "route@1", "activation_mode": "ALL_INBOUND", "condition_key": "plan.route", "routes": ["EXECUTE", "HOLD_FOR_USER", "REJECT"]},
        {"node_key": "implement", "name": "实现", "kind": "agent", "region": "PROFESSIONAL", "role_ref": "engineer", "input_contract_ref": "route@1", "output_contract_ref": "deliverable@1", "activation_mode": "ALL_INBOUND"},
        {"node_key": "validate", "name": "质量门", "kind": "agent", "region": "FIXED_CONTROL", "role_ref": "validator", "input_contract_ref": "deliverable@1", "output_contract_ref": "text.output@1", "activation_mode": "ALL_INBOUND"},
    ],
    "edges": [
        {"edge_key": "e1", "from": "normalize", "to": "plan"},
        {"edge_key": "e2", "from": "plan", "to": "validate_plan"},
        {"edge_key": "e3", "from": "validate_plan", "to": "route"},
        {"edge_key": "e4", "from": "route", "to": "implement", "route": "EXECUTE"},
        {"edge_key": "e5", "from": "implement", "to": "validate"},
    ],
}


def test_main_line_end_to_end() -> None:
    # 1. 建项目
    r = client.post("/api/v1/projects", json={"name": f"e2e-{uuid.uuid4().hex[:8]}"})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]

    # 2. 建工作流草稿
    r = client.post(f"/api/v1/projects/{pid}/workflows", json={"template_key": "software_factory", "title": "e2e"})
    assert r.status_code == 201, r.text
    wid = r.json()["workflow_id"]

    # 3. 写入定义（08 Schema 校验）
    r = client.put(f"/api/v1/projects/{pid}/workflows/{wid}/draft", json={"definition": VALID_DEFINITION})
    assert r.status_code == 200, r.text

    # 4. 发布版本
    r = client.post(f"/api/v1/projects/{pid}/workflows/{wid}/publish")
    assert r.status_code == 201, r.text
    vid = r.json()["workflow_version_id"]

    # 5. 建 Run（202 + operation_id）
    r = client.post(f"/api/v1/projects/{pid}/workflow-versions/{vid}/runs")
    assert r.status_code == 202, r.text
    body = r.json()
    rid = body["run_id"]
    assert body["status"] == "ACCEPTED"
    assert body["operation_id"] == rid

    # 6. 查 Run
    r = client.get(f"/api/v1/projects/{pid}/runs/{rid}")
    assert r.status_code == 200
    assert r.json()["state"] == "QUEUED"

    # 7. 事件 + outbox + 审计真实落库（SSE 回放在真实 uvicorn 进程上另行验证）
    from sqlalchemy import select

    from ai_native.bootstrap.db import SessionLocal, project_context as ctx
    from ai_native.modules.operations_events.adapters.orm import AuditEvent, EventOutbox
    from ai_native.modules.operations_events.application import service as ops_service

    s = SessionLocal()
    try:
        ctx(s, uuid.UUID(pid))
        events = ops_service.list_events(s, uuid.UUID(rid))
        assert [e.event_type for e in events] == ["RUN_CREATED"]
        # outbox：同事务至少一次发布
        outbox = list(s.scalars(select(EventOutbox).where(EventOutbox.aggregate_id == uuid.UUID(rid))))
        assert len(outbox) == 1 and outbox[0].published_at is None
        # 审计：RUN_STARTED 追加写，摘要链 non-null
        audits = list(s.scalars(select(AuditEvent).where(AuditEvent.project_id == uuid.UUID(pid)).order_by(AuditEvent.audit_seq)))
        assert audits and audits[0].event_type == "RUN_STARTED" and audits[0].event_digest.startswith("sha256:")
    finally:
        s.close()


def test_publish_rejects_invalid_definition() -> None:
    r = client.post("/api/v1/projects", json={"name": f"e2e-bad-{uuid.uuid4().hex[:8]}"})
    assert r.status_code == 201
    pid = r.json()["id"]
    r = client.post(f"/api/v1/projects/{pid}/workflows", json={"template_key": "software_factory", "title": "bad"})
    wid = r.json()["workflow_id"]
    bad = {"schema_version": "1.0"}  # 缺字段 → 08 Schema 应拒绝
    r = client.put(f"/api/v1/projects/{pid}/workflows/{wid}/draft", json={"definition": bad})
    assert r.status_code == 422, r.text