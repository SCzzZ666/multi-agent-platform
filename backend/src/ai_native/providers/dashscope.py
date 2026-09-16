"""阿里云百炼（DashScope）适配器 —— OpenAI 兼容端点，走统一归一化实现。"""
from __future__ import annotations

from ai_native.providers.openai_compat import OpenAICompatProvider


class DashScopeProvider(OpenAICompatProvider):
    def __init__(self, api_key: str, base_url: str) -> None:
        super().__init__(name="dashscope", api_key=api_key, base_url=base_url)