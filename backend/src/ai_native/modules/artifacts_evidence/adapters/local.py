"""本地内容寻址 ArtifactStore 适配器（首发实现，06 基线 15.1 / 15.2）。

正文写入 {root}/{sha256[:2]}/{sha256}；同内容去重；读取时重算摘要并强校验。
"""
from __future__ import annotations

import pathlib

from ai_native.runtime.envelopes import ArtifactRef
from ai_native.shared_kernel.digest import sha256_hex


class LocalContentAddressedStore:
    def __init__(self, root: str | pathlib.Path) -> None:
        self._root = pathlib.Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, sha256: str) -> pathlib.Path:
        return self._root / sha256[:2] / sha256

    def put(self, content: bytes, media_type: str, artifact_id: str | None = None) -> ArtifactRef:
        digest = sha256_hex(content)
        path = self._path(digest)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        return ArtifactRef(
            artifact_id=artifact_id if artifact_id else digest,
            sha256=digest,
            media_type=media_type,
            size=len(content),
        )

    def get(self, ref: ArtifactRef) -> bytes:
        content = self._path(ref.sha256).read_bytes()
        if sha256_hex(content) != ref.sha256:
            raise ValueError(f"artifact digest mismatch: {ref.sha256}")
        return content

    def exists(self, ref: ArtifactRef) -> bool:
        return self._path(ref.sha256).exists()