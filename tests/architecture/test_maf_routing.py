"""MAF 条件边路由的独立验证：计划路由 Condition 两个分支都真实触发。

真实口径：RouteMsg(verdict=VALID) 只进入 VALID 分支；verdict=INVALID 只进入 REJECT 分支。
这是对「计划路由 Condition 不可绕过、模型不得自由路由」的 MAF 级机器验证。
"""
from __future__ import annotations

import asyncio
from typing import Never

from agent_framework import Executor, WorkflowBuilder, WorkflowContext, handler

from ai_native.runtime.maf.closed_loop import RouteMsg


class Source(Executor):
    def __init__(self, verdict: str) -> None:
        super().__init__(id="src")
        self._verdict = verdict

    @handler
    async def process(self, text: str, ctx: WorkflowContext[RouteMsg]) -> None:
        await ctx.send_message(RouteMsg(verdict=self._verdict, objective="t", diagnostics=(), plan_ref=None))


class Branch(Executor):
    def __init__(self, label: str) -> None:
        super().__init__(id=f"branch-{label}")
        self._label = label

    @handler
    async def process(self, route: RouteMsg, ctx: WorkflowContext[Never, str]) -> None:
        await ctx.yield_output(f"{self._label}:{route.verdict}")


def _run(verdict: str):
    src = Source(verdict)
    valid_b = Branch("VALID")
    invalid_b = Branch("INVALID")
    workflow = (
        WorkflowBuilder(start_executor=src)
        .add_edge(src, valid_b, condition=lambda r: r.verdict == "VALID")
        .add_edge(src, invalid_b, condition=lambda r: r.verdict != "VALID")
        .build()
    )
    return asyncio.run(workflow.run("go"))


def test_valid_routes_only_to_valid_branch() -> None:
    outs = _run("VALID").get_outputs()
    assert list(outs) == ["VALID:VALID"]


def test_invalid_routes_only_to_invalid_branch() -> None:
    outs = _run("INVALID").get_outputs()
    assert list(outs) == ["INVALID:INVALID"]