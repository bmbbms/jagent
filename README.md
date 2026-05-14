# Acquiring AI MVP

面向“收单AI-智能服务体系”一期需求的最小可用版本，当前已升级为数据库持久化版本。

## 当前版本能力

- 首页状态：`GET /`
- 健康检查：`GET /health`
- 能力清单：`GET /api/capabilities`
- 智能路由聊天：`POST /api/chat`
- 知识检索：`GET /api/knowledge/search`
- 审批列表：`GET /api/approvals`
- 审批创建：`POST /api/approvals`
- 审批处理：`POST /api/approvals/{approval_id}/decision`
- 审计查看：`GET /api/audit`

## 已持久化的数据

- 审批任务
- 审计日志
- 聊天会话
- 聊天消息

## 数据库配置

默认使用本地 SQLite 方便启动：

- `ACQUIRING_AI_DATABASE_URL=sqlite+pysqlite:///./acquiring_ai.db`

切换到 MySQL 8：

```bash
set ACQUIRING_AI_DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/acquiring_ai?charset=utf8mb4
```

建议同时保留：

```bash
set ACQUIRING_AI_DATABASE_AUTO_CREATE=true
set ACQUIRING_AI_DATABASE_ECHO=false
```

## 启动方式

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev,mysql]
uvicorn app.main:app --reload
```

打开：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`

## 当前架构特点

- 主平台不写死业务能力
- 业务能力通过 `app/agents/capabilities/` 下的 Agent 自注册
- Router 只负责发现和路由
- Registry 已抽象，可接本地注册和 Nacos
- 数据层已抽象为 SQLAlchemy，可切换 MySQL 8

## 当前边界

- 仍未接真实 Tool 和企业内部系统
- 知识检索仍是内存样例数据
- Nacos 和远程 capability 仍未做真实联调
- 暂未引入 Alembic 迁移，当前依赖自动建表
