# 一期需求当前交付状态

## 当前已完成

### 1. 平台主工程骨架

- FastAPI 主服务
- `/health`
- `/api/chat`
- `/api/capabilities`
- `/api/skills`
- `/api/knowledge/search`
- `/api/approvals`
- `/api/approvals/{approval_id}/decision`
- `/api/audit`
- `/api/tasks`
- `/api/tasks/{task_id}`
- `/api/tasks/{task_id}/events/stream`
- `/api/evaluations`
- `/api/evaluations/{evaluation_id}`

### 2. 业务 Agent 注册发现

当前已注册的一期业务能力：

- `merchant.qa`
- `merchant.issue_handling`
- `merchant.ops_analysis`
- `operations.quota_review`
- `operations.onboarding_review`
- `operations.merchant_change_review`
- `data_support.direct_sales_data`
- `data_support.compliance_report`

### 3. Skill 目录化

当前已加载 Skill：

- `merchant_qa`
- `merchant_issue_handling`
- `merchant_ops_analysis`
- `quota_review`
- `merchant_onboarding_review`
- `merchant_change_review`
- `direct_sales_data_assistant`
- `compliance_report_generation`

### 4. 运行时主线

- Runtime 默认值已切到 `AgentScope`
- `RouterAgent` 已通过运行时边界执行业务 Agent
- 响应中已带 `routing_trace`

### 5. 任务实时展示闭环

当前已经完成：

- `task` 创建
- `task event` 记录
- `artifact` 记录
- `SSE` 实时事件流

已实现事件：

- `task_created`
- `agent_selected`
- `agent_started`
- `thought_generated`
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

### 6. 审批、审计与评估

- 高风险任务可创建审批单
- 审批结果可回写任务状态与时间线
- 审计事件可查询
- 每次任务完成后自动生成在线评估结果
- 评估详情与优化建议可查询

### 7. MCP 最小接入

- 可从配置识别 MCP 工具
- 可走统一 `MCPService` 调用入口
- 可在任务时间线中看到真实 `mcp_call_started / mcp_call_finished`

## 当前实现边界

当前版本已经不是最初的“接口骨架”，而是“可运行的一期平台样机”。

但仍有这些边界：

- `AgentScope runtime` 还不是完整 AgentScope 编排执行器
- `MCPService` 还是最小桥接器，不是完整 MCP 客户端
- 生产目标数据库是 `MySQL 8.0`，但当前仍保留 `SQLite` 开发兜底
- Alembic 迁移尚未接入
- Redis 还没有全面接管事件分发与运行态缓存
- 外部向量检索尚未落地

## 下一步建议顺序

1. 接入 Alembic，冻结 MySQL 8.0 正式库表
2. 继续把历史文档统一到 AgentScope / MySQL 8.0 最新口径
3. 将 AgentScope runtime 升级为真实执行器
4. 将 MCPService 升级为完整 MCP 客户端
5. 引入 Redis 事件总线与运行态缓存
6. 深化 Workflow / Risk / Approval 治理链路

## 当前平台状态判断

如果按一期阶段划分，当前状态可以定义为：

`一期平台样机已跑通主闭环，正在从骨架期进入可联调期。`
