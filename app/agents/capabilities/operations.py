from __future__ import annotations

from app.agents.base import CapabilityAgent, CapabilityDefinition
from app.registry.bootstrap import register_capability
from app.schemas import BizDomain, ChatRequest, ChatResponse
from app.tools import available_tools


@register_capability
class QuotaReviewAgent(CapabilityAgent):
    definition = CapabilityDefinition(
        capability_id="operations.quota_review",
        name="Quota Review Agent",
        biz_domain=BizDomain.operations,
        description="面向调额审核辅助的能力。",
        triggers=["调额", "额度", "提额", "限额", "quota review"],
        skills=["quota_review"],
        priority=10,
        risk_level="high",
        requires_approval=True,
        tags=["operations", "quota_review", "approval", "phase1"],
    )

    def run(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            domain=BizDomain.operations,
            capability_id=self.definition.capability_id,
            capability_name=self.definition.name,
            summary="已命中调额审核能力，需要收集资料、校验规则并进入审批流程。",
            next_action="调用商户、交易、风控类工具后生成结构化建议，并提交审批。",
            selected_skills=["quota_review"],
            selected_tools=available_tools(BizDomain.operations),
            references=["K004: 调额审核规则"],
            requires_approval=True,
            workflow="quota_review",
            audit_tags=["operations", "quota_review", "approval", "phase1"],
        )


@register_capability
class OnboardingReviewAgent(CapabilityAgent):
    definition = CapabilityDefinition(
        capability_id="operations.onboarding_review",
        name="Onboarding Review Agent",
        biz_domain=BizDomain.operations,
        description="面向商户进件审核辅助的能力。",
        triggers=["进件", "准入", "开户", "入网"],
        skills=["merchant_onboarding_review"],
        priority=20,
        risk_level="high",
        requires_approval=True,
        tags=["operations", "onboarding_review", "approval", "phase1"],
    )

    def run(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            domain=BizDomain.operations,
            capability_id=self.definition.capability_id,
            capability_name=self.definition.name,
            summary="已命中进件审核能力，需要对照准入规则、资料要求和合规条件处理。",
            next_action="校验资料完整性，识别风险点后进入审批流程。",
            selected_skills=["merchant_onboarding_review"],
            selected_tools=available_tools(BizDomain.operations),
            references=["K002: 商户入网规则手册"],
            requires_approval=True,
            workflow="onboarding_review",
            audit_tags=["operations", "onboarding_review", "approval", "phase1"],
        )


@register_capability
class MerchantChangeReviewAgent(CapabilityAgent):
    definition = CapabilityDefinition(
        capability_id="operations.merchant_change_review",
        name="Merchant Change Review Agent",
        biz_domain=BizDomain.operations,
        description="面向商户变更审核辅助的能力。",
        triggers=["变更", "修改", "更新资料"],
        skills=["merchant_change_review"],
        priority=30,
        risk_level="high",
        requires_approval=True,
        tags=["operations", "merchant_change_review", "approval", "phase1"],
    )

    def run(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            domain=BizDomain.operations,
            capability_id=self.definition.capability_id,
            capability_name=self.definition.name,
            summary="已命中商户变更审核能力，需要对材料、历史记录和规则约束做结构化校验。",
            next_action="调用变更审核相关工具，形成建议后进入审批。",
            selected_skills=["merchant_change_review"],
            selected_tools=available_tools(BizDomain.operations),
            references=["K003: 商户变更审核规范"],
            requires_approval=True,
            workflow="merchant_change_review",
            audit_tags=["operations", "merchant_change_review", "approval", "phase1"],
        )
