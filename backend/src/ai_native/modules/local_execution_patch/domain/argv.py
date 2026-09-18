"""ExecutionProfile → argv 生成（09 §9.8）。

调用方只提交结构化参数，最终 argv 由本模块按不可变 Profile 的 argv_template 在边界内生成；
DIRECT 直接起登记可执行（无 shell）；FIXED_SCRIPT 校验脚本摘要且不改脚本/不追加命令。
"""
from __future__ import annotations

import re

from ai_native.modules.local_execution_patch.domain.profile import ExecutionProfile, ProfileMode, ProfileError, validate

_SLOT_RE = re.compile(r"^\{([a-z][a-z0-9_]{0,63})\}$")


def _substitute(argv_template: tuple[str, ...], params: dict) -> list[str]:
    slots: set[str] = set()
    argv: list[str] = []
    for token in argv_template:
        m = _SLOT_RE.match(token)
        if m:
            slots.add(m.group(1))
            if m.group(1) not in params:
                raise ProfileError("PROFILE_PARAM_MISSING", f"缺少参数槽: {m.group(1)}")
            val = params[m.group(1)]
            _validate_value(val)
            argv.append(val)
        else:
            if "{" in token or "}" in token:
                raise ProfileError("PROFILE_BAD_ARGV_TEMPLATE", f"非法模板片: {token}")
            argv.append(token)
    extra = set(params) - slots
    if extra:
        raise ProfileError("PROFILE_PARAM_UNEXPECTED", f"多余参数: {sorted(extra)}")
    if len(argv) != len(slots) + sum(1 for t in argv_template if not _SLOT_RE.match(t)):
        raise ProfileError("PROFILE_ARGV_INTERNAL", "argv 生成内部不一致")
    return argv


def _validate_value(value: str) -> None:
    if "\x00" in value:
        raise ProfileError("PROFILE_ARG_NUL_BYTE", "参数值含 NUL 字节")
    if len(value) > 4096:
        raise ProfileError("PROFILE_ARG_TOO_LONG", "参数值超长")


def direct_argv(profile: ExecutionProfile, params: dict) -> list[str]:
    """DIRECT：验证可执行身份 + 结构化参数 → argv（无 shell 解释）。"""
    validate(profile)
    if profile.mode != ProfileMode.DIRECT.value:
        raise ProfileError("PROFILE_MODE_MISMATCH", "该 Profile 不是 DIRECT 模式")
    return _substitute(profile.argv_template, params)


def fixed_script_args(profile: ExecutionProfile, params: dict, provided_script_digest: str) -> list[str]:
    """FIXED_SCRIPT：固定 Shell 身份 + 脚本摘要 + 参数槽；运行时不可换脚本/追加命令。"""
    validate(profile)
    if profile.mode != ProfileMode.FIXED_SCRIPT.value:
        raise ProfileError("PROFILE_MODE_MISMATCH", "该 Profile 不是 FIXED_SCRIPT 模式")
    if provided_script_digest != profile.fixed_script_digest:
        raise ProfileError("PROFILE_SCRIPT_DIGEST_MISMATCH", "脚本摘要与固定脚本不一致")
    return _substitute(profile.argv_template, params)