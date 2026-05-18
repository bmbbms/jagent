from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol
from uuid import uuid4

from app.services.internal_tool_provider import (
    InternalToolProvider,
)
from app.tools import ToolSpec


@dataclass(frozen=True)
class InternalToolAdapterResult:
    status: str
    output_summary: str
    payload: dict[str, Any] = field(default_factory=dict)


class InternalToolAdapter(Protocol):
    def execute(
        self,
        *,
        tool_spec: ToolSpec,
        request_context: dict[str, Any],
    ) -> InternalToolAdapterResult:
        raise NotImplementedError


class MerchantProfileQueryAdapter:
    def __init__(self, provider: InternalToolProvider) -> None:
        self._provider = provider

    def execute(
        self,
        *,
        tool_spec: ToolSpec,
        request_context: dict[str, Any],
    ) -> InternalToolAdapterResult:
        merchant_id = _resolve_merchant_id(request_context)
        profile = self._provider.query_merchant_profile(merchant_id=merchant_id)
        if profile is None:
            return InternalToolAdapterResult(
                status="failed",
                output_summary=f"未找到商户档案，merchant_id={merchant_id}。",
                payload=_build_payload(
                    tool_spec=tool_spec,
                    request_context=request_context,
                    result={"merchant_id": merchant_id, "found": False},
                    data_access_records=[
                        {
                            "data_source": "mysql",
                            "data_object": "t_merchant_profile",
                            "access_type": "read",
                            "sensitive_level": "medium",
                            "row_count": 0,
                            "field_scope": {
                                "fields": [
                                    "merchant_id",
                                    "merchant_name",
                                    "status",
                                    "risk_level",
                                ]
                            },
                        }
                    ],
                ),
            )

        return InternalToolAdapterResult(
            status="success",
            output_summary=f"已查询商户档案，merchant_id={merchant_id}，当前状态={profile.status}。",
            payload=_build_payload(
                tool_spec=tool_spec,
                request_context=request_context,
                result={
                    "merchant_id": profile.merchant_id,
                    "merchant_name": profile.merchant_name,
                    "status": profile.status,
                    "risk_level": profile.risk_level,
                    "industry_code": profile.industry_code,
                    "contact_name": profile.contact_name,
                    "contact_phone": profile.contact_phone,
                    "register_time": profile.register_time,
                },
                data_access_records=[
                    {
                        "data_source": "mysql",
                        "data_object": "t_merchant_profile",
                        "access_type": "read",
                        "sensitive_level": "medium",
                        "row_count": 1,
                        "field_scope": {
                            "fields": [
                                "merchant_id",
                                "merchant_name",
                                "status",
                                "risk_level",
                                "industry_code",
                                "contact_name",
                                "contact_phone",
                                "register_time",
                            ]
                        },
                    }
                ],
            ),
        )


class MerchantTransactionSummaryAdapter:
    def __init__(self, provider: InternalToolProvider) -> None:
        self._provider = provider

    def execute(
        self,
        *,
        tool_spec: ToolSpec,
        request_context: dict[str, Any],
    ) -> InternalToolAdapterResult:
        merchant_id = _resolve_merchant_id(request_context)
        summary = self._provider.query_merchant_transaction_summary(merchant_id=merchant_id)
        if summary is None:
            return InternalToolAdapterResult(
                status="failed",
                output_summary=f"未找到交易汇总，merchant_id={merchant_id}。",
                payload=_build_payload(
                    tool_spec=tool_spec,
                    request_context=request_context,
                    result={"merchant_id": merchant_id, "found": False},
                    data_access_records=[
                        {
                            "data_source": "mysql",
                            "data_object": "t_merchant_transaction_daily",
                            "access_type": "read",
                            "sensitive_level": "medium",
                            "row_count": 0,
                            "field_scope": {
                                "fields": [
                                    "merchant_id",
                                    "stat_date",
                                    "txn_count",
                                    "success_count",
                                    "refund_count",
                                    "gmv_amount",
                                    "refund_amount",
                                ]
                            },
                        }
                    ],
                ),
            )

        refund_rate = round(
            (summary.refund_count / summary.txn_count) if summary.txn_count else 0.0,
            4,
        )
        return InternalToolAdapterResult(
            status="success",
            output_summary=f"已汇总商户交易，merchant_id={merchant_id}，GMV={summary.gmv_amount} 分。",
            payload=_build_payload(
                tool_spec=tool_spec,
                request_context=request_context,
                result={
                    "merchant_id": merchant_id,
                    "txn_count": summary.txn_count,
                    "success_count": summary.success_count,
                    "refund_count": summary.refund_count,
                    "gmv_amount": summary.gmv_amount,
                    "refund_amount": summary.refund_amount,
                    "refund_rate": refund_rate,
                },
                data_access_records=[
                    {
                        "data_source": "mysql",
                        "data_object": "t_merchant_transaction_daily",
                        "access_type": "read",
                        "sensitive_level": "medium",
                        "row_count": 7,
                        "field_scope": {
                            "fields": [
                                "merchant_id",
                                "stat_date",
                                "txn_count",
                                "success_count",
                                "refund_count",
                                "gmv_amount",
                                "refund_amount",
                            ]
                        },
                    }
                ],
            ),
        )


