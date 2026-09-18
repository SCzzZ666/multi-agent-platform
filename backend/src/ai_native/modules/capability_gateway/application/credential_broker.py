"""Credential Broker（09 §9.7）：晚绑定、最小范围、最短生命周期、禁入 argv。

- 全链路只流转 credential_ref；
- Intent 提交后、调用前最后时刻解析；
- 默认注入显式环境变量槽（Profile 声明的槽），**绝不给 ARGV**；
- 未知 ref / 用途不允许 → 失败关闭（CredentialResolutionError，不回退明文配置）。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol

from ai_native.bootstrap.config import Settings
from ai_native.modules.capability_gateway.domain.credential import (
    CredentialBinding,
    CredentialResolutionError,
    CredentialSlot,
)


class CredentialBrokerPort(Protocol):
    def resolve(self, credential_ref: str, allowed_purposes: frozenset[str], ttl_seconds: int = 300) -> CredentialBinding: ...


class DevCredentialBroker:
    """开发期 Broker：registry = {credential_ref: {purpose, env_name, secret}}。"""

    def __init__(self, registry: dict) -> None:
        self._registry = registry

    def resolve(self, credential_ref: str, allowed_purposes: frozenset[str], ttl_seconds: int = 300) -> CredentialBinding:
        entry = self._registry.get(credential_ref)
        if entry is None:
            raise CredentialResolutionError("CREDENTIAL_NOT_FOUND", f"未知 credential_ref: {credential_ref}")
        purpose = entry["purpose"]
        if allowed_purposes and purpose not in allowed_purposes:
            raise CredentialResolutionError("CREDENTIAL_PURPOSE_DENIED", f"credential 用途 {purpose} 不在允许集")
        return CredentialBinding(
            credential_ref=credential_ref,
            purpose=purpose,
            slot=CredentialSlot.ENV,
            slot_name=entry["env_name"],
            secret=entry["secret"],
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
        )


def dev_broker_from_settings(s: Settings) -> DevCredentialBroker:
    """把 .env 里的真实供应商凭据注册为 credential_ref（只走引用，正文由 Broker 解析）。"""
    registry: dict[str, dict] = {}
    if s.dashscope_api_key:
        registry["credential_ref:openai-primary"] = {"purpose": "model", "env_name": "OPENAI_API_KEY", "secret": s.dashscope_api_key}
    if s.deepseek_api_key:
        registry["credential_ref:deepseek-primary"] = {"purpose": "model", "env_name": "DEEPSEEK_API_KEY", "secret": s.deepseek_api_key}
    if s.kimi_api_key:
        registry["credential_ref:kimi-primary"] = {"purpose": "model", "env_name": "MOONSHOT_API_KEY", "secret": s.kimi_api_key}
    return DevCredentialBroker(registry)