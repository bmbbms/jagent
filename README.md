# jagent

企业内部 Agent 平台最小可用版本，当前主线定位是：

- 运行时框架：`AgentScope`
- 服务框架：`FastAPI`
- 主数据库：`MySQL 8.0`
- 缓存：`Redis`
- 接入方式：`Internal Tools + MCP + External Agent`
- 治理能力：`Task Runtime + Approval + Audit + Evaluation + Service Ticket`
- 部署方式：`Docker Compose`，后续可扩展到 `Kubernetes`

这个项目当前重点不是把所有业务能力写死在平台里，而是先把“可扩展的 Agent 平台底座”搭起来：

- 业务能力通过 Agent / Capability 注册接入
- Skill 通过目录自动发现和运行时加载
- 外部 Agent 支持手工接入、健康检查、统一治理
- 任务执行过程可实时展示
- 评估 Agent 可对执行效果进行打分、提出优化建议
- 优化建议可转工单，并形成闭环跟踪

## 1. 当前已实现

### 1.1 平台主链路

- `POST /api/chat` 已接入 `AgentScope` 运行时
- 支持业务域：
  - `merchant`
  - `operations`
  - `data_support`
- 支持本地 Capability 注册
- 支持外部 Agent 注册、更新、发现、健康检查
- 支持 Skill 自动发现、查询、详情查看
- 支持 Workflow 查询与治理展示

### 1.2 任务执行与实时展示

已实现任务主对象沉淀：

- `task`
- `task event`
- `task artifact`
- `tool call log`
- `data access log`
- `runtime session / observation`

已实现接口：

- `GET /api/tasks`
- `GET /api/tasks/{task_id}`
- `GET /api/tasks/{task_id}/events/stream`
- `GET /api/tasks/{task_id}/tool-calls`
- `GET /api/tasks/{task_id}/data-access`
- `GET /api/tasks/{task_id}/observations`
- `GET /api/tasks/{task_id}/runtime-sessions`
- `GET /api/tasks/{task_id}/output-overview`
- `GET /api/tasks/{task_id}/evaluation`

已实现页面：

- `GET /ui/tasks`

任务面板当前支持：

- 最近任务列表
- 状态、业务域、Agent、风险、阶段、审批单过滤
- 分页与排序
- SSE 实时事件流
- 工具执行结果展示
- 数据访问日志展示
- Runtime Session 展示
- 评估结果展示
- 从任务直接跳到评估、工单、审批、审计

### 1.3 审批与高风险流程

已实现接口：

- `GET /api/approvals`
- `GET /api/approvals/{approval_id}`
- `POST /api/approvals`
- `POST /api/approvals/{approval_id}/decision`

已实现页面：

- `GET /ui/approvals`

当前支持：

- 高风险任务进入审批流
- 审批结果回写任务状态
- 审批事件进入任务时间线

### 1.4 审计中心

已实现接口：

- `GET /api/audit`

已实现页面：

- `GET /ui/audit`

当前支持：

- 按 `action / actor_id / task_id / approval_id / capability_id / workflow` 过滤
- 从审计事件直接跳转到任务、审批、能力、流程页面

### 1.5 评估 Agent 与优化建议

已实现接口：

- `GET /api/evaluations`
- `GET /api/evaluations/{evaluation_id}`
- `GET /api/evaluations/analytics/by-agent`
- `GET /api/evaluations/analytics/overview`
- `GET /api/evaluations/suggestions`
- `GET /api/evaluations/suggestions/overview`
- `PUT /api/evaluations/suggestions/{suggestion_id}`
- `POST /api/evaluations/suggestions/{suggestion_id}/ticket`

已实现页面：

- `GET /ui/evaluations`

当前支持：

- 任务完成后自动生成评估记录
- 评估维度打分：
  - completion
  - accuracy
  - tool_usage
  - efficiency
  - compliance
  - user_feedback
  - cost
- 输出优化建议类型：
  - `prompt`
  - `tool`
  - `runtime`
  - `workflow`
- 按 Agent 聚合统计
- 高关注 Agent 标识
- 优化建议治理概览
- 优化建议转工单

### 1.6 工单中心

已实现接口：

- `GET /api/service-tickets`
- `GET /api/service-tickets/{ticket_id}`
- `PUT /api/service-tickets/{ticket_id}`

已实现页面：

- `GET /ui/service-tickets`

当前支持：

- 工单列表查看与状态维护
- 从评估建议转工单
- 工单状态回写优化建议
- 工单按 `task_id` 过滤
- 从工单回跳：
  - 任务
  - 评估
  - 建议
  - 审计

