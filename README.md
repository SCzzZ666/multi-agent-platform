# ai-native · 多角色 Agent 协作平台

> 围绕一个项目目标，配置固定职责 Agent、项目资料与允许能力，运行**可中断、可审批、可追溯**的协作流程，产出有来源的工程／科研成果。
>
> 状态：**Day 1（第 1 周）已收口 · Day 2（第 2 周）核心达成** · 测试 `93 passed`（+1 真实模型回归）
>
> 对应设计基线：`document_modified/` 下 01—12 冻结设计（统一基线 `MOD-BL-2026-09-14-01`）

---

## 1. 项目简介

首期同时交付**三条业务线**（共用同一套底座，差异只在专业执行 DAG / 输入输出合同 / 可用角色 / 能力绑定）：

| 模板 `template_key` | 干什么 | 关键人工决定 | 受控副作用 |
|---|---|---|---|
| **软件工厂** `software_factory` | 需求→设计→隔离副本实现 Patch→检查测试→条件回写 | Patch Apply Approval | 回写宿主（经 Gateway + Host Bridge） |
| **Skills** `skills_factory` | 原始 Skill 包→规范化候选→结构/脚本检查→发布固定版本 | 接受候选 + 发布审批 | 发布 SkillVersion |
| **AI4S** `ai4s` | 研究问题→文献/实验/分析→双质量门→研究报告 | 第二个 Validator 后确认报告 | 受控分析任务（Runner） |

**核心能力**：固定 8 角色 Agent 协作 · 模板化工作流（DAG 可视化编辑）· 可中断/恢复 · 四类审批与审阅隔离 · 制品与证据可追溯 · 本地目录受控回写。

## 2. 架构总览

模块化单体控制平面（**API + Worker 同代码库、两进程**）+ 两个跨安全边界的独立进程（Windows 的 .NET Host Bridge、Linux/WSL 的 Python Runner）。

| 进程／单元 | 位置 | 职责 | 严禁 |
|---|---|---|---|
| Web | `frontend/` | 三栏工作区、DAG 设计器、运行/审批/制品视图 | 直连库、自判授权、推进 Run |
| API | `backend/…/entrypoints/api.py` | 会话、项目作用域、幂等、ETag、命令受理、查询 | import MAF、执行 Tool、访宿主绝对路径 |
| Worker | `backend/…/entrypoints/worker.py` | Run 领取、租约/fencing、MAF 宿主、恢复、事件投影 | **自算 DAG 下一节点、绕过 Gateway** |
| MAF RuntimeAdapter | `backend/…/runtime/maf/` | ★**全仓唯一可 import MAF**：08 定义确定性编译为 MAF 图 | 存公共业务事实、实现第二套调度 |
| Capability Gateway | `backend/…/modules/capability_gateway/` | 授权交集、Intent、派发、Receipt | 让 Approval 提权、让 Connector 自行放行 |
| Host Bridge | `host-bridge/`（.NET 10） | Windows 目录登记、句柄身份、受控读、Patch Apply | MAF、模型、任意命令、通用 DB |
| Runner | `runner/`（Python） | 解析 ExecutionProfile 跑受控任务 | 宿主直写、任意 Shell、平台凭据 |

### 三条最高红线

1. **Worker／平台不得实现 DAG 推进**——MAF 是唯一 Workflow 执行引擎。
2. **一切副作用必过 Capability Gateway + 09 统一安全闸门**——先有 `InvocationIntent` 才派发。
3. **宿主修改只能走 Patch Apply**——独立审批 + 预检 + before-image + journal；Runner 默认禁 Shell、禁直写宿主。

## 3. 技术栈（锁定版）

| 层 | 选型 | 说明 |
|---|---|---|
| 后端 | Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2 · psycopg3 · Alembic · **uv workspace** | `backend/` 与 `runner/` 为 workspace 成员 |
| 编排 | **Microsoft Agent Framework `agent-framework-core==1.18.0`** | 唯一 DAG 引擎，仅用官方图式 Workflow API |
| 模型网关 | 三家 OpenAI 兼容供应商（百炼 `qwen-plus` / DeepSeek `deepseek-chat` / Kimi `kimi-k3`） | 经统一 `ModelProviderPort` 归一化 |
| 数据库 | PostgreSQL 18 系 + pgvector | 43 表 / RLS 纵深防御 / 唯一事实源 |
| 制品 | ArtifactStore 端口 + 本地内容寻址 | 正文不入库，DB 只存引用/摘要/大小/媒体类型 |
| 前端 | React 19 · TypeScript · Vite · React Flow(`@xyflow/react`) · pnpm | API 客户端/事件类型由 07 合同生成 |
| Host Bridge | .NET 10 LTS / C# | 受控 Windows 句柄 / 文件身份 / 本地 IPC |

