# jagent

企业内部 Agent 平台最小可用版本，当前主线技术栈为：

- Agent Runtime：`AgentScope`
- Web 框架：`FastAPI`
- 数据底座：`MySQL 8.0 + Redis`
- 接入方式：`Internal Tools + MCP + External Agent`
- 治理能力：`Task Runtime + Audit + Evaluation + Service Ticket`
- 部署方式：`Docker Compose`

当前仓库的目标不是把所有业务能力写死在平台里，而是先把一个可扩展、可治理、可验证的 Agent 平台底座搭起来：

- 业务能力通过 `Capability / Agent` 注册接入
- `Skill` 通过目录自动发现并在运行时加载
- 支持接入外部 Agent，并做统一治理
- 支持任务执行过程实时展示
- 支持评估 Agent 对运行结果进行诊断和优化建议生成
- 支持建议转工单，形成治理闭环

## 1. 当前已实现

### 1.1 平台主链路

- `POST /api/chat` 接入 `AgentScope` runtime
- 支持业务域：
  - `merchant`
  - `operations`
  - `data_support`
- 支持本地 Capability 注册与查询
- 支持 Skill 自动发现、列表查询、详情查看
- 支持 Workflow 列表与详情查询
- 支持外部 Agent 发现、添加、更新、删除、健康检查、治理问题筛选

核心接口：

- `GET /api/capabilities`
- `GET /api/capabilities/{capability_id}`
- `GET /api/capabilities/overview/summary`
- `GET /api/capabilities/{capability_id}/recent-tasks`
- `GET /api/skills`
- `GET /api/skills/{skill_id}`
- `GET /api/workflows`
- `GET /api/workflows/{workflow_code}`
- `GET /api/external-agents`
- `POST /api/external-agents/discover`
- `POST /api/external-agents/add`
- `PUT /api/external-agents/{capability_id}`
- `DELETE /api/external-agents/{capability_id}`
- `GET /api/external-agents/health-overview`
- `GET /api/external-agents/governance-overview`
- `GET /api/external-agents/governance-issues`
- `POST /api/external-agents/{capability_id}/health-check`

配套页面：

- `GET /ui/capabilities`
- `GET /ui/skills`
- `GET /ui/workflows`
- `GET /ui/external-agents`

### 1.2 任务执行与实时展示

已落地对象：

- `task`
- `task event`
- `task artifact`
- `tool call log`
- `data access log`
- `runtime observation`
- `runtime session`

核心接口：

- `GET /api/tasks`
- `GET /api/tasks/runtime-governance/overview`
- `GET /api/tasks/{task_id}`
- `GET /api/tasks/{task_id}/events/stream`
- `GET /api/tasks/{task_id}/tool-calls`
- `GET /api/tasks/{task_id}/data-access`
- `GET /api/tasks/{task_id}/observations`
- `GET /api/tasks/{task_id}/runtime-sessions`
- `GET /api/tasks/{task_id}/output-overview`
- `GET /api/tasks/{task_id}/evaluation`

当前支持：

- 最近任务列表
- 按状态、业务域、Agent、风险、阶段过滤
- 分页与排序
- SSE 实时事件流
- 任务实际产出展示
- 结构化工具结果展示
- Workflow / Skill 快照
- Runtime Session 展示
- Runtime fallback / handoff 治理概览
- 任务直达评估、工单、审计、能力中心

### 1.3 审计中心

核心接口：

- `GET /api/audit`
- `GET /api/audit/overview`
- `GET /api/audit/linked-context`
- `GET /api/audit/context/{context_type}/{context_id}`
- `GET /api/audit/execution-plan-runs`

当前支持：

- 按 `action / actor_id / source / event_type / outcome` 过滤
- 按 `task_id / capability_id / workflow / ticket_id / suggestion_id / evaluation_id` 过滤
- 审计联动上下文聚合与钻取
- 审计字段标准化
- 执行计划运行记录聚合

### 1.4 评估与优化

核心接口：

- `GET /api/evaluations`
- `GET /api/evaluations/{evaluation_id}`
- `GET /api/evaluations/analytics/by-agent`
- `GET /api/evaluations/analytics/overview`
- `GET /api/evaluations/analytics/focus-agents`
- `GET /api/evaluations/analytics/dimensions`
- `GET /api/evaluations/analytics/root-causes`
- `GET /api/evaluations/analytics/trend`
- `GET /api/evaluations/suggestions`
- `GET /api/evaluations/suggestions/overview`
- `GET /api/evaluations/suggestions/execution-backlog`
- `GET /api/evaluations/suggestions/execution-plan`
- `PUT /api/evaluations/suggestions/{suggestion_id}`
- `POST /api/evaluations/suggestions/{suggestion_id}/ticket`
- `POST /api/evaluations/suggestions/execution-plan/apply`

当前支持：

- 任务完成后自动生成评估
- 维度评分：
  - `completion`
  - `accuracy`
  - `tool_usage`
  - `efficiency`
  - `compliance`
  - `user_feedback`
  - `cost`
- 自动根因诊断：
  - `problem_type`
  - `severity`
  - `root_cause_signals`
  - `governance_summary`
- 优化建议：
  - `prompt`
  - `tool`
  - `runtime`
  - `workflow`
- 建议执行闭环、执行计划、工单联动

### 1.5 工单中心

核心接口：

- `GET /api/service-tickets`
- `GET /api/service-tickets/{ticket_id}`
- `GET /api/service-tickets/overview`
- `PUT /api/service-tickets/{ticket_id}`

