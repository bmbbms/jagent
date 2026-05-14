# Skill: quota_review

## Purpose

用于调额审核辅助，帮助运营人员对申请资料、风险信息、历史交易表现进行结构化审查，并输出审核建议。

## When To Use

- 发起调额审核
- 询问某商户是否具备调额条件
- 需要输出调额审核结论草稿

## Required Inputs

- merchant_id
- apply_amount
- apply_reason
- historical_transaction_summary
- risk_flags

## Steps

1. 校验输入是否完整
2. 查询商户基础信息、历史交易、风险标签
3. 对照调额规则逐项检查
4. 输出风险点、支持点、待补充材料
5. 命中高风险条件时转审批工作流

## Allowed Tools

- merchant_profile_query
- merchant_transaction_summary
- merchant_risk_tag_query
- quota_approval_submit

## Human Escalation

- 命中重大风险标签
- 额度超过人工审批阈值
- 规则冲突或资料不一致