**首版不引入**：Celery／Redis 队列／Kafka／Temporal／第二套 Agent 框架（命令队列走 PostgreSQL）。

## 4. 目录结构

```text
project/
├─ pyproject.toml / uv.lock          # uv workspace 根
├─ backend/
│  ├─ alembic.ini
│  ├─ migrations/                    # 一条有序 Alembic 迁移链（0001–0013，43 表）
│  └─ src/ai_native/
│     ├─ entrypoints/                # api.py（API 进程）、worker.py（Worker 进程）
│     ├─ bootstrap/                  # 配置装载 / DB 装配 / RLS 项目上下文
│     ├─ modules/                    # 11 个纵向业务模块（domain/application/ports/adapters/api）
│     ├─ runtime/maf/                # ★全仓唯一可 import MAF
│     ├─ runtime/                    # plans / plan_validator / conditions / envelopes / transforms / capabilities
│     ├─ providers/                  # ★供应商 SDK 唯一允许位置
│     └─ shared_kernel/              # UUIDv7 / Digest / JCS / 时间
├─ runner/                           # 受限执行边界（独立依赖集）
├─ frontend/                         # React 19 + Vite
├─ host-bridge/                      # .NET 10
├─ tests/                            # architecture / contracts / integration / security / e2e / fixtures
├─ design-contracts/                 # 07—09 机器合同只读副本（唯一事实源在 document_modified/）
└─ DEVLOG.md                         # 开发日志（每次开发后更新）
```

## 5. 快速开始

### 前置

- Python 3.12 · uv ≥ 0.7 · Node 22 + pnpm · Docker（PostgreSQL）· .NET 10 SDK（Host Bridge，Day 3+）

### 安装

```bash
uv sync --all-packages          # 装 backend + runner 全部依赖（workspace 根只装根项目，须 --all-packages）
```

### 配置

```bash
cp .env.example .env            # 逐项填真实值；.env 已被 .gitignore 排除，绝不入库
```

按 `.env.example` 逐项填：三家模型 key（`DASHSCOPE_API_KEY` / `DEEPSEEK_API_KEY` / `KIMI_API_KEY`，均 OpenAI 兼容端点）、`DATABASE_URL`、`ARTIFACT_STORE_DIR`。

### 起数据库 + 迁移 + 建账户

```bash
# 1) 起 PostgreSQL 18 + pgvector（首次只建超级用户 ai_native）
docker run -d --name ai-native-pg -e POSTGRES_USER=ai_native -e POSTGRES_PASSWORD=ai_native_dev \
  -e POSTGRES_DB=ai_native -p 5432:5432 pgvector/pgvector:pg18

# 2) 迁移（env.py 默认用超级用户 ai_native）→ 0013 (head)：43 表 + RLS + 不可变触发器
cd backend && uv run alembic upgrade head

# 3) 建三账户并授权（迁移/API/Worker 分离；应用连的是 api_user/worker_user）
docker exec -i ai-native-pg psql -U ai_native -d ai_native <<'SQL'
CREATE ROLE migrator LOGIN PASSWORD 'ai_native_dev';
CREATE ROLE api_user LOGIN PASSWORD 'ai_native_dev';
CREATE ROLE worker_user LOGIN PASSWORD 'ai_native_dev';
GRANT USAGE ON SCHEMA platform TO api_user, worker_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA platform TO api_user, worker_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA platform GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO api_user, worker_user;
SQL
```

> RLS 纵深防御：应用在每个新事务前 `SET LOCAL app.project_id`（代码已做），`api_user` 非表所有者/非 superuser 才会被 RLS 约束。

### 已知环境坑（详见 `DEVLOG.md` §1.4）

