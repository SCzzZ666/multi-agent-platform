# 开发日志 (DEVLOG)

> 本文件是项目持续更新的开发日志。**每次开发后补充/修订**，用于核对整体链路进度。
> 状态约定：✅ 已真实完成并验证 · ⏳ 进行中 · ❌ 阻塞 · ⬜ 未开始
> 诚实原则：只记录真实落地并验证的结果，失败/阻塞/残留如实标注，不伪造成功。

---

## 0. 交付路线总览（4 天 = 计划四周）

| 开发日 | 对应计划 | 内容 | 状态 |
|---|---|---|---|
| **Day 1** | 第 1 周 | 后端基础 + MAF 协作内核 + 三家模型 | ✅ 核心达成（见 §1） |
| Day 2 | 第 2 周 | Skills 引擎 + 20 Skill + 提示词雏形 | ⬜ 未开始 |
| Day 3 | 第 3 周 | Web 控制台 + 50 Skill + 200 提示词 | ⬜ 未开始 |
| Day 4 | 第 4 周 | 三模板真实端到端 + 发布材料 + 58 TC | ⬜ 未开始 |

---

## 1. Day 1（第 1 周）—— 后端基础 + MAF 内核 + 三家模型

### 1.1 第 1 周完成条件核对（7/7 ✅）

| # | 完成条件 | 状态 | 真实证据 |
|---|---|---|---|
| 1 | 后端进程 + 数据库可启动 | ✅ | `uvicorn` → `GET /healthz 200`；PG18+pgvector 容器 Up；`alembic current → 0001 (head)` |
| 2 | 07/08/09 合同可解析+引用闭合 | ✅ | `test_contracts_parse` 3 通过（9 份全解析 + 双风格 $ref 闭合） |
| 3 | 真实 MAF 构建执行最小无环图 | ✅ | `minimal_dag.py` → `outputs=['FAM OLLEH::DONE']` |
| 4 | 8 角色 + 三层称谓映射 | ✅ | `test_roles` 5 通过（机器守护不变式） |
| 5 | **三家模型真实响应** | ✅ | 3/3：dashscope/qwen-plus、deepseek/deepseek-flash、kimi/kimi-k3，均真实 response + usage |
| 6 | Worker 无第二套 DAG | ✅ | MAF 只在 `runtime/maf/`（架构守护测试强制） |
| 7 | 失败/未完成如实 | ✅ | validator 主动 REWORK（4 项真实缺陷）；kimi 过载如实重试 |

### 1.2 已落地文件清单（相对 `project/`）

- 骨架：根/backend/runner 三份 `pyproject.toml`、`frontend/package.json`、`host-bridge/global.json`、`.gitignore`、`.env.example`、`.python-version`、`README.md`、`uv.lock`
- 合同：`design-contracts/`（9 份机器合同，镜像 07/08/09 子目录，解决 openapi 相对 $ref）
- 数据库：`backend/alembic.ini` + `backend/migrations/{env.py, script.py.mako, versions/0001_foundation.py}`
- 后端：
  - `shared_kernel/{ids,digest,time}.py`（UUIDv7 / sha256 / utcnow）
  - `bootstrap/config.py`（.env 装载 + Settings）
  - `providers/{ports,openai_compat,dashscope,registry}.py`（统一端口归一化三家）
  - `runtime/{plans,plan_validator,conditions,envelopes}.py`（计划模型 / 确定性校验 / 三态路由 / 交接信封）
  - `runtime/maf/{minimal_dag,agent_loop,closed_loop}.py`（MAF 仅此包）
  - `modules/catalog_registry/domain/roles.py`（8 角色）
  - `modules/artifacts_evidence/{ports/store.py,adapters/local.py}`（内容寻址存储）
  - `entrypoints/{api,worker}.py`
- 测试：`tests/{architecture(6),contracts(1),integration(1)}` 共 31 用例

### 1.3 关键真实证据（非 mock）

