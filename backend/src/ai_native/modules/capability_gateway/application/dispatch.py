"""tool 节点经 Gateway 派发（09 主链）：授权(PDP) → Intent → 执行 → Receipt。

副作用唯一入口：先持久化 InvocationIntent 才执行；确定性能力来自 runtime/capabilities。
本模块不 commit，由调用方在同一事务提交。
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ai_native.modules.capability_gateway.adapters.orm import InvocationIntent, InvocationReceipt
from ai_native.modules.capability_gateway.domain.pdp import Effect, decide
from ai_native.modules.capability_gateway.domain.scopes import ResourceScope
from ai_native.runtime.capabilities import TOOL_REGISTRY
from ai_native.shared_kernel.ids import uuid7
from ai_native.shared_kernel.jcs import jcs_digest


def dispatch_capability(
    db: Session,
    *,
    project_id,
    run_id,
    node_attempt_id,
    tool_binding: dict,
    input_data: dict,
    fencing_token: int = 1,
    member: bool = True,
) -> dict:
    """授权 → Intent → 执行 → Receipt。任一拒绝不执行；UNKNOWN 不自动重发（此处 READ_ONLY）。"""
    tool_key = tool_binding["tool_key"]
    fn = TOOL_REGISTRY.get(tool_key)
    if fn is None:
        return {"dispatched": False, "reason": "TOOL_NOT_REGISTERED"}

    # 1. 授权（PDP 失败关闭）：候选 = 该 tool 的 TOOL_RESOURCE scope；层 = 节点声明（同一能力）
    scope = ResourceScope(
        "TOOL_RESOURCE", frozenset({"execute"}), tool_key=tool_key,
        capability_key=tool_binding["capability_key"], tool_schema_digest=tool_binding["tool_schema_digest"],
        resource_keys=frozenset({"*"}),
    )
    layers = dict(project_scopes=[scope], role_scopes=[scope], node_scopes=[scope],
                  plan_scopes=[scope], skill_scopes=[scope], tool_scopes=[scope], runtime_scopes=[scope])
    decision = decide(member=member, candidate_scopes=[scope], risk_level="LOW", **layers)
    if decision.effect != Effect.ALLOW:
        return {"dispatched": False, "reason": "AUTHORIZE_DENIED", "decision": decision.to_dict()}

    # 2. Intent 先于派发（COMMITTED）
    intent = InvocationIntent(
        id=uuid7(), project_id=project_id, run_id=run_id, node_attempt_id=node_attempt_id,
        action_id=uuid7(), schema_digest=tool_binding.get("tool_schema_digest", "sha256:" + "0" * 64),
        args_digest=jcs_digest(input_data), resources_digest=jcs_digest(scope.to_dict()),
        idempotency_class="READ_ONLY", fencing_token=fencing_token, status="COMMITTED",
    )
    db.add(intent)
    db.flush()

    # 3. 执行（确定性能力）
    result = fn(input_data)
    intent.status = "SUCCEEDED"

    # 4. Receipt
    db.add(InvocationReceipt(
        id=uuid7(), project_id=project_id, invocation_intent_id=intent.id,
        receipt_seq=1, outcome="SUCCEEDED", result_digest=jcs_digest(result),
    ))
    db.flush()
    return {"dispatched": True, "intent_id": str(intent.id), "result": result, "outcome": "SUCCEEDED"}