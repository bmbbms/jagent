# Skill: merchant_ops_analysis

## Purpose

Support merchant operation analysis based on transaction, settlement, and performance indicators.

## When To Use

- Merchant asks for GMV, transaction, refund, or growth analysis
- Operations team needs a structured explanation of merchant performance
- A business user needs next-step suggestions based on merchant metrics

## Required Inputs

- merchant_id
- analysis_period
- metric_scope

## Steps

1. Confirm merchant identity, period, and metric scope.
2. Query read-only merchant operation indicators.
3. Compare trend, abnormal movement, and key contributing dimensions.
4. Return structured findings, risks, and recommended follow-up actions.

## Output

- analysis_summary
- metric_findings
- next_action

## Human Escalation

- Missing or inconsistent metrics
- User requests write operations or manual adjustment
- Potential compliance or risk signal appears in the analysis
