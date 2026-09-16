# 第 1 周收口核对卡

> 使用对象：开发负责人 / 代码检察员，逐条把 DEVLOG 自评还原为「基线原文→代码证据→缺口→判定」。
> 比对基线：`document_modified/12_开发顺序和验收标准/12_开发顺序与验收标准设计基线_v1.0.md`（DELIVERY-BL-2026-09-15-01）§4.3 与 §8。
> 需求身份：`document_modified/01_产品目标和范围/04_需求追踪矩阵.md`（58 REQ/TC，当前全部"待开发验证"，未在本文改动任何 TC 状态）。
> 生成日期：2026-09-16（Day 1 收口时点）。状态约定同 DEVLOG：✅ 已真实完成并验证 · ⚠️ 达成但带缺口 · ❌ 未完成 · ⬜ 未开始。
> 诚实原则：判定只认真实代码 + 真实运行产物 + 测试证据；本卡自身也遵守"DCR/基线是唯一事实源，卡是核对工具"。

---

## 0. 收口总判定

**第 1 周"核心达成"成立，但口径要精确**：7 条完成条件里 **5 条 ✅、2 条 ⚠️（可启动但最小 / 模型已打通但无回归）**；真正的风险不在"7 条"里，而在 **5 项 Day1 残留**，其中 2 项（git 0 commit、43 表迁移未建）会直接阻断第 2 周起量。

一句话：**最难的三件事（真实 MAF 最小图、8 角色映射、三家真实模型）已经用真实组件证明了；但"后端能用"的标志——发布 Definition→建 Run→202→SSE 这条业务主线——尚未接通，且所有代码还没有一个 git 回滚点。**

---

## 1. 完成条件核对（§4.3 七条）

### 1.1 后端进程和数据库可以在开发环境启动

- **基线原文**：后端进程和数据库可以在开发环境启动
- **代码证据**：[entrypoints/api.py](backend/src/ai_native/entrypoints/api.py)（uvicorn 起 → `GET /healthz` 200）；[migrations/versions/0001_foundation.py](backend/migrations/versions/0001_foundation.py)（建 `platform` schema + `vector` 扩展）；DEVLOG §1.1 记录 PG18+pgvector 容器 Up、`alembic current → 0001 (head)`
- **缺口**：① API 只有 `/healthz`，无任何 07 合同业务路由；② `healthz` 不检查 DB 就绪，只返回静态字段；③ 数据库"可启动"只到空 schema，43 张业务表未建（见残留 #2）
- **判定**：⚠️ 字面达成，但属于"最小可启动"，不是"后端可用"

### 1.2 公共合同及 08、09 机器合同可解析且引用闭合

- **基线原文**：公共合同及08、09机器合同可解析且引用闭合
- **代码证据**：`design-contracts/`（9 份合同 + README）；[tests/contracts/test_contracts_parse.py](tests/contracts/test_contracts_parse.py) 3 用例通过（`test_nine_contracts_all_parse` / `test_openapi_is_3x` / `test_external_refs_resolve`）
- **缺口**：仅"解析 + 引用闭合"静态层达成；"API 按合同实现"是残留 #3（最薄主线）
- **判定**：✅ 完成条件本身只要求解析闭合，本条真实达成

### 1.3 真实 MAF 可以构建并执行最小无环 Workflow

- **基线原文**：真实MAF可以构建并执行最小无环Workflow
- **代码证据**：[runtime/maf/minimal_dag.py](backend/src/ai_native/runtime/maf/minimal_dag.py) 真实 `from agent_framework import WorkflowBuilder/Executor/WorkflowContext/WorkflowRunResult`，`normalize→reverse→tag` 跑通 → `outputs=['FAM OLLEH::DONE']`；[runtime/maf/closed_loop.py](backend/src/ai_native/runtime/maf/closed_loop.py) 单条真实闭环（planner→确定性校验→条件路由→engineer→validator→ArtifactRef）
- **缺口**：最小图为纯 `transform` 类 Executor；六类节点（agent/skill/tool/condition/approval）完整映射、HITL、PG Checkpoint 自研均未做（见残留 #4，属开工地图第 16 节最高风险）
- **判定**：✅ 最小无环图真实跑通；六类节点全映射属 P4 范畴，不判定为本条失败但必须列残留

