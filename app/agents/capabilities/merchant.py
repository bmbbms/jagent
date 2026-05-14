from __future__ import annotations

from app.agents.base import CapabilityAgent, CapabilityDefinition
from app.registry.bootstrap import register_capability
from app.schemas import BizDomain, ChatRequest, ChatResponse
from app.tools import available_tools


@register_capability
class MerchantQaAgent(CapabilityAgent):
    definition = CapabilityDefinition(
        capability_id="merchant.qa",
        name="Merchant QA Agent",
        biz_domain=BizDomain.merchant,
        description="面向商户常见问题的知识问答能力",
        triggers=["规则", "流程", "怎么", "faq", "问答", "咨询"],
        skills=["merchant_qa"],
        priority=10,
    )

    def run(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            domain=BizDomain.merchant,
            capability_id=self.definition.capability_id,
            capability_name=self.definition.name,
            summary="已命中商户问答能力，优先基于 FAQ 和制度知识返回标准口径。",
            next_action="检索商户知识库并返回标准答复，无法确认时转人工。",
            selected_skills=["merchant_qa"],
            selected_tools=available_tools(BizDomain.merchant),
            references=["K001: 商户常见问题FAQ"],
            requires_approval=False,
            workflow=None,
            audit_tags=["merchant", "qa", "phase1"],
        )


@register_capability
class MerchantIssueHandlingAgent(CapabilityAgent):
    definition = CapabilityDefinition(
        capability_id="merchant.issue_handling",
        name="Merchant Issue Handling Agent",
        biz_domain=BizDomain.merchant,
        description="面向商户问题分类与处理建议的能力",
        triggers=["问题", "异常", "失败", "工单", "差错", "冻结", "处理"],
        skills=["merchant_issue_handling"],
        priority=20,
    )

    def run(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            domain=BizDomain.merchant,
            capability_id=self.definition.capability_id,
            capability_name=self.definition.name,
            summary="已命中商户问题处理能力，可输出问题分类、处理路径和提单建议。",
            next_action="先分类问题并补齐关键信息，再视情况提交工单或升级人工。",
            selected_skills=["merchant_issue_handling"],
            selected_tools=available_tools(BizDomain.merchant),
            references=["K001: 商户常见问题FAQ", "K010: 商户问题处理案例库"],
            requires_approval=False,
            workflow=None,
            audit_tags=["merchant", "issue", "phase1"],
        )


@register_capability
class MerchantOpsAnalysisAgent(CapabilityAgent):
    definition = CapabilityDefinition(
        capability_id="merchant.ops_analysis",
        name="Merchant Ops Analysis Agent",
        biz_domain=BizDomain.merchant,
        description="面向商户经营分析和交易表现解读的能力",
        triggers=["经营", "分析", "交易", "增长", "gmv", "退款"],
        skills=["merchant_ops_analysis"],
        priority=30,
    )

    def run(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            domain=BizDomain.merchant,
            capability_id=self.definition.capability_id,
            capability_name=self.definition.name,
            summary="已命中商户经营分析能力，可基于交易和指标数据给出初步结论。",
            next_action="调用交易与经营数据查询工具，返回结构化分析结果。",
            selected_skills=["merchant_ops_analysis"],
            selected_tools=available_tools(BizDomain.merchant),
            references=["K008: 销售数据指标字典"],
            requires_approval=False,
            workflow=None,
            audit_tags=["merchant", "analysis", "phase1"],
        )
