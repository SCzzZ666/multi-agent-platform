"""确定性 PlanValidator 不变式测试（第 1 周完成条件 #4 的治理侧）。

真实口径：合法计划 → VALID；违反 05/08/11 冻结不变式的计划 → INVALID 且带诊断；
Planner 标记信息不足 → NEEDS_INPUT；Condition 三态映射一一对应。
"""
from __future__ import annotations

from ai_native.runtime.conditions import EXECUTE, HOLD_FOR_USER, REJECT, plan_route
from ai_native.runtime.plan_validator import validate_plan
from ai_native.runtime.plans import Plan, PlanEdge, PlanNode, PlanVerdict


def _node(key: str, kind: str, role: str, region: str = "PROFESSIONAL", fixed: bool = False) -> PlanNode:
    return PlanNode(node_key=key, kind=kind, role_ref=role, region=region, fixed=fixed)


def _valid_plan() -> Plan:
    """最小合法计划：normalize → planner → validate_plan → route → work → validate_out。

    治理骨架：planner(role) + validator(role) + transform(kind) + condition(kind) 齐全。
    """
    nodes = (
        _node("n01", "transform", "planner", "FIXED_CONTROL", fixed=True),
        _node("p02", "agent", "planner", "FIXED_CONTROL", fixed=True),
        _node("v03", "transform", "validator", "FIXED_CONTROL", fixed=True),
        _node("r04", "condition", "validator", "FIXED_CONTROL", fixed=True),
        _node("w05", "agent", "engineer", "PROFESSIONAL", fixed=False),
        _node("o06", "agent", "validator", "FIXED_CONTROL", fixed=True),
    )
    edges = (
        PlanEdge("n01", "p02"),
        PlanEdge("p02", "v03"),
        PlanEdge("v03", "r04"),
        PlanEdge("r04", "w05"),
        PlanEdge("w05", "o06"),
    )
    return Plan(
        workflow_key="smoke",
        entry_node_key="n01",
        output_node_keys=("o06",),
        nodes=nodes,
        edges=edges,
    )


def test_valid_plan_passes() -> None:
    r = validate_plan(_valid_plan())
    assert r.verdict == PlanVerdict.VALID, r.diagnostics


def test_cycle_detected() -> None:
    p = _valid_plan()
    p = Plan(
        workflow_key=p.workflow_key,
        entry_node_key=p.entry_node_key,
        output_node_keys=p.output_node_keys,
        nodes=p.nodes,
        edges=(*p.edges, PlanEdge("o06", "n01")),  # 回边
        max_nodes=p.max_nodes,
    )
    r = validate_plan(p)
    assert r.verdict == PlanVerdict.INVALID
    assert any(d.code == "PLAN_CYCLE_DETECTED" for d in r.diagnostics)


def test_unknown_role_invalid() -> None:
    p = _valid_plan()
    nodes = (_node("bad", "agent", "commander", "PROFESSIONAL"),) + p.nodes
    p = Plan(p.workflow_key, p.entry_node_key, p.output_node_keys, nodes, p.edges, p.max_nodes)
    r = validate_plan(p)
    assert r.verdict == PlanVerdict.INVALID
    assert any(d.code == "PLAN_INVALID_ROLE" for d in r.diagnostics)


def test_unknown_kind_invalid() -> None:
    p = _valid_plan()
    nodes = (_node("bad", "mcp", "planner", "PROFESSIONAL"),) + p.nodes
    p = Plan(p.workflow_key, p.entry_node_key, p.output_node_keys, nodes, p.edges, p.max_nodes)
    r = validate_plan(p)
    assert r.verdict == PlanVerdict.INVALID
    assert any(d.code == "PLAN_INVALID_NODE_KIND" for d in r.diagnostics)


def test_validator_cannot_be_bypassed() -> None:
    p = _valid_plan()
    nodes = tuple(n for n in p.nodes if n.role_ref != "validator")
    p = Plan(p.workflow_key, p.entry_node_key, p.output_node_keys, nodes, p.edges, p.max_nodes)
    r = validate_plan(p)
    assert r.verdict == PlanVerdict.INVALID
    assert any(d.code == "PLAN_GOVERNANCE_BYPASSED" for d in r.diagnostics)


def test_dangling_edge_invalid() -> None:
    p = _valid_plan()
    p = Plan(p.workflow_key, p.entry_node_key, p.output_node_keys, p.nodes, (*p.edges, PlanEdge("ghost", "n01")), p.max_nodes)
    r = validate_plan(p)
    assert r.verdict == PlanVerdict.INVALID
    assert any(d.code == "PLAN_DANGLING_EDGE" for d in r.diagnostics)


def test_node_limit_exceeded() -> None:
    p = _valid_plan()
    p = Plan(p.workflow_key, p.entry_node_key, p.output_node_keys, p.nodes, p.edges, max_nodes=3)
    r = validate_plan(p)
    assert r.verdict == PlanVerdict.INVALID
    assert any(d.code == "PLAN_LIMIT_EXCEEDED" for d in r.diagnostics)


def test_needs_input_verdict() -> None:
    p = _valid_plan()
    p = Plan(p.workflow_key, p.entry_node_key, p.output_node_keys, p.nodes, p.edges, p.max_nodes, needs_input=True)
    r = validate_plan(p)
    assert r.verdict == PlanVerdict.NEEDS_INPUT


def test_condition_route_mapping() -> None:
    assert plan_route(PlanVerdict.VALID) == EXECUTE
    assert plan_route(PlanVerdict.NEEDS_INPUT) == HOLD_FOR_USER
    assert plan_route(PlanVerdict.INVALID) == REJECT