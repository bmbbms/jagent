from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Iterable

from app.schemas import BizDomain


@dataclass(frozen=True)
class WorkflowStepDefinition:
    step_code: str
    name: str
    step_type: str
    description: str
    required_tools: list[str] = field(default_factory=list)
    approval_required: bool = False


@dataclass(frozen=True)
class WorkflowDefinition:
    workflow_code: str
    name: str
    biz_domain: BizDomain
    purpose: str
    required_inputs: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    approval_points: list[str] = field(default_factory=list)
    fallback_rules: list[str] = field(default_factory=list)
    audit_tags: list[str] = field(default_factory=list)
    steps: list[WorkflowStepDefinition] = field(default_factory=list)


DEFAULT_WORKFLOWS: list[WorkflowDefinition] = [
    WorkflowDefinition(
        workflow_code="quota_review",
        name="调额审核流程",
        biz_domain=BizDomain.operations,
        purpose="收集商户、交易、风险信息后形成调额建议，并提交人工审批。",
        required_inputs=["merchant_id", "target_quota", "reason"],
        required_tools=[
            "merchant_profile_query",
            "merchant_transaction_summary",
            "merchant_risk_tag_query",
            "quota_approval_submit",
        ],
        approval_points=["额度建议确认", "人工审批放行"],
        fallback_rules=["商户档案缺失时转人工", "风险标签异常时强制审批"],
        audit_tags=["workflow", "quota_review", "approval"],
        steps=[
            WorkflowStepDefinition(
                step_code="collect_profile",
                name="收集商户档案",
                step_type="data_query",
                description="查询商户基础信息和状态。",
                required_tools=["merchant_profile_query"],
            ),
            WorkflowStepDefinition(
                step_code="collect_transactions",
                name="收集交易汇总",
                step_type="data_query",
                description="汇总交易量、成功率、退款率等指标。",
                required_tools=["merchant_transaction_summary"],
            ),
            WorkflowStepDefinition(
                step_code="collect_risk_tags",
                name="收集风险标签",
                step_type="risk_check",
                description="识别风险标签并给出风险分。",
                required_tools=["merchant_risk_tag_query"],
            ),
            WorkflowStepDefinition(
                step_code="submit_approval",
                name="提交调额审批",
                step_type="approval",
                description="形成结构化建议并提交审批。",
                required_tools=["quota_approval_submit"],
                approval_required=True,
            ),
        ],
    ),
    WorkflowDefinition(
        workflow_code="onboarding_review",
        name="进件审核流程",
        biz_domain=BizDomain.operations,
        purpose="校验进件资料、识别风险点并进入人工审核。",
        required_inputs=["merchant_id", "materials"],
        required_tools=["merchant_profile_query", "ticket_submit"],
        approval_points=["准入条件确认", "人工终审"],
        fallback_rules=["资料缺失时创建工单补件", "高风险行业强制人工审核"],
        audit_tags=["workflow", "onboarding_review", "approval"],
        steps=[
            WorkflowStepDefinition(
                step_code="check_profile",
                name="校验商户基础信息",
                step_type="data_query",
                description="核验商户主体与状态信息。",
                required_tools=["merchant_profile_query"],
            ),
            WorkflowStepDefinition(
                step_code="raise_ticket",
                name="补件工单",
                step_type="ops_ticket",
                description="资料不完整时生成补件工单。",
                required_tools=["ticket_submit"],
                approval_required=True,
            ),
        ],
    ),
    WorkflowDefinition(
        workflow_code="merchant_change_review",
        name="商户变更审核流程",
        biz_domain=BizDomain.operations,
        purpose="校验商户变更申请，评估风险并进入审批。",
        required_inputs=["merchant_id", "change_request"],
        required_tools=["merchant_profile_query", "merchant_risk_tag_query", "ticket_submit"],
        approval_points=["变更建议确认", "人工审批放行"],
        fallback_rules=["命中高风险标签时转人工", "缺资料时生成工单"],
        audit_tags=["workflow", "merchant_change_review", "approval"],
        steps=[
            WorkflowStepDefinition(
                step_code="check_profile",
                name="校验商户档案",
                step_type="data_query",
                description="确认商户当前基础信息。",
                required_tools=["merchant_profile_query"],
            ),
            WorkflowStepDefinition(
                step_code="check_risk",
                name="校验风险标签",
                step_type="risk_check",
                description="识别变更相关风险点。",
                required_tools=["merchant_risk_tag_query"],
            ),
            WorkflowStepDefinition(
                step_code="raise_ticket",
                name="创建变更跟进工单",
                step_type="ops_ticket",
                description="需要补充材料或人工跟进时创建工单。",
                required_tools=["ticket_submit"],
                approval_required=True,
            ),
        ],
    ),
    WorkflowDefinition(
        workflow_code="compliance_report",
        name="合规报表导出流程",
        biz_domain=BizDomain.data_support,
        purpose="查询指标并导出合规报表。",
        required_inputs=["report_type", "format", "metrics_date"],
        required_tools=["direct_sales_metrics_query", "compliance_report_export"],
        approval_points=[],
        fallback_rules=["指标缺失时中止导出并转人工确认"],
        audit_tags=["workflow", "compliance_report"],
        steps=[
            WorkflowStepDefinition(
                step_code="query_metrics",
                name="查询经营指标",
                step_type="data_query",
                description="查询直营经营指标作为报表输入。",
                required_tools=["direct_sales_metrics_query"],
            ),
            WorkflowStepDefinition(
                step_code="export_report",
                name="导出报表",
                step_type="report_export",
                description="生成可下载报表任务。",
                required_tools=["compliance_report_export"],
            ),
        ],
    ),
]


class WorkflowRegistry:
    def __init__(self, workflows: Iterable[WorkflowDefinition] | None = None) -> None:
        items = list(workflows or DEFAULT_WORKFLOWS)
        self._workflows = {item.workflow_code: item for item in items}

    def register(self, workflow: WorkflowDefinition) -> None:
        self._workflows[workflow.workflow_code] = workflow

    def get(self, workflow_code: str) -> WorkflowDefinition | None:
        return self._workflows.get(workflow_code)

    def list(self, biz_domain: BizDomain | None = None) -> list[WorkflowDefinition]:
        items = list(self._workflows.values())
        if biz_domain is not None:
            items = [item for item in items if item.biz_domain == biz_domain]
        return sorted(items, key=lambda item: (item.biz_domain.value, item.workflow_code))
