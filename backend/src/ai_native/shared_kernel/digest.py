"""摘要工具。

注意（04 基线 6.1 / 09 基线 9.4）：存在两套 Digest Schema 不可混用——
- `sha256:` 前缀 + 64 位小写十六进制：用于 DB 摘要列（char(71)）与 ActionBinding 摘要；
- 裸 64 位小写十六进制：ArtifactRef.sha256 与上传内容摘要。
"""
from __future__ import annotations

import hashlib


def sha256_hex(data: bytes) -> str:
    """裸 64 位小写十六进制（ArtifactRef / 上传摘要用）。"""
    return hashlib.sha256(data).hexdigest()


def sha256_prefixed(data: bytes) -> str:
    """`sha256:` + 64 位小写十六进制（DB char(71) 摘要列用）。"""
    return "sha256:" + sha256_hex(data)