### 1.4 八个角色身份保持不变，"指挥官—专家—验证者"映射正确

- **基线原文**：八个角色身份保持不变，“指挥官—专家—验证者”映射正确
- **代码证据**：[modules/catalog_registry/domain/roles.py](backend/src/ai_native/modules/catalog_registry/domain/roles.py)（8 角色 + 三层称谓映射 + 不变式写入 docstring）；[tests/architecture/test_roles.py](tests/architecture/test_roles.py) 5 用例通过（`test_exactly_eight_roles` / `test_planner_is_sole_coordinator` / `test_validator_is_independent_gate` / `test_expert_layer_is_six_roles` / `test_fixed_role_checker`）
- **缺口**：无
- **判定**：✅

### 1.5 三家以上模型经统一端口获得真实响应，并记录模型身份、错误和用量

- **基线原文**：三家以上模型经统一端口获得真实响应，并记录模型身份、错误和用量
- **代码证据**：[providers/ports.py](backend/src/ai_native/providers/ports.py)（统一 `ModelProviderPort` + `ModelUsage.is_known()`，用量未知记 None 不记 0）；[providers/openai_compat.py](backend/src/ai_native/providers/openai_compat.py)（httpx 真实调用 `/chat/completions`，流式/非流式都实现，供应商异常转 `ProviderError` 不含明文凭据）；DEVLOG §1.3 记录三家真实用量 dashscope(in12/out61)/deepseek(in8/out23)/kimi(in89/out179)
- **缺口**：三家"真实响应"是 spike/脚本级证据，**无自动化网络回归用例**——31 个 pytest 用例 1.19s 跑完、一个网络/DB 调用都没有；模型一旦供应商侧变动，无测试能复现"打通"结论
- **判定**：✅ 真实打通（证据在 DEVLOG §1.3，非 mock），但需在后续补回归用例，否则本条可再生性不足

### 1.6 Worker 代码中没有第二套 DAG 推进逻辑

- **基线原文**：Worker代码中没有第二套DAG推进逻辑
- **代码证据**：[entrypoints/worker.py](backend/src/ai_native/entrypoints/worker.py) 当前为空占位（仅 docstring 声明"严禁写第二套 DAG"）；[tests/architecture/test_maf_isolation.py](tests/architecture/test_maf_isolation.py) 静态扫描强制 `agent_framework` 只能在 `runtime/maf/` 内 import
- **缺口**：Worker 尚未实现，本条是"没写"而非"写了也没写 DAG"；真正的防线是开工地图红线卡 A，需在 Worker 填实现后持续用架构测试守住
- **判定**：✅（当前成立，靠架构守护测试从第一天机器守住）

### 1.7 失败路径和未完成能力如实显示，不伪造 Run 成功

- **基线原文**：失败路径和未完成能力如实显示，不伪造Run成功
- **代码证据**：[plan_validator.py](backend/src/ai_native/runtime/plan_validator.py) 对抗路径 `commander`→`INVALID + PLAN_INVALID_ROLE` 不放行；[closed_loop.py](backend/src/ai_native/runtime/maf/closed_loop.py) `RejectExecutor` 形成 CANCELLED 路径；DEVLOG §1.5 阻塞表 / §1.6 残留如实列，不删"非全绿"记录
- **缺口**：无（这是过程性与诚实性检查，当前落实良好）
- **判定**：✅

---

## 2. Day 1 残留（DEVLOG §1.6 五项，含归属与风险）