当前支持：

- 工单列表、概览、状态维护
- 从评估建议转工单
- 工单状态回写优化建议
- 与任务、评估、建议、审计联动

### 1.6 MCP 治理

核心接口：

- `GET /api/mcp/tools`
- `GET /api/mcp/overview`
- `GET /api/mcp/governance-issues`
- `GET /api/mcp/tools/{tool_id}/recent-calls`

当前支持：

- MCP 工具目录与过滤
- Provider / Transport / Enabled / Only Called 过滤
- 风险治理总览
- 最近调用回看

## 2. 当前不再作为主线的能力

审批流已经从当前运行时主链路中移除，不再作为默认执行路径。仓库内若仍保留部分审批相关模型、字段或历史页面代码，当前仅视为兼容遗留，不代表主线能力。

## 3. 目录结构

```text
app/
  agents/                Capability / Agent 定义
  api/routes/            FastAPI 路由
  db/                    SQLAlchemy 模型与会话
  repositories/          数据访问层
  runtimes/              AgentScope Runtime 适配
  services/              任务、审计、评估、工单等服务
  skills/                Skill 定义
  static/                前端页面
alembic/
  versions/              数据库迁移脚本
config/
docs/
scripts/
tests/
```

## 4. 快速启动

### 4.1 Docker Compose

```bash
git clone git@github.com:bmbbms/jagent.git
cd jagent
cp .env.example .env
docker compose up --build
```

启动后访问：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/ui/tasks`
- `http://127.0.0.1:8000/ui/external-agents`
- `http://127.0.0.1:8000/ui/evaluations`
- `http://127.0.0.1:8000/ui/audit`

默认会启动：

- `mysql`
- `redis`
- `app`
- `external-agent`

### 4.2 本地 Python

Linux / macOS：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev,ai,mysql,mcp]
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev,ai,mysql,mcp]
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

如果使用本地 MySQL / Redis，请至少配置：

```bash
ACQUIRING_AI_DATABASE_URL=mysql+pymysql://jagent:jagent@127.0.0.1:3306/jagent?charset=utf8mb4
ACQUIRING_AI_REDIS_URL=redis://127.0.0.1:6379/0
ACQUIRING_AI_DATABASE_AUTO_CREATE=false
ACQUIRING_AI_DATABASE_RUN_MIGRATIONS=true
```

## 5. 数据库迁移

查看当前迁移版本：

```bash
alembic current
```

升级到最新版本：

```bash
alembic upgrade head
```

查看迁移链：

```bash
alembic history
alembic heads
```

如果只想初始化数据库：

```bash
python scripts/init_db.py
```

## 6. 验证方式

基础验证：

```bash
python scripts/verify_stack.py
python scripts/verify_api_flow.py
python scripts/verify_external_agent_flow.py --base-url http://127.0.0.1:8000
```

测试验证：

```bash
pytest
```

建议手工验证路径：

1. 打开 `http://127.0.0.1:8000/ui/external-agents`
2. 添加或发现一个外部 Agent
3. 通过 `/api/chat` 或页面触发一次任务
4. 在任务页检查事件流、工具执行、Runtime Session、输出结果
5. 在评估中心查看评分、根因诊断、优化建议
6. 将建议转工单并验证回写
7. 在审计中心检查任务、建议、工单、评估的联动链路

## 7. 关键配置项

常用配置见 [`.env.example`](./.env.example)。

重点配置包括：

- `ACQUIRING_AI_AGENT_RUNTIME=agentscope`
- `ACQUIRING_AI_DATABASE_URL`
- `ACQUIRING_AI_REDIS_URL`
- `ACQUIRING_AI_DATABASE_RUN_MIGRATIONS`
- `ACQUIRING_AI_MCP_ENABLED`
- `ACQUIRING_AI_AGENTSCOPE_USE_MODEL_BRIDGE`
- `ACQUIRING_AI_NACOS_ENABLED`

## 8. 当前技术边界

已经真实落地并验证：

- `MySQL 8.0`
- `Redis`
- `AgentScope`
- `FastAPI`
- `Alembic`
- `MCP`
- `External Agent`

仍属于后续演进方向：

- `PostgreSQL + pgvector` 正式知识库底座
- 更完整的 MCP Client 能力
- 更深的多 Agent 协作编排
- 更强的自动治理与告警联动
- Kubernetes 生产部署清单

## 9. 最新三期进展

近期已完成：

- 审计联动上下文钻取增强
- 审计埋点字段标准化
- 评估自动根因诊断增强
- External Agent 治理问题筛选增强
- External Agent 页面治理问题联动筛选

仍建议继续推进：

1. Runtime 多 Agent handoff / fallback 可视化继续细化
2. MCP / External Agent 告警与趋势视图继续增强
3. README 之外的部署文档与 K8s 清单继续补齐

## 10. 常见问题

### `alembic upgrade head` 报表已存在

优先确认：

- 当前连接的是不是同一套 MySQL
- 是否之前手工建过表
- `.env` 与容器内环境变量是否一致

### Alembic 日志打印两遍

当前已在 `alembic.ini` 中关闭 `alembic` logger 冒泡：

- `propagate = 0`

如果仍然重复，优先检查是否有外层脚本重复调用 Alembic。

### `the input device is not a TTY`

某些环境下使用 heredoc 方式执行 `docker compose run` 会遇到这个问题。可以改用：

```bash
docker compose exec app python -c "from app.dependencies import get_engine; print(get_engine())"
```
