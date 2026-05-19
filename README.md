# jagent

企业内部 Agent 平台最小可用版本。

当前仓库的真实主线定位：

- 主框架：`AgentScope`
- 服务框架：`FastAPI`
- 数据底座：`MySQL 8.0 + Redis`
- 系统接入：`Internal Tools + MCP + External Agent`
- 治理能力：`Task Runtime + Approval + Audit + Evaluation + Service Ticket`
- 部署方式：`Docker Compose`

这个项目当前重点不是把所有业务能力写死在平台里，而是先把“可扩展的 Agent 平台底座”搭起来：

- 业务能力通过 `Agent / Capability` 注册接入
- `Skill` 通过目录自动发现并在运行时加载
- 外部 Agent 支持手工接入、发现、健康检查、统一治理
- 任务执行过程支持实时展示
- 评估 Agent 对任务执行结果打分、分析并提出优化建议
- 优化建议可转工单并形成治理闭环

## 1. 当前已实现

### 1.1 平台主链路

已实现：

- `POST /api/chat` 接入 `AgentScope` 运行时
- 支持业务域：
  - `merchant`
  - `operations`
  - `data_support`
- 支持本地 Capability 注册与查询
- 支持 Skill 自动发现、列表查询、详情查看
- 支持 Workflow 列表与详情查询
- 支持外部 Agent 发现、注册、更新、删除、健康检查
- 支持外部 Agent 最近任务回看

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
- `POST /api/external-agents/register`
- `POST /api/external-agents/discover`
- `POST /api/external-agents/add`
- `PUT /api/external-agents/{capability_id}`
- `DELETE /api/external-agents/{capability_id}`
- `GET /api/external-agents/health-overview`
- `GET /api/external-agents/governance-overview`
- `GET /api/external-agents/{capability_id}/health`
- `POST /api/external-agents/{capability_id}/health-check`
- `GET /api/external-agents/{capability_id}/recent-tasks`

配套页面：

- `GET /ui/capabilities`
- `GET /ui/skills`
- `GET /ui/workflows`
- `GET /ui/external-agents`

### 1.2 任务执行与实时展示

已落地的任务对象：

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

配套页面：

- `GET /ui/tasks`

当前支持：

- 最近任务列表
- 按状态、业务域、Agent、风险、阶段、审批单过滤
- 分页与排序
- SSE 实时事件流
- 任务实际产出展示
- 结构化工具产出展示
- Workflow / Skill 运行快照
- Runtime Session 展示
- 单任务运行治理摘要
- 任务列表视角的运行时治理总览
- 从任务直接跳转到评估、工单、审批、审计、能力、外部 Agent

### 1.3 审批与高风险流程

核心接口：

- `GET /api/approvals`
- `GET /api/approvals/{approval_id}`
- `POST /api/approvals`
- `POST /api/approvals/{approval_id}/decision`

配套页面：

- `GET /ui/approvals`

当前支持：

- 高风险任务进入审批流
- 审批结果回写任务状态
- 审批事件进入任务时间线

### 1.4 审计中心

核心接口：

- `GET /api/audit`
- `GET /api/audit/overview`

配套页面：

- `GET /ui/audit`

当前支持：

- 按 `action / actor_id / source / event_type / outcome` 过滤
- 按 `task_id / approval_id / capability_id / workflow` 过滤
- 按 `ticket_id / suggestion_id / evaluation_id` 过滤
- 审计联动上下文分布总览
- 从审计事件直接跳转到任务、审批、能力、流程、工单、评估

### 1.5 评估 Agent 与优化建议

核心接口：

- `GET /api/evaluations`
- `GET /api/evaluations/{evaluation_id}`
- `GET /api/evaluations/analytics/by-agent`
- `GET /api/evaluations/analytics/overview`
- `GET /api/evaluations/analytics/focus-agents`
- `GET /api/evaluations/analytics/dimensions`
- `GET /api/evaluations/analytics/trend`
- `GET /api/evaluations/suggestions`
- `GET /api/evaluations/suggestions/overview`
- `PUT /api/evaluations/suggestions/{suggestion_id}`
- `POST /api/evaluations/suggestions/{suggestion_id}/ticket`

配套页面：

- `GET /ui/evaluations`

当前支持：

- 任务完成后自动生成评估记录
- 评估维度打分：
  - `completion`
  - `accuracy`
  - `tool_usage`
  - `efficiency`
  - `compliance`
  - `user_feedback`
  - `cost`
