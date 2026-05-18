# Acquiring AI 企业内部 Agent 平台

面向企业内部场景的 Agent 平台最小可用版本，当前主线技术选型如下：

- Agent Runtime：`AgentScope`
- 服务框架：`FastAPI`
- 主数据库：`MySQL 8.0`
- 本地联调库：`SQLite`
- 缓存：`Redis`
- 系统接入：`MCP + Internal Tools`
- 高风险流程：`Workflow + Approval`
- 部署方式：`Docker + Kubernetes`

当前重点不是把业务能力写死在平台里，而是先把可扩展的平台骨架搭起来：

- 业务 Agent 通过注册发现接入平台
- Skill 通过目录自动发现
- 平台统一沉淀会话、任务、事件、产物、审计、评估和优化建议
- 支持任务实时展示
- 支持评估 Agent 对运行结果进行评分和优化建议输出

## 当前已实现

### 1. Agent 平台主链路

- Runtime 已切换为 `AgentScope`
- 支持业务 Agent 注册发现
- 支持 `merchant`、`operations`、`data_support` 等业务域
- 支持 Skill 自动发现
- 支持 `Internal Tools` 与最小 `MCP` 桥接

### 2. 对话与任务闭环

- `POST /api/chat` 已接入任务主线
- 每次对话会生成并沉淀：
  - `contact`
  - `message`
  - `task`
  - `task event`
  - `artifact`
  - `evaluation`

### 3. 任务实时展示

已支持以下接口：

- `GET /api/tasks`
- `GET /api/tasks/{task_id}`
- `GET /api/tasks/{task_id}/events/stream`
- `GET /api/tasks/{task_id}/tool-calls`
- `GET /api/tasks/{task_id}/data-access`
- `GET /api/tasks/{task_id}/evaluation`

其中 `GET /api/tasks` 现已支持：

- `status`
- `biz_domain`
- `selected_agent_id`
- `start_date_from`
- `start_date_to`
- `page`
- `page_size`
- `sort_by`
- `sort_order`
- 兼容旧参数 `limit`

返回结构为分页对象：

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 50,
  "sort_by": "start_time",
  "sort_order": "desc",
  "has_next": false
}
```

最小前端原型页：

- `GET /ui/tasks`

页面支持：

- 最近任务列表
- 状态 / 业务域 / Agent / 时间范围筛选
- 分页与排序
- 筛选状态保留到 URL
- 点击任务切换详情
- SSE 事件流重连
- 评估结果展示

当前事件类型包括：

- `task_created`
- `agent_selected`
- `agent_started`
- `runtime_session_started`
- `skill_bundle_loaded`
- `tool_inventory_prepared`
- `planner_started`
- `execution_plan_created`
- `planner_completed`
- `executor_started`
- `thought_generated`
- `executor_completed`
- `tool_call_started`
- `tool_call_finished`
- `mcp_call_started`
- `mcp_call_finished`
- `approval_requested`
- `approval_finished`
- `final_response`
- `artifact_generated`
- `heartbeat`
- `task_completed`

### 4. 审批、审计、评估

- 高风险任务可进入审批流
- 审批决策会回写任务时间线
- 每次任务完成后可生成在线评估记录
- 已支持评估明细和优化建议查询

### 5. 二期 Runtime 基础

- `AgentScope runtime` 已进入二期基础形态
- 运行时会生成结构化 `runtime session`
- 运行时会加载 skill bundle，并解析 `required_inputs`、`steps`、`allowed_tools`
- 运行时会基于业务域与 skill 限制生成 `tool inventory`
- 运行时会生成可展示的 `execution plan`
- 运行时已拆分为 `planner / executor` 两阶段，便于后续接入真实 AgentScope session、memory 与 tool orchestration
- 配置模型桥接后，`executor` 会优先尝试 `AgentScope ReActAgent + Toolkit`，失败时回退到本地 capability

### 6. 数据模型基线

当前已沉淀以下核心表：

- Agent Registry
- Agent Skill / Tool Binding
- Contact / Message
- Task / Task Event / Task Artifact
- Approval / Approval Audit
- Audit / Observation / Tool Call / Data Access / Risk Audit
- Evaluation / Evaluation Detail / Optimization Suggestion
- Knowledge Document / Chunk

模型定义见：

- [app/db/models.py](D:/ai-code/jagent/app/db/models.py)

## 技术栈

| 模块 | 选型 |
| --- | --- |
| Agent Runtime | `AgentScope` |
| API 服务 | `FastAPI` |
| ORM | `SQLAlchemy 2.x` |
| 数据迁移 | `Alembic` |
| 主数据库 | `MySQL 8.0` |
| 缓存 | `Redis` |
| 注册发现 | `Nacos` |
| 外部协议接入 | `MCP` |
| 部署 | `Docker + Kubernetes` |

说明：

- 本地开发仍允许使用 `SQLite` 快速启动
- 生产目标数据库为 `MySQL 8.0`
- 向量检索当前不与 `pgvector` 强绑定，后续建议独立为外部向量能力

## 快速启动

### 1. 安装依赖

```powershell
cd D:\ai-code\jagent
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev,ai,mysql,mcp]
```

建议先创建本地环境变量文件：

```powershell
Copy-Item .env.example .env
```

### 2. 使用 SQLite 本地快速启动

```powershell
$env:ACQUIRING_AI_DATABASE_URL="sqlite+pysqlite:///./acquiring_ai.db"
$env:ACQUIRING_AI_DATABASE_AUTO_CREATE="true"
$env:ACQUIRING_AI_DATABASE_RUN_MIGRATIONS="false"
uvicorn app.main:app --reload
```

### 3. 使用 MySQL 8.0 启动

```powershell
$env:ACQUIRING_AI_DATABASE_URL="mysql+pymysql://root:password@127.0.0.1:3306/jagent?charset=utf8mb4"
$env:ACQUIRING_AI_REDIS_URL="redis://127.0.0.1:6379/0"
$env:ACQUIRING_AI_DATABASE_AUTO_CREATE="false"
$env:ACQUIRING_AI_DATABASE_RUN_MIGRATIONS="true"
uvicorn app.main:app --reload
```

### 4. 启用 MCP 示例工具

```powershell
$env:ACQUIRING_AI_MCP_ENABLED="true"
$env:ACQUIRING_AI_MCP_CONFIG_PATH="config/mcp.example.json"
```

### 5. 可选开启 AgentScope Model Bridge

```powershell
$env:ACQUIRING_AI_AGENTSCOPE_USE_MODEL_BRIDGE="true"
$env:ACQUIRING_AI_AGENTSCOPE_MODEL_NAME="gpt-4.1-mini"
$env:ACQUIRING_AI_AGENTSCOPE_API_KEY="your-api-key"
```

如使用兼容 OpenAI 的网关，也可补充：

```powershell
$env:ACQUIRING_AI_AGENTSCOPE_BASE_URL="https://your-openai-compatible-endpoint/v1"
```

访问地址：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/ui/tasks`
- `http://127.0.0.1:8000/ui/tasks?task_id=task_xxx`

