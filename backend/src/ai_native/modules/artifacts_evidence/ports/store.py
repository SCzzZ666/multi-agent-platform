"""ArtifactStore 端口（04/06 基线：正文不入库，DB 只存引用/摘要/大小/媒体类型）。"""
from __future__ import annotations

from typing import Protocol

from ai_native.runtime.envelopes import ArtifactRef


class ArtifactStorePort(Protocol):
    def put(self, content: bytes, media_type: str, artifact_id: str | None = None) -> ArtifactRef:
        """内容寻址写入：返回不可变 ArtifactRef；同内容同摘要去重。"""

    def get(self, ref: ArtifactRef) -> bytes:
        """读取正文并校验摘要；摘要不符必须报错（06 基线：节点不得据此声明完成）。"""

    def exists(self, ref: ArtifactRef) -> bool: ...