- MAF 最小无环图：normalize→reverse→tag → `final_state=IDLE, outputs=['FAM OLLEH::DONE']`
- MAF 双 agent 真实模型：planner 产出 3 步计划、validator 给 **REWORK**（缺 API key 管理/错误降级/响应式/HTTPS 等）
- **单条真实闭环** `closed_loop.py`：planner→确定性校验(VERDICT=VALID,0 诊断)→条件路由(EXECUTE)→engineer(1962 字节 Markdown 落盘)→validator(REWORK)→ArtifactRef 交接
- 对抗路径：非法角色 `commander` → `INVALID + PLAN_INVALID_ROLE`，不放行
- MAF 条件路由双分支独立验证：`test_maf_routing` 2 通过
- 三家模型：dashscope(in12/out61)、deepseek(in8/out23)、kimi(in89/out179)，均有真实用量

### 1.4 踩坑记录（复用时避免重犯）

1. **MAF 真实包名是 `agent_framework`**（下划线），不是 `agent_framework_core`。
2. Windows 下 `configparser` 用 **GBK 读 .ini**：`alembic.ini` 必须纯 ASCII。
3. PG18 `pg_available_extensions` 列名是 **`default_version`**（无 `extversion`）。
4. Kimi 旧型号 `moonshot-v1-8k`/`kimi-latest` 已 **404 下线**；走 `.cn` 端点用 **`kimi-k3`**；kimi-k3 是推理模型（CoT 在 `reasoning_content`，勿并入 content）。
5. MAF 模型桥接在拆分包 **`agent-framework-openai`**（最新 1.14.3，与 core 1.18.0 版本漂移但实测兼容）；百炼只支持 chat/completions → 用 `OpenAIChatCompletionClient`。
6. `uv sync` 在 workspace 根只装根项目，装成员须 `uv sync --all-packages`。

### 1.5 阻塞与解决记录

| 阻塞 | 结果 |
|---|---|
| 百炼第一把 key（sk-sp-…）401 | 换 sk-ws-… 解决（真实验证） |
| agent-framework-openai==1.18.0 不存在 | 改用 >=1.14.3（版本漂移已记录） |
| Kimi 404 / 429 过载 | 改模型名 kimi-k3 + 带退避重试 |

### 1.6 Day 1 残留（QA 卡 R1-R5，按 §4 顺序推进）

- [x] **R5 git 首次 commit** —— ✅ `aba8fc6`，`.env` 已确认不入库（`git ls-files` 无 .env）
- [x] **R2 43 表族完整迁移** —— ✅ `alembic 0002-0013 (head)`：43 表 + sha256_digest 域 + 6 不可变触发器 + RLS(35) + 索引；种子 8 角色/3 模板；PG18 实测核对通过
- [x] **R3 后端最薄主线** —— ✅ identity_project / workflow_definition（08 schema 校验 + publish）/ workflow_runtime（Run+RunEvent 落库）/ artifacts_evidence（登记）；真实 API 打通「发布 Definition→建 Run 202+Operation→SSE RUN_CREATED」，live uvicorn 实测 + 2 e2e 测试
- [x] **R1 Run 落库** —— ✅（run / run_snapshot / run_event 真实落库）；NodeAttempt / RunPlanVersion 的代码写在 Worker/MAF 集成时补（R4）
- [x] **QA 1.5 模型回归** —— ✅ `tests/integration/test_models_real.py` 真实调三家 + 证据 JSON（D12-11 §8.2）；默认套件排除，`-m real_model` 显式跑
- [ ] R4 P4 补完：superstep / HITL / PG Checkpoint 自研存储（并行持续项）

---

## 2. 待办 / 下一步

1. **commit Day 1**（建议优先，锁回滚点；确认 `.env` 被 gitignore 挡住）
2. **Day 2 Skills 引擎**：包解析 / 封闭路径 / 不可变版本 / 受控热加载 + 经 Gateway+Runner 受控执行脚本，20 个有效 Skill，Skills 模板首个闭环

---

## 3. 更新约定（每次开发后）

1. 在对应「开发日」小节**追加/修订**本次改动：文件、真实证据、踩坑、阻塞与解决。
2. 更新 §0 状态表和对应周完成条件核对表。
3. 状态只标真实结果；失败与残留如实写入，不删除「非全绿」记录。
4. 涉及公共合同/MAF 映射/安全边界/三模板/交付范围的变化，先记 DCR。

> 基线 / 合同唯一事实源仍在 `document_modified/`（MOD-BL-2026-09-14-01 等）；本日志只记录进度，不替代冻结基线。