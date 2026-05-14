# Acquiring AI 企业内部 Agent 平台

面向企业内部“收单 AI 智能服务体系”的 Agent 平台 MVP。当前版本重点完成平台底座、业务 Agent 注册发现、Skill 目录化、审批审计、运行时抽象和部署骨架，为后续接入真实 Agno Agent、MCP、内部系统工具、PostgreSQL/pgvector/Redis 打基础。

## 技术选型

- 主框架：Agno
- 服务框架：FastAPI
- 数据底座：PostgreSQL + pgvector + Redis
- 系统接入：MCP + Internal Tools
- 高风险流程：Workflow + Approval
- 部署方式：Docker + Kubernetes

当前代码默认选择 `agno` 运行时；如果本地未安装 Agno，会自动回退到本地执行，保证 MVP 可以先跑通。

## 已实现功能

### 1. FastAPI 服务入口

- `GET /`：首页状态
- `GET /health`：健康检查
- `POST /api/chat`：智能路由聊天
- `GET /api/capabilities`：业务 Agent 能力清单
- `GET /api/skills`：Skill 清单
- `GET /api/knowledge/search`：知识检索
- `GET /api/approvals`：审批任务列表
- `POST /api/approvals`：创建审批任务
- `POST /api/approvals/{approval_id}/decision`：审批处理
- `GET /api/audit`：审计事件列表

### 2. 业务 Agent 注册发现

业务能力不写死在主平台中，而是通过 Agent 模块自注册。

- 默认扫描包：`app.agents.capabilities`
- 配置项：`ACQUIRING_AI_CAPABILITY_MODULE_PACKAGES`
- 注册方式：业务 Agent 使用 `@register_capability`
- 支持本地 Registry
- 预留 Nacos Registry，用于远程 Agent 注册发现

当前内置业务域：

- 商户服务：商户问答、问题处理、经营分析
- 运营审核：调额审核、入网审核、商户变更审核
- 数据支持：直营销售数据、合规报表

### 3. Skill 目录化管理

Skill 通过 `SKILL.md` 文件管理，不再只依赖静态代码表。

默认目录结构：

```text
app/skills/{domain}/{skill_id}/SKILL.md
```

当前已加载的 Skill：

- `merchant_qa`
- `merchant_issue_handling`
- `merchant_ops_analysis`
- `quota_review`
- `merchant_onboarding_review`
- `merchant_change_review`
- `direct_sales_data_assistant`
- `compliance_report_generation`

### 4. 主 Agent 路由与可观测 Trace

`RouterAgent` 负责选择合适的业务 Agent，并返回路由追踪信息。

`/api/chat` 响应中包含：

- 候选能力列表
- 命中的能力列表
- 最终选中的能力
- 该能力声明的 Skill
- 路由策略和原因
- 当前运行时信息，例如 `Runtime=agno`

这为后续接入真实 Agno 推理、链路审计和问题排查提供基础。

### 5. Agno 运行时边界

已新增统一运行时抽象：

```text
app/runtimes/
  base.py
  local.py
  agno.py
```

当前状态：

- `LocalAgentRuntime`：直接执行当前 Python 业务 Agent
- `AgnoAgentRuntime`：作为目标运行时适配器，当前未安装 Agno 时回退本地执行
- `RouterAgent` 只依赖运行时接口，不直接绑定具体框架

### 6. 审批、审计和聊天持久化

已通过 SQLAlchemy 抽象数据层，当前持久化内容包括：

- 审批任务
- 审计日志
- 聊天会话
- 聊天消息

默认本地使用 SQLite，便于快速启动；生产目标是 PostgreSQL。

### 7. 高风险 Workflow + Approval

当前高风险场景会创建审批任务，例如：

- 调额审核
- 入网审核
- 商户变更审核

业务 Agent 可通过 `requires_approval=True` 和 `workflow` 标记进入审批流。

### 8. MCP 和 Internal Tools 预留

当前已有：

- 内部工具清单：`app/tools.py`
- Workflow 清单：`app/workflows.py`
- MCP 示例配置：`config/mcp.example.json`

后续会把内部工具和 MCP Server 转换为 Agno 可调用工具。

### 9. Docker 和 Kubernetes 部署骨架

已提供：

- `Dockerfile`
- `docker-compose.yml`
- `deploy/k8s/deployment.yaml`
- `deploy/k8s/service.yaml`
- `deploy/k8s/secret.example.yaml`

`docker-compose.yml` 包含：

- FastAPI 应用
- PostgreSQL + pgvector
- Redis

## 快速启动

### 本地开发

```powershell
cd D:\ai-code\jagent
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev,ai,postgres,mcp]
uvicorn app.main:app --reload
```

访问：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`

### 使用 SQLite 快速启动

默认配置已经使用 SQLite：

```powershell
$env:ACQUIRING_AI_DATABASE_URL="sqlite+pysqlite:///./acquiring_ai.db"
```

### 使用 PostgreSQL + pgvector + Redis

```powershell
$env:ACQUIRING_AI_DATABASE_URL="postgresql+psycopg://acquiring_ai:acquiring_ai@127.0.0.1:5432/acquiring_ai"
$env:ACQUIRING_AI_REDIS_URL="redis://127.0.0.1:6379/0"
$env:ACQUIRING_AI_VECTOR_STORE_ENABLED="true"
```

### Docker Compose 启动

```powershell
docker compose up --build
```

启动后访问：

- `http://127.0.0.1:8000/docs`