- 输出优化建议类型：
  - `prompt`
  - `tool`
  - `runtime`
  - `workflow`
- 按 Agent 聚合评估分析
- 重点 Agent 治理视图
- 评估趋势分析
- 评估维度治理分析
- 优化建议总览、状态维护、转工单
- 从评估和建议直接跳转到工单与审计

### 1.6 工单中心

核心接口：

- `GET /api/service-tickets`
- `GET /api/service-tickets/{ticket_id}`
- `GET /api/service-tickets/overview`
- `PUT /api/service-tickets/{ticket_id}`

配套页面：

- `GET /ui/service-tickets`

当前支持：

- 工单列表查看与状态维护
- 工单治理总览
- 从评估建议转工单
- 工单状态回写优化建议
- 按 `task_id` 过滤
- 从工单回跳任务、评估、建议、审计

### 1.7 MCP 治理中心

核心接口：

- `GET /api/mcp/tools`
- `GET /api/mcp/overview`
- `GET /api/mcp/tools/{tool_id}/recent-calls`

配套页面：

- `GET /ui/mcp`

当前支持：

- MCP 工具目录查看
- Provider / Transport / Enabled / Only Called 过滤
- 最近调用任务回看
- MCP 风险治理总览：
  - 未启用工具数
  - 慢调用工具数
  - 高风险工具数
  - Provider 风险分布
  - Transport 风险分布

### 1.8 技术治理与数据库迁移

当前已具备：

- `Alembic` 版本化迁移
- MySQL 8.0 主线迁移脚本
- 迁移幂等增强
- 重复建表场景防护
- 离线模式下的迁移检查兼容

## 2. 目录结构

```text
app/
  agents/                Agent / Capability 装配
  api/routes/            FastAPI 路由
  db/                    SQLAlchemy 模型与会话
  repositories/          数据访问层
  runtimes/              AgentScope 运行时适配
  services/              任务、审批、评估、审计、工单等服务
  skills/                Skill 定义
  static/                前端原型页面
alembic/
  versions/              数据库迁移脚本
config/
docs/
scripts/
tests/
```

## 3. 快速启动

### 3.1 Linux 全新机器启动

方式一：推荐，使用 Docker Compose

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
- `http://127.0.0.1:8000/ui/capabilities`
- `http://127.0.0.1:8000/ui/evaluations`
- `http://127.0.0.1:8000/ui/service-tickets`
- `http://127.0.0.1:8000/ui/audit`
- `http://127.0.0.1:8000/ui/mcp`

默认会启动：

- `mysql`
- `redis`
- `app`
- `external-agent`

方式二：本地 Python 启动

```bash
git clone git@github.com:bmbbms/jagent.git
cd jagent
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev,ai,mysql,mcp]
cp .env.example .env
```

如果本地已有 MySQL 8.0 和 Redis：

```bash
export ACQUIRING_AI_DATABASE_URL="mysql+pymysql://jagent:jagent@127.0.0.1:3306/jagent?charset=utf8mb4"
export ACQUIRING_AI_REDIS_URL="redis://127.0.0.1:6379/0"
export ACQUIRING_AI_DATABASE_AUTO_CREATE="false"
export ACQUIRING_AI_DATABASE_RUN_MIGRATIONS="true"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3.2 Windows 本地启动

```powershell
cd D:\ai-code\jagent
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev,ai,mysql,mcp]
Copy-Item .env.example .env
```

使用 MySQL 8.0：

```powershell
$env:ACQUIRING_AI_DATABASE_URL="mysql+pymysql://jagent:jagent@127.0.0.1:3306/jagent?charset=utf8mb4"
$env:ACQUIRING_AI_REDIS_URL="redis://127.0.0.1:6379/0"
$env:ACQUIRING_AI_DATABASE_AUTO_CREATE="false"
$env:ACQUIRING_AI_DATABASE_RUN_MIGRATIONS="true"
uvicorn app.main:app --reload
```

## 4. 数据库初始化与迁移

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

如果只想初始化库结构，也可以执行：

```bash
python scripts/init_db.py
```

## 5. 验证方式

### 5.1 基础验证

```bash
python scripts/verify_stack.py
python scripts/verify_api_flow.py
python scripts/verify_external_agent_flow.py --base-url http://127.0.0.1:8000
```

### 5.2 测试验证

```bash
pytest
```

### 5.3 手工验证建议

1. 打开 `http://127.0.0.1:8000/ui/external-agents`
2. 添加一个外部 Agent
3. 通过 `/api/chat` 或任务页触发一次任务
4. 在任务页查看：
   - 时间线
   - 工具执行
   - Runtime Session
   - 运行时治理摘要
   - 评估结果