class MerchantRiskTagQueryAdapter:
    def __init__(self, provider: InternalToolProvider) -> None:
        self._provider = provider

    def execute(
        self,
        *,
        tool_spec: ToolSpec,
        request_context: dict[str, Any],
    ) -> InternalToolAdapterResult:
        merchant_id = _resolve_merchant_id(request_context)
        summary = self._provider.query_merchant_risk_tags(merchant_id=merchant_id)
        if summary is None:
            return InternalToolAdapterResult(
                status="failed",
                output_summary=f"未找到风险标签，merchant_id={merchant_id}。",
                payload=_build_payload(
                    tool_spec=tool_spec,
                    request_context=request_context,
                    result={"merchant_id": merchant_id, "found": False},
                    data_access_records=[
                        {
                            "data_source": "mysql",
                            "data_object": "t_merchant_risk_tag",
                            "access_type": "read",
                            "sensitive_level": "medium",
                            "row_count": 0,
                            "field_scope": {
                                "fields": ["merchant_id", "risk_tag", "risk_score"]
                            },
                        }
                    ],
                ),
            )

        return InternalToolAdapterResult(
            status="success",
            output_summary=f"已查询风险标签，merchant_id={merchant_id}，最高风险分={summary.max_risk_score}。",
            payload=_build_payload(
                tool_spec=tool_spec,
                request_context=request_context,
                result={
                    "merchant_id": merchant_id,
                    "risk_tags": summary.risk_tags,
                    "risk_score": summary.max_risk_score,
                },
                data_access_records=[
                    {
                        "data_source": "mysql",
                        "data_object": "t_merchant_risk_tag",
                        "access_type": "read",
                        "sensitive_level": "medium",
                        "row_count": len(summary.risk_tags),
                        "field_scope": {
                            "fields": ["merchant_id", "risk_tag", "risk_score"]
                        },
                    }
                ],
            ),
        )


class QuotaApprovalSubmitAdapter:
    def __init__(self, provider: InternalToolProvider) -> None:
        self._provider = provider

    def execute(
        self,
        *,
        tool_spec: ToolSpec,
        request_context: dict[str, Any],
    ) -> InternalToolAdapterResult:
        merchant_id = _resolve_merchant_id(request_context)
        kwargs = dict(request_context.get("kwargs") or {})
        approval_id = f"APR-{uuid4().hex[:8].upper()}"
        requested_by = str(request_context.get("user_id") or "system")
        apply_amount = kwargs.get("target_quota") or kwargs.get("apply_amount")
        reason = str(kwargs.get("reason") or request_context.get("request_message") or "额度调整申请")
        submission = self._provider.submit_quota_approval(
            approval_id=approval_id,
            task_id=request_context.get("task_id"),
            contact_id=request_context.get("contact_id"),
            merchant_id=merchant_id,
            requested_by=requested_by,
            title=f"商户额度调整审批-{merchant_id}",
            reason=reason,
            payload={
                "merchant_id": merchant_id,
                "apply_amount": apply_amount,
                "request_message": request_context.get("request_message"),
                "request_kwargs": kwargs,
            },
        )
        return InternalToolAdapterResult(
            status="success",
            output_summary=f"已提交调额审批，审批单号={submission.approval_id}。",
            payload=_build_payload(
                tool_spec=tool_spec,
                request_context=request_context,
                result={
                    "merchant_id": submission.merchant_id,
                    "approval_id": submission.approval_id,
                    "status": submission.status,
                    "approval_type": submission.approval_type,
                    "workflow_code": submission.workflow_code,
                    "apply_amount": submission.apply_amount,
                },
                data_access_records=[
                    {
                        "data_source": "mysql",
                        "data_object": "t_approval_task",
                        "access_type": "write",
                        "sensitive_level": "high",
                        "row_count": 1,
                        "field_scope": {
                            "fields": [
                                "approval_id",
                                "merchant_id",
                                "approval_type",
                                "status",
                                "requested_by",
                            ]
                        },
                    }
                ],
            ),
        )


