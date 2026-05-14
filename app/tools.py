from __future__ import annotations

from typing import Dict, List

from app.schemas import BizDomain


def available_tools(biz_domain: BizDomain) -> List[str]:
    tools: Dict[BizDomain, List[str]] = {
        BizDomain.merchant: [
            "merchant_profile_query",
            "ticket_submit",
        ],
        BizDomain.operations: [
            "merchant_profile_query",
            "merchant_transaction_summary",
            "merchant_risk_tag_query",
            "quota_approval_submit",
        ],
        BizDomain.data_support: [
            "direct_sales_metrics_query",
            "compliance_report_export",
        ],
    }
    return tools.get(biz_domain, [])
