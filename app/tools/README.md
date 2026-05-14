# Phase 1 Tools

当前一期只定义 Tool 能力边界，尚未接入企业内部真实系统。

建议优先实现的工具：

- `merchant_profile_query`
- `merchant_transaction_summary`
- `merchant_risk_tag_query`
- `quota_approval_submit`
- `direct_sales_metrics_query`
- `compliance_report_export`
- `ticket_submit`

后续接入原则：

- 只读查询与写操作分开管理
- 高风险写操作默认需要审批
- 所有 Tool 统一补充权限透传、审计、超时、重试和错误码