5. 在 Capability Center 或 External Agent 页面查看最近任务
6. 在评估中心查看：
   - 重点 Agent 治理
   - 评估趋势
   - 评估维度治理
7. 将优化建议转工单
8. 在工单中心更新状态并验证回写
9. 在审计中心核对 task / suggestion / ticket / evaluation 联动链路
10. 在 MCP 中心查看工具风险概览与最近调用

## 6. 关键配置项

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| `ACQUIRING_AI_AGENT_RUNTIME` | Agent 运行时 | `agentscope` |
| `ACQUIRING_AI_DATABASE_URL` | 主数据库连接串 | MySQL |
| `ACQUIRING_AI_REDIS_URL` | Redis 连接串 | `redis://127.0.0.1:6379/0` |
| `ACQUIRING_AI_DATABASE_AUTO_CREATE` | 是否自动建表 | `false` |
| `ACQUIRING_AI_DATABASE_RUN_MIGRATIONS` | 启动时是否自动跑迁移 | `true` |
| `ACQUIRING_AI_MCP_ENABLED` | 是否启用 MCP | `false` |
| `ACQUIRING_AI_MCP_CONFIG_PATH` | MCP 配置文件 | `config/mcp.example.json` |
| `ACQUIRING_AI_NACOS_ENABLED` | 是否启用 Nacos | `false` |
| `ACQUIRING_AI_AGENTSCOPE_USE_MODEL_BRIDGE` | 是否启用模型桥接 | `false` |
| `ACQUIRING_AI_AGENTSCOPE_MODEL_NAME` | 模型名 | 空 |
| `ACQUIRING_AI_AGENTSCOPE_API_KEY` | 模型密钥 | 空 |
| `ACQUIRING_AI_AGENTSCOPE_BASE_URL` | 兼容 OpenAI 的模型网关地址 | 空 |

完整示例见：

- [`.env.example`](D:/ai-code/jagent/.env.example)

## 7. 当前技术边界

当前仓库真实落地并验证过的主线是：

- `MySQL 8.0`
- `Redis`
- `AgentScope`
- `FastAPI`
- `Alembic`
- `MCP`
- `External Agent`

规划中但尚未完整落地：

- `PostgreSQL + pgvector` 正式知识库底座
- 更完整的 MCP Client 能力
- 更深的多 Agent 编排与协作调度
- 自动化优化执行闭环
- Kubernetes 生产级部署清单

也就是说，当前仓库的“真实实现”以 `MySQL 8.0 + Redis + AgentScope + FastAPI` 为准；`PostgreSQL + pgvector` 仍属于后续演进方向。

## 8. 最新三期待办

基于当前代码状态，后续建议优先方向为：

1. 审计中心继续深化按工单、建议、评估、任务的联动钻取体验。
2. 评估 Agent 继续补更细粒度规则评估与自动归因能力。
3. Runtime 层继续增强多 Agent 协作、重试、fallback、handoff 的细化视图。
4. MCP / External Agent 继续补更生产化的治理能力，例如熔断、超时策略、告警视图。
5. 知识库能力正式切换到向量检索底座。
6. 完善部署文档、容器健康检查和 K8s 清单。

## 9. 常见排障

### `alembic upgrade head` 报表已存在

当前迁移已经做了幂等增强。若仍报错，先确认：

- 当前连接的是不是同一套 MySQL
- 是否之前手工建过表
- `.env` 与容器内环境变量是否一致

### Alembic 日志打印两遍

已在 `alembic.ini` 中关闭 `alembic` logger 冒泡：

- `propagate = 0`

如果仍看到重复日志，优先检查是否有外层脚本重复调用 Alembic。

### `the input device is not a TTY`

在某些环境下执行带 heredoc 的 `docker compose run` 会遇到这个问题。可以改用：

```bash
docker compose exec app python -c "from app.dependencies import get_engine; print(get_engine())"
```

或在当前 shell 中避免交互式 heredoc 方式。

---

如果继续推进三期，当前建议优先顺序是：

1. 审计联动体验继续增强
2. 评估治理与自动归因继续深化
3. Runtime 多 Agent 视图继续细化
4. MCP / 外部 Agent 生产治理继续增强
5. 部署与验收文档标准化
