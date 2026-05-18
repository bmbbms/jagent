from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    MerchantProfileModel,
    MerchantRiskTagModel,
    MerchantTransactionDailyModel,
)


@dataclass(frozen=True)
class MerchantProfileRecord:
    merchant_id: str
    merchant_name: str
    status: str
    risk_level: str
    industry_code: str | None
    contact_name: str | None
    contact_phone: str | None
    register_time: str | None


@dataclass(frozen=True)
class MerchantTransactionSummaryRecord:
    merchant_id: str
    txn_count: int
    success_count: int
    refund_count: int
    gmv_amount: int
    refund_amount: int


@dataclass(frozen=True)
class MerchantRiskTagSummaryRecord:
    merchant_id: str
    risk_tags: list[str]
    max_risk_score: int


class MerchantDataRepository:
    def get_profile(self, session: Session, merchant_id: str) -> MerchantProfileRecord | None:
        row = session.get(MerchantProfileModel, merchant_id)
        if row is None:
            return None
        return MerchantProfileRecord(
            merchant_id=row.merchant_id,
            merchant_name=row.merchant_name,
            status=row.status,
            risk_level=row.risk_level,
            industry_code=row.industry_code,
            contact_name=row.contact_name,
            contact_phone=row.contact_phone,
            register_time=row.register_time.isoformat() if row.register_time else None,
        )

    def get_transaction_summary(
        self,
        session: Session,
        merchant_id: str,
    ) -> MerchantTransactionSummaryRecord | None:
        row = (
            session.query(
                func.sum(MerchantTransactionDailyModel.txn_count),
                func.sum(MerchantTransactionDailyModel.success_count),
                func.sum(MerchantTransactionDailyModel.refund_count),
                func.sum(MerchantTransactionDailyModel.gmv_amount),
                func.sum(MerchantTransactionDailyModel.refund_amount),
            )
            .filter(MerchantTransactionDailyModel.merchant_id == merchant_id)
            .one()
        )
        if row is None or row[0] is None:
            return None
        return MerchantTransactionSummaryRecord(
            merchant_id=merchant_id,
            txn_count=int(row[0] or 0),
            success_count=int(row[1] or 0),
            refund_count=int(row[2] or 0),
            gmv_amount=int(row[3] or 0),
            refund_amount=int(row[4] or 0),
        )

    def get_risk_tag_summary(
        self,
        session: Session,
        merchant_id: str,
    ) -> MerchantRiskTagSummaryRecord | None:
        rows = (
            session.query(MerchantRiskTagModel)
            .filter(MerchantRiskTagModel.merchant_id == merchant_id)
            .filter(MerchantRiskTagModel.is_active.is_(True))
            .all()
        )
        if not rows:
            return None
        return MerchantRiskTagSummaryRecord(
            merchant_id=merchant_id,
            risk_tags=[row.risk_tag for row in rows],
            max_risk_score=max(row.risk_score for row in rows),
        )
