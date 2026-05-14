from __future__ import annotations

from typing import Dict


WORKFLOWS: Dict[str, Dict[str, str]] = {
    "quota_review": {
        "purpose": "调额审核辅助",
        "risk_level": "high",
        "requires_approval": "true",
    },
    "onboarding_review": {
        "purpose": "入网审核辅助",
        "risk_level": "high",
        "requires_approval": "true",
    },
    "merchant_change_review": {
        "purpose": "商户变更审核辅助",
        "risk_level": "high",
        "requires_approval": "true",
    },
    "compliance_report": {
        "purpose": "合规固定报表辅助",
        "risk_level": "medium",
        "requires_approval": "false",
    },
}
