"""运行期计划模型（Planner 候选计划）——确定性校验的输入。

对应 05 基线六类节点 / 08 基线 WorkflowDefinition；region 语义：
- FIXED_CONTROL  = 010-099 / 200-299（固定控制骨架，Planner 不可改）
- PROFESSIONAL   = 100-199（专业执行区，Planner 只能在白名单与上限内扩展）

本模块只含纯数据模型，不 import 框架。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

NODE_KINDS = ("agent", "skill", "tool", "transform", "condition", "approval")


class PlanVerdict(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    NEEDS_INPUT = "NEEDS_INPUT"


class NodeRegion(str, Enum):
    FIXED_CONTROL = "FIXED_CONTROL"
    PROFESSIONAL = "PROFESSIONAL"


@dataclass(frozen=True)
class PlanNode:
    node_key: str
    kind: str
    role_ref: str
    region: str
    fixed: bool = False


@dataclass(frozen=True)
class PlanEdge:
    source: str
    target: str


@dataclass(frozen=True)
class Plan:
    workflow_key: str
    entry_node_key: str
    output_node_keys: tuple[str, ...]
    nodes: tuple[PlanNode, ...]
    edges: tuple[PlanEdge, ...]
    # 模板治理上限（11 基线：SF 27 / Skills 23 / AI4S 31），调用方按模板传入
    max_nodes: int = 27
    max_parallel: int = 6
    # Planner 显式标记「信息不足，需要用户输入」时置 True
    needs_input: bool = False


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: str  # ERROR | WARNING
    path: str
    message: str


@dataclass(frozen=True)
class PlanValidationResult:
    verdict: PlanVerdict
    diagnostics: tuple[Diagnostic, ...] = ()