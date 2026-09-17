"""能力审批原子消费 + InvocationIntent 落库（真实 PG 事务，09 主链）。

真实口径：真实项目/用户/运行/NodeAttempt/审批请求/审批决定全落库，
消费在单事务内锁行→校摘要→查幂等→扣 used_count→建 Intent。无 mock。
RLS 的 SET LOCAL 为事务级：每个新事务前重设项目上下文（与 API 路由行为一致）。
"""
from __future__ import annotations

import uuid as _uuid

from sqlalchemy import select

from ai_native.bootstrap.db import SessionLocal, project_context
from ai_native.modules.capability_gateway.application import consumption
from ai_native.modules.capability_gateway.domain.binding import compute_binding_digests
from ai_native.modules.capability_gateway.domain.scopes import ResourceScope
from ai_native.modules.identity_project.adapters.orm import AppUser
from ai_native.modules.workflow_runtime.adapters.orm import NodeAttempt, Run
from ai_native.shared_kernel.ids import uuid7

from fastapi.testclient import TestClient

from ai_native.entrypoints.api import app

VALID = {
    "schema_version": "1.0", "workflow_key": "software_factory", "name": "cap",
    "input_contract_ref": "text.input@1", "output_contract_ref": "text.output@1",
    "entry_node_key": "n1", "output_node_keys": ["n3"],
    "nodes": [
        {"node_key": "n1", "name": "s", "kind": "transform", "region": "FIXED_CONTROL", "role_ref": "planner", "input_contract_ref": "text.input@1", "output_contract_ref": "c@1", "activation_mode": "ALL_INBOUND", "transform_key": "input.normalize"},
        {"node_key": "n2", "name": "p", "kind": "agent", "region": "FIXED_CONTROL", "role_ref": "planner", "input_contract_ref": "c@1", "output_contract_ref": "d@1", "activation_mode": "ALL_INBOUND"},
        {"node_key": "n3", "name": "v", "kind": "agent", "region": "FIXED_CONTROL", "role_ref": "validator", "input_contract_ref": "d@1", "output_contract_ref": "text.output@1", "activation_mode": "ALL_INBOUND"},
    ],
    "edges": [{"edge_key": "e1", "from": "n1", "to": "n2"}, {"edge_key": "e2", "from": "n2", "to": "n3"}],
}


def _scopes():
    return ResourceScope("PROJECT_RESOURCE", frozenset({"publish"}), resource_kind="skill_registry", resource_ids=frozenset({"r1"}))


def _alt_scopes():
    return ResourceScope("PROJECT_RESOURCE", frozenset({"publish"}), resource_kind="skill_registry", resource_ids=frozenset({"rOTHER"}))


def _layers(s):
    return dict(project_scopes=[s], role_scopes=[s], node_scopes=[s], plan_scopes=[s], skill_scopes=[s], tool_scopes=[s], runtime_scopes=[s])


def _setup():
    c = TestClient(app)
    pid = c.post("/api/v1/projects", json={"name": f"cap-{_uuid.uuid4().hex[:6]}"}).json()["id"]
    wid = c.post(f"/api/v1/projects/{pid}/workflows", json={"template_key": "software_factory", "title": "cap"}).json()["workflow_id"]
    c.put(f"/api/v1/projects/{pid}/workflows/{wid}/draft", json={"definition": VALID})
    vid = c.post(f"/api/v1/projects/{pid}/workflows/{wid}/publish").json()["workflow_version_id"]
    rid = c.post(f"/api/v1/projects/{pid}/workflow-versions/{vid}/runs").json()["run_id"]

    db = SessionLocal()
    project_context(db, _uuid.UUID(pid))
    run = db.get(Run, _uuid.UUID(rid))
    na = NodeAttempt(id=uuid7(), project_id=run.project_id, run_id=run.id, node_key="publish", task_id="t1",
                     role_ref="skill_maintainer", attempt_no=1, rework_round=0, state="WAITING_APPROVAL",
                     fencing_token=1, state_version=0)
    db.add(na)
    db.flush()
    action_id = uuid7()
    digests = compute_binding_digests(
        project_id=str(pid), run_id=rid, workflow_version_id=str(vid), run_plan_version_id=str(uuid7()),
        node_attempt_id=str(uuid7()), action_id=str(action_id), tool_key="registry", capability_key="skill.publish",
        tool_schema_digest="sha256:" + "a" * 64, normalized_args={"skill_id": "s1"},
        resource_scopes=[_scopes()], risk_level="HIGH", credential_refs=["cred:publish"],
    )
    req = consumption.request_approval(
        db, project_id=run.project_id, run_id=run.id, node_attempt_id=na.id, action_id=action_id,
        workflow_digest="sha256:" + "b" * 64, schema_digest=digests["tool_schema_digest"],
        args_digest=digests["args_digest"], resources_digest=digests["resource_scope_digest"],
        risk="HIGH", max_uses=1,
    )
    db.commit()
    return db, pid, req.id, digests


