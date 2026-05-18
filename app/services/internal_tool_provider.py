from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Protocol

from sqlalchemy.orm import Session, sessionmaker

from app.db.models import (
    MerchantProfileModel,
    MerchantRiskTagModel,
    MerchantTransactionDailyModel,
)
from app.db.session import session_scope
from app.repositories.internal_tool_business_repository import (
    DirectSalesMetricDailyRecord,
    InternalToolBusinessRepository,
)
from app.repositories.merchant_data_repository import (
    MerchantDataRepository,
    MerchantProfileRecord,
    MerchantRiskTagSummaryRecord,
    MerchantTransactionSummaryRecord,
)


@dataclass(frozen=True)
class QuotaApprovalSubmission:
    approval_id: str
    merchant_id: str
    status: str
    approval_type: str
    workflow_code: str | None
    apply_amount: Any


@dataclass(frozen=True)
class ReportExportSubmission:
    report_id: str
    report_type: str
    export_format: str
    status: str
    output_uri: str | None


@dataclass(frozen=True)
class ServiceTicketSubmission:
    ticket_id: str
    merchant_id: str | None
    status: str
    category: str
    priority: str


class InternalToolProvider(Protocol):
    def query_merchant_profile(self, *, merchant_id: str) -> MerchantProfileRecord | None:
        raise NotImplementedError

    def query_merchant_transaction_summary(
        self,
        *,
        merchant_id: str,
    ) -> MerchantTransactionSummaryRecord | None:
        raise NotImplementedError

    def query_merchant_risk_tags(
        self,
        *,
        merchant_id: str,
    ) -> MerchantRiskTagSummaryRecord | None:
        raise NotImplementedError

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
        raise NotImplementedError

    def query_direct_sales_metrics(
        self,
        *,
        stat_date: str,
        region_code: str,
    ) -> DirectSalesMetricDailyRecord | None:
        raise NotImplementedError

    def export_compliance_report(
        self,
        *,
        report_id: str,
        report_type: str,
        export_format: str,
        requested_by: str,
        request_params: dict[str, Any],
    ) -> ReportExportSubmission:
        raise NotImplementedError

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
        raise NotImplementedError


