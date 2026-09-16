"""三家模型默认配置的冻结守卫（D12-05：至少三家真实模型经统一端口接入）。"""
from __future__ import annotations

from ai_native.providers.registry import DEFAULT_MODEL, model_for


def test_three_providers_registered() -> None:
    assert set(DEFAULT_MODEL) == {"dashscope", "deepseek", "kimi"}


def test_default_model_names_pinned() -> None:
    # 这些模型名已实测真实可用；回归不得悄悄改回下线型号（如 moonshot-v1-8k）
    assert DEFAULT_MODEL["dashscope"] == "qwen-plus"
    assert DEFAULT_MODEL["deepseek"] == "deepseek-chat"
    assert DEFAULT_MODEL["kimi"] == "kimi-k3"


def test_model_for() -> None:
    assert model_for("kimi") == "kimi-k3"