"""MAF 1.18.0 最小无环图冒烟：证明 WorkflowBuilder + Executor + Edge + run 真实可跑。

对应 P4 完成条件「真实 MAF 可构建并执行最小无环 Workflow」。
三条确定性 transform 式 Executor 串联（无模型、无副作用），等价于平台六类节点里的
`transform` 语义，用来验证 1.18.0 图式 API 在当前环境真实构建 + 执行 + 产出结果。

本模块必须位于 runtime/maf —— 这是全仓唯一允许 import MAF 的位置（架构守护测试强制）。
MCP / model client 不在此冒烟范围（模型节点需真实凭据，见 providers/）。
"""
from __future__ import annotations

import asyncio
from typing import Never

from agent_framework import Executor, WorkflowBuilder, WorkflowContext, WorkflowRunResult, handler


class NormalizeExecutor(Executor):
    """规范化：去空白 + 大写。"""

    @handler
    async def process(self, text: str, ctx: WorkflowContext[str]) -> None:
        await ctx.send_message(text.strip().upper())


class ReverseExecutor(Executor):
    """反转字符串。"""

    @handler
    async def process(self, text: str, ctx: WorkflowContext[str]) -> None:
        await ctx.send_message(text[::-1])


class TagExecutor(Executor):
    """终节点：产出最终结果。"""

    @handler
    async def process(self, text: str, ctx: WorkflowContext[Never, str]) -> None:
        await ctx.yield_output(f"{text}::DONE")


async def build_and_run(message: str = "  hello maf  ") -> WorkflowRunResult:
    normalize = NormalizeExecutor(id="normalize")
    reverse = ReverseExecutor(id="reverse")
    tag = TagExecutor(id="tag")
    workflow = (
        WorkflowBuilder(start_executor=normalize)
        .add_edge(normalize, reverse)
        .add_edge(reverse, tag)
        .build()
    )
    return await workflow.run(message)


async def main() -> None:
    result = await build_and_run()
    print("final_state:", result.get_final_state())
    print("outputs:    ", result.get_outputs())
    print("intermediate:", result.get_intermediate_outputs())


if __name__ == "__main__":
    asyncio.run(main())