class LocalDbInternalToolProvider:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        merchant_repository: MerchantDataRepository | None = None,
        business_repository: InternalToolBusinessRepository | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._merchant_repository = merchant_repository or MerchantDataRepository()
        self._business_repository = business_repository or InternalToolBusinessRepository()

    def query_merchant_profile(self, *, merchant_id: str) -> MerchantProfileRecord | None:
        with session_scope(self._session_factory) as session:
            _seed_demo_merchant_data(session, merchant_id)
            return self._merchant_repository.get_profile(session, merchant_id)

    def query_merchant_transaction_summary(
        self,
        *,
        merchant_id: str,
    ) -> MerchantTransactionSummaryRecord | None:
        with session_scope(self._session_factory) as session:
            _seed_demo_merchant_data(session, merchant_id)
            return self._merchant_repository.get_transaction_summary(session, merchant_id)

    def query_merchant_risk_tags(
        self,
        *,
        merchant_id: str,
    ) -> MerchantRiskTagSummaryRecord | None:
        with session_scope(self._session_factory) as session:
            _seed_demo_merchant_data(session, merchant_id)
            return self._merchant_repository.get_risk_tag_summary(session, merchant_id)

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
        with session_scope(self._session_factory) as session:
            model = self._business_repository.create_quota_approval_task(
                session,
                approval_id=approval_id,
                task_id=task_id,
                contact_id=contact_id,
                merchant_id=merchant_id,
                requested_by=requested_by,
                title=title,
                reason=reason,
                payload=payload,
            )
            return QuotaApprovalSubmission(
                approval_id=model.approval_id,
                merchant_id=merchant_id,
                status=model.status,
                approval_type=model.approval_type,
                workflow_code=model.workflow_code,
                apply_amount=(model.payload or {}).get("apply_amount"),
            )

    def query_direct_sales_metrics(
        self,
        *,
        stat_date: str,
        region_code: str,
    ) -> DirectSalesMetricDailyRecord | None:
        with session_scope(self._session_factory) as session:
            self._business_repository.seed_direct_sales_metric(
                session,
                stat_date=stat_date,
                region_code=region_code,
            )
            return self._business_repository.get_direct_sales_metric(
                session,
                stat_date=stat_date,
                region_code=region_code,
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
        output_uri = f"/exports/{report_id}.{export_format}"
        with session_scope(self._session_factory) as session:
            model = self._business_repository.create_report_export_job(
                session,
                report_id=report_id,
                report_type=report_type,
                biz_domain="data_support",
                export_format=export_format,
                requested_by=requested_by,
                output_uri=output_uri,
                request_params=request_params,
            )
            return ReportExportSubmission(
                report_id=model.report_id,
                report_type=model.report_type,
                export_format=model.format,
                status=model.status,
                output_uri=model.output_uri,
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
        with session_scope(self._session_factory) as session:
            model = self._business_repository.create_service_ticket(
                session,
                ticket_id=ticket_id,
                merchant_id=merchant_id,
                biz_domain="operations",
                category=category,
                priority=priority,
                title=title,
                description=description,
                requested_by=requested_by,
                payload=payload,
            )
            return ServiceTicketSubmission(
                ticket_id=model.ticket_id,
                merchant_id=model.merchant_id,
                status=model.status,
                category=model.category,
                priority=model.priority,
            )


def _seed_demo_merchant_data(session: Session, merchant_id: str) -> None:
    profile = session.get(MerchantProfileModel, merchant_id)
    if profile is None:
        session.add(
            MerchantProfileModel(
                merchant_id=merchant_id,
                merchant_name=f"示例商户-{merchant_id[-4:]}",
                biz_domain="merchant",
                status="active",
                risk_level="low",
                industry_code="retail",
                contact_name="张三",
                contact_phone="13800000000",
                register_time=datetime.utcnow() - timedelta(days=180),
                metadata_json={"seeded": True},
            )
        )

    txn_exists = (
        session.query(MerchantTransactionDailyModel.id)
        .filter(MerchantTransactionDailyModel.merchant_id == merchant_id)
        .first()
    )
    if txn_exists is None:
        base_day = date.today()
        for offset, txn_count, success_count, refund_count, gmv_amount, refund_amount in [
            (0, 32, 30, 1, 860000, 12000),
            (1, 28, 27, 1, 720000, 8000),
            (2, 24, 23, 0, 610000, 0),
            (3, 18, 17, 1, 420000, 6000),
            (4, 26, 25, 1, 700000, 9000),
            (5, 20, 19, 0, 530000, 0),
            (6, 22, 21, 0, 610000, 0),
        ]:
            session.add(
                MerchantTransactionDailyModel(
                    merchant_id=merchant_id,
                    stat_date=(base_day - timedelta(days=offset)).isoformat(),
                    txn_count=txn_count,
                    success_count=success_count,
                    refund_count=refund_count,
                    gmv_amount=gmv_amount,
                    refund_amount=refund_amount,
                )
            )

    risk_exists = (
        session.query(MerchantRiskTagModel.id)
        .filter(MerchantRiskTagModel.merchant_id == merchant_id)
        .filter(MerchantRiskTagModel.is_active.is_(True))
        .first()
    )
    if risk_exists is None:
        session.add(
            MerchantRiskTagModel(
                merchant_id=merchant_id,
                risk_tag="normal",
                risk_score=18,
                source_system="seed",
                is_active=True,
                metadata_json={"seeded": True},
            )
        )
        session.add(
            MerchantRiskTagModel(
                merchant_id=merchant_id,
                risk_tag="stable_settlement",
                risk_score=12,
                source_system="seed",
                is_active=True,
                metadata_json={"seeded": True},
            )
        )
    session.flush()
