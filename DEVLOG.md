# 开发日志 (DEVLOG)

> 本文件是项目持续更新的开发日志。**每次开发后补充/修订**，用于核对整体链路进度。
> 状态约定：✅ 已真实完成并验证 · ⏳ 进行中 · ❌ 阻塞 · ⬜ 未开始
> 诚实原则：只记录真实落地并验证的结果，失败/阻塞/残留如实标注，不伪造成功。

---

## 0. 交付路线总览（4 天 = 计划四周）

| 开发日 | 对应计划 | 内容 | 状态 |
|---|---|---|---|
| **Day 1** | 第 1 周 | 后端基础 + MAF 协作内核 + 三家模型 | ✅ 核心达成（见 §1） |
| Day 2 | 第 2 周 | 编排完整化（六类节点/HITL/安全底座）+ Skills 能力层 | ⏳ 核心达成（见 §2） |
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

## 2. Day 2（第 2 周）—— 实际开发记录

> 实际重心：**把 MAF 编排从「内存最小闭环」落成「数据驱动 + 落库 + 六类节点 + 安全底座」的完整形态**；
> Skills 作为首个被编排的模板载体（不是「只做 skill 封装」）。

### 2.1 已完成块（真实证据，非 mock）

| 块 | 内容 | commit | 真实证据 |
|---|---|---|---|
| 0 | operations_events（outbox + SSE 游标 + Operation 回执 + 审计摘要链） | `2f9c53a` | 事件/outbox/审计三点同事务落库断言；SSE `after_sequence` 去重 live 验证 |
| 1 | Run/NodeAttempt 状态机 + 编排内核落库 | `f24c2cf` | QUEUED→SUCCEEDED、6×NodeAttempt、9 事件流 |
| 2 | 六类节点全映射 agent/transform/condition/approval/skill/tool **（6/6）** | `b25b636` `ae4c158` `3797b13` | approval→MAF HITL(通过/拒绝)；skill 装载固定版本；tool 经 Gateway(Intent+Receipt) |
| 3 | Skills 能力层：SKILL.md 解析 + 封闭路径 + 静态扫描 + 不可变版本目录 | `9584e58` | 7 测试；热加载追加不覆盖 |
| 4 | 安全底座：JCS / 九层交集 PDP / ActionBinding 三摘要 / Intent 状态机 / 审批原子消费 / Credential Broker / Runner(ExecutionProfile 内核) | `dcf791c`…`16585e2` `d4ea858` | 安全域 + 审批消费(5 用例) + Credential(5) + ExecutionProfile(8) |

### 2.2 关键真实验证

- **编排内核**：Worker 领 Run(租约/fencing) → 由 08 定义数据驱动编译 MAF → 真实模型 agent → NodeAttempt+事件落库 → SUCCEEDED
- **HITL**：通过 `WAITING_APPROVAL→RUNNING→SUCCEEDED`；拒绝 `CANCELLED + APPROVAL_REJECTED`
- **skill 节点**：发布 Skill(固定版本) → 工作流挂 skill 节点 → 装载该版本指令 → SUCCEEDED(3 节点)
- **tool 节点**：经 Gateway 派发 → `InvocationIntent(SUCCEEDED, READ_ONLY)` + `InvocationReceipt(SUCCEEDED)` 落库
- **审批原子消费**：通过/幂等/拒绝/摘要不匹配/重鉴权拒绝；含审计+outbox 同事务
- **测试**：93 passed（默认套件）+ 1 real_model（`pytest -m real_model`）

### 2.3 用户 QA 揪出并修复的 5 处硬伤（`65d59e7`）

1. PDP 空候选 scope fail-open → 改 DENY
2. 派发前重鉴权 `member=True` 写死 → 改参数传入
3. 两份相反 Invocation 状态机都绿 → 删错误的 `invocation.py`（保留 `intent.py`）
4. 消费事务缺审计/outbox → 补 `append_audit`+`emit_event`
5. `fencing_token` 收了不校验 → 比对 `run_lease`

### 2.4 尚未完成（如实挂账）

- **块5**：TemplateResolver(11 §11.1) / Skills 模板真实闭环（skill_maintainer→检查→validator→HITL→publish Tool 含 Receipt）
- **块6**：20 有效 Skill / 提示词可解析机制 / 测试交付物(D12-11)
- **收尾**：identity 归档(D06-10)/成员、workflow_definition 完整语义校验、**fencing 递增/接管**（现写死 token=1）
- **PG Checkpoint 自研** + 恢复语义（现为内存态 HITL 续跑）
- **Runner 实际进程**：子进程执行/工作副本/网络隔离/凭据注入清理/输出采集（现仅 Profile+argv 内核）
- **并行 QA 观察**：仓库中存在非本人提交（`7d99845`/`5c8415e`/`c86df44` 等）在重构安全域/补测试/改本日志，测试均绿；来源待用户确认

---

## 3. 更新约定（每次开发后）

1. 在对应「开发日」小节**追加/修订**本次改动：文件、真实证据、踩坑、阻塞与解决。
2. 更新 §0 状态表和对应周完成条件核对表。
3. 状态只标真实结果；失败与残留如实写入，不删除「非全绿」记录。
4. 涉及公共合同/MAF 映射/安全边界/三模板/交付范围的变化，先记 DCR。

> 基线 / 合同唯一事实源仍在 `document_modified/`（MOD-BL-2026-09-14-01 等）；本日志只记录进度，不替代冻结基线。