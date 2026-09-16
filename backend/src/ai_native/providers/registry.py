"""模型供应商注册表（三家经统一端口归一化；D12-05：模型网关管选模/路由/归一化）。

每家模型默认：
- dashscope → qwen-plus
- deepseek  → deepseek-chat
- kimi      → moonshot-v1-8k
"""
from __future__ import annotations

from ai_native.bootstrap.config import Settings
from ai_native.providers.openai_compat import OpenAICompatProvider

DEFAULT_MODEL = {
    "dashscope": "qwen-plus",
    "deepseek": "deepseek-chat",
    "kimi": "kimi-k3",
}


def build_providers(s: Settings) -> dict[str, OpenAICompatProvider]:
    out: dict[str, OpenAICompatProvider] = {}
    if s.dashscope_api_key:
        out["dashscope"] = OpenAICompatProvider("dashscope", s.dashscope_api_key, s.dashscope_base_url)
    if s.deepseek_api_key:
        out["deepseek"] = OpenAICompatProvider("deepseek", s.deepseek_api_key, s.deepseek_base_url)
    if s.kimi_api_key:
        out["kimi"] = OpenAICompatProvider("kimi", s.kimi_api_key, s.kimi_base_url)
    return out


def model_for(provider_name: str) -> str:
    return DEFAULT_MODEL[provider_name]