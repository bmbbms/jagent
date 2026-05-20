# 主 Agent 网关需求文档与开发计划

## 1. 背景

当前项目已经具备 AgentScope runtime、外部 Agent 接入、任务看板、审计、评估、MCP 展示等基础能力。随着接入方式从本地能力逐步转向 Nacos 发现的外部子 Agent，需要重新明确主 Agent 的定位。

主 Agent 不再作为业务能力实现方，也不作为 Skill、MCP、Workflow 的中心化管理方。它应定位为企业内部 Agent Gateway，负责统一入口、路由、权限、审计、任务观察、评估与治理。

子 Agent 自己声明支持的 Skill、依赖的 MCP、支持的 Workflow。主 Agent 只同步这些声明信息，形成子 Agent 能力画像，用于展示、路由解释、权限判断、审计记录、任务看板和评估分析。

## 2. 总体定位

### 2.1 主 Agent 是什么

主 Agent 是企业 Agent Gateway，承担以下职责：

- 统一接收外部请求。
- 从 Nacos 发现子 Agent。
- 维护子 Agent 能力画像快照。
- 根据请求选择合适的子 Agent。
- 做用户、租户、角色、业务域维度的访问控制。
- 调用子 Agent 并记录全过程。
- 展示任务执行过程、子 Agent 声明能力和实际产出。
- 对单次任务和子 Agent 长期表现做评估。
- 输出治理建议和告警。

### 2.2 主 Agent 不是什么

主 Agent 不承担以下职责：

- 不实现具体业务能力。
- 不管理子 Agent 内部 Skill。
- 不管理子 Agent 内部 MCP。
- 不编排子 Agent 内部 Workflow。
- 不向子 Agent 强制下发 Skill、MCP、Workflow。
- 不把 Nacos metadata 视为完整业务事实来源。

## 3. 核心概念

### 3.1 子 Agent

子 Agent 是真实执行主体。它通过 Nacos 注册或暴露 Agent Card，声明自身名称、描述、入口地址、协议、版本、能力、标签等信息。

### 3.2 Agent Profile

Agent Profile 是主 Agent 同步后的子 Agent 能力画像。它是展示、路由、审计、评估和治理的核心对象。

Agent Profile 来源于：

- Nacos Agent Card 原始字段。
- Agent Card 中声明的 skills。
- Agent Card metadata 中可能存在的 mcps、workflows、tags、biz_domain。
- 平台侧补全字段，如业务域、风险等级、权限策略、治理状态。

### 3.3 Declared Skill

Declared Skill 是子 Agent 声明自己支持的技能。主 Agent 只展示和使用它辅助路由，不管理其内部实现。

### 3.4 Declared MCP

Declared MCP 是子 Agent 声明自己可能依赖或使用的 MCP。它表示能力画像，不等于本次任务实际调用。

### 3.5 Declared Workflow

Declared Workflow 是子 Agent 声明自己支持的流程。主 Agent 不编排该流程，只在展示、审计和评估时记录。

### 3.6 Observed MCP / Observed Workflow

Observed MCP 和 Observed Workflow 来源于任务执行过程中的事件、日志或子 Agent 返回的 trace。它表示本次任务实际发生了什么。

## 4. 需求范围

### 4.1 发现与同步

主 Agent 需要从 Nacos 拉取子 Agent 信息，并形成平台内部 Agent Profile。

功能要求：

- 支持从 Nacos AI A2A 接口拉取 Agent Card。
- 支持保存原始 Agent Card。
- 支持标准化为 Agent Profile。
- 支持保存 Agent 声明的 Skill。
- 支持从 metadata 中提取声明的 MCP。
- 支持从 metadata 中提取声明的 Workflow。
- 当 metadata 缺失时，仍可保存 Agent 基础画像。
- 支持同步日志，记录拉取数量、成功数量、失败数量和错误信息。
- 支持手动触发同步。
- 后续支持定时同步。

### 4.2 Agent Profile 展示

主 Agent 需要提供子 Agent 画像查询能力。

功能要求：

- 展示 Agent 列表。
- 展示 Agent 详情。
- 展示 Agent 声明的 skills。
- 展示 Agent 声明的 mcps。
- 展示 Agent 声明的 workflows。
- 展示 Agent 权限策略。
- 展示 Agent 健康状态。
- 展示 Agent 近期任务和评估结果。

### 4.3 路由

主 Agent 负责将请求路由到子 Agent。

路由依据：

