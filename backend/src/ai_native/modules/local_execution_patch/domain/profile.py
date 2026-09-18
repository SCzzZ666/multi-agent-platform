"""ExecutionProfile 不可变版本（09 §9.8）。

模式封闭为 DIRECT（默认，直接起登记可执行，结构化值→边界内生成 argv，调用方不得提交最终 argv）
与 FIXED_SCRIPT（需要 Shell 的唯一例外：固定 Shell 身份 + 脚本摘要 + 参数槽）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ai_native.shared_kernel.jcs import jcs_digest


class ProfileMode(str, Enum):
    DIRECT = "DIRECT"
    FIXED_SCRIPT = "FIXED_SCRIPT"


class ProfileError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ExecutionProfile:
    profile_id: str
    version: int
    mode: str  # DIRECT | FIXED_SCRIPT
    executable_identity: str
    argv_template: tuple[str, ...]
    working_directory_policy: str = "work_copy_only"
    environment_allowlist: tuple[str, ...] = ()
    secret_slots: tuple = ()
    network_policy: str = "none"
    resource_limits: dict = field(default_factory=dict)
    child_process_policy: str = "none"
    output_limits: dict = field(default_factory=dict)
    fixed_script_digest: str | None = None
    fixed_script_path: str | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}

    def digest(self) -> str:
        return jcs_digest(self.to_dict())


def validate(profile: ExecutionProfile) -> None:
    if profile.mode not in (ProfileMode.DIRECT.value, ProfileMode.FIXED_SCRIPT.value):
        raise ProfileError("PROFILE_INVALID_MODE", f"未知模式: {profile.mode}")
    if not profile.argv_template:
        raise ProfileError("PROFILE_EMPTY_ARGV_TEMPLATE", "argv_template 不能为空")
    if profile.argv_template[0] != profile.executable_identity:
        raise ProfileError("PROFILE_EXECUTABLE_MISMATCH", "argv[0] 必须等于登记的 executable_identity")
    if profile.mode == ProfileMode.FIXED_SCRIPT.value:
        if not profile.fixed_script_digest or not profile.fixed_script_path:
            raise ProfileError("PROFILE_FIXED_SCRIPT_INCOMPLETE", "FIXED_SCRIPT 必须声明固定脚本摘要与路径")
    if profile.network_policy not in ("none", "loopback", "allowlisted"):
        raise ProfileError("PROFILE_INVALID_NETWORK_POLICY", str(profile.network_policy))