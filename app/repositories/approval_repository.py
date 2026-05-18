from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from app.db.models import ApprovalTaskModel
from app.schemas import ApprovalStatus, ApprovalTask, BizDomain, CreateApprovalRequest


class ApprovalRepository:
    def list_tasks(self, session: Session) -> List[ApprovalTask]:
        items = session.query(ApprovalTaskModel).order_by(ApprovalTaskModel.create_time.desc()).all()
        return [self._to_schema(item) for item in items]

    def get_task(self, session: Session, approval_id: str) -> ApprovalTask | None:
        item = session.get(ApprovalTaskModel, approval_id)
        return self._to_schema(item) if item else None

    def create_task(
        self,
        session: Session,
        approval_id: str,
        request: CreateApprovalRequest,
    ) -> ApprovalTask:
        model = ApprovalTaskModel(
            approval_id=approval_id,
            task_id=request.payload.get("task_id"),
            title=request.title,
            biz_domain=request.biz_domain.value,
            approval_type=request.payload.get("approval_type", "manual_review"),
            reason=request.payload.get("reason"),
            status=ApprovalStatus.pending.value,
            risk_level=request.risk_level,
            requested_by=request.requested_by,
            capability_id=request.capability_id,
            workflow_code=request.workflow,
            payload=request.payload,
        )
        session.add(model)
        session.flush()
        return self._to_schema(model)

    def update_status(
        self,
        session: Session,
        approval_id: str,
        status: ApprovalStatus,
    ) -> ApprovalTask | None:
        model = session.get(ApprovalTaskModel, approval_id)
        if model is None:
            return None
        model.status = status.value
        session.add(model)
        session.flush()
        return self._to_schema(model)

    def seed_if_empty(self, session: Session) -> None:
        exists = session.query(ApprovalTaskModel).first()
        if exists is not None:
            return
        session.add(
            ApprovalTaskModel(
                approval_id="APR-001",
                title="调额审核辅助结果确认",
                biz_domain=BizDomain.operations.value,
                status=ApprovalStatus.pending.value,
                risk_level="high",
                requested_by="system",
                capability_id="operations.quota_review",
                workflow_code="quota_review",
                payload={"seed": True},
            )
        )

    def _to_schema(self, model: ApprovalTaskModel) -> ApprovalTask:
        return ApprovalTask(
            approval_id=model.approval_id,
            title=model.title,
            biz_domain=BizDomain(model.biz_domain),
            status=ApprovalStatus(model.status),
            risk_level=model.risk_level,
            requested_by=model.requested_by,
            capability_id=model.capability_id,
            workflow=model.workflow_code,
            payload=model.payload or {},
        )