## 关键配置项

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `ACQUIRING_AI_AGENT_RUNTIME` | `agno` | Agent 运行时 |
| `ACQUIRING_AI_DATABASE_URL` | `sqlite+pysqlite:///./acquiring_ai.db` | 主数据库连接 |
| `ACQUIRING_AI_REDIS_URL` | `redis://127.0.0.1:6379/0` | Redis 连接 |
| `ACQUIRING_AI_VECTOR_STORE_ENABLED` | `false` | 是否启用向量库 |
| `ACQUIRING_AI_VECTOR_STORE_PROVIDER` | `pgvector` | 向量库实现 |
| `ACQUIRING_AI_SKILL_ROOT` | `app/skills` | Skill 目录 |
| `ACQUIRING_AI_MCP_ENABLED` | `false` | 是否启用 MCP |
| `ACQUIRING_AI_MCP_CONFIG_PATH` | `config/mcp.json` | MCP 配置路径 |
| `ACQUIRING_AI_NACOS_ENABLED` | `false` | 是否启用 Nacos 注册发现 |
| `ACQUIRING_AI_CAPABILITY_MODULE_PACKAGES` | `app.agents.capabilities` | 业务 Agent 扫描包 |

## 目录结构

```text
app/
  agents/             # RouterAgent、业务 Agent、注册加载器
  api/routes/         # FastAPI 路由
  db/                 # SQLAlchemy 数据库初始化和模型
  registry/           # 本地/Nacos/组合注册发现
  repositories/       # 数据访问层
  runtimes/           # local/agno 运行时适配层
  services/           # 审批、审计、聊天、知识、Skill 服务
  skills/             # SKILL.md 技能目录
  tools.py            # Internal Tools 清单
  workflows.py        # Workflow 清单
config/               # MCP 示例配置
deploy/k8s/           # Kubernetes 示例部署
docs/                 # 设计和技术文档
tests/                # 测试用例
```

## 当前边界

- Agno 已作为目标运行时接入边界，但还没有真正构建 Agno Agent/Tool 编排。
- PostgreSQL/pgvector/Redis 已完成配置和部署骨架，但业务数据仍主要通过 SQLAlchemy 表持久化，向量检索尚未真正接入。
- MCP 目前是配置示例，尚未加载 MCP Server 并转换为运行时工具。
- Internal Tools 当前是清单，还没有真实对接企业内部系统。
- Nacos 注册发现已有抽象和客户端，但远程 Agent 联调还未完成。
- 数据库迁移尚未接入 Alembic，目前仍依赖自动建表。
- 知识检索仍是内存样例数据。

## 后续需要实现的功能

### 第一阶段：Agno 真实运行时

1. 使用 Agno 构建主 Agent 和业务 Agent 执行器。
2. 将 `CapabilityAgent` 的执行过程迁移为 Agno Agent 调用。
3. 把 `SkillInfo` 注入 Agno prompt/context。
4. 把 `routing_trace` 和 Agno 执行过程打通。

### 第二阶段：工具系统

1. 把 `app/tools.py` 从清单升级为工具注册中心。
2. 将 Internal Tools 适配为 Agno Tool。
3. 增加工具权限、超时、审计和脱敏控制。
4. 支持工具调用结果进入聊天记录和审计日志。

### 第三阶段：MCP 接入

1. 加载 `config/mcp.json`。
2. 支持 stdio/http/sse 类型 MCP Server。
3. 将 MCP 工具转换为平台 Tool/Agno Tool。
4. 增加 MCP 工具白名单和调用审计。

### 第四阶段：PostgreSQL + pgvector + Redis

1. 使用 PostgreSQL 作为默认生产数据库。
2. 引入 Alembic 管理表结构迁移。
3. 将知识库切换到 pgvector 向量检索。
4. 将会话状态、运行时状态、任务缓存接入 Redis。
5. 增加知识入库、切片、向量化和召回接口。

### 第五阶段：Workflow + Approval 完整化

1. 把 `app/workflows.py` 升级为工作流定义和执行引擎。
2. 支持多步骤审批、回退、驳回、重新提交。
3. 将高风险工具调用强制绑定审批策略。
4. 增加审批 SLA、审批人规则和审批审计。

### 第六阶段：远程 Agent 注册发现

1. 完成 Nacos 真实注册和发现联调。
2. 支持远程 Agent 健康检查和版本元数据。
3. 支持按业务域、风险等级、权重路由。
4. 支持远程 Agent 熔断、降级和重试。

### 第七阶段：生产化部署

1. 完善 Docker 镜像构建参数和环境变量。
2. 完善 Kubernetes ConfigMap、Secret、Ingress、HPA。
3. 增加日志、指标、链路追踪。
4. 增加 CI 流水线、镜像扫描和自动部署。

## 验证命令

```powershell
python -m compileall app tests
python -c "from fastapi.testclient import TestClient; from app.main import app; c=TestClient(app); r=c.post('/api/chat', json={'user_id':'u','biz_domain':'merchant','message':'faq'}); print(r.status_code); print(r.json()['routing_trace'])"
```

如果安装了开发依赖：

```powershell
python -m pytest
```
