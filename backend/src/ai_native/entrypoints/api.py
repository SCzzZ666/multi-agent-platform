"""API 进程入口（第 1 周主线版）。

约束（02 基线 / D10）：本进程不得 import MAF、不得直接执行 Tool、不得访问宿主绝对路径。
提供：/healthz（存活）、/healthz/ready（DB 就绪）、identity_project / workflow_definition /
workflow_runtime 三条业务模块路由的挂载，基址 /api/v1。
MAF 只在 runtime/maf 内由 Worker 侧 RuntimeAdapter 使用。
"""
from __future__ import annotations

from fastapi import FastAPI
from sqlalchemy import text

from ai_native.bootstrap.config import Settings
from ai_native.bootstrap.db import engine
from ai_native.modules.identity_project.api.routes import router as identity_router
from ai_native.modules.operations_events.api.routes import router as ops_router
from ai_native.modules.workflow_definition.api.routes import router as workflow_router
from ai_native.modules.workflow_runtime.api.routes import router as run_router

app = FastAPI(title="ai-native", description="多角色 Agent 协作平台 —— 控制平面 API", version="0.1.0")
app.include_router(identity_router, prefix="/api/v1")
app.include_router(workflow_router, prefix="/api/v1")
app.include_router(run_router, prefix="/api/v1")
app.include_router(ops_router, prefix="/api/v1")


@app.get("/healthz")
def healthz() -> dict:
    s = Settings.load()
    return {"status": "ok", "env": s.env, "profile": s.profile}


@app.get("/api/v1/healthz/ready")
def healthz_ready() -> dict:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception as e:  # noqa: BLE001
        return {"status": "not_ready", "database": str(e)[:200]}