- MAF 真实包名是 `agent_framework`（非 `agent_framework_core`）；模型桥接在拆分包 `agent-framework-openai`。
- Windows 下 `alembic.ini` 必须纯 ASCII（configparser 用 GBK 读 `.ini`）。
- PG18 `pg_available_extensions` 列名是 `default_version`（无 `extversion`）。
- Kimi 旧型号已下线，用 `kimi-k3`（它是推理模型，CoT 在 `reasoning_content`）。
- `uv sync` 在 workspace 根只装根项目，装成员须 `--all-packages`。

### 起后端

```bash
uv run uvicorn ai_native.entrypoints.api:app --host 127.0.0.1 --port 8000
# GET /healthz（存活）、/api/v1/healthz/ready（DB 就绪）
```

### 跑 Worker

```bash
uv run python -m ai_native.entrypoints.worker <project_id>                    # 领一个 QUEUED Run 执行（可能停在审批）
uv run python -m ai_native.entrypoints.worker approve <project_id> <run_id> approved|rejected
```

### 测试

```bash
uv run pytest                       # 默认套件（93 用例，无网络/无模型）
uv run pytest -m real_model         # 三家模型真实调用回归（需 .env key，落证据 JSON）
```

## 6. 当前进度

### Day 1（第 1 周）— 已收口 ✅

| 号 | 完成条件 | 状态 |
|---|---|---|
| 1 | 后端进程 + 数据库可启动 | ✅ |
| 2 | 07/08/09 合同可解析且引用闭合 | ✅ |
| 3 | 真实 MAF 构建执行最小无环图 | ✅ |
| 4 | 8 角色身份 + 三层称谓映射 | ✅ |
| 5 | 三家模型经统一端口真实响应 | ✅ |
| 6 | Worker 无第二套 DAG 推进 | ✅ |
| 7 | 失败／未完成如实显示 | ✅ |

附带：git 回滚点 · 43 表迁移 · 最薄主线（发布 Definition→建 Run 202→SSE）· Run 落库 · 模型回归用例。

### Day 2（第 2 周）— 核心达成 ⏳

| 块 | 内容 | 状态 |
|---|---|---|
| 0 | operations_events（outbox + SSE 游标 + Operation 回执 + 审计摘要链） | ✅ |
| 1 | Run/NodeAttempt 状态机 + 编排内核落库（Worker→08 定义驱动→MAF→落库） | ✅ |
| 2 | **六类节点 6/6**：agent / transform / condition / approval(HITL) / skill / tool | ✅ |
| 3 | Skills 能力层（SKILL.md 解析 + 封闭路径 + 静态扫描 + 不可变版本目录） | ✅ |
| 4 | 安全底座（JCS / 九层交集 PDP / ActionBinding 三摘要 / Intent / 审批原子消费 / Credential Broker / Runner-Profile） | ✅ |
| 5 | TemplateResolver + Skills 模板真实闭环 | ⬜ 待接 |
| 6 | 20 有效 Skill + 提示词可解析机制 + 测试交付物 | ⬜ 待接 |

**待深化**：PG Checkpoint 自研 + 恢复语义 · Runner 实际进程（子进程/工作副本/网络隔离/凭据注入清理） · fencing 递增/接管 · identity 归档/成员 · workflow_definition 完整语义校验。

> 详细逐项记录见 [`DEVLOG.md`](DEVLOG.md)。

## 7. 开发约定

- **变更控制**：01—12 已全冻结。凡需改公共合同／MAF 映射／安全边界／三模板／交付范围，**必须先写 DCR 并经用户确认**，不得以实现便利静默改基线。
- **架构守护**：`tests/architecture/` 机器守卫——MAF 仅 `runtime/maf` 可导入、`domain` 层禁依赖 FastAPI/Pydantic/SQLAlchemy/psycopg/MAF。
- **分支**：`main` 受保护；功能走 `feat/` 分支 + PR，每周一个 `release/weekN` 里程碑标签。
- **秘密**：真实 `.env`／Token／密钥绝不入库；示例配置只用占位符与 `credential_ref`。

## 8. 相关文档

| 文档 | 位置 |
|---|---|
| 开发日志（每次开发后更新） | [`DEVLOG.md`](DEVLOG.md) |
| 12 主题冻结设计基线 | `../document_modified/` |
| 机器合同（07—09）唯一事实源 | `../document_modified/07_API接口` · `08_WorkflowDefinition` · `09_权限审批和本地执行安全` |
| 合同只读副本（供 codegen） | `design-contracts/` |