class DirectSalesMetricsQueryAdapter:
    def __init__(self, provider: InternalToolProvider) -> None:
        self._provider = provider

    def execute(
        self,
        *,
        tool_spec: ToolSpec,
        request_context: dict[str, Any],
    ) -> InternalToolAdapterResult:
        kwargs = dict(request_context.get("kwargs") or {})
        metrics_date = str(kwargs.get("metrics_date") or kwargs.get("date") or date.today().isoformat())
        region_code = str(kwargs.get("region_code") or "national")
        metric = self._provider.query_direct_sales_metrics(
            stat_date=metrics_date,
            region_code=region_code,
        )
        if metric is None:
            return InternalToolAdapterResult(
                status="failed",
                output_summary=f"未找到直营销售指标，date={metrics_date}，region={region_code}。",
                payload=_build_payload(
                    tool_spec=tool_spec,
                    request_context=request_context,
                    result={
                        "metrics_date": metrics_date,
                        "region_code": region_code,
                        "found": False,
                    },
                    data_access_records=[
                        {
                            "data_source": "mysql",
                            "data_object": "t_direct_sales_metric_daily",
                            "access_type": "read",
                            "sensitive_level": "medium",
                            "row_count": 0,
                            "field_scope": {
                                "fields": [
                                    "stat_date",
                                    "region_code",
                                    "sales_amount",
                                    "merchant_count",
                                    "conversion_rate",
                                ]
                            },
                        }
                    ],
                ),
            )

        sales_amount_yuan = round(metric.sales_amount / 100, 2)
        return InternalToolAdapterResult(
            status="success",
            output_summary=f"已查询直营销售指标，date={metrics_date}，region={region_code}，销售额={sales_amount_yuan} 元。",
            payload=_build_payload(
                tool_spec=tool_spec,
                request_context=request_context,
                result={
                    "metrics_date": metric.stat_date,
                    "region_code": metric.region_code,
                    "sales_amount": metric.sales_amount,
                    "sales_amount_yuan": sales_amount_yuan,
                    "merchant_count": metric.merchant_count,
                    "conversion_rate": metric.conversion_rate,
                },
                data_access_records=[
                    {
                        "data_source": "mysql",
                        "data_object": "t_direct_sales_metric_daily",
                        "access_type": "read",
                        "sensitive_level": "medium",
                        "row_count": 1,
                        "field_scope": {
                            "fields": [
                                "stat_date",
                                "region_code",
                                "sales_amount",
                                "merchant_count",
                                "conversion_rate",
                            ]
                        },
                    }
                ],
            ),
        )


class ComplianceReportExportAdapter:
    def __init__(self, provider: InternalToolProvider) -> None:
        self._provider = provider

    def execute(
        self,
        *,
        tool_spec: ToolSpec,
        request_context: dict[str, Any],
    ) -> InternalToolAdapterResult:
        kwargs = dict(request_context.get("kwargs") or {})
        report_id = f"RPT-{uuid4().hex[:8].upper()}"
        export_format = str(kwargs.get("format") or "xlsx")
        report_type = str(kwargs.get("report_type") or "compliance")
        requested_by = str(request_context.get("user_id") or "system")
        submission = self._provider.export_compliance_report(
            report_id=report_id,
            report_type=report_type,
            export_format=export_format,
            requested_by=requested_by,
            request_params={
                "request_message": request_context.get("request_message"),
                "request_kwargs": kwargs,
            },
        )
        return InternalToolAdapterResult(
            status="success",
            output_summary=f"已生成合规报表，report_id={submission.report_id}。",
            payload=_build_payload(
                tool_spec=tool_spec,
                request_context=request_context,
                result={
                    "report_id": submission.report_id,
                    "report_type": submission.report_type,
                    "format": submission.export_format,
                    "status": submission.status,
                    "output_uri": submission.output_uri,
                },
                data_access_records=[
                    {
                        "data_source": "mysql",
                        "data_object": "t_report_export_job",
                        "access_type": "write",
                        "sensitive_level": "medium",
                        "row_count": 1,
                        "field_scope": {
                            "fields": [
                                "report_id",
                                "report_type",
                                "format",
                                "status",
                                "requested_by",
                            ]
                        },
                    }
                ],
            ),
        )