| # | 残留项 | 真实证据 | 归属 / 风险 | 建议 |
|---|---|---|---|---|
| R1 | Run/NodeAttempt/RunPlanVersion 落库（当前闭环内存态） | [closed_loop.py](backend/src/ai_native/runtime/maf/closed_loop.py) 全程内存态，`run_snapshot`/`run`/`node_attempt` 表未建 | 第 2 周 `workflow_runtime` 模块 · 中 | 与 R2 一并做，落库需先有表 |
| R2 | identity/run 43 表族完整迁移（当前仅 foundation 0001） | [0001_foundation.py](backend/migrations/versions/0001_foundation.py) 只建 schema+vector | 第 1 周收口/第 2 周 · **高（阻断 R3）** | 承接 04 `02_初始迁移设计.sql`，按 12 步落 Alembic，先空库跑通 |
| R3 | 后端最薄主线：发布 Definition→建 Run→202+Operation→SSE | [api.py](backend/src/ai_native/entrypoints/api.py) 只有 `/healthz`；[worker.py](backend/src/ai_native/entrypoints/worker.py) 空占位 | 第 2 周 · **高（后端"能用"的标志）** | 依开工地图 §12.4 第 4 步纵切：identity→definition→runtime→artifacts→operations |
| R4 | P4 补完：superstep 展示 / HITL / PG Checkpoint 自研存储 | 未开始，无对应代码 | 第 2 周及以后 · **最高（开工地图第 16 节风险 #1/#2）** | 先写 spike 核对 1.18.0 真实 API 签名；杀 Worker 故障注入验证不重做副作用 |
| R5 | git 首次 commit（当前 0 commit） | `git log` 无提交，全文件 untracked | **立即（今天）** · **极高（无回滚点，误操作即全丢）** | 确认 `.env`/密钥被 `.gitignore` 挡住后 commit Day 1，锁首个回滚点 |

---

## 3. 测试真实分布（2026-09-16 实测 `pytest -q`）

```
31 passed in 1.19s
  tests/architecture     25 用例 / 6 文件   (envelopes 4, maf_isolation 2, maf_routing 2,
                                             plan_validator 9, provider_registry 3, roles 5)
  tests/contracts         3 用例 / 1 文件   (nine_contracts_all_parse, openapi_is_3x, external_refs_resolve)
  tests/integration       3 用例 / 1 文件   (artifact_store: put_get/digest_mismatch/distinct_content)
```

- 关键诚实点：**integration 只覆盖本地内容寻址 ArtifactStore，不覆盖 PostgreSQL**；整套测试无网络、无 DB、无真实模型回归。
- 三家模型真实响应（条件 1.5）当前是 DEVLOG 记录 + `closed_loop.py` 脚本级证据，非可自动复现的回归。

---

## 4. 收口结论 → 移交第 2 周

- **第 1 周判据**：5/7 ✅ + 2/7 ⚠️，"核心达成"成立；5 项残留全部实名挂账，无"全绿"造假。
- **第 2 周启动前置（按优先级）**：R5（commit）→ R2（43 表迁移）→ R3（最薄主线）→ R1（Run 落库），R4（HITL/PG Checkpoint）作为持续技术验证项与第 2 周并行。
- 进入第 2 周后，本卡按 §5 更新约定滚动为"第 2 周收口核对卡"，比对对象切换到同基线 §5.3（Skills 引擎完成条件）+ 开工地图第 5.5 节（Skill Runtime/Registry）。

---

## 5. 更新约定（每次开发后）

1. 本卡与 [DEVLOG.md](DEVLOG.md) 同步维护：DEVLOG 记"做了什么"，本卡记"对上哪条完成条件/还有哪些缺口"。
2. 判定列只写四种（✅/⚠️/❌/⬜），⚠️ 必须写清"达成了什么 + 缺什么"。
3. 新增"完成条件"时先回链 `12_基线` §4.3/5.3/6.3/7.4 原文，不自行扩缩条件。
4. 涉及合同/MAF/安全边界/三模板/交付范围的变化，先立 DCR，再改本卡（卡不替代基线）。