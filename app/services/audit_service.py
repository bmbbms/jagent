from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import sessionmaker, Session

from app.db.session import session_scope
from app.repositories.audit_repository import AuditRepository
from app.schemas import AuditEventResponse


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
