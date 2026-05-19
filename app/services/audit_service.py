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
        task_id: str | None = None,
        approval_id: str | None = None,
        capability_id: str | None = None,
        workflow: str | None = None,
    ) -> List[AuditEventResponse]:
        with self._session_factory() as session:
            return self._repository.list_events(
                session,
                action=action,
                actor_id=actor_id,
                task_id=task_id,
                approval_id=approval_id,
                capability_id=capability_id,
                workflow=workflow,
            )
