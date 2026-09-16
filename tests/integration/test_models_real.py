"""三家模型真实调用回归（QA 卡 1.5 补强：从「手跑一次」到「可自动化复现」）。

真实口径：无 key 时 skip；有 key 时真实调三家（dashscope/deepseek/kimi），
断言非空内容 + usage 已知，并把证据按 D12-11 §8.2 字段落 JSON（.data/evidence/，gitignore）。
默认被 -m 'not real_model' 排除（保持日常套件快）；证据生成用 `pytest -m real_model`。
"""
from __future__ import annotations

import asyncio
import datetime
import json
import pathlib
import platform
import sys

import pytest

from ai_native.bootstrap.config import Settings
from ai_native.providers.ports import ModelRequest
from ai_native.providers.registry import build_providers, model_for

pytestmark = pytest.mark.real_model

_REQUIRED = {"dashscope", "deepseek", "kimi"}


def _providers():
    return build_providers(Settings.load())


@pytest.mark.skipif(not _REQUIRED.issubset(_providers()), reason="本地缺三家模型 key")
def test_three_providers_real_response_and_usage() -> None:
    providers = _providers()
    assert _REQUIRED.issubset(providers), list(providers)
    evidence: list[dict] = []

    async def drive() -> None:
        for name in sorted(_REQUIRED):
            req = ModelRequest(model=model_for(name), messages=(("user", "只回复两个字: ok"),), max_tokens=256)
            resp = await providers[name].complete(req)
            assert resp.content.strip(), name
            assert resp.usage is not None and resp.usage.total_tokens is not None, name
            evidence.append({
                "provider": name,
                "model": resp.model,
                "finish_reason": resp.finish_reason,
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
                "content_preview": resp.content[:30],
            })

    asyncio.run(drive())

    record = {
        "kind": "model_real_response",
        "env": {"python": sys.version.split()[0], "os": platform.system()},
        "models": evidence,
        "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    out = pathlib.Path(".data/evidence")
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    (out / f"models_{stamp}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")