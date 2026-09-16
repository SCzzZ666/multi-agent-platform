"""模型供应商统一端口（providers/ 是供应商 SDK 唯一允许位置）。

职责分离（D12-05 / 02 基线）：模型网关管「选模/路由/归一化」，
Capability Gateway 管「Tool/Skill 脚本/MCP/副作用安全」——不是同一套授权。
模型对象、密钥、供应商异常不得泄漏到公共 API / WorkflowDefinition / 普通日志。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Protocol


@dataclass(frozen=True)
class ModelRequest:
    model: str
    messages: tuple[tuple[str, str], ...]  # (role, content)
    max_tokens: int = 2048
    temperature: float | None = None
    stream: bool = False


@dataclass(frozen=True)
class ModelUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

    def is_known(self) -> bool:
        """用量未知时如实标记，不记 0。"""
        return (self.total_tokens is not None) or (
            self.input_tokens is not None and self.output_tokens is not None
        )


@dataclass(frozen=True)
class ModelResponse:
    provider: str
    model: str
    content: str
    usage: ModelUsage | None = None
    finish_reason: str | None = None


class ModelProviderPort(Protocol):
    """统一模型端口。实现位于 providers/，业务层只依赖本端口。"""

    name: str

    async def complete(self, req: ModelRequest) -> ModelResponse: ...

    def stream(self, req: ModelRequest) -> AsyncIterator[str]: ...