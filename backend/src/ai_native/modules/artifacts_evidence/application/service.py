"""artifacts_evidence 应用用例：Artifact 登记（06 基线 15.1 写入顺序）。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ai_native.modules.artifacts_evidence.adapters.local import LocalContentAddressedStore
from ai_native.modules.artifacts_evidence.adapters.orm import Artifact
from ai_native.runtime.envelopes import ArtifactRef
from ai_native.shared_kernel.ids import uuid7


def register_artifact(
    db: Session,
    store: LocalContentAddressedStore,
    *,
    project_id,
    run_id,
    artifact_type: str,
    media_type: str,
    content: bytes,
) -> ArtifactRef:
    """先内容寻址写正文 → 同事务登记元数据（正文不入库，DB 只存引用/摘要/大小/媒体类型）。"""
    ref = store.put(content, media_type)
    row = Artifact(
        id=uuid7(), project_id=project_id, run_id=run_id, artifact_type=artifact_type,
        media_type=media_type, object_ref=ref.sha256, content_digest=f"sha256:{ref.sha256}",
        size_bytes=ref.size, sensitivity="INTERNAL",
    )
    db.add(row)
    db.flush()
    return ArtifactRef(artifact_id=str(row.id), sha256=ref.sha256, media_type=media_type, size=ref.size)