"""能力审批原子消费 + InvocationIntent 落库（09 主链）。

消费与建 Intent 同一短事务：锁审批行 → 校 fencing → 校状态/摘要 → 查幂等 → 扣 used_count →
写 Intent + 审计 + 事件/outbox → 一起提交。失败绝不派发；派发前重跑完整鉴权（PDP，含主体-项目关系）。
本模块不 commit，由调用方在同一事务提交。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_native.modules.capability_gateway.adapters.orm import ApprovalDecision, ApprovalRequest, InvocationIntent
from ai_native.modules.capability_gateway.domain.pdp import Effect, decide
from ai_native.modules.operations_events.application.service import append_audit, emit_event
from ai_native.modules.workflow_runtime.adapters.orm import Run, RunLease
from ai_native.shared_kernel.ids import uuid7
from ai_native.shared_kernel.jcs import jcs_digest

# 契约层 InvocationStatus.INTENT_RECORDED ↔ DB 层 'COMMITTED'
INTENT_RECORDED_DB = "COMMITTED"


def request_approval(
    db: Session, *, project_id, run_id, node_attempt_id, action_id,
    workflow_digest, schema_digest, args_digest, resources_digest, risk,
    max_uses: int = 1, ttl_minutes: int = 30,
) -> ApprovalRequest:
    req = ApprovalRequest(
        id=uuid7(), project_id=project_id, run_id=run_id, node_attempt_id=node_attempt_id,
        action_id=action_id, workflow_digest=workflow_digest, schema_digest=schema_digest,
        args_digest=args_digest, resources_digest=resources_digest, risk=risk,
        status="PENDING", expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
        max_uses=max_uses, used_count=0,
    )
    db.add(req)
    db.flush()
    return req


def record_decision(
    db: Session, *, approval_request_id, decided_by, decision: str, idempotency_key: str, reason: str = "",
) -> ApprovalDecision:
    req = db.get(ApprovalRequest, approval_request_id)
    if req is None:
        raise ValueError("审批请求不存在")
    if req.status != "PENDING":
        raise ValueError(f"审批已处理: {req.status}")
    request_digest = jcs_digest(
        {"approval_request_id": str(req.id), "action_id": str(req.action_id),
         "args_digest": req.args_digest, "resources_digest": req.resources_digest}
    )
    dec = ApprovalDecision(
        id=uuid7(), project_id=req.project_id, approval_request_id=req.id,
        decision=decision, decided_by=decided_by, idempotency_key=idempotency_key,
        request_digest=request_digest, reason=reason,
    )
    db.add(dec)
    req.status = "APPROVED" if decision == "APPROVE" else "REJECTED"
    if decision == "REVOKE":
        req.revoked_at = datetime.now(timezone.utc)
    db.flush()
    return dec


def consume_approval_and_record_intent(
    db: Session,
    *,
    approval_request_id,
    binding_digests: dict,
    layers: dict,
    candidate_scopes,
    risk_level: str,
    idempotency_class: str,
    fencing_token: int,
    member: bool,
) -> dict:
    """原子消费：返回 {'dispatched': bool, 'intent_id'?, 'reason'?}。失败不得发生派发副作用。

    派发前重跑完整鉴权：主体-项目关系（member，不写死）+ 九层单调交集（PDP）。
    """
    req = db.scalar(
        select(ApprovalRequest)
        .where(ApprovalRequest.id == approval_request_id)
        .with_for_update()
    )
    if req is None:
        return {"dispatched": False, "reason": "NOT_FOUND"}
    # fencing 校验：丢租约 Worker 不得提交新动作（开工地图 §5.3）
    lease = db.scalar(select(RunLease).where(RunLease.run_id == req.run_id))
    if lease is None or lease.fencing_token != fencing_token:
        return {"dispatched": False, "reason": "STALE_FENCING_TOKEN"}
    # 幂等优先：同 (project, action) 已建 Intent 不重复消费（无论审批是否已 CONSUMED）
    existing = db.scalar(
        select(InvocationIntent).where(
            InvocationIntent.project_id == req.project_id,
            InvocationIntent.action_id == req.action_id,
        )
    )
    if existing is not None:
        return {"dispatched": False, "intent_id": str(existing.id), "reason": "IDEMPOTENT_ALREADY_RECORDED"}
    if req.status != "APPROVED":
        return {"dispatched": False, "reason": "APPROVAL_NOT_APPROVED"}
    now = datetime.now(timezone.utc)
    if req.revoked_at is not None or req.expires_at < now:
        return {"dispatched": False, "reason": "APPROVAL_EXPIRED_OR_REVOKED"}
    if req.used_count >= req.max_uses:
        return {"dispatched": False, "reason": "APPROVAL_EXHAUSTED"}
    # 摘要一致（服务端与审批时一致才有效）
    if (
        req.args_digest != binding_digests["args_digest"]
        or req.resources_digest != binding_digests["resource_scope_digest"]
        or req.schema_digest != binding_digests["tool_schema_digest"]
    ):
        return {"dispatched": False, "reason": "APPROVAL_BINDING_MISMATCH"}
    # 派发前重跑完整鉴权（PDP 失败关闭；Approval 只对已在交集内的动作加确认；member 不写死）
    decision = decide(member=member, candidate_scopes=candidate_scopes, risk_level=risk_level, has_valid_approval=True, **layers)
    if decision.effect != Effect.ALLOW:
        return {"dispatched": False, "reason": "REAUTH_DENIED", "decision": decision.to_dict()}

    req.used_count += 1
    if req.used_count >= req.max_uses:
        req.status = "CONSUMED"
    intent = InvocationIntent(
        id=uuid7(), project_id=req.project_id, run_id=req.run_id, node_attempt_id=req.node_attempt_id,
        approval_request_id=req.id, action_id=req.action_id,
        tool_schema_version_id=req.tool_schema_version_id,
        schema_digest=req.schema_digest, args_digest=req.args_digest, resources_digest=req.resources_digest,
        idempotency_class=idempotency_class, fencing_token=fencing_token, status=INTENT_RECORDED_DB,
    )
    db.add(intent)
    db.flush()
    # 审计 + 事件/outbox 与 Intent 同事务提交（09 §9.5 第⑥步；可追溯不中断）
    append_audit(
        db, project_id=req.project_id, event_type="INVOCATION_INTENT_RECORDED",
        actor={"kind": "gateway"}, subject={"intent_id": str(intent.id), "action_id": str(intent.action_id)},
        payload={"status": intent.status, "idempotency_class": intent.idempotency_class},
    )
    run = db.get(Run, req.run_id)
    if run is not None:
        seq = int(run.event_seq or 0) + 1
        run.event_seq = seq
        emit_event(
            db, run_id=run.id, project_id=req.project_id, event_seq=seq,
            state_version=run.state_version or 0, event_type="INVOCATION_INTENT_RECORDED",
            payload={"intent_id": str(intent.id), "action_id": str(intent.action_id)},
        )
    return {"dispatched": True, "intent_id": str(intent.id), "status": INTENT_RECORDED_DB}