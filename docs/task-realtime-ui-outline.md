# Task Realtime UI Outline

## 1. 目标

本文定义“任务实时展示模块”的前端页面结构、组件划分和交互建议，配合 [task-event-protocol.md](D:/ai-code/jagent/docs/task-event-protocol.md) 使用。

这份文档重点回答三个问题：

- 页面应该长什么样
- 组件应该如何拆分
- 每个组件消费哪些接口和数据

## 2. 页面定位

该页面不是普通聊天记录页，而是“Agent 工作过程页”。

页面需要同时承载五类信息：

- 用户当前任务目标
- Agent 的实时执行过程
- Agent 的实际工作产出
- 工具调用明细与数据访问明细
- 任务完成后的评估与优化建议

推荐页面名称：

- `任务执行详情`
- `Agent 工作台`
- `智能体执行过程`

## 3. 页面整体布局

建议桌面端采用三栏布局：

```text
+-------------------------------------------------------------+
| Top Bar                                                     |
+----------------------+---------------------------+----------+
| Left Panel           | Main Timeline             | Right    |
| Task Summary         | Task Event Stream         | Side     |
| Status / Meta        | Tool / Approval / Output  | Eval     |
| Quick Facts          | Artifact / Tool Details   | Panel    |
+----------------------+---------------------------+----------+
```

移动端建议改为上下分区：

```text
Top Summary
Task Timeline
Tool Detail Drawer
Artifact Area
Evaluation Drawer
```

## 4. 页面区域说明

### 4.1 顶部栏

用途：

- 展示页面标题
- 展示任务状态
- 提供基础操作按钮

建议内容：

- 页面标题：`任务执行详情`
- 任务状态标签：`执行中 / 待审批 / 已完成 / 已失败`
- 刷新按钮
- 复制任务 ID
- 查看评估按钮

推荐组件：

- `TaskHeader`
- `TaskStatusBadge`
- `TaskToolbar`

### 4.2 左侧摘要区

用途：

- 展示任务基础信息
- 展示当前阶段
- 展示路由和选中 Agent
- 展示快速统计

建议字段：

- `task_id`
- `task_title`
- `task_goal`
- `biz_domain`
- `selected_agent_id`
- `current_stage`
- `trace_id`
- `approval_id`
- `start_time`
- `duration_ms`

建议补充统计卡片：

- `tool_calls.length`
- `data_access_logs.length`
- `artifacts.length`
- `events.length`

推荐组件：

- `TaskSummaryCard`
- `TaskMetaList`
- `RouteTraceCard`
- `TaskQuickStats`

### 4.3 中央时间线区

用途：

- 实时展示任务执行过程
- 展示工具调用与审批流程
- 作为页面核心区域

建议展示：

- 任务创建
- Agent 选择
- Runtime Session 创建
- Skill Bundle 装载
- Planner / Execution Plan
- Executor 执行阶段
- 阶段性思考结果
- 工具调用
- MCP 调用
- 审批事件
- 最终回复
- 产物生成

推荐组件：

- `TaskTimeline`
- `TaskEventItem`
- `TaskEventGroup`
- `FinalResponseCard`
- `ArtifactCard`

### 4.4 工具执行明细区

用途：

- 展示本任务所有工具调用记录
- 展示工具输入输出摘要
- 展示工具执行耗时与状态

建议数据源：

- `GET /api/tasks/{task_id}` 中的 `tool_calls`
- 或按需调用 `GET /api/tasks/{task_id}/tool-calls`

建议展示字段：

- `tool_name`
- `tool_type`
- `provider`
- `status`
- `duration_ms`
- `response_summary`

推荐组件：

- `ToolCallList`
- `ToolCallCard`
- `ToolCallStatusBadge`

### 4.5 数据访问明细区

用途：

- 展示任务访问了哪些数据对象
- 展示访问字段范围和敏感等级
- 为审计和风险治理提供可视化入口

建议数据源：

- `GET /api/tasks/{task_id}` 中的 `data_access_logs`
- 或按需调用 `GET /api/tasks/{task_id}/data-access`

建议展示字段：

- `data_source`
- `data_object`
- `access_type`
- `sensitive_level`
- `row_count`
- `field_scope.fields`

推荐组件：

- `DataAccessList`
- `DataAccessCard`
- `SensitiveLevelTag`

### 4.6 右侧评估区

用途：

- 展示任务完成后的评估结果
- 展示优化建议

推荐组件：

- `EvaluationPanel`
- `EvaluationScoreCard`
- `EvaluationDetailList`
- `OptimizationSuggestionList`

## 5. 建议组件树

```text
TaskRealtimePage
  TaskHeader
  TaskLayout
    TaskSummaryPanel
      TaskSummaryCard
      RouteTraceCard
      TaskQuickStats
    TaskTimelinePanel
      TaskTimeline
        TaskEventItem
        ApprovalEventCard
        FinalResponseCard
        ArtifactCard
    ToolInsightPanel
      ToolCallList
      DataAccessList
    EvaluationSidePanel
      EvaluationScoreCard
      EvaluationDetailList
      OptimizationSuggestionList
```

## 6. 页面初始化流程

推荐初始化顺序：

1. 页面拿到 `task_id`
2. 调用 `GET /api/tasks/{task_id}`
3. 用返回值初始化：
   - `task summary`
   - `events`
   - `artifacts`
   - `tool_calls`
   - `data_access_logs`
4. 取当前最大 `event_seq`
5. 打开 SSE
6. 监听新事件并增量刷新时间线
7. 如存在 `evaluation_id`，任务完成后再请求评估接口

## 7. 前端状态模型建议

```ts
type TaskRealtimeState = {
  task: TaskDetail | null
  events: TaskEvent[]
  artifacts: TaskArtifact[]
  toolCalls: ToolCall[]
  dataAccessLogs: DataAccessLog[]
  evaluation: Evaluation | null
  connectionStatus: "connecting" | "open" | "closed" | "error"
  lastEventSeq: number
}
```

关键原则：

- `events` 只增不减
- `toolCalls` 和 `dataAccessLogs` 首屏可直接从任务详情拿
- `lastEventSeq` 单调递增
- `task.status` 以任务详情和 `task_completed` 事件为准

## 8. 推荐交互细节

### 8.1 首屏优先展示

首屏优先显示：

- 任务摘要
- 执行状态
- 时间线
- 最近一次最终结论

工具调用明细和数据访问明细可放在折叠区或 Tab 中。

### 8.2 任务完成后的刷新策略

当收到 `task_completed` 后：

1. 再次调用 `GET /api/tasks/{task_id}`
2. 用返回值做一次最终全量对齐
3. 如有 `evaluation_id`，再拉评估详情

### 8.3 工具明细展示建议

建议展示形式：

- 时间线下方折叠面板
- 或页面中部二级 Tab

推荐排序：

- 按 `start_time` 升序

### 8.4 数据访问明细展示建议

建议重点高亮：

- `sensitive_level`
- `data_object`
- `field_scope`

这样审计与治理场景下价值更高。

## 9. 一期前端可交付范围

建议先做到：

- 支持任务详情首屏展示
- 支持 SSE 实时追事件
- 支持工具调用明细展示
- 支持数据访问明细展示
- 支持任务完成后查看评估

可暂缓：

- 多任务对比
- 高级筛选器
- 全局检索
- 成本/Token 分析图

## 10. 后续演进建议

后续可在此基础上继续扩展：

- 多 Agent 协作视图
- Workflow 节点图
- 风险策略命中面板
- Tool Call Performance 面板
- 数据访问审计专页
- 任务回放模式
