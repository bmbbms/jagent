# Skill: merchant_issue_handling

## Purpose

对商户问题进行分类，给出标准处理路径，并在需要时引导提单。

## When To Use

- 商户反馈异常、失败、差错、冻结、清算类问题
- 客服需要判断问题归属和处理方式

## Required Inputs

- issue_description

## Steps

1. 分类问题类型
2. 判断是否命中标准处理流程
3. 给出需要补充的关键信息
4. 提示是否需要提交工单或升级人工

## Output

- issue_type
- standard_path
- required_materials
- next_action
