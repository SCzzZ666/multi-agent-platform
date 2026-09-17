"""Worker 进程入口（编排内核 + HITL 版）。

职责白名单（02 基线 / D10-08）：命令领取、租约与 fencing、运行宿主、资源/预算控制、
调 RuntimeAdapter、恢复协调、事实投影。DAG 推进/HITL 等待/Checkpoint 归 MAF。

- run_once: 领 Run → 由 08 定义编译 MAF → 真实执行；命中 approval 节点则转 WAITING_APPROVAL
- approve_run: 人审结论后就 (resume with responses) → SUCCEEDED / CANCELLED(APPROVAL_REJECTED)

HITL 为内存态（同一 workflow 对象续跑）；跨进程恢复依赖 PG Checkpoint(R4 待补)。
"""
from __future__ import annotations

import asyncio
import sys
import uuid

from ai_native.bootstrap.config import Settings
from ai_native.bootstrap.db import SessionLocal, project_context
from ai_native.modules.workflow_definition.adapters.orm import WorkflowVersion
from ai_native.modules.workflow_runtime.adapters.orm import Run
from ai_native.modules.workflow_runtime.application import worker_service
from ai_native.providers.openai_compat import OpenAICompatProvider
from ai_native.runtime.maf.approval import ApprovalResponse
from ai_native.runtime.maf.compiler import compile_definition

# 内存态 HITL：run_id(str) → (workflow, definition)
_WORKFLOWS: dict[str, tuple] = {}


def _build_workflow(definition: dict, s: Settings):
    provider = OpenAICompatProvider("dashscope", s.dashscope_api_key, s.dashscope_base_url)
    return compile_definition(definition, provider=provider, model="qwen-plus")


def _approval_request_id(definition: dict) -> str | None:
    for n in definition["nodes"]:
        if n["kind"] == "approval":
            return f"approval:{n['node_key']}"
    return None


async def run_once(project_id) -> tuple:
    s = Settings.load()
    db = SessionLocal()
    try:
        ctx = str(project_id)
        project_context(db, ctx)
        run = worker_service.claim_next_run(db)
        if run is None:
            db.rollback()
            return None, "no_run", None
        rid = run.id
        wv_id = run.workflow_version_id
        db.commit()

        project_context(db, ctx)
        definition = db.get(WorkflowVersion, wv_id).definition_json
        db.rollback()

        workflow = _build_workflow(definition, s)
        try:
            result = await workflow.run({"input": "开发一个 TODO 应用"})
        except Exception as e:  # noqa: BLE001
            project_context(db, ctx)
            run = db.get(Run, rid)
            worker_service.fail_run(db, run, str(e))
            db.commit()
            print(f"[worker] 失败→FAILED: {str(e)[:160]}")
            return run, "failed", None

        if list(result.get_request_info_events()):
            reqid = _approval_request_id(definition)
            _WORKFLOWS[str(rid)] = (workflow, definition)
            project_context(db, ctx)
            run = db.get(Run, rid)
            worker_service.set_waiting_approval(db, run, reqid)
            db.commit()
            print(f"[worker] 暂停等待审批 request_id={reqid}")
            return run, "waiting_approval", reqid

        project_context(db, ctx)
        run = db.get(Run, rid)
        for node in definition["nodes"]:
            worker_service.project_node(db, run, node)
        worker_service.complete_run(db, run)
        db.commit()
        print(f"[worker] {rid} → SUCCEEDED, projected {len(definition['nodes'])} nodes")
        return run, "succeeded", None
    finally:
        db.close()


async def approve_run(project_id, run_id, approved: bool, reason: str = "") -> str:
    holder = _WORKFLOWS.get(str(run_id))
    if holder is None:
        return "no_inmemory_workflow"
    workflow, definition = holder
    s = Settings.load()
    db = SessionLocal()
    try:
        reqid = _approval_request_id(definition)
        result = await workflow.run(
            responses={reqid: ApprovalResponse(approved=approved, reason=reason)}
        )
        ctx = str(project_id)
        project_context(db, ctx)
        run = db.get(Run, run_id)
        if approved:
            worker_service.resume_from_approval(db, run, reason)
            for node in definition["nodes"]:
                worker_service.project_node(db, run, node)
            worker_service.complete_run(db, run)
            db.commit()
            print(f"[worker] 审批通过 → {run.state}")
            return "succeeded"
        else:
            worker_service.reject_run(db, run, reason)
            db.commit()
            print(f"[worker] 审批拒绝 → {run.state}")
            return "rejected"
    finally:
        db.close()
        _WORKFLOWS.pop(str(run_id), None)


async def main() -> None:
    if len(sys.argv) < 2:
        print("用法: worker <project_id>")
        print("      worker approve <project_id> <run_id> approved|rejected")
        return
    if sys.argv[1] == "approve":
        project_id = uuid.UUID(sys.argv[2])
        run_id = uuid.UUID(sys.argv[3])
        approved = sys.argv[4].lower().startswith("appr")
        print("resume:", await approve_run(project_id, run_id, approved))
        return
    project_id = uuid.UUID(sys.argv[1])
    _, status, _ = await run_once(project_id)
    print(f"[worker] status={status}")


if __name__ == "__main__":
    asyncio.run(main())