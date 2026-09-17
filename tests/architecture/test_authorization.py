"""九层失败关闭交集 + ActionBinding 三摘要（09 基线）。"""
from __future__ import annotations

from ai_native.modules.capability_gateway.domain.authorization import (
    LAYER_NAMES,
    LayerResult,
    evaluate,
)
from ai_native.modules.capability_gateway.domain.binding import ActionBinding


def _allow() -> dict:
    return {n: LayerResult(n, "ALLOW") for n in LAYER_NAMES}


def test_all_allow() -> None:
    assert evaluate(_allow()).decision == "ALLOW"


def test_missing_layer_denies_fail_closed() -> None:
    layers = _allow()
    layers.pop("tool_schema_snapshot")
    d = evaluate(layers)
    assert d.decision == "DENY"
    assert any("tool_schema_snapshot" in diag for diag in d.diagnostics)


def test_cross_project_deny() -> None:
    layers = _allow()
    layers["subject_project"] = LayerResult("subject_project", "DENY", "跨项目访问")
    d = evaluate(layers)
    assert d.decision == "DENY"
    assert any("跨项目访问" in diag for diag in d.diagnostics)


def test_approval_required_not_allow() -> None:
    layers = _allow()
    layers["effective_approval"] = LayerResult("effective_approval", "APPROVAL_REQUIRED", "高风险需审批")
    assert evaluate(layers).decision == "APPROVAL_REQUIRED"


def _build(args=None, creds=("x", "y")):
    return ActionBinding.build(
        action_id="a1", project_id="p1", tool_key="repo.read", capability_key="c",
        tool_schema_digest="sha256:" + "0" * 64,
        normalized_args=args or {"a": 1, "b": 2}, resource_scopes={"paths": ["src"]},
        risk="LOW", credential_refs=creds,
    )


def test_binding_digests_deterministic() -> None:
    assert _build().action_digest == _build().action_digest


def test_args_change_changes_digest() -> None:
    assert _build({"a": 1}).args_digest != _build({"a": 2}).args_digest


def test_credential_refs_order_independent() -> None:
    assert _build(creds=("x", "y")).action_digest == _build(creds=("y", "x")).action_digest