- 用户请求文本。
- 用户指定的 agent_id。
- 业务域 biz_domain。
- Agent name。
- Agent description。
- Agent tags。
- Declared skills 的名称、描述、标签、示例。
- Agent 权限和启用状态。
- Agent 健康状态和治理状态。
- Agent 历史评估得分。

路由输出：

- selected_agent_id。
- matched_skill_ids。
- route_reason。
- candidate_agent_ids。
- filtered_agent_ids。
- policy_decision。
- risk_flags。

### 4.4 权限控制

主 Agent 负责请求进入子 Agent 前的第一道权限控制。

控制维度：

- tenant_id。
- user_id。
- role。
- biz_domain。
- source。
- agent_id。
- risk_level。
- enabled 状态。

策略结果：

- allow。
- deny。
- require_review。
- degraded。

首期要求：

- 支持 Agent 级启停。
- 支持按租户、角色、用户配置允许访问。
- 支持默认允许或默认拒绝策略。
- 支持记录权限判断审计。

### 4.5 调用与任务看板

主 Agent 调用子 Agent 时，需要把执行过程写入任务看板。

看板需要展示：

- 请求来源。
- 路由候选 Agent。
- 最终选中的子 Agent。
- 命中的 declared skills。
- 子 Agent 声明的 declared mcps。
- 子 Agent 声明的 declared workflows。
- 子 Agent 调用耗时。
- 子 Agent 返回内容。
- 子 Agent 返回的事件或 trace。
- observed mcps。
- observed workflows。
- 最终产出。
- 错误信息。
- 评估结果。

### 4.6 审计

主 Agent 需要记录请求、路由、权限、调用、响应、评估和治理动作。

审计事件包括：

- request_received。
- agent_profile_synced。
- route_candidates_built。
- route_selected。
- policy_checked。
- sub_agent_invoked。
- sub_agent_completed。
- sub_agent_failed。
- task_evaluated。
- governance_issue_created。

审计字段至少包括：

- task_id。
- trace_id。
- user_id。
- tenant_id。
- source。
- selected_agent_id。
- matched_skill_ids。
- declared_mcp_ids。
- declared_workflow_ids。
- policy_result。
- latency_ms。
- outcome。
- payload。

### 4.7 评估

评估是主 Agent 的核心能力之一，但评估视角是网关视角，不评价子 Agent 内部实现细节。

单次任务评估维度：

- route_match_score：路由是否准确。
- success_score：子 Agent 是否成功响应。
- latency_score：耗时是否合理。
- answer_quality_score：回答是否可用。
- safety_score：是否存在合规、安全或敏感风险。
- declared_capability_match_score：结果是否符合子 Agent 声明能力。
- user_feedback_score：用户反馈得分。
- overall_score：综合得分。

长期 Agent 评估指标：

- 调用次数。
- 成功率。
- 失败率。
- 平均耗时。
- P95 耗时。
- 平均评分。
- 用户点赞率。
- 用户点踩率。
- 路由误判次数。
- 风险事件数。
- 治理状态。

评估来源：

- 规则评估。
- 用户反馈。
- LLM 评估 Agent。
- 审计和运行时日志。

### 4.8 治理

治理不直接自动下线子 Agent，首期以建议和告警为主。

治理场景：

- 连续失败。
- 响应过慢。
- 评分下降。
- 用户差评多。
- 路由误判高。
- 声明能力与实际结果不一致。
- 安全风险较高。

治理输出：

- issue。
- alert。
- recommended_action。
- severity。
- target_agent_id。
- evidence。

## 5. 数据设计

### 5.1 t_agent_profile

保存子 Agent 画像。

字段建议：

- agent_id：平台内部稳定 ID。
- source_agent_name：Nacos 原始 name。
- agent_name：展示名称。
- description。
- endpoint。
- protocol。
- transport。
- version。
- namespace。
- source：nacos。
- biz_domain。
- tags。
- raw_card。
- normalized_card。
- health_status。
- governance_status。
- risk_level。
- enabled。
- last_sync_time。
- create_time。
- update_time。

### 5.2 t_agent_declared_skill

保存子 Agent 声明的 skill。

字段建议：

- id。
- agent_id。
- skill_id。
- skill_name。
- description。
- tags。
- examples。
- input_modes。
- output_modes。
- raw_payload。
- create_time。
- update_time。

### 5.3 t_agent_declared_mcp

保存子 Agent 声明的 MCP。

字段建议：

- id。
- agent_id。
- mcp_id。
- mcp_name。
- description。
- transport。
- endpoint。
- tags。
- raw_payload。
- create_time。
- update_time。

