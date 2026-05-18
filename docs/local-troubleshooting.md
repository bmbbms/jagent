# 本地启动与联调排障手册

本文面向当前 `AgentScope + FastAPI + MySQL 8.0 + Redis` 本地开发环境。

## 1. 推荐启动顺序

```powershell
cd D:\ai-code\jagent
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev,ai,mysql,mcp]
docker compose up --build
```

另开一个终端执行：

```powershell
cd D:\ai-code\jagent
.venv\Scripts\activate
python scripts/verify_stack.py
python scripts/verify_api_flow.py
```

## 2. 常见问题总览

| 现象 | 优先检查项 |
| --- | --- |
| `pytest` 找不到 `fastapi` / `app` | 是否进入 `.venv` |
| API 启动失败 | `.env`、MySQL、Redis、依赖是否安装 |
| `alembic upgrade head` 失败 | 数据库连接串、MySQL 是否可连、权限是否足够 |
| `/api/chat` 成功但 `/api/tasks/{task_id}` 为空 | 数据库是否落库、是否连到了错误数据库 |
| SSE 无事件或只有 heartbeat | 任务是否已完成、任务 ID 是否正确、轮询参数是否过小 |
| `operations` 任务一直停在 `waiting_approval` | 是否调用了审批决策接口 |
| `verify_api_flow.py` 失败 | 先看 `/health`，再看数据库和 Redis 验证 |

## 3. Python 与依赖问题

### 3.1 `ModuleNotFoundError: No module named 'fastapi'`

原因通常是没有进入项目虚拟环境，或者当前命令跑到了系统 Python。

处理方式：

```powershell
cd D:\ai-code\jagent
.venv\Scripts\activate
python -V
pip list
```

确认后重新安装依赖：

```powershell
pip install -e .[dev,ai,mysql,mcp]
```

### 3.2 `ModuleNotFoundError: No module named 'app'`

通常是当前目录不在项目根目录，或者命令没有在 `D:\ai-code\jagent` 下执行。

处理方式：

```powershell
cd D:\ai-code\jagent
.venv\Scripts\activate
pytest
```

## 4. MySQL 8.0 相关问题

### 4.1 数据库连不上

先检查连接串：

```env
ACQUIRING_AI_DATABASE_URL=mysql+pymysql://jagent:jagent@127.0.0.1:3306/jagent?charset=utf8mb4
```

再检查容器或本地服务是否已启动：

```powershell
docker compose ps
```

如果 MySQL 容器未健康，可查看日志：

```powershell
docker compose logs mysql
```

### 4.2 `alembic upgrade head` 失败

优先检查：

- 数据库是否已创建
- 用户是否有建表权限
- `ACQUIRING_AI_DATABASE_URL` 是否指向正确实例
- 是否仍有旧的 SQLite 文件路径配置干扰

建议先执行：

```powershell
.venv\Scripts\activate
python scripts/init_db.py
```

若仍失败，再执行：

```powershell
alembic upgrade head
```

### 4.3 任务查不到或数据没落库

先确认应用连的是哪一个数据库：

- `.env`
- 当前终端环境变量
- `docker compose.yml` 中的容器环境变量

最常见的问题是：

- 本地脚本连的是 `127.0.0.1:3306`
- 容器里的应用连的是 `mysql:3306`
- 两边以为是同一套数据，实际不是

## 5. Redis 相关问题

### 5.1 `verify_stack.py` 报 Redis 失败

先检查 Redis 容器状态：

```powershell
docker compose ps
docker compose logs redis
```

再确认配置：

```env
ACQUIRING_AI_REDIS_URL=redis://127.0.0.1:6379/0
```

如果应用运行在 Docker 内，则容器内地址通常应为：

```env
ACQUIRING_AI_REDIS_URL=redis://redis:6379/0
```

## 6. API 与任务链路问题

### 6.1 `/health` 正常，但 `/api/chat` 失败

优先检查：

- 请求体字段是否完整：`user_id`、`biz_domain`、`message`
- `biz_domain` 是否为支持值：`merchant` / `operations` / `data_support`
- 依赖服务是否正常

可先手工验证：

```powershell
curl http://127.0.0.1:8000/health
```

### 6.2 `/api/chat` 成功，但 `/api/tasks/{task_id}` 404

常见原因：

- 请求打到了 A 服务实例，但查任务打到了另一套数据库
- 启动时数据库迁移失败，部分表不存在
- `task_id` 取错

建议先执行：

```powershell
python scripts/verify_stack.py
python scripts/verify_api_flow.py
```

### 6.3 SSE 只有 heartbeat，没有业务事件

先确认：

- `task_id` 是否真实存在
- 任务是否已经完成
- `last_event_seq` 是否过大

可直接打开：

`GET /api/tasks/{task_id}`

如果详情里已有事件，而 SSE 只有 heartbeat，多半是：

- 你连接得太晚，任务早已结束
- 查询参数把事件过滤掉了

## 7. 审批链路问题

### 7.1 `operations` 任务一直是 `waiting_approval`

这是正常表现，说明任务已进入高风险审批流。

需要调用：

`POST /api/approvals/{approval_id}/decision`

批准后任务状态会从：

- `waiting_approval`

变为：

- `success`

拒绝后会变为：

- `failed`

### 7.2 审批通过了，但任务状态没更新

优先检查：

- 审批接口是否返回 `approved`
- `approval_id` 是否与任务上的一致
- 数据库事务是否成功提交

然后查询：

- `GET /api/approvals`
- `GET /api/tasks/{task_id}`

## 8. MCP 相关问题

### 8.1 开启了 MCP 但没有 `mcp_call_started`

先确认：

- `ACQUIRING_AI_MCP_ENABLED=true`
- `ACQUIRING_AI_MCP_CONFIG_PATH=config/mcp.example.json`
- 当前任务能力是否真的使用了 MCP 工具

当前项目里的 MCP 还是最小桥接器，不是完整协议客户端，所以优先先验证事件链路，不要先按复杂远程 MCP 故障去排。

## 9. 推荐排障顺序

遇到问题时，建议固定按这个顺序排：

1. 先看虚拟环境是否正确：`.venv`
2. 再看 `docker compose ps`
3. 再跑 `python scripts/verify_stack.py`
4. 再跑 `python scripts/verify_api_flow.py`
5. 再手工查 `/health`、`/api/tasks/{task_id}`、`/api/approvals`
6. 最后再看 `docker compose logs app mysql redis`

## 10. 当前已知边界

- 当前 `AgentScope runtime` 还是占位适配层，不是完整多 Agent 编排器
- 当前 `MCPService` 是最小桥接器
- 当前测试是否能运行，强依赖你是否进入了正确的虚拟环境
- 当前工作区可能同时存在历史 SQLite 数据和新 MySQL 数据，联调时要明确自己到底连的是哪一套
