"""Credential Broker 晚绑定测试：禁入 argv、失败关闭、脱敏。"""
from __future__ import annotations

import pytest

from ai_native.modules.capability_gateway.application.credential_broker import DevCredentialBroker
from ai_native.modules.capability_gateway.domain.credential import (
    CredentialResolutionError,
    CredentialSlot,
    redact,
)

_REG = {"credential_ref:ci": {"purpose": "ci", "env_name": "CI_TOKEN", "secret": "s3cret-value"}}


def test_resolve_env_slot_only_no_argv() -> None:
    broker = DevCredentialBroker(_REG)
    b = broker.resolve("credential_ref:ci", frozenset({"ci"}))
    assert b.slot == CredentialSlot.ENV and b.slot_name == "CI_TOKEN"
    assert b.secret == "s3cret-value"
    # 绝不产生 ARGV 槽
    assert {s.value for s in CredentialSlot} == {"ENV", "FILE", "STDIN", "HANDLE"}


def test_unknown_ref_fails_closed() -> None:
    with pytest.raises(CredentialResolutionError) as e:
        DevCredentialBroker({}).resolve("credential_ref:nope", frozenset({"ci"}))
    assert e.value.code == "CREDENTIAL_NOT_FOUND"


def test_purpose_denied_fails_closed() -> None:
    broker = DevCredentialBroker(_REG)
    with pytest.raises(CredentialResolutionError) as e:
        broker.resolve("credential_ref:ci", frozenset({"other"}))
    assert e.value.code == "CREDENTIAL_PURPOSE_DENIED"


def test_binding_repr_and_redacted_do_not_leak_secret() -> None:
    b = DevCredentialBroker(_REG).resolve("credential_ref:ci", frozenset({"ci"}))
    assert "s3cret-value" not in repr(b)
    assert "s3cret-value" not in b.redacted()


def test_redact_masks_known_secrets() -> None:
    assert redact("token s3cret-value here", {"s3cret-value"}) == "token *** here"
    assert redact("无秘密", {"s3cret-value"}) == "无秘密"