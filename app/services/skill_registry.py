from __future__ import annotations

from typing import Dict, List

from app.schemas import BizDomain


class SkillRegistry:
    """Static phase 1 skill registry."""

    def __init__(self) -> None:
        self._skills: Dict[BizDomain, List[str]] = {
            BizDomain.merchant: [
                "merchant_qa",
                "merchant_issue_handling",
            ],
            BizDomain.operations: [
                "quota_review",
                "merchant_onboarding_review",
                "merchant_change_review",
            ],
            BizDomain.data_support: [
                "direct_sales_data_assistant",
                "compliance_report_generation",
            ],
        }

    def get_skills(self, biz_domain: BizDomain) -> List[str]:
        return self._skills.get(biz_domain, [])
