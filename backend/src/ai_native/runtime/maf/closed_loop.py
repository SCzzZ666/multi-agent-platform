"""单条真实闭环：planner → 确定性计划校验 → 条件路由 → 专业执行 → 独立 validator → Artifact。

对应 06 基线流程 D/F 与 12 基线第 1 周最小闭环。真实语义：
- planner 用真实模型（DashScope 经统一端口）提出一个专业执行节点；
- 计划校验 Transform 是确定性代码（不调模型），校验「固定治理骨架 + 专业扩展」；
- 计划路由是 MAF 条件边（VALID→专业区 / 否则→REJECT），模型不得自由路由；
- engineer / validator 用真实模型；产出经 ArtifactStore 落盘、以 ArtifactRef 交接。

本模块必须在 runtime/maf（全仓唯一可 import MAF 处）。
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Never

from agent_framework import Executor, WorkflowBuilder, WorkflowContext, handler

from ai_native.bootstrap.config import Settings
from ai_native.modules.artifacts_evidence.adapters.local import LocalContentAddressedStore
from ai_native.providers.dashscope import DashScopeProvider
from ai_native.providers.ports import ModelRequest
from ai_native.runtime.conditions import REJECT, plan_route
from ai_native.runtime.envelopes import ArtifactRef
from ai_native.runtime.plan_validator import validate_plan
from ai_native.runtime.plans import Plan, PlanEdge, PlanNode, PlanVerdict

# ---- 流内消息 ----
@dataclass(frozen=True)
class ProposalMsg:
    node_key: str
    kind: str
    role_ref: str
    objective: str
    parse_error: str | None = None


@dataclass(frozen=True)
class RouteMsg:
    verdict: str  # VALID / INVALID / NEEDS_INPUT
    objective: str
    diagnostics: tuple
    plan_ref: ArtifactRef | None


@dataclass(frozen=True)
class DeliverableMsg:
    text: str
    ref: ArtifactRef


@dataclass(frozen=True)
class VerdictMsg:
    decision: str
    reason: str
    deliverable_ref: ArtifactRef


# ---- 全局装配（每进程一次）----
_SETTINGS = Settings.load()
_PROVIDER = DashScopeProvider(api_key=_SETTINGS.dashscope_api_key, base_url=_SETTINGS.dashscope_base_url)
_STORE = LocalContentAddressedStore(_SETTINGS.artifact_store_dir)


async def _ask(system: str, user: str, max_tokens: int = 600) -> str:
    req = ModelRequest(
        model="qwen-plus",
        messages=(("system", system), ("user", user)),
        max_tokens=max_tokens,
    )
    resp = await _PROVIDER.complete(req)
    return resp.content


def _parse_json(text: str) -> dict | None:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1]
        t = t.rsplit("```", 1)[0].strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        return None


def _combined_plan(proposal: ProposalMsg) -> tuple[Plan, str]:
    """固定治理骨架 + 专业扩展，组合成待校验计划。"""
    if proposal.parse_error:
        return (_skeleton_plan(), "PROPOSAL_PARSE_ERROR")
    proposed = PlanNode(
        node_key=proposal.node_key, kind=proposal.kind, role_ref=proposal.role_ref,
        region="PROFESSIONAL", fixed=False,
    )
    nodes = _SKELETON_NODES + (proposed,)
    # 把专业节点插入到计划路由(r04)与独立质量门(val05)之间
    edges = tuple(e for e in _SKELETON_EDGES if not (e.source == "r04" and e.target == "val05"))
    edges = edges + (PlanEdge("r04", proposal.node_key), PlanEdge(proposal.node_key, "val05"))
    plan = Plan(
        workflow_key="software_factory", entry_node_key="n01", output_node_keys=("val05",),
        nodes=nodes, edges=edges, max_nodes=27,
    )
    return plan, ""


_SKELETON_NODES = (
    PlanNode("n01", "transform", "planner", "FIXED_CONTROL", fixed=True),
    PlanNode("p02", "agent", "planner", "FIXED_CONTROL", fixed=True),
    PlanNode("v03", "transform", "planner", "FIXED_CONTROL", fixed=True),
    PlanNode("r04", "condition", "planner", "FIXED_CONTROL", fixed=True),
    PlanNode("val05", "agent", "validator", "FIXED_CONTROL", fixed=True),
)
_SKELETON_EDGES = (
    PlanEdge("n01", "p02"), PlanEdge("p02", "v03"), PlanEdge("v03", "r04"), PlanEdge("r04", "val05"),
)


def _skeleton_plan() -> Plan:
    return Plan(
        workflow_key="software_factory", entry_node_key="n01", output_node_keys=("val05",),
        nodes=_SKELETON_NODES, edges=_SKELETON_EDGES, max_nodes=27,
    )


# ---- MAF Executors ----
class NormalizeExecutor(Executor):
    @handler
    async def process(self, text: str, ctx: WorkflowContext[str]) -> None:
        await ctx.send_message(text.strip())


class PlannerExecutor(Executor):
    @handler
    async def process(self, text: str, ctx: WorkflowContext[ProposalMsg]) -> None:
        sys = (
            "你是规划者(planner)。只输出一个 JSON 对象，表示新增的一个专业执行节点，字段严格为："
            '{"node_key":"sf_implement_backend","kind":"agent","role_ref":"engineer","objective":"..."}。'
            "不要输出任何 JSON 之外的文字。"
        )
        raw = await _ask(sys, f"目标：{text}\n请提出一个专业执行节点。")
        data = _parse_json(raw)
        if data is None:
            await ctx.send_message(ProposalMsg("", "agent", "engineer", text, parse_error="PROPOSAL_PARSE_ERROR"))
            return
        await ctx.send_message(ProposalMsg(
            node_key=str(data.get("node_key", "")), kind=str(data.get("kind", "agent")),
            role_ref=str(data.get("role_ref", "engineer")), objective=str(data.get("objective", text)),
        ))


class ValidatePlanExecutor(Executor):
    @handler
    async def process(self, proposal: ProposalMsg, ctx: WorkflowContext[RouteMsg]) -> None:
        plan, parse_error = _combined_plan(proposal)
        result = validate_plan(plan)
        verdict = result.verdict.value
        if parse_error:
            verdict = PlanVerdict.INVALID.value
        # 计划作为不可变制品落盘（ArtifactRef 交接）
        plan_bytes = json.dumps(plan, ensure_ascii=False, default=str).encode("utf-8")
        plan_ref = _STORE.put(plan_bytes, "application/json", artifact_id=f"plan:{plan.workflow_key}")
        route = plan_route(PlanVerdict(verdict))
        await ctx.send_message(RouteMsg(
            verdict=verdict, objective=proposal.objective,
            diagnostics=result.diagnostics, plan_ref=plan_ref,
        ))
        print(f"[validate] verdict={verdict} route={route} diagnostics={len(result.diagnostics)}")


class EngineerExecutor(Executor):
    @handler
    async def process(self, route: RouteMsg, ctx: WorkflowContext[DeliverableMsg]) -> None:
        text = await _ask(
            "你是工程师(engineer)，在隔离副本实现，不直接回写宿主。",
            f"实现目标：{route.objective}。输出一段交付说明（Markdown）。",
        )
        ref = _STORE.put(text.encode("utf-8"), "text/markdown")
        await ctx.send_message(DeliverableMsg(text=text, ref=ref))


class ValidatorExecutor(Executor):
    @handler
    async def process(self, deliverable: DeliverableMsg, ctx: WorkflowContext[VerdictMsg]) -> None:
        answer = await _ask(
            "你是独立验证者(validator)。只输出一行结论：PASS 或 REWORK（附一句话理由）。",
            f"交付物：\n{deliverable.text[:1500]}",
        )
        decision = "REWORK" if "REWORK" in answer.upper() else "PASS"
        await ctx.send_message(VerdictMsg(decision=decision, reason=answer.strip(), deliverable_ref=deliverable.ref))


class FinalExecutor(Executor):
    @handler
    async def process(self, verdict: VerdictMsg, ctx: WorkflowContext[Never, dict]) -> None:
        summary = {
            "decision": verdict.decision,
            "reason": verdict.reason,
            "deliverable_ref": {
                "artifact_id": verdict.deliverable_ref.artifact_id,
                "sha256": verdict.deliverable_ref.sha256,
                "media_type": verdict.deliverable_ref.media_type,
                "size": verdict.deliverable_ref.size,
            },
        }
        _STORE.put(json.dumps(summary, ensure_ascii=False).encode(), "application/json")
        await ctx.yield_output(summary)


class RejectExecutor(Executor):
    @handler
    async def process(self, route: RouteMsg, ctx: WorkflowContext[Never, dict]) -> None:
        summary = {
            "route": REJECT,
            "verdict": route.verdict,
            "objective": route.objective,
            "diagnostics": [d.code for d in route.diagnostics[:5]],
        }
        _STORE.put(json.dumps(summary, ensure_ascii=False).encode(), "application/json")
        await ctx.yield_output(summary)


def _build_workflow():
    n = NormalizeExecutor(id="normalize")
    p = PlannerExecutor(id="planner")
    v = ValidatePlanExecutor(id="validate_plan")
    e = EngineerExecutor(id="engineer")
    val = ValidatorExecutor(id="validator")
    f = FinalExecutor(id="final")
    r = RejectExecutor(id="reject")

    def valid(route: RouteMsg) -> bool:
        return route.verdict == PlanVerdict.VALID.value

    def not_valid(route: RouteMsg) -> bool:
        return route.verdict != PlanVerdict.VALID.value

    return (
        WorkflowBuilder(start_executor=n)
        .add_edge(n, p)
        .add_edge(p, v)
        .add_edge(v, e, condition=valid)
        .add_edge(v, r, condition=not_valid)
        .add_edge(e, val)
        .add_edge(val, f)
        .build()
    )


async def run_once(message: str) -> dict:
    result = await _build_workflow().run(message)
    outs = result.get_outputs()
    print(f"[run] final_state={result.get_final_state()} outputs={len(outs)}")
    for o in outs:
        print("  ->", json.dumps(o, ensure_ascii=False, default=str)[:400])
        print()
    return list(outs)


async def main() -> None:
    print("=== 正常路径（合法专业节点） ===")
    await run_once("开发一个能查询本地天气的 Web 页面")
    print("=== 对抗路径（模型提出非法角色） ===")
    # 直接以非法提案驱动校验+路由，证明确定性与路由不放行
    bad = ProposalMsg("sf_implement_backend", "agent", "commander", "目标")
    plan, _ = _combined_plan(bad)
    res = validate_plan(plan)
    print(f"[deterministic] 非法角色 commander -> verdict={res.verdict.value} codes={[d.code for d in res.diagnostics]}")


if __name__ == "__main__":
    asyncio.run(main())