from __future__ import annotations

from sqlalchemy.orm import sessionmaker, Session

from app.db.session import session_scope
from app.repositories.approval_repository import ApprovalRepository
from app.schemas import (
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    ApprovalStatus,
    ApprovalTask,
    CreateApprovalRequest,
)


class ApprovalService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        repository: ApprovalRepository,
    ) -> None:
        self._session_factory = session_factory
        self._repository = repository

    def list_tasks(self) -> list[ApprovalTask]:
        with self._session_factory() as session:
            return self._repository.list_tasks(session)

    def get_task(self, approval_id: str) -> ApprovalTask:
        with self._session_factory() as session:
            item = self._repository.get_task(session, approval_id)
            if item is None:
                raise KeyError(approval_id)
            return item

    def create(self, request: CreateApprovalRequest) -> ApprovalTask:
        with session_scope(self._session_factory) as session:
            next_number = len(self._repository.list_tasks(session)) + 1
            approval_id = f"APR-{next_number:03d}"
            return self._repository.create_task(session, approval_id, request)

    def decide(
        self, approval_id: str, request: ApprovalDecisionRequest
    ) -> ApprovalDecisionResponse:
        target_status = (
            ApprovalStatus.approved
            if request.decision.value == "approve"
            else ApprovalStatus.rejected
        )
        with session_scope(self._session_factory) as session:
            task = self._repository.update_status(session, approval_id, target_status)
            if task is None:
                raise KeyError(approval_id)
        return ApprovalDecisionResponse(
            approval_id=approval_id,
            status=target_status,
            reviewer_id=request.reviewer_id,
            decision=request.decision,
            comment=request.comment,
        )

    def seed_if_needed(self) -> None:
        with session_scope(self._session_factory) as session:
            self._repository.seed_if_empty(session)
