# 二期运行时推进：AgentScope Runtime 基础层

## 目标

在不破坏一期接口与任务链路的前提下，把 `AgentScope runtime` 从占位适配层升级成可编排、可观测、可扩展的运行时基础层。

本阶段重点不是一次性做完完整多 Agent 编排，而是先把后续扩展必须依赖的基础能力打牢：

- 结构化 runtime session
- skill bundle 装载
- tool inventory 生成
- planner / executor 分层
- 统一工具执行服务
- 前端可展示的任务执行事件

## 本阶段已落地

### 1. Runtime Session

每次任务执行都会生成结构化运行时会话，包含：

- `session_id`
- `task_id`
- `contact_id`
- `trace_id`
- `capability_id`
- `capability_name`
- `framework_available`
- `framework_version`

### 2. Skill Bundle 装载

运行时不再只拿到 `skill_id`，而是会解析 `SKILL.md`，读取：

- `purpose`
- `when_to_use`
- `required_inputs`
- `steps`
- `allowed_tools`
- `human_escalation`

这使 skill 不再只是展示信息，而是开始参与 runtime 规划与约束。

### 3. Tool Inventory 生成

运行时会先按业务域加载平台工具目录，再结合 skill 中声明的 `allowed_tools` 做过滤，生成本次任务真实可见的工具清单。

### 4. Execution Plan 生成

运行时会生成结构化 execution plan，包含：

- 选中的 skill
- 已装载的 skill
- 工具清单
- 必要输入
- system prompt 预览
- 计划步骤

这部分已经可以直接服务前端实时展示模块。

### 5. 新增任务事件

已新增运行时事件：

- `runtime_session_started`
- `skill_bundle_loaded`
- `tool_inventory_prepared`
- `planner_started`
- `execution_plan_created`
- `planner_completed`
- `executor_started`
- `executor_completed`

### 6. Planner / Executor 两阶段

当前运行时已拆分为两层：

- `planner`
  - 汇总 skill / tool / required inputs
  - 生成 execution plan
  - 生成 escalation reasons
- `executor`
  - 执行业务能力
  - 汇总 selected skills / tools / approval flag
  - 输出 execution summary

### 7. AgentScope Model Bridge

当配置开启时，`executor` 会优先尝试：

- `AgentScope ReActAgent + Toolkit`
- 将 skill prompt 与 tool inventory 注入 framework bridge

当桥接未开启、模型未配置或执行失败时：

- 自动回退到本地 capability
- 在 `audit_tags` 与 `executor_completed.metadata` 中保留桥接模式与回退原因

### 8. 统一 Tool Execution Service

本阶段已新增平台统一工具执行服务：

- 新增 `ToolExecutionService`
- 统一收口 `Internal Tool` 与 `MCP Tool`
- 统一输出 `ToolExecutionResult`
- 统一发射工具事件

当前已支持：

- `tool_call_started`
- `tool_call_finished`
- `mcp_call_started`
- `mcp_call_finished`

### 9. Internal Tool Adapter Registry

为避免把内部工具能力写死在统一工具执行服务中，本阶段进一步增加了可注册的适配器层：

- 新增 `InternalToolRegistry`
- 新增 `InternalToolAdapter` 协议
- 支持按 `tool_id` 注册独立适配器
- 默认内置一组平台 mock adapter 作为开发态实现

这意味着后续接入真实业务系统时，只需要：

- 新增或替换对应 `tool_id` 的 adapter
- 不需要改 `AgentScope runtime`
- 不需要改任务主链路与事件协议

### 10. 第一批数据库型 Tool Adapter

本阶段已继续推进第一批“真实数据库适配器”：

- `merchant_profile_query`
- `merchant_transaction_summary`
- `merchant_risk_tag_query`

当前实现方式：

- 新增平台最小业务表
  - `t_merchant_profile`
  - `t_merchant_transaction_daily`
  - `t_merchant_risk_tag`
- 新增 `MerchantDataRepository`
- 对应 adapter 已通过 repository 读取数据库，而不是返回纯内存 mock

这一步的意义是先打通“真实数据库查询链路”，后续再替换为外部业务库或真实业务服务时，不需要再改 runtime 与工具执行服务接口。

### 11. AgentScope 真实工具桥

当前 `AgentScope runtime` 在 framework bridge 路径下，已不再使用虚拟 tool bridge，而是通过统一工具执行服务触发平台工具层。

这意味着：

- runtime 可以真实产出工具调用事件
- 前端任务时间线可以展示 agent 实际工具动作
- 审计 / 评估 / 优化模块后续可以基于真实工具事实工作

### 12. Runtime 与 Task Timeline 对齐

为避免同一工具调用在 runtime 执行阶段与任务收尾阶段重复记账，当前已增加以下约束：

- runtime 若真实执行过工具，会把执行结果写入 `ChatResponse.runtime_tool_results`
- `TaskService.finalize_chat_task()` 会跳过这些已在 runtime 中发生过的工具调用
- 因此任务时间线中的工具事件与 runtime 实际执行事实保持一致

### 13. Tool Execution Fact Logging

工具执行事实已开始沉淀到数据库表：

- `t_tool_call_log`
- `t_data_access_log`

当前落库方式：

- `ToolExecutionService` 负责工具执行
- `ToolExecutionLogService` 负责事实持久化
- 数据库型 adapter 会在返回 payload 中补充 `data_access_records`
- 日志服务根据执行结果自动写入工具调用日志与数据访问日志

这意味着后续的：

- 审计
- 评估 agent
- 数据权限治理
- 风险复盘

都已经有了可复用的底层事实来源

### 14. Tool Execution Query API

已新增工具执行明细查询能力，挂在任务视图下：

- `GET /api/tasks/{task_id}/tool-calls`
- `GET /api/tasks/{task_id}/data-access`
- `GET /api/tasks/{task_id}` 已聚合返回 `tool_calls` 与 `data_access_logs`

这样前端可以在任务详情页中补充：

- 工具调用时间线
- 工具输入输出摘要
- 数据访问对象与字段范围
- 数据访问敏感等级
- 首屏一次请求拿到完整任务详情

## 当前边界

- 当前最终业务结论仍以现有 `CapabilityAgent.run()` 为主
- 当前 `AgentScope` 的 model / memory 还没有升级为完整生产级运行态
- 当前 execution plan 更偏“准备态可观察性”，还不是复杂 workflow engine
- 当前仅第一批商户相关工具已切到数据库型 adapter，其它 internal tools 仍是默认 mock adapter
- 当前工具执行日志已入库，且已具备查询 API，但前端展示层尚未补齐
- 当前 framework bridge 已能接到平台工具执行层，但尚未完成真实在线模型联调

## 下一步建议

1. 继续把剩余高频 internal tools 切换为数据库型或真实业务系统 adapter
2. 给任务实时展示页补充 `tool-calls` / `data-access` 明细视图
3. 引入真实 `AgentScope` session、memory、message abstraction
4. 把 planner 输出从静态计划升级为可执行 plan graph
5. 把 observation / tool call / approval 与 runtime session 做更强关联
