# Task Event Protocol

## 1. 目标

本文定义前端“任务实时展示模块”与后端之间的接口约定，覆盖以下场景：

- 展示 Agent 任务执行全过程
- 展示工具调用、MCP 调用、审批状态
- 展示最终结论、任务产物、工具执行明细、数据访问明细
- 页面刷新后恢复任务状态

当前协议基于以下接口组合：

- 全量详情接口：`GET /api/tasks/{task_id}`
- 增量事件接口：`GET /api/tasks/{task_id}/events/stream`
- 工具明细接口：`GET /api/tasks/{task_id}/tool-calls`
- 数据访问接口：`GET /api/tasks/{task_id}/data-access`

## 2. 前端接入方式

推荐前端按如下顺序接入：

1. 调用 `POST /api/chat`
2. 从响应中拿到 `task_id`
3. 调用 `GET /api/tasks/{task_id}` 获取任务全量详情
4. 页面初始化完成后，建立 SSE 连接：

```text
GET /api/tasks/{task_id}/events/stream?last_event_seq=<当前最后事件序号>
```

5. 后续基于事件流增量刷新页面

推荐理由：

- 首屏依赖全量详情，避免页面空白
- 增量更新依赖 SSE，避免频繁轮询整任务详情
- 刷新后可通过 `last_event_seq` 断点续传

## 3. 接口协议

### 3.1 创建任务

接口：

```http
POST /api/chat
```

关键响应字段：

```json
{
  "task_id": "task_xxx",
  "evaluation_id": "eval_xxx",
  "approval_id": null,
  "routing_trace": {
    "selected_capability_id": "merchant.qa",
    "reason": "Selected first matched capability after priority sorting. Runtime=agentscope."
  }
}
```

前端最少需要关心：

- `task_id`
- `evaluation_id`
- `approval_id`
- `summary`
- `next_action`

### 3.2 获取任务详情

接口：

```http
GET /api/tasks/{task_id}
```

当前返回结构已经是聚合详情，包含：

- 任务主信息
- `events`
- `artifacts`
- `tool_calls`
- `data_access_logs`

示例：

```json
{
  "task_id": "task_xxx",
  "status": "success",
  "current_stage": "completed",
  "task_title": "Merchant QA Agent 任务",
  "task_goal": "faq",
  "events": [],
  "artifacts": [],
  "tool_calls": [],
  "data_access_logs": []
}
```

用途：

- 页面首屏加载
- 页面刷新恢复
- SSE 中断后的兜底恢复

### 3.3 获取工具调用明细

接口：

```http
GET /api/tasks/{task_id}/tool-calls
```

返回字段重点：

- `tool_call_id`
- `tool_id`
- `tool_type`
- `provider`
- `request_args`
- `response_summary`
- `status`
- `duration_ms`

用途：

- 工具调用明细 Tab
- 工具执行调试面板
- 评估模块按工具使用情况打分

### 3.4 获取数据访问明细

接口：

```http
GET /api/tasks/{task_id}/data-access
```

返回字段重点：

- `data_source`
- `data_object`
- `access_type`
- `sensitive_level`
- `row_count`
- `field_scope`

用途：

- 数据访问审计视图
- 风险与合规检查
- 前端展示“本任务访问了哪些表/字段”

### 3.5 订阅事件流

接口：

```http
GET /api/tasks/{task_id}/events/stream?last_event_seq=0&poll_interval=1.0&max_idle_rounds=30
```

返回类型：

```http
Content-Type: text/event-stream
```

SSE 事件示例：

```text
id: 3
event: agent_started
data: {"event_id":"evt_xxx","event_type":"agent_started","event_seq":3,"title":"Agent started","content":"faq","event_status":"success","visible_to_user":true,"agent_id":"merchant.qa","start_time":"2026-05-18T02:21:32.672892","end_time":null,"duration_ms":null,"event_payload":{"runtime":"agentscope"}}
```

心跳事件：

```text
event: heartbeat
data: {"task_id":"task_xxx","last_event_seq":6}
```

任务完成事件：

```text
event: task_completed
data: {"task_id":"task_xxx","status":"success","current_stage":"completed"}
```

## 4. 任务状态机

当前任务状态建议前端按如下理解：

| 状态 | 含义 |
| --- | --- |
| `running` | 正在执行 |
| `waiting_approval` | 等待审批 |
| `success` | 已完成 |
| `failed` | 执行失败或审批拒绝 |

当前阶段字段 `current_stage` 建议用于更细粒度展示：

- `routing`
- `preparing`
- `planning`
- `executing`
- `approval`
- `completed`
- `failed`

## 5. 事件模型

统一事件对象字段如下：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `event_id` | `string` | 事件唯一标识 |
| `event_type` | `string` | 事件类型 |
| `event_seq` | `number` | 任务内单调递增序号 |
| `title` | `string` | 短标题 |
| `content` | `string` | 事件内容 |
| `event_status` | `string` | 当前事件状态 |
| `visible_to_user` | `boolean` | 是否前端可见 |
| `agent_id` | `string \| null` | 关联 Agent |
| `start_time` | `string` | ISO 时间 |
| `end_time` | `string \| null` | ISO 时间 |
| `duration_ms` | `number \| null` | 耗时 |
| `event_payload` | `object` | 扩展字段 |

## 6. 已实现事件清单

当前后端已支持：

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
- `final_response`
- `artifact_generated`
- `approval_requested`
- `approval_finished`
- `heartbeat`
- `task_completed`

## 7. 前端推荐使用方式

推荐前端以 `GET /api/tasks/{task_id}` 作为首屏数据源：

- `events` 渲染主时间线
- `artifacts` 渲染产物区
- `tool_calls` 渲染工具执行明细
- `data_access_logs` 渲染数据访问明细

后续通过 SSE 增量追加：

- 新事件进入时间线
- 当任务完成或用户主动刷新时，再次调用任务详情接口做一次全量对齐

## 8. 异常处理建议

### 8.1 SSE 断开

建议：

1. 记录当前最后一个 `event_seq`
2. 自动重连：

```text
/api/tasks/{task_id}/events/stream?last_event_seq=<last_seq>
```

3. 如果重连失败，则退化到重新请求：

```text
GET /api/tasks/{task_id}
```

### 8.2 事件丢失或乱序

后端保证同一任务按 `event_seq` 单调递增，前端应：

- 以 `event_seq` 作为唯一排序依据
- 忽略小于等于当前最大 `event_seq` 的重复事件

## 9. 后续扩展建议

后续如继续扩展，建议保持基础字段兼容，只新增事件类型或扩展 `event_payload`：

- `workflow_node_started`
- `workflow_node_finished`
- `risk_detected`
- `risk_blocked`
- `approval_timeout`
- `agent_retry`
- `agent_fallback`
- `multi_agent_handoff`
