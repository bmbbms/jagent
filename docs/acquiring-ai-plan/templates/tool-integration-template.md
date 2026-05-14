# 首批 Tool 对接清单样表

## 样表

| Tool编号 | Tool名称 | 所属业务域 | 功能说明 | 对接系统 | 动作类型 | 风险等级 | 是否审批 | 返回类型 | 优先级 |
|---|---|---|---|---|---|---|---|---|---|
| T001 | merchant_profile_query | 商户AI / 运营支持 | 查询商户基础资料 | 商户系统 | 只读查询 | 低 | 否 | JSON | P0 |
| T002 | merchant_transaction_summary | 商户AI / 运营支持 | 查询商户交易概况 | 交易系统 | 只读查询 | 低 | 否 | JSON | P0 |
| T003 | merchant_risk_tag_query | 运营支持 | 查询商户风险标签 | 风控系统 | 只读查询 | 中 | 否 | JSON | P0 |
| T004 | merchant_history_review_query | 运营支持 | 查询历史审核记录 | 审核系统 | 只读查询 | 中 | 否 | JSON | P1 |
| T005 | onboarding_material_check | 运营支持 | 校验入网资料完整性 | 商户系统 / 审核系统 | 只读查询 | 中 | 否 | JSON | P1 |
| T006 | quota_approval_submit | 运营支持 | 提交调额审批申请 | 审批系统 | 写操作 | 高 | 是 | JSON | P0 |
| T007 | onboarding_approval_submit | 运营支持 | 提交入网审核结果 | 审批系统 | 写操作 | 高 | 是 | JSON | P1 |
| T008 | merchant_change_approval_submit | 运营支持 | 提交变更审核结果 | 审批系统 | 写操作 | 高 | 是 | JSON | P1 |
| T009 | direct_sales_metrics_query | 数据支持 | 查询直营销售指标 | 数据仓库 / BI系统 | 只读查询 | 中 | 否 | JSON / 表格 | P0 |
| T010 | branch_metrics_query | 数据支持 | 查询分公司经营指标 | 数据仓库 / BI系统 | 只读查询 | 中 | 否 | JSON / 表格 | P1 |
| T011 | compliance_report_export | 数据支持 | 导出固定合规报表 | 报表系统 | 导出操作 | 中高 | 视场景 | 文件 / 链接 | P1 |
| T012 | ticket_submit | 商户AI / 运营支持 | 提交问题工单 | 工单系统 | 写操作 | 中 | 视场景 | JSON | P1 |

## 建议补充列

- 接口方式：API / DB / MCP / 文件交换
- 认证方式：Token / SSO / 内网白名单
- 是否支持批量
- 超时时间
- 限流要求
- 失败重试策略
- 返回字段说明
- 负责人
- 联调状态

## Tool 设计建议

- 只读查询和写操作必须分开管理
- 每个 Tool 都要标清风险等级
- 高风险 Tool 必须明确审批前置
- Tool 返回尽量结构化，避免大段自由文本
- Tool 层统一做超时、异常、审计、权限透传
