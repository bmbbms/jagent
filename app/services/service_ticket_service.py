from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session, sessionmaker

from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.service_ticket_repository import ServiceTicketRepository
from app.schemas import (
    ServiceTicketOverviewResponse,
    ServiceTicketResponse,
    ServiceTicketUpdateRequest,
)


class ServiceTicketService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        repository: ServiceTicketRepository,
        evaluation_repository: EvaluationRepository | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._repository = repository
        self._evaluation_repository = evaluation_repository or EvaluationRepository()

    def list_tickets(
        self,
        *,
        category: str | None = None,
        status: str | None = None,
        owner: str | None = None,
        requested_by: str | None = None,
        source: str | None = None,
        priority: str | None = None,
        task_id: str | None = None,
    ) -> list[ServiceTicketResponse]:
        with self._session_factory() as session:
            items = self._repository.list_tickets(
                session,
                category=category,
                status=status,
                owner=owner,
                requested_by=requested_by,
                source=source,
                priority=priority,
                task_id=task_id,
            )
            return [self._to_response(item) for item in items]

    def get_ticket(self, ticket_id: str) -> ServiceTicketResponse | None:
        with self._session_factory() as session:
            item = self._repository.get_ticket(session, ticket_id)
            if item is None:
                return None
            return self._to_response(item)

    def build_overview(self) -> ServiceTicketOverviewResponse:
        items = self.list_tickets()
        total = len(items)
        backlog_count = sum(1 for item in items if item.status not in {"resolved", "closed"})
        stale_threshold = datetime.utcnow() - timedelta(days=3)
        stale_open_count = sum(
            1
            for item in items
            if item.status not in {"resolved", "closed"}
            and item.update_time
            and datetime.fromisoformat(item.update_time) <= stale_threshold
        )
        completion_rate = round(
            (
                sum(1 for item in items if item.status in {"resolved", "closed"})
                / total
            )
            * 100,
            2,
        ) if total else 0.0
        return ServiceTicketOverviewResponse(
            total=total,
            submitted_count=sum(1 for item in items if item.status == "submitted"),
            in_progress_count=sum(1 for item in items if item.status == "in_progress"),
            resolved_count=sum(1 for item in items if item.status == "resolved"),
            closed_count=sum(1 for item in items if item.status == "closed"),
            backlog_count=backlog_count,
            high_priority_count=sum(1 for item in items if item.priority == "high"),
            unassigned_count=sum(1 for item in items if not item.owner),
            stale_open_count=stale_open_count,
            evaluation_source_count=sum(1 for item in items if item.source == "evaluation"),
            internal_tool_source_count=sum(1 for item in items if item.source == "internal_tool"),
            completion_rate=completion_rate,
        )

    def get_ticket_audit_context(self, ticket_id: str) -> dict[str, str | int | None] | None:
        with self._session_factory() as session:
            item = self._repository.get_ticket(session, ticket_id)
            if item is None:
                return None
            payload = item.payload or {}
            return {
                "ticket_id": item.ticket_id,
                "task_id": payload.get("task_id"),
                "evaluation_id": payload.get("evaluation_id"),
                "suggestion_id": payload.get("suggestion_id"),
                "agent_id": payload.get("agent_id"),
                "status": item.status,
                "priority": item.priority,
                "owner": item.owner,
                "source": item.source,
            }

    def update_ticket(
        self,
        ticket_id: str,
        request: ServiceTicketUpdateRequest,
    ) -> ServiceTicketResponse | None:
        with self._session_factory() as session:
            item = self._repository.update_ticket(
                session,
                ticket_id=ticket_id,
                status=request.status,
                owner=request.owner,
                priority=request.priority,
            )
            if item is None:
                return None
            self._evaluation_repository.sync_suggestion_with_ticket(
                session,
                ticket_id=item.ticket_id,
                ticket_status=item.status,
                owner=item.owner,
                priority=item.priority,
                closed_at=item.closed_at,
            )
            session.commit()
            session.refresh(item)
            return self._to_response(item)

    @staticmethod
    def _to_response(item) -> ServiceTicketResponse:
        payload = item.payload or {}
        return ServiceTicketResponse(
            ticket_id=item.ticket_id,
            merchant_id=item.merchant_id,
            biz_domain=item.biz_domain,
            category=item.category,
            priority=item.priority,
            title=item.title,
            description=item.description or "",
            status=item.status,
            requested_by=item.requested_by,
            owner=item.owner,
            source=item.source,
            payload=payload,
            create_time=item.create_time.isoformat() if item.create_time else "",
            update_time=item.update_time.isoformat() if item.update_time else "",
            closed_at=item.closed_at.isoformat() if item.closed_at else None,
            linked_suggestion_id=payload.get("suggestion_id"),
            linked_evaluation_id=payload.get("evaluation_id"),
            linked_agent_id=payload.get("agent_id"),
            linked_task_id=payload.get("task_id"),
        )
