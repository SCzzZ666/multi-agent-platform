# ai-native —— 多角色 Agent 协作平台

对应 `document_modified/` 下 01—12 冻结设计基线（MOD-BL-2026-09-14-01 等）。
任何涉及公共合同 / MAF 映射 / 安全边界 / 三模板 / 交付范围的改变，**必须先写 DCR 并经用户确认**，
不得以实现便利静默改基线。

## 三条最高红线

1. Worker / 平台不得实现 DAG 推进（MAF 是唯一 Workflow 执行引擎）。
2. 一切副作用必过 Capability Gateway + 09 统一安全闸门（先有 InvocationIntent 才派发）。
3. 宿主修改只能走 Patch Apply（独立审批 + 预检 + before-image + journal）；Runner 默认禁 Shell、禁直写宿主。

## 目录

- `backend/` — API + Worker 控制平面（uv workspace 成员）
  - `src/ai_native/runtime/maf/` ★全仓唯一可 import MAF 的适配包
  - `src/ai_native/providers/` 供应商 SDK 唯一允许位置
  - `src/ai_native/modules/` 11 个纵向业务模块（domain/application/ports/adapters/api）
- `runner/` — 受限执行边界（Python，独立依赖集）
- `frontend/` — React 19 + Vite + React Flow（React 19 用 `@xyflow/react`）
- `host-bridge/` — .NET 10 LTS（Windows 句柄身份 / 受控读 / Patch Apply）
- `tests/` — architecture / contracts / integration / security / e2e / fixtures
- `design-contracts/` — 07—09 机器合同只读副本（唯一事实源在 `document_modified/`）

## 交付路线（四周 compressed → 四天，详见 12 号基线）

Day1 后端基础 + MAF 协作内核 + 三家模型 → Day2 Skills 引擎 → Day3 Web 控制台 → Day4 三模板真实端到端 + 发布材料。

## 开发环境

- Python 3.12 / uv workspace；Node 22 / pnpm；.NET 10 LTS（Host Bridge）；Docker（Runner 容器）
- 根目录 `uv lock && uv sync` 安装 backend + runner
- 后端启动（Day 1 完成后）：`uv run --package ai-native-backend uvicorn ai_native.entrypoints.api:app`