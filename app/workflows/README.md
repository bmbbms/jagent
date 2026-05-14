# Phase 1 Workflows

本目录收纳一期 MVP 的高风险业务流程定义。

当前一期范围：

- 调额审核辅助
- 入网审核辅助
- 商户变更审核辅助
- 合规固定报表辅助

当前代码中暂以 `app/workflows.py` 保存简化流程元数据。

后续建议拆分为独立模块：

- `quota_review.py`
- `onboarding_review.py`
- `merchant_change_review.py`
- `compliance_report.py`

每个 workflow 建议统一包含：

- purpose
- inputs
- required_tools
- approval_points
- fallback_rules
- audit_tags
