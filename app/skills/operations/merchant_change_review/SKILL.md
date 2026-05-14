# Skill: merchant_change_review

## Purpose

辅助处理商户变更审核，判断材料是否齐备、是否符合规则，并给出处理建议。

## When To Use

- 商户基础信息、账户信息、经营信息变更审核

## Required Inputs

- merchant_id
- change_type
- change_materials
- historical_review_records

## Steps

1. 判断变更类型
2. 核对材料和历史审核记录
3. 识别风险点和规则约束
4. 生成结构化建议
5. 提交审批

## Human Escalation

- 关键信息不一致
- 风险标签命中
- 超出标准变更范围
