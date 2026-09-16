"""WorkflowDefinition 1.0 发布校验（08 基线 Schema 校验，JSON Schema 2020-12）。

Schema 通过 ≠ 可发布：这里做 08 schema 局部结构校验；确定性语义校验（无环/入口/出口、
固定控制区、治理骨架）由 runtime/plan_validator 在运行期承担，发布期再做一层轻量确认。
"""
from __future__ import annotations

import json
import pathlib

import jsonschema

_SCHEMA_PATH = (
    pathlib.Path(__file__).resolve().parents[6]
    / "design-contracts"
    / "08_WorkflowDefinition"
    / "workflow-definition.schema.json"
)


def _load_schema():
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_definition(definition: dict) -> tuple[bool, list[str]]:
    """返回 (是否通过, 错误列表)。"""
    try:
        jsonschema.validate(instance=definition, schema=_load_schema())
    except jsonschema.ValidationError as e:
        return False, [f"{'/'.join(str(p) for p in e.absolute_path)}: {e.message}"]
    return True, []


def is_acyclic(definition: dict) -> tuple[bool, str]:
    """轻量无环校验（发布期）。"""
    from collections import defaultdict, deque

    adj: dict[str, list[str]] = defaultdict(list)
    indeg: dict[str, int] = defaultdict(int)
    node_keys = {n["node_key"] for n in definition.get("nodes", [])}
    for e in definition.get("edges", []):
        adj[e["from"]].append(e["to"])
        indeg[e["to"]] += 1
    q = deque([k for k in node_keys if indeg.get(k, 0) == 0])
    seen = 0
    while q:
        k = q.popleft()
        seen += 1
        for t in adj.get(k, []):
            indeg[t] -= 1
            if indeg[t] == 0:
                q.append(t)
    if seen != len(node_keys):
        return False, "cycle detected"
    return True, ""