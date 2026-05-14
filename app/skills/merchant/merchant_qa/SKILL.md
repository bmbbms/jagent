# Skill: merchant_qa

## Purpose

回答商户常见问题，并尽量基于制度和 FAQ 返回标准化口径。

## When To Use

- 商户咨询制度、规则、操作流程
- 客服需要快速生成标准答复

## Required Inputs

- question

## Steps

1. 判断问题归属是否为商户问答场景
2. 检索 FAQ、制度文档和知识片段
3. 优先输出标准口径和处理建议
4. 无法确认时提示转人工

## Output

- answer_summary
- references
- next_action

## Human Escalation

- 规则冲突
- 缺少有效知识依据
- 用户诉求超出 FAQ 和制度边界
