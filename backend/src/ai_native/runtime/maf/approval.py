"""approval 节点（六类之一）→ MAF HITL 映射。

approval 节点执行：request_info 发起人工请求并暂停；@response_handler 收到 APPROVE/REJECT 后继续。
resume 用 `run(responses={request_id: ApprovalResponse})`（responses-only replay）。
本模块全仓唯一可 import MAF。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from agent_framework import Executor, WorkflowContext, handler, response_handler


@dataclass(frozen=True)
class ApprovalRequestData:
    node_key: str
    approval_type: str
    payload: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ApprovalResponse:
    approved: bool
    reason: str = ""


class ApprovalExecutor(Executor):
    def __init__(self, node_key: str, approval_type: str) -> None:
        super().__init__(id=node_key)
        self._node_key = node_key
        self._approval_type = approval_type
        self.request_id = f"approval:{node_key}"

    @handler
    async def process(self, data: dict, ctx: WorkflowContext[dict]) -> None:
        await ctx.request_info(
            ApprovalRequestData(node_key=self._node_key, approval_type=self._approval_type, payload=data),
            ApprovalResponse,
            request_id=self.request_id,
        )

    @response_handler(request=ApprovalRequestData, response=ApprovalResponse, output=dict)
    async def handle_response(self, original_request, response, ctx) -> None:
        out = {**original_request.payload, "approved": response.approved, "reason": response.reason}
        await ctx.send_message(out)