### 5.4 t_agent_declared_workflow

保存子 Agent 声明的 workflow。

字段建议：

- id。
- agent_id。
- workflow_id。
- workflow_name。
- description。
- steps。
- tags。
- raw_payload。
- create_time。
- update_time。

### 5.5 t_agent_policy

保存主 Agent 对子 Agent 的访问控制策略。

字段建议：

- policy_id。
- agent_id。
- tenant_id。
- allowed_users。
- allowed_roles。
- allowed_sources。
- default_decision。
- rate_limit。
- audit_required。
- enabled。
- create_time。
- update_time。

### 5.6 t_agent_profile_sync_log

保存同步日志。

字段建议：

- sync_id。
- namespace。
- source。
- status。
- pulled_count。
- upserted_count。
- failed_count。
- error_message。
- start_time。
- end_time。

### 5.7 t_agent_task_evaluation

保存单次任务评估。

字段建议：

- evaluation_id。
- task_id。
- agent_id。
- route_match_score。
- success_score。
- latency_score。
- answer_quality_score。
- safety_score。
- declared_capability_match_score。
- user_feedback_score。
- overall_score。
- result_label。
- evaluator_type。
- summary。
- suggestions。
- evidence。
- create_time。

### 5.8 t_agent_profile_evaluation_daily

保存 Agent 长期评估聚合。

字段建议：

- id。
- stat_date。
- agent_id。
- call_count。
- success_count。
- failure_count。
- avg_latency_ms。
- p95_latency_ms。
- avg_score。
- positive_feedback_count。
- negative_feedback_count。
- route_miss_count。
- risk_event_count。
- governance_status。
- create_time。

## 6. API 设计

### 6.1 Agent Profile

- `POST /api/agent-profiles/sync`：手动从 Nacos 同步。
- `GET /api/agent-profiles`：查询 Agent Profile 列表。
- `GET /api/agent-profiles/{agent_id}`：查询 Agent Profile 详情。
- `GET /api/agent-profiles/{agent_id}/declared-skills`：查询声明技能。
- `GET /api/agent-profiles/{agent_id}/declared-mcps`：查询声明 MCP。
- `GET /api/agent-profiles/{agent_id}/declared-workflows`：查询声明 Workflow。
- `GET /api/agent-profiles/{agent_id}/recent-tasks`：查询近期任务。

### 6.2 Policy

- `GET /api/agent-policies`：查询策略。
- `PUT /api/agent-policies/{agent_id}`：更新 Agent 访问策略。
- `POST /api/agent-policies/check`：检查调用权限。

### 6.3 Routing

- `POST /api/agent-gateway/route`：只做路由解释，不实际调用。
- `POST /api/agent-gateway/invoke`：路由并调用子 Agent。

### 6.4 Evaluation

- `GET /api/agent-profiles/{agent_id}/evaluations`：查询 Agent 评估历史。
- `GET /api/agent-profiles/{agent_id}/evaluation-summary`：查询 Agent 聚合评估。
- `POST /api/tasks/{task_id}/evaluate`：手动触发单次任务评估。

### 6.5 Governance

- `GET /api/agent-governance/issues`：查询治理问题。
- `GET /api/agent-governance/overview`：治理概览。
- `POST /api/agent-governance/issues/{issue_id}/actions`：记录治理动作。

## 7. 路由执行流程

1. 接收外部请求。
2. 写入 task。
3. 加载可用 Agent Profile。
4. 根据用户输入、biz_domain、description、declared skills 构建候选集。
5. 执行 Agent Policy 检查。
6. 选择目标子 Agent。
7. 写入 route_selected 任务事件和审计。
8. 通过 A2A/HTTP 调用子 Agent。
9. 记录子 Agent 响应和耗时。
10. 写入任务看板事件。
11. 执行单次任务评估。
12. 更新 Agent 长期评估数据。
13. 返回最终结果。

## 8. 前端设计

### 8.1 Agent Profile 页面

展示内容：

- Agent 列表。
- Agent 详情。
- 声明 skills。
- 声明 mcps。
- 声明 workflows。
- 权限策略。
- 健康状态。
- 近期任务。
- 评估摘要。
- 治理问题。

### 8.2 任务看板增强

新增展示：

- 路由候选 Agent。
- 最终选中 Agent。
- 命中 declared skills。
- declared mcps。
- declared workflows。
- 子 Agent 实际返回事件。
- observed mcps。
- 单次任务评估。

### 8.3 评估看板增强

新增展示：

