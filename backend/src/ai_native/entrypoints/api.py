"""API 进程入口（Day 1 最小可启动版）。

约束（02 基线 / D10）：本进程不得 import MAF、不得直接执行 Tool、不得访问宿主绝对路径。
MAF 只在 backend/src/ai_native/runtime/maf/ 内由 Worker 侧 RuntimeAdapter 使用。

本文件当前只提供健康检查，用于证明「后端进程可启动」；
业务路由（07 合同 /projects/... 等）在 P3 最薄主线中逐步挂载。
"""
from __future__ import annotations

from fastapi import FastAPI

from ai_native.bootstrap.config import Settings

app = FastAPI(
    title="ai-native",
    description="多角色 Agent 协作平台 —— 控制平面 API",
    version="0.1.0",
)


@app.get("/healthz")
def healthz() -> dict:
    """进程存活检查（DB 就绪检查待 PG 上线后补 /healthz/ready）。"""
    s = Settings.load()
    return {
        "status": "ok",
        "env": s.env,
        "profile": s.profile,
        "model_provider_configured": s.dashscope_api_key is not None,
    }