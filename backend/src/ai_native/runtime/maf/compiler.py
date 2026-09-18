"""把 08 WorkflowDefinition 确定性编译为 MAF Workflow（六类节点 → Executor 映射）。

数据驱动：不再手写图；agent 节点用统一模型端口真实调用，transform/condition 用确定性注册表，
approval(HITL) 与 skill/tool 待后续接入时在此扩展。本模块全仓唯一可 import MAF。
"""
from __future__ import annotations

import asyncio
from typing import Never

from agent_framework import Executor, WorkflowBuilder, WorkflowContext, handler

from ai_native.providers.openai_compat import OpenAICompatProvider
from ai_native.providers.ports import ModelRequest
from ai_native.runtime.maf.approval import ApprovalExecutor
from ai_native.runtime.transforms import CONDITION_REGISTRY, TRANSFORM_REGISTRY, role_prompt


class _TransformExecutor(Executor):
    def __init__(self, node_key: str, fn) -> None:
        super().__init__(id=node_key)
        self._node_key = node_key
        self._fn = fn

    @handler
    async def process(self, data: dict, ctx: WorkflowContext[dict]) -> None:
        await ctx.send_message(self._fn(data))


class _AgentExecutor(Executor):
    def __init__(self, node_key: str, role_ref: str, provider: OpenAICompatProvider, model: str) -> None:
        super().__init__(id=node_key)
        self._node_key = node_key
        self._role_ref = role_ref
        self._provider = provider
        self._model = model

    @handler
    async def process(self, data: dict, ctx: WorkflowContext[dict]) -> None:
        prompt = f"{role_prompt(self._role_ref)}\n\n上下文: {str(data)[:2000]}"
        resp = await self._provider.complete(
            ModelRequest(model=self._model, messages=(("user", prompt),), max_tokens=400)
        )
        out = {**data, "last_node": self._node_key, "last_output": resp.content}
        await ctx.send_message(out)


class _YieldExecutor(Executor):
    def __init__(self, node_key: str) -> None:
        super().__init__(id=f"__output__{node_key}")

    @handler
    async def process(self, data: dict, ctx: WorkflowContext[Never, dict]) -> None:
        await ctx.yield_output(data)


class _SkillExecutor(Executor):
    """skill 节点：装载固定 skill_version_id 的指令（编译期解析并绑定，不可变）。"""

    def __init__(self, node_key: str, role_ref: str, provider: OpenAICompatProvider, model: str, skill: dict) -> None:
        super().__init__(id=node_key)
        self._node_key = node_key
        self._role_ref = role_ref
        self._provider = provider
        self._model = model
        self._skill = skill

    @handler
    async def process(self, data: dict, ctx: WorkflowContext[dict]) -> None:
        prompt = (
            f"{role_prompt(self._role_ref)}\n\n"
            f"你要遵循以下已发布 Skill 的指令（固定版本 v{self._skill.get('version_no')}）：\n"
            f"{self._skill.get('instructions', '')}\n\n上下文: {str(data)[:1200]}"
        )
        resp = await self._provider.complete(
            ModelRequest(model=self._model, messages=(("user", prompt),), max_tokens=400)
        )
        await ctx.send_message({**data, "last_node": self._node_key, "skill_used": self._skill.get("name"), "last_output": resp.content})


class _ToolExecutor(Executor):
    """tool 节点：经 Gateway 派发（授权→Intent→执行→Receipt），在 worker 线程执行同步派发。"""

    def __init__(self, node_key: str, tool_binding: dict, tool_dispatcher) -> None:
        super().__init__(id=node_key)
        self._node_key = node_key
        self._binding = tool_binding
        self._dispatcher = tool_dispatcher

    @handler
    async def process(self, data: dict, ctx: WorkflowContext[dict]) -> None:
        result = await asyncio.to_thread(self._dispatcher, self._node_key, self._binding, data)
        await ctx.send_message({
            **data, "last_node": self._node_key,
            "tool_outcome": result.get("outcome"), "tool_result": result.get("result"),
        })


def compile_definition(definition: dict, *, provider: OpenAICompatProvider, model: str, skill_resolver=None, tool_dispatcher=None) -> object:
    nodes = definition["nodes"]
    edges = definition["edges"]
    executors: dict[str, Executor] = {}

    for n in nodes:
        key = n["node_key"]
        kind = n["kind"]
        if kind == "transform":
            fn = TRANSFORM_REGISTRY.get(n.get("transform_key", ""))
            if fn is None:
                raise ValueError(f"未注册的 transform_key: {n.get('transform_key')} (node {key})")
            executors[key] = _TransformExecutor(key, fn)
        elif kind == "agent":
            executors[key] = _AgentExecutor(key, n["role_ref"], provider, model)
        elif kind == "condition":
            cfn = CONDITION_REGISTRY.get(n.get("condition_key", ""))
            if cfn is None:
                raise ValueError(f"未注册的 condition_key: {n.get('condition_key')} (node {key})")
            executors[key] = _TransformExecutor(key, lambda d, f=cfn: {**d, "route": f(d)})
        elif kind == "approval":
            executors[key] = ApprovalExecutor(key, n.get("approval_type", "WORKFLOW"))
        elif kind == "skill":
            sid = n.get("skill_version_id")
            if skill_resolver is None:
                raise ValueError(f"skill 节点需 skill_resolver: {key}")
            skill = skill_resolver(sid)
            if not skill:
                raise ValueError(f"skill_version 不可解析: {sid} (node {key})")
            executors[key] = _SkillExecutor(key, n["role_ref"], provider, model, skill)
        elif kind == "tool":
            if tool_dispatcher is None:
                raise ValueError(f"tool 节点需 tool_dispatcher: {key}")
            executors[key] = _ToolExecutor(key, n.get("tool_binding", {}), tool_dispatcher)
        else:
            raise ValueError(f"{key}: 未知节点类型 {kind}")

    if definition["entry_node_key"] not in executors:
        raise ValueError(f"入口节点不存在: {definition['entry_node_key']}")
    builder = WorkflowBuilder(start_executor=executors[definition["entry_node_key"]])

    for e in edges:
        src = executors[e["from"]]
        tgt = executors[e["to"]]
        route = e.get("route")
        if route:
            builder.add_edge(src, tgt, condition=lambda d, r=route: d.get("route") == r)
        else:
            builder.add_edge(src, tgt)

    for ok in definition["output_node_keys"]:
        builder.add_edge(executors[ok], _YieldExecutor(ok))

    return builder.build()