- Agent 维度评分趋势。
- 成功率趋势。
- 延迟趋势。
- 路由命中质量。
- 声明能力匹配情况。
- 治理建议。

## 9. 开发计划

### 阶段 1：Agent Profile 同步闭环

目标：从 Nacos 拉取子 Agent，落库并可查询。

任务：

- 新增 `t_agent_profile`。
- 新增 `t_agent_declared_skill`。
- 新增 `t_agent_declared_mcp`。
- 新增 `t_agent_declared_workflow`。
- 新增 `t_agent_profile_sync_log`。
- 实现 `AgentProfileRepository`。
- 实现 `AgentProfileSyncService`。
- 新增 `/api/agent-profiles/sync`。
- 新增 `/api/agent-profiles` 和详情接口。
- 补单元测试。

验收：

- 能从 Nacos 拉到 Agent Card。
- metadata 缺失时仍可生成 Agent Profile。
- Agent 声明 skills 能落库展示。
- mcps/workflows 有则展示，无则为空。

### 阶段 2：权限与路由解释

目标：主 Agent 能基于 Agent Profile 做路由和权限判断。

任务：

- 新增 `t_agent_policy`。
- 实现 `AgentPolicyService`。
- 实现 `AgentGatewayRoutingService`。
- 新增 `/api/agent-gateway/route`。
- 在路由结果中返回候选、过滤原因、命中 skill。
- 补审计事件。

验收：

- 可以指定用户、角色、业务域检查访问权限。
- 可以解释为什么选中某个 Agent。
- 禁用 Agent 不会被路由选中。

### 阶段 3：网关调用与任务看板

目标：主 Agent 调用子 Agent，并把过程展示到任务看板。

任务：

- 新增 `/api/agent-gateway/invoke`。
- 调用子 Agent A2A/HTTP endpoint。
- 写入 task event。
- 写入 audit log。
- 任务详情展示 declared skills/mcps/workflows。
- 解析子 Agent 返回事件形成 observed 记录。

验收：

- 能通过网关调用子 Agent。
- 任务看板能看到路由、调用、响应、耗时。
- 审计能回放一次调用全过程。

### 阶段 4：单次任务评估

目标：每次子 Agent 调用后生成任务评估。

任务：

- 新增 `t_agent_task_evaluation`。
- 实现规则评估。
- 接入现有 EvaluationService。
- 评估维度新增 route_match、latency、declared_capability_match。
- 任务详情展示评估结果。

验收：

- 每次任务可生成评估。
- 评估结果能关联 task_id 和 agent_id。
- 低评分任务能进入治理问题候选。

### 阶段 5：长期评估与治理

目标：形成 Agent 级别的运行质量分析。

任务：

- 新增 `t_agent_profile_evaluation_daily`。
- 实现聚合任务。
- 实现 `AgentGovernanceService`。
- 新增治理概览和问题接口。
- Agent Profile 页面展示评估趋势和治理建议。

验收：

- 可以看到 Agent 成功率、耗时、评分趋势。
- 可以识别慢响应、高失败、低质量 Agent。
- 可以生成治理建议。

## 10. 当前分支交付策略

当前分支：`codex/nacos-resource-center`。

虽然分支名仍是 resource center，但本分支实际目标调整为 Agent Gateway Control Plane。

推荐提交节奏：

- Commit 1：需求文档和开发计划。
- Commit 2：Agent Profile 表结构和迁移。
- Commit 3：Agent Profile 同步服务。
- Commit 4：Agent Profile API。
- Commit 5：权限策略和路由解释。
- Commit 6：网关调用和任务看板增强。
- Commit 7：评估和治理增强。

## 11. 关键设计决策

- 子 Agent 是能力拥有方。
- Skill、MCP、Workflow 是子 Agent 的声明能力，不由主 Agent 管理。
- 主 Agent 可以记录 declared 信息，但不修改其内部语义。
- 主 Agent 控制用户能否调用子 Agent。
- 子 Agent 控制内部如何执行 Skill、MCP、Workflow。
- 主 Agent 负责审计、观察、评估和治理。
- Nacos metadata 缺失时，主 Agent 仍可正常展示和路由基础 Agent。
- declared 和 observed 必须分开展示。

## 12. 待确认事项

- 子 Agent 是否统一支持 A2A Agent Card。
- 子 Agent 是否会在 Agent Card metadata 中补充 mcps/workflows。
- 用户、角色、租户信息从哪里获取。
- 评估 Agent 使用本地规则还是接入外部模型。
- 治理建议是否只展示，还是允许后续自动降权。
