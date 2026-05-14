# Skill: merchant_onboarding_review

## Purpose

辅助运营人员完成商户入网审核，输出结构化审核意见。

## When To Use

- 用户发起入网审核
- 需要核对入网材料与准入要求

## Required Inputs

- merchant_id
- onboarding_materials
- industry_info
- compliance_flags

## Steps

1. 核验资料完整性
2. 对照准入规则检查
3. 标识高风险或缺失项
4. 产出审核建议
5. 进入人工审批

## Human Escalation

- 资料缺失
- 合规命中
- 黑名单命中
