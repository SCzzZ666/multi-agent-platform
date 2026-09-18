"""安全域确定性核心测试：JCS 摘要 / ResourceScope 交集 / 九层 PDP / ActionBinding 三摘要。"""
from __future__ import annotations

from ai_native.modules.capability_gateway.domain.binding import compute_binding_digests
from ai_native.modules.capability_gateway.domain.intent import (
    IdempotencyClass,
    InvocationStatus,
    can_auto_retry,
    can_transition,
    is_terminal,
)
from ai_native.modules.capability_gateway.domain.pdp import Effect, decide
from ai_native.modules.capability_gateway.domain.scopes import ResourceScope, covers, intersect
from ai_native.shared_kernel.jcs import canonicalize, jcs_digest

D = lambda actions, **kw: ResourceScope("PROJECT_RESOURCE", frozenset(actions), **kw)


def _proj(ids=("p1",), actions=("read",), kind="repository"):
    return ResourceScope("PROJECT_RESOURCE", frozenset(actions), resource_kind=kind, resource_ids=frozenset(ids))


def _layers(s=None):
    s = s or _proj()
    return dict(
        project_scopes=[s], role_scopes=[s], node_scopes=[s], plan_scopes=[s],
        skill_scopes=[s], tool_scopes=[s], runtime_scopes=[s],
    )


# ---- JCS ----
def test_jcs_key_order_and_whitespace_independent() -> None:
    a = jcs_digest({"b": 1, "a": [{"z": True, "y": None}]})
    b = jcs_digest({"a": [{"y": None, "z": True}], "b": 1})
    assert a == b
    assert a.startswith("sha256:") and len(a) == 71


def test_jcs_sorts_keys_no_spaces() -> None:
    assert canonicalize({"b": 1, "a": 2}) == '{"a":2,"b":1}'


# ---- ResourceScope 交集 ----
def test_project_scope_intersection() -> None:
    a = _proj(("p1", "p2"), ("read", "write"))
    b = _proj(("p2", "p3"), ("read",))
    r = intersect(a, b)
    assert r is not None and r.resource_ids == frozenset({"p2"}) and r.actions == frozenset({"read"})


def test_scope_kind_mismatch_fails_closed() -> None:
    a = _proj(("p1",), ("read",), kind="repository")
    b = _proj(("p1",), ("read",), kind="dataset")
    assert intersect(a, b) is None


def test_scope_actions_disjoint_fails_closed() -> None:
    assert intersect(_proj(("p1",), ("read",)), _proj(("p1",), ("write",))) is None


def test_tool_scope_identity_mismatch_fails_closed() -> None:
    a = ResourceScope("TOOL_RESOURCE", frozenset({"read"}), tool_key="repo", capability_key="repository.read",
                      tool_schema_digest="sha256:" + "0" * 64, resource_keys=frozenset({"data"}))
    b = ResourceScope("TOOL_RESOURCE", frozenset({"read"}), tool_key="repo", capability_key="other.read",
                      tool_schema_digest="sha256:" + "0" * 64, resource_keys=frozenset({"data"}))
    assert intersect(a, b) is None


# ---- PDP ----
def test_pdp_allow_when_intersection_covers_candidate() -> None:
    d = decide(member=True, candidate_scopes=[_proj(("p1",), ("read",))], risk_level="LOW", **_layers())
    assert d.effect == Effect.ALLOW


def test_pdp_deny_non_member() -> None:
    d = decide(member=False, candidate_scopes=[_proj()], risk_level="LOW", **_layers())
    assert d.effect == Effect.DENY and "SUBJECT_NOT_MEMBER" in d.reason_codes


def test_pdp_deny_missing_layer() -> None:
    kw = _layers()
    kw["role_scopes"] = []
    d = decide(member=True, candidate_scopes=[_proj()], risk_level="LOW", **kw)
    assert d.effect == Effect.DENY and "ROLE_CEILING_MISSING" in d.reason_codes


