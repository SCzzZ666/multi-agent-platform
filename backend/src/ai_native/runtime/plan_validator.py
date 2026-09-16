"""确定性 PlanValidator（不调模型、无副作用）。

校验 Planner 候选计划是否满足 05/08/11 冻结不变式，输出 VALID / INVALID / NEEDS_INPUT。
该模块是「Planner 之后的确定性计划校验」落地；位于 runtime/ 但严禁 import MAF。

v1 覆盖：节点唯一/类型/角色/区域、边闭合、无环、入口/出口极性、治理骨架不可绕过
（planner + 独立 validator + condition + transform）、总节点与并行上限。
未覆盖（后续与模板绑定接入）：Skill/Tool 版本存在性、相邻 payload 合同可连、返工/重规划/预算上限。
"""
from __future__ import annotations

from collections import defaultdict, deque

from ai_native.modules.catalog_registry.domain.roles import ROLE_IDS

from .plans import (
    NODE_KINDS,
    NodeRegion,
    Plan,
    PlanValidationResult,
    PlanVerdict,
    Diagnostic,
)

# 治理骨架不可绕过的必备要素（05/12 冻结）
_REQUIRED_ROLES = ("planner", "validator")
_REQUIRED_KINDS = ("transform", "condition")


def validate_plan(plan: Plan) -> PlanValidationResult:
    diags: list[Diagnostic] = []

    def err(code: str, path: str, message: str) -> None:
        diags.append(Diagnostic(code=code, severity="ERROR", path=path, message=message))

    nodes = plan.nodes
    edges = plan.edges
    by_key = {n.node_key: n for n in nodes}
    node_keys = list(by_key)

    # 1. node_key 唯一、非空
    seen: set[str] = set()
    for n in nodes:
        if not n.node_key:
            err("PLAN_EMPTY_NODE_KEY", "$", "node_key 不能为空")
        elif n.node_key in seen:
            err("PLAN_DUPLICATE_NODE_KEY", f"nodes.{n.node_key}", f"node_key 重复: {n.node_key}")
        seen.add(n.node_key)

    # 2. kind / role 合法性
    for n in nodes:
        if n.kind not in NODE_KINDS:
            err("PLAN_INVALID_NODE_KIND", f"nodes.{n.node_key}", f"未知节点类型: {n.kind}")
        if n.role_ref not in ROLE_IDS:
            err("PLAN_INVALID_ROLE", f"nodes.{n.node_key}", f"未知角色: {n.role_ref}")
        if n.region not in (NodeRegion.FIXED_CONTROL.value, NodeRegion.PROFESSIONAL.value):
            err("PLAN_INVALID_REGION", f"nodes.{n.node_key}", f"未知区域: {n.region}")
        # 区域与固定性一致：固定控制区必须是固定节点，专业区必须是可扩展节点
        if n.region == NodeRegion.PROFESSIONAL.value and n.fixed:
            err("PLAN_FIXED_NODE_MUTATION", f"nodes.{n.node_key}", "专业区节点不能标记为固定")
        if n.region == NodeRegion.FIXED_CONTROL.value and not n.fixed:
            err("PLAN_FIXED_NODE_MUTATION", f"nodes.{n.node_key}", "固定控制区节点必须保持固定")

    # 3. 边闭合
    for e in edges:
        if e.source not in by_key:
            err("PLAN_DANGLING_EDGE", f"edges.{e.source}->{e.target}", f"边源节点不存在: {e.source}")
        if e.target not in by_key:
            err("PLAN_DANGLING_EDGE", f"edges.{e.source}->{e.target}", f"边目标节点不存在: {e.target}")

    # 4. 无环（Kahn 拓扑排序）
    indeg = defaultdict(int)
    adj: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        adj[e.source].append(e.target)
        indeg[e.target] += 1
    q = deque([k for k in node_keys if indeg.get(k, 0) == 0])
    order: list[str] = []
    while q:
        k = q.popleft()
        order.append(k)
        for t in adj.get(k, []):
            indeg[t] -= 1
            if indeg[t] == 0:
                q.append(t)
    if len(order) != len(nodes):
        err("PLAN_CYCLE_DETECTED", "$", "计划中存在环")

    # 5. 入口/出口存在与极性
    if plan.entry_node_key not in by_key:
        err("PLAN_ENTRY_MISSING", "$", f"入口节点不存在: {plan.entry_node_key}")
    else:
        inbound = [e for e in edges if e.target == plan.entry_node_key]
        if inbound:
            err("PLAN_ENTRY_NOT_SOURCE", f"nodes.{plan.entry_node_key}", "入口节点不能有入边")
    for ok in plan.output_node_keys:
        if ok not in by_key:
            err("PLAN_OUTPUT_MISSING", "$", f"输出节点不存在: {ok}")
        else:
            outbound = [e for e in edges if e.source == ok]
            if outbound:
                err("PLAN_OUTPUT_NOT_SINK", f"nodes.{ok}", "输出节点不能有出边")

    # 6. 治理骨架不可绕过
    roles = {n.role_ref for n in nodes}
    kinds = {n.kind for n in nodes}
    for r in _REQUIRED_ROLES:
        if r not in roles:
            err("PLAN_GOVERNANCE_BYPASSED", "$", f"独立性角色缺失: {r}")
    for k in _REQUIRED_KINDS:
        if k not in kinds:
            err("PLAN_GOVERNANCE_BYPASSED", "$", f"治理节点类型缺失: {k}")

    # 7. 数量/并行上限
    if len(nodes) > plan.max_nodes:
        err("PLAN_LIMIT_EXCEEDED", "$", f"总节点数 {len(nodes)} 超过上限 {plan.max_nodes}")

    has_error = any(d.severity == "ERROR" for d in diags)
    if has_error:
        verdict = PlanVerdict.INVALID
    elif plan.needs_input:
        verdict = PlanVerdict.NEEDS_INPUT
    else:
        verdict = PlanVerdict.VALID
    return PlanValidationResult(verdict=verdict, diagnostics=tuple(diags))