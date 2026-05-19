from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import sessionmaker, Session

from app.db.session import session_scope
from app.repositories.audit_repository import AuditRepository
from app.schemas import AuditEventResponse, AuditOverviewResponse


class AuditService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        repository: AuditRepository,
    ) -> None:
        self._session_factory = session_factory
        self._repository = repository

    def record(self, action: str, actor_id: str, payload: Dict[str, Any]) -> None:
        with session_scope(self._session_factory) as session:
            self._repository.create(
                session,
                action=action,
                actor_id=actor_id,
                payload=payload,
            )

    def list_events(
        self,
        *,
        action: str | None = None,
        actor_id: str | None = None,
        source: str | None = None,
        event_type: str | None = None,
        outcome: int | None = None,
        task_id: str | None = None,
        approval_id: str | None = None,
        capability_id: str | None = None,
        workflow: str | None = None,
        ticket_id: str | None = None,
        suggestion_id: int | None = None,
        evaluation_id: str | None = None,
    ) -> List[AuditEventResponse]:
        with self._session_factory() as session:
            return self._repository.list_events(
                session,
                action=action,
                actor_id=actor_id,
                source=source,
                event_type=event_type,
                outcome=outcome,
                task_id=task_id,
                approval_id=approval_id,
                capability_id=capability_id,
                workflow=workflow,
                ticket_id=ticket_id,
                suggestion_id=suggestion_id,
                evaluation_id=evaluation_id,
            )

    def build_overview(self) -> AuditOverviewResponse:
        items = self.list_events()
        source_counts: dict[str, int] = {}
        event_type_counts: dict[str, int] = {}
        action_counts: dict[str, int] = {}
        success_count = 0
        failed_count = 0
        pending_count = 0

        for item in items:
            source_key = item.source or "unknown"
            event_type_key = item.event_type or "unknown"
            action_key = item.action or "unknown"
            source_counts[source_key] = source_counts.get(source_key, 0) + 1
            event_type_counts[event_type_key] = event_type_counts.get(event_type_key, 0) + 1
            action_counts[action_key] = action_counts.get(action_key, 0) + 1

            if item.outcome == 1:
                success_count += 1
            elif item.outcome == 2:
                failed_count += 1
            else:
                pending_count += 1

        return AuditOverviewResponse(
            total=len(items),
            success_count=success_count,
            failed_count=failed_count,
            pending_count=pending_count,
            source_counts=source_counts,
            event_type_counts=event_type_counts,
            action_counts=action_counts,
        )
