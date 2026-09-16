"""通用 OpenAI 兼容 Provider（chat/completions）。

百炼/DeepSeek/Kimi 三家均走 OpenAI 兼容端点，用同一归一化实现；模型经 ModelRequest.model 指定。
只依赖 httpx，不引入供应商 SDK；供应商异常在此转换为平台稳定 ProviderError（不含明文凭据）。
"""
from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from ai_native.providers.ports import ModelRequest, ModelResponse, ModelUsage


class ProviderError(RuntimeError):
    """供应商调用失败（稳定载体，不含明文凭据）。"""


class OpenAICompatProvider:
    def __init__(self, name: str, api_key: str, base_url: str) -> None:
        self.name = name
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    def _payload(self, req: ModelRequest, stream: bool) -> dict:
        payload: dict = {
            "model": req.model,
            "messages": [{"role": r, "content": c} for r, c in req.messages],
            "max_tokens": req.max_tokens,
            "stream": stream,
        }
        if req.temperature is not None:
            payload["temperature"] = req.temperature
        return payload

    def _to_response(self, data: dict, req: ModelRequest) -> ModelResponse:
        choice = data["choices"][0]
        usage = data.get("usage") or {}
        return ModelResponse(
            provider=self.name,
            model=data.get("model") or req.model,
            content=(choice["message"].get("content") or "") if "message" in choice else "",
            usage=ModelUsage(
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
            ),
            finish_reason=choice.get("finish_reason"),
        )

    async def complete(self, req: ModelRequest) -> ModelResponse:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json=self._payload(req, stream=False),
            )
            if resp.status_code != 200:
                raise ProviderError(f"{self.name} http {resp.status_code}: {resp.text[:300]}")
            return self._to_response(resp.json(), req)

    async def stream(self, req: ModelRequest) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json=self._payload(req, stream=True),
            ) as resp:
                if resp.status_code != 200:
                    body = (await resp.aread()).decode(errors="replace")
                    raise ProviderError(f"{self.name} http {resp.status_code}: {body[:300]}")
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    chunk = line[5:].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        obj = json.loads(chunk)
                    except json.JSONDecodeError:
                        continue
                    delta = obj.get("choices", [{}])[0].get("delta", {}).get("content")
                    if delta:
                        yield delta