def _decided_by(db):
    return db.scalar(select(AppUser).limit(1)).id


def _approve(db, pid, req_id, decision="APPROVE"):
    project_context(db, _uuid.UUID(pid))
    decided_by = db.scalar(select(AppUser).limit(1)).id
    consumption.record_decision(db, approval_request_id=req_id, decided_by=decided_by,
                                decision=decision, idempotency_key=f"k-{_uuid.uuid4().hex[:8]}")
    db.commit()


def _consume(db, pid, req_id, digests, candidate):
    project_context(db, _uuid.UUID(pid))
    result = consumption.consume_approval_and_record_intent(
        db, approval_request_id=req_id, binding_digests=digests,
        layers=_layers(_scopes()), candidate_scopes=[candidate], risk_level="HIGH",
        idempotency_class="PROVIDER_IDEMPOTENT", fencing_token=1,
    )
    db.commit()
    return result


def _req_status(db, pid, req_id):
    from ai_native.modules.capability_gateway.adapters.orm import ApprovalRequest

    project_context(db, _uuid.UUID(pid))
    return db.get(ApprovalRequest, req_id)


def test_consume_after_approve_records_intent() -> None:
    db, pid, req_id, digests = _setup()
    assert _req_status(db, pid, req_id).status == "PENDING"
    _approve(db, pid, req_id)
    r = _consume(db, pid, req_id, digests, _scopes())
    assert r["dispatched"] is True and r["status"] == "COMMITTED", r
    req = _req_status(db, pid, req_id)
    assert req.status == "CONSUMED" and req.used_count == 1


def test_double_consume_is_idempotent() -> None:
    db, pid, req_id, digests = _setup()
    _approve(db, pid, req_id)
    first = _consume(db, pid, req_id, digests, _scopes())
    second = _consume(db, pid, req_id, digests, _scopes())
    assert first["dispatched"] is True
    assert second["dispatched"] is False and second["reason"] == "IDEMPOTENT_ALREADY_RECORDED", second
    assert _req_status(db, pid, req_id).used_count == 1  # 未重复消费


def test_rejected_approval_not_consumed() -> None:
    db, pid, req_id, digests = _setup()
    _approve(db, pid, req_id, decision="REJECT")
    r = _consume(db, pid, req_id, digests, _scopes())
    assert r["dispatched"] is False and r["reason"] == "APPROVAL_NOT_APPROVED", r


def test_binding_mismatch_not_consumed() -> None:
    db, pid, req_id, digests = _setup()
    _approve(db, pid, req_id)
    wrong = {**digests, "args_digest": "sha256:" + "c" * 64}
    r = _consume(db, pid, req_id, wrong, _scopes())
    assert r["dispatched"] is False and r["reason"] == "APPROVAL_BINDING_MISMATCH", r


def test_reauth_denied_not_consumed() -> None:
    db, pid, req_id, digests = _setup()
    _approve(db, pid, req_id)
    r = _consume(db, pid, req_id, digests, _alt_scopes())
    assert r["dispatched"] is False and r["reason"] == "REAUTH_DENIED", r