### 6. 使用 Docker Compose 启动完整本地依赖

```powershell
docker compose up --build
```

默认会启动：

- `MySQL 8.0`
- `Redis`
- `FastAPI App`

## 验证方式

应用启动后，可直接执行：

```powershell
python scripts/verify_api_flow.py
```

如需指定地址：

```powershell
python scripts/verify_api_flow.py --base-url http://127.0.0.1:8000
```

该脚本会自动验证：

- `/health`
- `merchant` 无审批对话链路
- `operations` 审批对话链路
- `task detail`
- `task sse event stream`
- `evaluation detail`

## Alembic 使用方式

### 1. 查看当前迁移状态

```powershell
alembic current
```

### 2. 升级到最新版本

```powershell
alembic upgrade head
```

### 3. 生成新迁移

```powershell
alembic revision -m "add_xxx"
```

说明：

- 当前已提供首个基线迁移：`0001_create_initial_mysql_schema`
- 生产环境建议优先通过 Alembic 维护表结构
- `database_auto_create` 仅保留给本地快速开发兜底使用
- 如只想单独初始化数据库，也可以执行：

```powershell
python scripts/init_db.py
```

## 关键配置

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `ACQUIRING_AI_AGENT_RUNTIME` | `agentscope` | Agent 运行时 |
| `ACQUIRING_AI_DATABASE_URL` | `sqlite+pysqlite:///./acquiring_ai.db` | 数据库连接 |
| `ACQUIRING_AI_REDIS_URL` | `redis://127.0.0.1:6379/0` | Redis 连接 |
| `ACQUIRING_AI_DATABASE_AUTO_CREATE` | `true` | 是否自动建表 |
| `ACQUIRING_AI_DATABASE_RUN_MIGRATIONS` | `false` | 是否启动时执行 Alembic 迁移 |
| `ACQUIRING_AI_MCP_ENABLED` | `false` | 是否启用 MCP |
| `ACQUIRING_AI_MCP_CONFIG_PATH` | `config/mcp.json` | MCP 配置路径 |
| `ACQUIRING_AI_NACOS_ENABLED` | `false` | 是否启用 Nacos |
| `ACQUIRING_AI_CAPABILITY_MODULE_PACKAGES` | `app.agents.capabilities` | Agent 能力扫描包 |
| `ACQUIRING_AI_SKILL_ROOT` | `app/skills` | Skill 根目录 |

## 目录结构

```text
app/
  agents/             # RouterAgent、业务 Agent、加载器
  api/routes/         # FastAPI 路由
  db/                 # SQLAlchemy 模型、会话、初始化、迁移入口
  registry/           # 本地 / Nacos / 组合注册发现
  repositories/       # 数据访问层
  runtimes/           # AgentScope / Local runtime 适配层
  services/           # chat、task、approval、audit、evaluation、mcp 等服务
  skills/             # Skill 目录
  static/             # UI 原型页
  tools.py            # Internal Tool / MCP Tool 统一目录
alembic/
  env.py
  versions/
docs/
  local-troubleshooting.md
  task-event-protocol.md
  task-realtime-ui-outline.md
```

## 排障参考

- 环境变量模板：[.env.example](D:/ai-code/jagent/.env.example)
- 本地联调排障手册：[docs/local-troubleshooting.md](D:/ai-code/jagent/docs/local-troubleshooting.md)

## 当前边界

- `AgentScope runtime` 已是正式主线，但还不是完整的复杂编排实现
- `MCPService` 当前仍是最小桥接器，不是完整 MCP 客户端
- `MySQL 8.0` 是正式目标库，`SQLite` 仍保留给本地调试
- 向量检索能力尚未正式接入
- 任务实时展示当前以事件流与产物沉淀为主，前端还可继续增强
- 评估 Agent 已具备最小闭环，后续仍需增强自动优化执行能力

## 后续建议优先级

1. 完善 `AgentScope` 编排能力，补齐多 Agent 协作与状态管理
2. 升级 `MCPService` 为更完整的 MCP 客户端能力
3. 补充更细粒度的 `Workflow / Risk / Approval` 策略
4. 将 `Redis` 更深入用于任务态缓存和事件分发
5. 引入更完整的知识摄取、切片、索引和检索链路
6. 增强评估 Agent 到“可闭环优化”的自动化能力

## 建议验证命令

```powershell
python -m compileall app tests
alembic current
alembic upgrade head
python scripts/verify_stack.py
python scripts/verify_api_flow.py
```
