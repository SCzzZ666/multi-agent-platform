"""节点交接公共数据合同（05 基线 6.1/6.2 + 06 基线 11.2/11.3）。

- 节点间只传 ArtifactRef，正文不隐式塞入共享聊天记录；
- 输出顺序：先落不可变 Artifact → 登记摘要 → NodeResultEnvelope 引用 → 提交 NodeAttempt → MAF 再推进下游。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class NodeResultStatus(str, Enum):
    """节点完成 ≠ Validator 通过 ≠ Run 成功（06 基线 11.3）。"""

    COMPLETED = "COMPLETED"
    NEEDS_INPUT = "NEEDS_INPUT"
    REWORK_REQUIRED = "REWORK_REQUIRED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class ArtifactRef:
    """对不可变制品版本的结构化引用（04 基线：sha256 为裸 64 位小写十六进制，两套 Digest 不可混用）。"""

    artifact_id: str
    sha256: str
    media_type: str
    size: int


@dataclass(frozen=True)
class NodeInputEnvelope:
    schema_version: str = "1.0"
    project_id: str = ""
    run_id: str = ""
    workflow_version_id: str = ""
    node_key: str = ""
    attempt_no: int = 1
    task_id: str = ""
    role_ref: str = ""
    trace_id: str = ""
    payload: dict | None = None
    input_artifact_refs: tuple = ()
    acceptance_criteria: tuple = ()
    capability_ceiling: tuple = ()
    budget: dict | None = None
    workspace_grant_ref: str | None = None
    previous_attempt_ref: str | None = None
    approval_decision_ref: str | None = None


@dataclass(frozen=True)
class NodeResultEnvelope:
    schema_version: str = "1.0"
    project_id: str = ""
    run_id: str = ""
    node_key: str = ""
    attempt_no: int = 1
    status: NodeResultStatus = NodeResultStatus.COMPLETED
    summary: str = ""
    payload: dict | None = None
    output_artifact_refs: tuple = ()
    evidence_refs: tuple = ()
    assumptions: tuple = ()
    risks: tuple = ()
    open_questions: tuple = ()
    metrics: dict | None = None
    errors: tuple = ()
    handoff_recommendation: str = ""
    completed_at: datetime | None = None