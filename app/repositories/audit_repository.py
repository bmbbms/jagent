from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.db.models import AuditEventModel
from app.schemas import AuditEventResponse


class AuditRepository:
    def create(
        self,
        session: Session,
        *,
        action: str,
        actor_id: str,
        payload: Dict[str, Any],
    ) -> None:
        session.add(AuditEventModel(action=action, actor_id=actor_id, payload=payload))
        session.flush()

    def list_events(self, session: Session) -> List[AuditEventResponse]:
        items = session.query(AuditEventModel).order_by(AuditEventModel.created_at.desc()).all()
        return [
            AuditEventResponse(
                action=item.action,
                actor_id=item.actor_id,
                payload=item.payload or {},
                created_at=item.created_at.isoformat(),
            )
            for item in items
        ]
