"""九层权限交集：失败关闭 + Approval 不扩权（09 §9.2 红线）。"""
from __future__ import annotations

from ai_native.modules.capability_gateway.domain.authorization import BASE_LAYERS, Decision, decide


def _all() -> dict[str, bool]:
    return {name: True for name in BASE_LAYERS}


def test_all_layers_pass_no_approval_needed() -> None:
    assert decide(_all()) == Decision.ALLOW


def test_any_layer_false_denies() -> None:
    for name in BASE_LAYERS:
        layers = _all()
        layers[name] = False
        assert decide(layers) == Decision.DENY, name


def test_missing_layer_denies() -> None:
    layers = _all()
    del layers["tool_schema_snapshot"]
    assert decide(layers) == Decision.DENY


def test_approval_required_without_approval() -> None:
    assert decide(_all(), approval_required=True, valid_approval=False) == Decision.APPROVAL_REQUIRED


def test_approval_required_with_approval() -> None:
    assert decide(_all(), approval_required=True, valid_approval=True) == Decision.ALLOW


def test_approval_cannot_escalate_deny() -> None:
    """红线：Approval 只对已在交集内的确定动作加人工确认，永远不能让 DENY 变 ALLOW。"""
    layers = _all()
    layers["runtime_security_egress"] = False
    assert decide(layers, approval_required=True, valid_approval=True) == Decision.DENY