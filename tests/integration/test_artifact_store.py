"""本地内容寻址 ArtifactStore 真实 I/O 测试（06 基线 15.1 写入顺序）。"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from ai_native.modules.artifacts_evidence.adapters.local import LocalContentAddressedStore
from ai_native.runtime.envelopes import ArtifactRef


def test_put_get_roundtrip_and_dedup() -> None:
    with tempfile.TemporaryDirectory() as d:
        store = LocalContentAddressedStore(d)
        ref1 = store.put(b'{"a": 1}', "application/json", artifact_id="artifact-1")
        ref2 = store.put(b'{"a": 1}', "application/json")  # 同内容 → 同摘要去重
        assert ref1.sha256 == ref2.sha256
        assert ref1.size == 8
        assert ref1.media_type == "application/json"
        assert store.get(ref1) == b'{"a": 1}'
        assert store.exists(ref1)


def test_digest_mismatch_detected() -> None:
    with tempfile.TemporaryDirectory() as d:
        store = LocalContentAddressedStore(d)
        ref = store.put(b"original", "text/plain")
        # 直接篡改底层正文（模拟丢失/损坏）
        path = pathlib.Path(d) / ref.sha256[:2] / ref.sha256
        path.write_bytes(b"tampered")
        with pytest.raises(ValueError, match="digest mismatch"):
            store.get(ref)


def test_distinct_content_distinct_refs() -> None:
    with tempfile.TemporaryDirectory() as d:
        store = LocalContentAddressedStore(d)
        a = store.put(b"content-a", "text/plain")
        b = store.put(b"content-b", "text/plain")
        assert a.sha256 != b.sha256
        assert not store.exists(ArtifactRef("x", "0" * 64, "text/plain", 0))