def test_pdp_deny_candidate_not_covered() -> None:
    d = decide(member=True, candidate_scopes=[_proj(("other",), ("read",))], risk_level="LOW", **_layers())
    assert d.effect == Effect.DENY and "SCOPE_NOT_GRANTED" in d.reason_codes


def test_pdp_deny_empty_candidate_scopes() -> None:
    # 未声明任何资源范围的 Tool 调用必须 DENY（任一缺失即失败关闭）
    d = decide(member=True, candidate_scopes=[], risk_level="LOW", **_layers())
    assert d.effect == Effect.DENY and "CANDIDATE_SCOPES_EMPTY" in d.reason_codes


def test_pdp_approval_required_on_high_risk() -> None:
    d = decide(member=True, candidate_scopes=[_proj(("p1",), ("read",))], risk_level="HIGH", **_layers())
    assert d.effect == Effect.APPROVAL_REQUIRED and d.required_approval_kind == "CAPABILITY"
    d2 = decide(member=True, candidate_scopes=[_proj(("p1",), ("read",))], risk_level="HIGH", has_valid_approval=True, **_layers())
    assert d2.effect == Effect.ALLOW


# ---- ActionBinding 三摘要 ----
_BIND = dict(
    project_id="u" * 32, run_id="u" * 32, workflow_version_id="u" * 32,
    run_plan_version_id="u" * 32, node_attempt_id="u" * 32, action_id="a" * 32,
    tool_key="repo", capability_key="repository.read", tool_schema_digest="sha256:" + "0" * 64,
    normalized_args={"id": "p1", "format": "json"}, resource_scopes=[_proj(("p1",), ("read",))],
    risk_level="LOW", credential_refs=["cred:a", "cred:b"],
)


def test_binding_digests_deterministic_and_order_independent() -> None:
    d1 = compute_binding_digests(**_BIND)
    d2 = compute_binding_digests(**{**_BIND, "credential_refs": ["cred:b", "cred:a"]})
    assert d1["action_digest"] == d2["action_digest"]
    assert d1["args_digest"].startswith("sha256:")


def test_binding_args_change_changes_digest() -> None:
    d1 = compute_binding_digests(**_BIND)
    d2 = compute_binding_digests(**{**_BIND, "normalized_args": {"id": "p2", "format": "json"}})
    assert d1["args_digest"] != d2["args_digest"]
    assert d1["action_digest"] != d2["action_digest"]


def test_binding_scope_change_changes_digest() -> None:
    d1 = compute_binding_digests(**_BIND)
    d2 = compute_binding_digests(**{**_BIND, "resource_scopes": [_proj(("p2",), ("read",))]})
    assert d1["resource_scope_digest"] != d2["resource_scope_digest"]
    assert d1["action_digest"] != d2["action_digest"]


# ---- Invocation 状态机 ----
def test_invocation_transitions() -> None:
    assert can_transition(InvocationStatus.INTENT_RECORDED, InvocationStatus.DISPATCHING)
    assert can_transition(InvocationStatus.DISPATCHING, InvocationStatus.SUCCEEDED)
    assert can_transition(InvocationStatus.DISPATCHING, InvocationStatus.UNKNOWN)
    assert not can_transition(InvocationStatus.SUCCEEDED, InvocationStatus.DISPATCHING)
    assert not can_transition(InvocationStatus.UNKNOWN, InvocationStatus.DISPATCHING)  # 不倒退


def test_non_idempotent_unknown_forbids_auto_retry() -> None:
    assert not can_auto_retry(IdempotencyClass.NON_IDEMPOTENT, InvocationStatus.UNKNOWN)
    assert can_auto_retry(IdempotencyClass.READ_ONLY, InvocationStatus.UNKNOWN)
    assert can_auto_retry(IdempotencyClass.IDEMPOTENT, InvocationStatus.UNKNOWN)


def test_terminal_status_no_retry() -> None:
    assert not can_auto_retry(IdempotencyClass.IDEMPOTENT, InvocationStatus.SUCCEEDED)
    assert is_terminal(InvocationStatus.SUCCEEDED) and not is_terminal(InvocationStatus.UNKNOWN)