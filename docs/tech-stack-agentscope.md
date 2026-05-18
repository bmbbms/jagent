# AgentScope-based Technical Stack

## Target Stack

- Agent runtime: `AgentScope`
- Service framework: `FastAPI`
- Primary database: `MySQL 8.0`
- Cache and short-lived state: `Redis`
- Integration: `MCP + Internal Tools`
- High-risk process: `Workflow + Approval`
- Deployment: `Docker + Kubernetes`

## Runtime Boundary

平台继续保留“业务能力作为 `CapabilityAgent` 注册”的结构。

`RouterAgent` 负责：

- 路由规划
- 选择业务 Agent
- 构造运行上下文

`AgentRuntime` 负责：

- 执行 Agent
- 写入运行阶段事件
- 向任务时间线输出执行轨迹

当前运行时：

- `agentscope`：默认正式运行时
- `local`：测试与兜底运行时

当前 `agentscope` 已接入为正式边界，但内部仍复用现有 `CapabilityAgent.run()`。

## Data Foundation

当前数据底座口径：

- 本地开发：允许 `SQLite`
- 生产目标：`MySQL 8.0 + Redis`

推荐生产配置：

```powershell
$env:ACQUIRING_AI_DATABASE_URL="mysql+pymysql://root:password@mysql:3306/jagent?charset=utf8mb4"
$env:ACQUIRING_AI_REDIS_URL="redis://redis:6379/0"
```

说明：

- 向量检索不再与主事务库强绑定
- 后续建议独立为外部向量服务

## Current Platform Capabilities

当前已经具备：

1. 业务 Agent 注册发现
2. Skill 目录化加载
3. 任务主线建模
4. 任务事件流建模
5. 任务产物建模
6. 审批与审计基础链路
7. 在线评估与优化建议
8. SSE 实时任务事件流
9. Internal Tool / MCP 事件接入

## Current MCP Boundary

当前 `MCPService` 已支持：

- 从配置文件识别 MCP 工具
- 统一调用入口
- 在任务时间线中产出：
  - `mcp_call_started`
  - `mcp_call_finished`

当前仍未完成：

- 真实 MCP 协议客户端
- 动态 tool discovery
- server session 生命周期管理

## Next Implementation Order

1. 将 `AgentScope runtime` 升级为真实 AgentScope 执行器
2. 接入 Alembic，冻结 MySQL 8.0 正式表结构
3. 把 Redis 引入事件流和运行态缓存
4. 将 `MCPService` 升级为完整 MCP 客户端
5. 扩展 Workflow / Risk / Approval 治理
6. 引入外部向量检索能力
