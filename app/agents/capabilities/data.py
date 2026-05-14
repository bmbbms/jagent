from __future__ import annotations

from app.agents.base import CapabilityAgent, CapabilityDefinition
from app.registry.bootstrap import register_capability
from app.schemas import BizDomain, ChatRequest, ChatResponse
from app.tools import available_tools


@register_capability
class DirectSalesDataAgent(CapabilityAgent):
    definition = CapabilityDefinition(
        capability_id="data_support.direct_sales_data",
        name="Direct Sales Data Agent",
        biz_domain=BizDomain.data_support,
        description="面向直营销售数据查询与分析的能力",
        triggers=["销售", "直营", "指标", "数据", "业绩"],
        skills=["direct_sales_data_assistant"],
        priority=10,
    )

    def run(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            domain=BizDomain.data_support,
            capability_id=self.definition.capability_id,
            capability_name=self.definition.name,
            summary="已命中直营销售数据能力，可进行只读查询和结构化分析输出。",
            next_action="执行指标查询并结合口径文档生成分析结论。",
            selected_skills=["direct_sales_data_assistant"],
            selected_tools=available_tools(BizDomain.data_support),
            references=["K008: 销售数据指标字典"],
            requires_approval=False,
            workflow=None,
            audit_tags=["data_support", "direct_sales_data", "phase1"],
        )


@register_capability
class ComplianceReportAgent(CapabilityAgent):
    definition = CapabilityDefinition(
        capability_id="data_support.compliance_report",
        name="Compliance Report Agent",
        biz_domain=BizDomain.data_support,
        description="面向固定合规报表生成与口径解释的能力",
        triggers=["报表", "监管", "合规", "导出"],
        skills=["compliance_report_generation"],
        priority=20,
    )

    def run(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            domain=BizDomain.data_support,
            capability_id=self.definition.capability_id,
            capability_name=self.definition.name,
            summary="已命中合规报表能力，可按固定口径辅助生成报表结果。",
            next_action="按报表口径执行只读查询，如涉及导出则补充审计。",
            selected_skills=["compliance_report_generation"],
            selected_tools=available_tools(BizDomain.data_support),
            references=["K007: 合规监管报表口径文档"],
            requires_approval=False,
            workflow="compliance_report",
            audit_tags=["data_support", "compliance_report", "phase1"],
        )
