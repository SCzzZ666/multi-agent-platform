"""Worker 进程入口（编排内核落库版）。

职责白名单（02 基线 / D10-08）：命令领取、租约与 fencing、运行宿主、资源/预算控制、
调 RuntimeAdapter、恢复协调、事实投影。Executor 激活/Edge 路由/条件/并行/汇合/HITL/Checkpoint 归 MAF。

用法：`python -m ai_native.entrypoints.worker <project_id>`（项目作用域内领一个 QUEUED Run 执行）。
支撑说明：跨项目命令队列的领取需非 RLS 的 command 表/安全函数，属后续「持久命令」硬化项。
"""
from __future__ import annotations

import asyncio
import sys
import uuid

from sqlalchemy import text

from ai_native.bootstrap.config import Settings
from ai_native.bootstrap.db import SessionLocal, project_context
from ai_native.modules.workflow_definition.adapters.orm import WorkflowVersion
from ai_native.modules.workflow_runtime.adapters.orm import Run
from ai_native.modules.workflow_runtime.application import worker_service
from ai_native.providers.openai_compat import OpenAICompatProvider
from ai_native.runtime.maf.compiler import compile_definition


async def run_once(project_id) -> int:
    s = Settings.load()
    db = SessionLocal()
    try:
        ctx = str(project_id)
        # 事务①：领 Run（QUEUED→RUNNING + 租约 + RUN_STARTED）
        project_context(db, ctx)
        run = worker_service.claim_next_run(db)
        if run is None:
            db.rollback()
            return 0
        rid = run.id
        workflow_version_id = run.workflow_version_id
        db.commit()

        # 读定义（新事务，重设上下文）
        project_context(db, ctx)
        version = db.get(WorkflowVersion, workflow_version_id)
        definition = version.definition_json
        db.rollback()

        # 编译 + 跑 MAF（不在 DB 事务内）
        provider = OpenAICompatProvider("dashscope", s.dashscope_api_key, s.dashscope_base_url)
        workflow = compile_definition(definition, provider=provider, model="qwen-plus")
        try:
            result = await workflow.run({"input": "开发一个 TODO 应用"})
            outputs = list(result.get_outputs()) if result else []
            print(f"[worker] MAF 执行完成 outputs={len(outputs)}")
        except Exception as e:  # noqa: BLE001
            project_context(db, ctx)
            run = db.get(Run, rid)
            worker_service.fail_run(db, run, str(e))
            db.commit()
            print(f"[worker] 执行失败并落 FAILED: {str(e)[:200]}")
            return 1

        # 事务②：投影节点 + 终态（SUCCEEDED）
        project_context(db, ctx)
        run = db.get(Run, rid)
        for node in definition["nodes"]:
            worker_service.project_node(db, run, node)
        worker_service.complete_run(db, run)
        db.commit()
        print(f"[worker] Run {rid} → SUCCEEDED，projected {len(definition['nodes'])} nodes")
        return 1
    finally:
        db.close()


async def main() -> None:
    if len(sys.argv) < 2:
        print("用法: python -m ai_native.entrypoints.worker <project_id>")
        return
    project_id = uuid.UUID(sys.argv[1])
    n = await run_once(project_id)
    print(f"[worker] processed={n}")


if __name__ == "__main__":
    asyncio.run(main())