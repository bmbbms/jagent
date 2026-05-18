from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.services.internal_tool_provider import (
    InternalToolProvider,
    QuotaApprovalSubmission,
    ReportExportSubmission,
    ServiceTicketSubmission,
)
from app.repositories.internal_tool_business_repository import DirectSalesMetricDailyRecord
from app.repositories.merchant_data_repository import (
    MerchantProfileRecord,
    MerchantRiskTagSummaryRecord,
    MerchantTransactionSummaryRecord,
)


class HttpInternalToolProvider(InternalToolProvider):
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 10.0,
        bearer_token: str = "",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._bearer_token = bearer_token

    def query_merchant_profile(self, *, merchant_id: str) -> MerchantProfileRecord | None:
        payload = self._request_json(
            method="GET",
            path="/merchant/profile",
            query_params={"merchant_id": merchant_id},
        )
        if not payload:
            return None
        return MerchantProfileRecord(
            merchant_id=str(payload["merchant_id"]),
            merchant_name=str(payload["merchant_name"]),
            status=str(payload["status"]),
            risk_level=str(payload["risk_level"]),
            industry_code=payload.get("industry_code"),
            contact_name=payload.get("contact_name"),
            contact_phone=payload.get("contact_phone"),
            register_time=payload.get("register_time"),
        )

    def query_merchant_transaction_summary(
        self,
        *,
        merchant_id: str,
    ) -> MerchantTransactionSummaryRecord | None:
        payload = self._request_json(
            method="GET",
            path="/merchant/transaction-summary",
            query_params={"merchant_id": merchant_id},
        )
        if not payload:
            return None
        return MerchantTransactionSummaryRecord(
            merchant_id=str(payload["merchant_id"]),
            txn_count=int(payload.get("txn_count", 0)),
            success_count=int(payload.get("success_count", 0)),
            refund_count=int(payload.get("refund_count", 0)),
            gmv_amount=int(payload.get("gmv_amount", 0)),
            refund_amount=int(payload.get("refund_amount", 0)),
        )

    def query_merchant_risk_tags(
        self,
        *,
        merchant_id: str,
    ) -> MerchantRiskTagSummaryRecord | None:
        payload = self._request_json(
            method="GET",
            path="/merchant/risk-tags",
            query_params={"merchant_id": merchant_id},
        )
        if not payload:
            return None
        return MerchantRiskTagSummaryRecord(
            merchant_id=str(payload["merchant_id"]),
            risk_tags=[str(item) for item in payload.get("risk_tags", [])],
            max_risk_score=int(payload.get("risk_score", 0)),
        )

    def submit_quota_approval(
        self,
        *,
        approval_id: str,
        task_id: str | None,
        contact_id: str | None,
        merchant_id: str,
        requested_by: str,
        title: str,
        reason: str,
        payload: dict[str, Any],
    ) -> QuotaApprovalSubmission:
        response = self._request_json(
            method="POST",
            path="/operations/quota-approvals",
            body={
                "approval_id": approval_id,
                "task_id": task_id,
                "contact_id": contact_id,
                "merchant_id": merchant_id,
                "requested_by": requested_by,
                "title": title,
                "reason": reason,
                "payload": payload,
            },
        )
        return QuotaApprovalSubmission(
            approval_id=str(response.get("approval_id", approval_id)),
            merchant_id=str(response.get("merchant_id", merchant_id)),
            status=str(response.get("status", "pending")),
            approval_type=str(response.get("approval_type", "quota_adjustment")),
            workflow_code=response.get("workflow_code", "quota_adjustment"),
            apply_amount=response.get("apply_amount", payload.get("apply_amount")),
        )

    def query_direct_sales_metrics(
        self,
        *,
        stat_date: str,
        region_code: str,
    ) -> DirectSalesMetricDailyRecord | None:
        payload = self._request_json(
            method="GET",
            path="/data/direct-sales-metrics",
            query_params={"stat_date": stat_date, "region_code": region_code},
        )
        if not payload:
            return None
        return DirectSalesMetricDailyRecord(
            stat_date=str(payload["stat_date"]),
            region_code=str(payload["region_code"]),
            sales_amount=int(payload.get("sales_amount", 0)),
            merchant_count=int(payload.get("merchant_count", 0)),
            conversion_rate=float(payload.get("conversion_rate", 0.0)),
        )

    def export_compliance_report(
        self,
        *,
        report_id: str,
        report_type: str,
        export_format: str,
        requested_by: str,
        request_params: dict[str, Any],
    ) -> ReportExportSubmission:
        response = self._request_json(
            method="POST",
            path="/data/compliance-reports/export",
            body={
                "report_id": report_id,
                "report_type": report_type,
                "format": export_format,
                "requested_by": requested_by,
                "request_params": request_params,
            },
        )
        return ReportExportSubmission(
            report_id=str(response.get("report_id", report_id)),
            report_type=str(response.get("report_type", report_type)),
            export_format=str(response.get("format", export_format)),
            status=str(response.get("status", "generated")),
            output_uri=response.get("output_uri"),
        )

    def submit_service_ticket(
        self,
        *,
        ticket_id: str,
        merchant_id: str | None,
        requested_by: str,
        category: str,
        priority: str,
        title: str,
        description: str,
        payload: dict[str, Any],
    ) -> ServiceTicketSubmission:
        response = self._request_json(
            method="POST",
            path="/operations/service-tickets",
            body={
                "ticket_id": ticket_id,
                "merchant_id": merchant_id,
                "requested_by": requested_by,
                "category": category,
                "priority": priority,
                "title": title,
                "description": description,
                "payload": payload,
            },
        )
        return ServiceTicketSubmission(
            ticket_id=str(response.get("ticket_id", ticket_id)),
            merchant_id=response.get("merchant_id", merchant_id),
            status=str(response.get("status", "submitted")),
            category=str(response.get("category", category)),
            priority=str(response.get("priority", priority)),
        )

    def _request_json(
        self,
        *,
        method: str,
        path: str,
        query_params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        query = f"?{urlencode(query_params)}" if query_params else ""
        url = f"{self._base_url}{path}{query}"
        headers = {"Accept": "application/json"}
        data: bytes | None = None
        if self._bearer_token:
            headers["Authorization"] = f"Bearer {self._bearer_token}"
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")

        request = Request(url=url, method=method.upper(), headers=headers, data=data)
        with urlopen(request, timeout=self._timeout_seconds) as response:
            raw = response.read().decode("utf-8")
        if not raw.strip():
            return {}
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("HTTP internal tool provider expects JSON object responses")
        return payload