class TicketSubmitAdapter:
    def __init__(self, provider: InternalToolProvider) -> None:
        self._provider = provider

    def execute(
        self,
        *,
        tool_spec: ToolSpec,
        request_context: dict[str, Any],
    ) -> InternalToolAdapterResult:
        kwargs = dict(request_context.get("kwargs") or {})
        ticket_id = f"TCK-{uuid4().hex[:8].upper()}"
        merchant_id = request_context.get("merchant_id") or kwargs.get("merchant_id")
        requested_by = str(request_context.get("user_id") or "system")
        category = str(kwargs.get("category") or "general")
        priority = str(kwargs.get("priority") or "medium")
        title = str(kwargs.get("title") or request_context.get("request_message") or "内部工单")
        description = str(
            kwargs.get("description")
            or request_context.get("request_message")
            or "由智能体自动提交的工单"
        )
        submission = self._provider.submit_service_ticket(
            ticket_id=ticket_id,
            merchant_id=str(merchant_id) if merchant_id else None,
            requested_by=requested_by,
            category=category,
            priority=priority,
            title=title,
            description=description,
            payload={
                "request_kwargs": kwargs,
                "request_message": request_context.get("request_message"),
            },
        )
        return InternalToolAdapterResult(
            status="success",
            output_summary=f"已提交工单，ticket_id={submission.ticket_id}。",
            payload=_build_payload(
                tool_spec=tool_spec,
                request_context=request_context,
                result={
                    "ticket_id": submission.ticket_id,
                    "status": submission.status,
                    "category": submission.category,
                    "priority": submission.priority,
                    "merchant_id": submission.merchant_id,
                },
                data_access_records=[
                    {
                        "data_source": "mysql",
                        "data_object": "t_service_ticket",
                        "access_type": "write",
                        "sensitive_level": "medium",
                        "row_count": 1,
                        "field_scope": {
                            "fields": [
                                "ticket_id",
                                "merchant_id",
                                "category",
                                "priority",
                                "status",
                                "requested_by",
                            ]
                        },
                    }
                ],
            ),
        )


class FallbackInternalToolAdapter:
    def execute(
        self,
        *,
        tool_spec: ToolSpec,
        request_context: dict[str, Any],
    ) -> InternalToolAdapterResult:
        return InternalToolAdapterResult(
            status="success",
            output_summary=f"已执行内部工具 {tool_spec.tool_id}。",
            payload=_build_payload(
                tool_spec=tool_spec,
                request_context=request_context,
                result={
                    "accepted": True,
                    "tool_id": tool_spec.tool_id,
                    "provider": tool_spec.provider,
                },
            ),
        )


class InternalToolRegistry:
    def __init__(
        self,
        adapters: dict[str, InternalToolAdapter] | None = None,
        fallback_adapter: InternalToolAdapter | None = None,
    ) -> None:
        self._adapters = dict(adapters or {})
        self._fallback_adapter = fallback_adapter or FallbackInternalToolAdapter()

    def register_adapter(self, tool_id: str, adapter: InternalToolAdapter) -> None:
        self._adapters[tool_id] = adapter

    def get_adapter(self, tool_id: str) -> InternalToolAdapter:
        return self._adapters.get(tool_id, self._fallback_adapter)


def build_default_internal_tool_registry(
    provider: InternalToolProvider,
) -> InternalToolRegistry:
    registry = InternalToolRegistry()
    registry.register_adapter("merchant_profile_query", MerchantProfileQueryAdapter(provider))
    registry.register_adapter(
        "merchant_transaction_summary",
        MerchantTransactionSummaryAdapter(provider),
    )
    registry.register_adapter("merchant_risk_tag_query", MerchantRiskTagQueryAdapter(provider))
    registry.register_adapter("quota_approval_submit", QuotaApprovalSubmitAdapter(provider))
    registry.register_adapter(
        "direct_sales_metrics_query",
        DirectSalesMetricsQueryAdapter(provider),
    )
    registry.register_adapter(
        "compliance_report_export",
        ComplianceReportExportAdapter(provider),
    )
    registry.register_adapter("ticket_submit", TicketSubmitAdapter(provider))
    return registry


def _resolve_merchant_id(request_context: dict[str, Any]) -> str:
    kwargs = dict(request_context.get("kwargs") or {})
    return str(request_context.get("merchant_id") or kwargs.get("merchant_id") or "M000001")


def _build_payload(
    *,
    tool_spec: ToolSpec,
    request_context: dict[str, Any],
    result: dict[str, Any],
    data_access_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "tool_id": tool_spec.tool_id,
        "provider": tool_spec.provider,
        "request_query": str(
            request_context.get("query") or request_context.get("request_message") or ""
        ).strip(),
        "request_kwargs": dict(request_context.get("kwargs") or {}),
        "request_context": request_context,
        "result": result,
        "data_access_records": data_access_records or [],
    }
