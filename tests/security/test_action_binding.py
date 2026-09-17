"""ActionBinding 三摘要 + 服务端重算比对（09 §9.4）。"""
from __future__ import annotations

from dataclasses import replace

from ai_native.modules.capability_gateway.domain.action_binding import ActionBinding


def _binding() -> ActionBinding:
    return ActionBinding(
        project_id="p1",
        run_id="r1",
        workflow_version_id="wv1",
        run_plan_version_id="rpv1",
        node_attempt_id="na1",
        action_id="a1",
        tool_key="repository.read",
        capability_key="repo.read",
        tool_schema_digest="sha256:" + "0" * 64,
        normalized_args={"path": "/src"},
        resource_scopes={"directory_id": "d1", "paths": ["/src"]},
        risk="LOW",
        credential_refs=("cred:git", "cred:gh"),
    )


def test_compute_and_verify_digests() -> None:
    b = _binding().compute_digests()
    assert b.args_digest.startswith("sha256:")
    assert b.resource_scope_digest.startswith("sha256:")
    assert b.action_digest.startswith("sha256:")
    assert b.verify_digests()


def test_field_change_invalidates_digest() -> None:
    b = _binding().compute_digests()
    tampered = replace(b, normalized_args={"path": "/etc"})
    assert not tampered.verify_digests()
    assert tampered.compute_digests().args_digest != b.args_digest


def test_scope_change_invalidates_digest() -> None:
    b = _binding().compute_digests()
    tampered = replace(b, resource_scopes={"directory_id": "d2", "paths": ["/"]})
    assert not tampered.verify_digests()


def test_risk_change_invalidates_action_digest() -> None:
    b = _binding().compute_digests()
    tampered = replace(b, risk="CRITICAL")
    assert not tampered.verify_digests()