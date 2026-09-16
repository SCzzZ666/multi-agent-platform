"""MAF + 真实模型双 Agent 冒烟：planner → validator（P5 最小闭环的模型侧）。

用 MAF 的 OpenAIChatCompletionClient 指向百炼 OpenAI 兼容端点（chat/completions），
两个真实 LLM Agent 经 AgentExecutor 串联，由 MAF 负责 Edge 激活与消息传递 ——
证明「真实 MAF + 真实模型 + 多 Agent」端到端可运行。

本模块必须在 runtime/maf（全仓唯一可 import MAF 处，架构守护测试强制）。
模型 key 只从 .env 经 Settings 解析，不写日志、不入库。
"""
from __future__ import annotations

import asyncio

from agent_framework import Agent, AgentExecutor, WorkflowBuilder
from agent_framework.openai import OpenAIChatCompletionClient

from ai_native.bootstrap.config import Settings


def _chat_client(s: Settings) -> OpenAIChatCompletionClient:
    return OpenAIChatCompletionClient(
        model="qwen-plus",
        api_key=s.dashscope_api_key,
        base_url=s.dashscope_base_url,
    )


async def build_and_run(message: str) -> None:
    s = Settings.load()
    client = _chat_client(s)

    planner = Agent(
        client,
        name="planner",
        instructions=(
            "你是规划者(planner)。把用户目标拆成一个不超过 3 步的执行计划，"
            "用中文分点输出，只输出计划本身，不要解释。"
        ),
    )
    validator = Agent(
        client,
        name="validator",
        instructions=(
            "你是独立验证者(validator)。检查计划是否合理、完整、无关键遗漏，"
            "只输出一行结论：PASS 或 REWORK（附一句话理由）。"
        ),
    )

    planner_exec = AgentExecutor(agent=planner, id="planner")
    validator_exec = AgentExecutor(agent=validator, id="validator")

    workflow = (
        WorkflowBuilder(start_executor=planner_exec)
        .add_edge(planner_exec, validator_exec)
        .build()
    )

    result = await workflow.run(message)
    print("final_state:", result.get_final_state())
    print("outputs:")
    for out in result.get_outputs():
        print("---")
        print(str(out)[:600])


async def main() -> None:
    await build_and_run("开发一个能查询本地天气的 Web 页面")


if __name__ == "__main__":
    asyncio.run(main())