"""ExecutionProfile / argv 生成测试（09 §9.8）：DIRECT 无 shell、FIXED_SCRIPT 摘要固定、调用方不交最终 argv。"""
from __future__ import annotations

import pytest

from ai_native.modules.local_execution_patch.domain.argv import direct_argv, fixed_script_args
from ai_native.modules.local_execution_patch.domain.profile import ExecutionProfile, ProfileError, validate

DIRECT = ExecutionProfile(
    profile_id="p1", version=1, mode="DIRECT", executable_identity="solve",
    argv_template=("solve", "--input", "{input_file}", "--out", "{out_dir}"),
)

FIXED = ExecutionProfile(
    profile_id="p2", version=1, mode="FIXED_SCRIPT", executable_identity="/bin/bash",
    argv_template=("/bin/bash", "run.sh", "{arg1}"),
    fixed_script_digest="sha256:" + "d" * 64, fixed_script_path="run.sh",
)


def test_direct_argv_from_structured_params() -> None:
    argv = direct_argv(DIRECT, {"input_file": "a.csv", "out_dir": "/tmp/x"})
    assert argv == ["solve", "--input", "a.csv", "--out", "/tmp/x"]


def test_direct_extra_param_rejected() -> None:
    with pytest.raises(ProfileError) as e:
        direct_argv(DIRECT, {"input_file": "a.csv", "out_dir": "/tmp/x", "inject": "x"})
    assert e.value.code == "PROFILE_PARAM_UNEXPECTED"


def test_direct_missing_param_rejected() -> None:
    with pytest.raises(ProfileError) as e:
        direct_argv(DIRECT, {"input_file": "a.csv"})
    assert e.value.code == "PROFILE_PARAM_MISSING"


def test_executable_identity_not_swappable() -> None:
    bad = ExecutionProfile(profile_id="p3", version=1, mode="DIRECT", executable_identity="solve",
                           argv_template=("evil", "{x}"))
    with pytest.raises(ProfileError) as e:
        validate(bad)
    assert e.value.code == "PROFILE_EXECUTABLE_MISMATCH"


def test_direct_value_with_shell_metachar_is_single_arg() -> None:
    # DIRECT 无 shell 解释：元字符只是单个 argv 元素
    argv = direct_argv(DIRECT, {"input_file": "--flag; rm -rf", "out_dir": "/x"})
    assert argv[2] == "--flag; rm -rf"


def test_fixed_script_digest_must_match() -> None:
    argv = fixed_script_args(FIXED, {"arg1": "x"}, "sha256:" + "d" * 64)
    assert argv == ["/bin/bash", "run.sh", "x"]
    with pytest.raises(ProfileError) as e:
        fixed_script_args(FIXED, {"arg1": "x"}, "sha256:" + "e" * 64)
    assert e.value.code == "PROFILE_SCRIPT_DIGEST_MISMATCH"


def test_mode_mismatch_rejected() -> None:
    with pytest.raises(ProfileError) as e:
        direct_argv(FIXED, {"arg1": "x"})
    assert e.value.code == "PROFILE_MODE_MISMATCH"
    with pytest.raises(ProfileError) as e:
        fixed_script_args(DIRECT, {}, "sha256:" + "d" * 64)
    assert e.value.code is not None


def test_nul_byte_rejected() -> None:
    with pytest.raises(ProfileError) as e:
        direct_argv(DIRECT, {"input_file": "a\x00b", "out_dir": "/x"})
    assert e.value.code == "PROFILE_ARG_NUL_BYTE"