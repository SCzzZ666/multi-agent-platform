"""JCS(RFC 8785)确定性序列化 + 摘要。"""
from __future__ import annotations

from ai_native.shared_kernel.jcs import canonicalize, jcs_digest


def test_jcs_sorts_keys_and_is_compact() -> None:
    assert canonicalize({"b": 1, "a": 2}) == '{"a":2,"b":1}'


def test_jcs_nested_and_unicode_deterministic() -> None:
    obj = {"z": {"y": "中文", "x": [1, 2, 3]}, "a": True}
    assert canonicalize(obj) == canonicalize({"a": True, "z": {"x": [1, 2, 3], "y": "中文"}})


def test_jcs_digest_is_sha256_prefixed() -> None:
    d = jcs_digest({"a": 1, "b": {"c": 2}})
    assert d.startswith("sha256:")
    assert len(d) == len("sha256:") + 64


def test_jcs_same_content_same_digest() -> None:
    assert jcs_digest({"a": 1, "b": [2, 3]}) == jcs_digest({"b": [2, 3], "a": 1})


def test_jcs_different_content_different_digest() -> None:
    assert jcs_digest({"a": 1}) != jcs_digest({"a": 2})