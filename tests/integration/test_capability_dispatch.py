"""tool 派发（Gateway：授权→Intent→执行→Receipt）：真实 PG。"""
from __future__ import annotations

import uuid as _uuid

from sqlalchemy import select

from fastapi.testclient import TestClient

from ai_native.bootstrap.db import SessionLocal, project_context
from ai_native.entrypoints.api import app
from ai_native.modules.capability_gateway.adapters.orm import InvocationIntent, InvocationReceipt
from ai_native.modules.capability_gateway.application.dispatch import dispatch_capability
from ai_native.modules.workflow_runtime.adapters.orm import Run
from ai_native.shared_kernel.ids import uuid7

VALID = {
    "schema_version": "1.0", "workflow_key": "software_factory", "name": "d",
    "input_contract_ref": "text.input@1", "output_contract_ref": "text.output@1",
    "entry_node_key": "n1", "output_node_keys": ["n2"],
    "nodes": [
        {"node_key": "n1", "name": "s", "kind": "transform", "region": "FIXED_CONTROL", "role_ref": "planner", "input_contract_ref": "text.input@1", "output_contract_ref": "c@1", "activation_mode": "ALL_INBOUND", "transform_key": "input.normalize"},
        {"node_key": "n2", "name": "v", "kind": "agent", "region": "FIXED_CONTROL", "role_ref": "validator", "input_contract_ref": "c@1", "output_contract_ref": "text.output@1", "activation_mode": "ALL_INBOUND"},
    ],
    "edges": [{"edge_key": "e1", "from": "n1", "to": "n2"}],
}


def _setup():
    c = TestClient(app)
    pid = c.post("/api/v1/projects", json={"name": f"td-{_uuid.uuid4().hex[:6]}"}).json()["id"]
    wid = c.post(f"/api/v1/projects/{pid}/workflows", json={"template_key": "software_factory", "title": "d"}).json()["workflow_id"]
    c.put(f"/api/v1/projects/{pid}/workflows/{wid}/draft", json={"definition": VALID})
    vid = c.post(f"/api/v1/projects/{pid}/workflows/{wid}/publish").json()["workflow_version_id"]
    rid = c.post(f"/api/v1/projects/{pid}/workflow-versions/{vid}/runs").json()["run_id"]
    db = SessionLocal()
    return db, _uuid.UUID(pid), _uuid.UUID(rid)


_BINDING = {"tool_key": "text.uppercase", "capability_key": "text.transform", "tool_schema_digest": "sha256:" + "0" * 64}


def test_dispatch_records_intent_and_receipt() -> None:
    from ai_native.modules.workflow_runtime.adapters.orm import NodeAttempt

    db, pid, rid = _setup()
    project_context(db, pid)
    run = db.get(Run, rid)
    na = NodeAttempt(id=uuid7(), project_id=pid, run_id=rid, node_key="t", task_id="t", role_ref="engineer",
                     attempt_no=1, rework_round=0, state="RUNNING", fencing_token=1, state_version=0)
    db.add(na)
    db.flush()
    r = dispatch_capability(db, project_id=pid, run_id=rid, node_attempt_id=na.id, tool_binding=_BINDING, input_data={"text": "hello"})
    assert r["dispatched"] is True and r["result"]["uppercased"] == "HELLO"
    project_context(db, pid)
    intents = list(db.scalars(select(InvocationIntent).where(InvocationIntent.project_id == pid)))
    receipts = list(db.scalars(select(InvocationReceipt).where(InvocationReceipt.project_id == pid)))
    assert len(intents) == 1 and intents[0].status == "SUCCEEDED"
    assert len(receipts) == 1 and receipts[0].outcome == "SUCCEEDED"


def test_dispatch_unknown_tool_denied() -> None:
    from ai_native.modules.workflow_runtime.adapters.orm import NodeAttempt

    db, pid, rid = _setup()
    project_context(db, pid)
    na = NodeAttempt(id=uuid7(), project_id=pid, run_id=rid, node_key="t", task_id="t", role_ref="engineer",
                     attempt_no=1, rework_round=0, state="RUNNING", fencing_token=1, state_version=0)
    db.add(na)
    db.flush()
    r = dispatch_capability(db, project_id=pid, run_id=rid, node_attempt_id=na.id,
                            tool_binding={"tool_key": "nope", "capability_key": "x", "tool_schema_digest": "sha256:" + "0" * 64},
                            input_data={"x": 1})
    assert r["dispatched"] is False and r["reason"] == "TOOL_NOT_REGISTERED"