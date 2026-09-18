"""Credential 晚绑定类型（09 §9.7）。

秘密只进显式槽（环境变量 / 短期文件 / stdin / 受控句柄），**绝无 ARGV 槽**。
全部对象 repr/redacted 不泄漏明文。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class CredentialSlot(str, Enum):
    ENV = "ENV"        # 显式环境变量槽
    FILE = "FILE"      # 短期文件槽
    STDIN = "STDIN"    # stdin 槽
    HANDLE = "HANDLE"  # 受控句柄


class CredentialResolutionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class CredentialBinding:
    credential_ref: str
    purpose: str
    slot: CredentialSlot
    slot_name: str
    secret: str
    expires_at: datetime

    def __repr__(self) -> str:  # 不泄漏明文
        return (
            f"CredentialBinding(ref={self.credential_ref!r}, purpose={self.purpose!r}, "
            f"slot={self.slot.value}, name={self.slot_name!r}, expires_at={self.expires_at.isoformat()})"
        )

    def redacted(self) -> str:
        return f"credential_ref={self.credential_ref!r} slot={self.slot.value}:{self.slot_name} (masked)"


def redact(text: str, secrets: set[str]) -> str:
    for s in secrets:
        if s and s in text:
            text = text.replace(s, "***")
    return text