from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import (
    ApprovalTaskModel,
    DirectSalesMetricDailyModel,
    ReportExportJobModel,
    ServiceTicketModel,
)


@dataclass(frozen=True)
class DirectSalesMetricDailyRecord:
    stat_date: str
    region_code: str
    sales_amount: int
    merchant_count: int
    conversion_rate: float


class InternalToolBusinessRepository:
    def get_direct_sales_metric(
        self,
        session: Session,
        *,
        stat_date: str,
        region_code: str,
    ) -> DirectSalesMetricDailyRecord | None:
        row = (
            session.query(DirectSalesMetricDailyModel)
            .filter(DirectSalesMetricDailyModel.stat_date == stat_date)
            .filter(DirectSalesMetricDailyModel.region_code == region_code)
            .one_or_none()
        )
        if row is None:
            return None
        return DirectSalesMetricDailyRecord(
            stat_date=row.stat_date,
            region_code=row.region_code,
            sales_amount=row.sales_amount,
            merchant_count=row.merchant_count,
            conversion_rate=row.conversion_rate,
        )

    def create_service_ticket(
        self,
        session: Session,
        *,
        ticket_id: str,
        merchant_id: str | None,
        biz_domain: str,
        category: str,
        priority: str,
        title: str,
        description: str | None,
        requested_by: str,
        payload: dict | None,
    ) -> ServiceTicketModel:
        model = ServiceTicketModel(
            ticket_id=ticket_id,
            merchant_id=merchant_id,
            biz_domain=biz_domain,
            category=category,
            priority=priority,
            title=title,
            description=description,
            status="submitted",
            requested_by=requested_by,
            owner=requested_by,
            source="internal_tool",
            payload=payload or {},
        )
        session.add(model)
        session.flush()
        return model

    def create_report_export_job(
        self,
        session: Session,
        *,
        report_id: str,
        report_type: str,
        biz_domain: str,
        export_format: str,
        requested_by: str,
        output_uri: str | None,
        request_params: dict | None,
    ) -> ReportExportJobModel:
        model = ReportExportJobModel(
            report_id=report_id,
            report_type=report_type,
            biz_domain=biz_domain,
            format=export_format,
            status="generated",
            requested_by=requested_by,
            output_uri=output_uri,
            request_params=request_params or {},
            completed_time=datetime.utcnow(),
        )
        session.add(model)
        session.flush()
        return model

    def create_quota_approval_task(
        self,
        session: Session,
        *,
        approval_id: str,
        task_id: str | None,
        contact_id: str | None,
        merchant_id: str | None,
        requested_by: str,
        title: str,
        reason: str | None,
        payload: dict | None,
    ) -> ApprovalTaskModel:
        model = ApprovalTaskModel(
            approval_id=approval_id,
            task_id=task_id,
            contact_id=contact_id,
            biz_domain="operations",
            approval_type="quota_adjustment",
            title=title,
            reason=reason,
            status="pending",
            risk_level="high",
            requested_by=requested_by,
            capability_id="operations.quota_review",
            workflow_code="quota_adjustment",
            payload={
                "merchant_id": merchant_id,
                **(payload or {}),
            },
        )
        session.add(model)
        session.flush()
        return model

    def seed_direct_sales_metric(
        self,
        session: Session,
        *,
        stat_date: str,
        region_code: str,
    ) -> None:
        exists = (
            session.query(DirectSalesMetricDailyModel.id)
            .filter(DirectSalesMetricDailyModel.stat_date == stat_date)
            .filter(DirectSalesMetricDailyModel.region_code == region_code)
            .first()
        )
        if exists is not None:
            return
        session.add(
            DirectSalesMetricDailyModel(
                stat_date=stat_date,
                region_code=region_code,
                sales_amount=89200000,
                merchant_count=64,
                conversion_rate=0.214,
            )
        )
        session.flush()
