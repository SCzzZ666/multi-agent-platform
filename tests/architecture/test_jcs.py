"""RFC 8785 JCS 规范化 + 摘要（09 基线摘要唯一口径）。"""
from __future__ import annotations

from ai_native.shared_kernel.jcs import canonical_json, jcs_sha256


def test_object_key_sort() -> None:
    assert canonical_json({"b": 1, "a": 2, "c": [1, 2, 3]}) == '{"a":2,"b":1,"c":[1,2,3]}'


def test_nested_object_and_literals() -> None:
    assert canonical_json({"z": {"y": 1}, "a": [True, False, None]}) == '{"a":[true,false,null],"z":{"y":1}}'


def test_string_escaping() -> None:
    assert canonical_json('a"b\\c\nd') == '"a\\"b\\\\c\\nd"'


def test_control_char_escaping() -> None:
    assert canonical_json("\t") == '"\\t"'
    assert canonical_json("") == '"\\u0001"'


def test_int_and_negative_zero() -> None:
    assert canonical_json(42) == "42"
    assert canonical_json(-0.0) == "0"


def test_jcs_sha256_prefix_and_len() -> None:
    d = jcs_sha256({"a": 1, "b": [2, 3]})
    assert d.startswith("sha256:")
    assert len(d) == 71  # 'sha256:' + 64 hex


def test_key_order_independent_digest() -> None:
    # 对象键序不影响摘要（JCS 排序后一致）
    assert jcs_sha256({"a": 1, "b": 2}) == jcs_sha256({"b": 2, "a": 1})