"""节点交接合同不变式（05/06 基线 Envelope / ArtifactRef）。"""
from __future__ import annotations

import dataclasses

from ai_native.runtime.envelopes import (
    ArtifactRef,
    NodeInputEnvelope,
    NodeResultEnvelope,
    NodeResultStatus,
)


def test_result_status_is_five_values() -> None:
    assert {s.value for s in NodeResultStatus} == {
        "COMPLETED",
        "NEEDS_INPUT",
        "REWORK_REQUIRED",
        "FAILED",
        "CANCELLED",
    }


def test_artifact_ref_sha256_is_bare_62_hex() -> None:
    r = ArtifactRef(artifact_id="a", sha256="ab" * 32, media_type="application/json", size=4)
    assert len(r.sha256) == 64
    assert all(c in "0123456789abcdef" for c in r.sha256)
    assert "sha256:" not in r.sha256  # ArtifactRef 是裸十六进制，非 char(71) 摘要列


def test_envelopes_are_frozen() -> None:
    assert dataclasses.is_dataclass(NodeInputEnvelope)
    assert dataclasses.is_dataclass(NodeResultEnvelope)
    r = NodeResultEnvelope(node_key="sf_validate_plan")
    assert r.status == NodeResultStatus.COMPLETED
    assert r.attempt_no == 1


def test_input_envelope_carries_conditional_refs() -> None:
    e = NodeInputEnvelope(
        node_key="sf_implement_backend",
        role_ref="engineer",
        previous_attempt_ref="att-1",
    )
    assert e.previous_attempt_ref == "att-1"
    assert e.workspace_grant_ref is None
    assert e.approval_decision_ref is None