### 1.7 外部 Agent 管理

已实现接口：

- `GET /api/external-agents`
- `POST /api/external-agents`
- `POST /api/external-agents/add`
- `PUT /api/external-agents/{capability_id}`
- `POST /api/external-agents/{capability_id}/health-check`
- `POST /api/external-agents/{capability_id}/verify`

已实现页面：

- `GET /ui/external-agents`

当前支持：

- 通用外部 Agent 地址接入
- 能力元数据维护
- 健康检查
- 验证调用

### 1.8 技术治理与数据库迁移

当前已具备：

- `Alembic` 版本化迁移
- MySQL 8.0 主线迁移脚本
- 迁移幂等增强
- 重复建表场景防护
- 离线模式下的迁移检查兼容

## 2. 当前目录结构

```text
app/
  agents/                Agent/Capability 装配
  api/routes/            FastAPI 路由
  db/                    SQLAlchemy 模型与会话
  repositories/          数据访问层
  runtimes/              AgentScope 运行时适配
  services/              任务、审批、评估、审计、工单等服务
  skills/                Skill 定义
  static/                原型页面
alembic/
  versions/              数据库迁移脚本
config/
docs/
scripts/
tests/
```

## 3. 快速启动

## 3.1 Linux 全新机器启动

### 方式一：推荐，用 Docker Compose

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
- `http://127.0.0.1:8000/ui/evaluations`
- `http://127.0.0.1:8000/ui/service-tickets`
- `http://127.0.0.1:8000/ui/external-agents`

默认会启动：

- `mysql`
- `redis`
- `app`
- `external-agent`

### 方式二：本地 Python 启动

先准备依赖：

```bash
git clone git@github.com:bmbbms/jagent.git
cd jagent
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev,ai,mysql,mcp]
cp .env.example .env
```

如果本地已经有 MySQL 8 和 Redis：

```bash
export ACQUIRING_AI_DATABASE_URL="mysql+pymysql://jagent:jagent@127.0.0.1:3306/jagent?charset=utf8mb4"
export ACQUIRING_AI_REDIS_URL="redis://127.0.0.1:6379/0"
export ACQUIRING_AI_DATABASE_AUTO_CREATE="false"
export ACQUIRING_AI_DATABASE_RUN_MIGRATIONS="true"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 3.2 Windows 本地启动

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
   - 评估结果
5. 在评估中心将建议转工单
6. 在工单中心更新状态并验证回写

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

## 7. 当前数据库与技术边界

### 已落地

- MySQL 8.0 主线
- Redis
- AgentScope
- FastAPI
- Alembic
- External Agent 接入与治理

### 规划中但尚未完整落地

- PostgreSQL + pgvector 正式知识库底座
- 更完整的 MCP Client 能力
- 多 Agent 编排与协作调度深化
- 自动化优化执行闭环
- Kubernetes 生产级部署清单

也就是说，当前仓库的“真实实现”以 `MySQL 8.0 + Redis + AgentScope + FastAPI` 为准；`PostgreSQL + pgvector` 仍属于后续演进方向。

## 8. 三期后续待办

当前仍建议继续推进的方向：

1. 审计中心进一步补齐按工单、按建议的联动过滤。
2. 评估 Agent 增加更细粒度的规则评估与趋势分析。
3. Runtime 层增强多 Agent 协作、重试、fallback、handoff 视图。
4. MCP 接入升级为更完整的生产可用客户端能力。
5. 知识库能力切换到正式的向量检索底座。
6. 完善部署文档、容器健康检查和 K8s 清单。

## 9. 常见排障

### `alembic upgrade head` 报表已存在

当前迁移已经做了幂等增强。若仍报错，先确认：

- 当前连接的是不是同一套 MySQL
- 是否之前手工建过表
- `.env` 和容器内环境变量是否一致

### Alembic 日志打印两遍

已在 `alembic.ini` 中关闭 `alembic` logger 的冒泡：

- `propagate = 0`

如果仍看到重复日志，优先检查是否有外层脚本重复调用 Alembic。

### `the input device is not a TTY`

在某些环境下执行 `docker compose run --rm app python - <<'PY'` 会遇到这个问题。可以改用：

```bash
docker compose exec app python -c "from app.dependencies import get_engine; print(get_engine())"
```

或在支持的 shell 中避免交互式 heredoc 方式。

---

如需继续推进三期，建议优先顺序是：

1. 审计联动增强
2. 评估趋势与治理看板深化
3. MCP / 外部 Agent 的生产化治理
4. README 对应的部署与验收脚本进一步标准化
