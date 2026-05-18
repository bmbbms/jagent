from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import AuditLogModel
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
        now = datetime.utcnow()
        session.add(
            AuditLogModel(
                log_id=f"audit_{uuid4().hex[:24]}",
                source=payload.get("source", "platform"),
                event_type=payload.get("event_type", "audit"),
                op_type=action,
                user_id=actor_id,
                agent_id=payload.get("agent_id"),
                task_id=payload.get("task_id"),
                session_id=payload.get("session_id"),
                trace_id=payload.get("trace_id", uuid4().hex),
                capability_id=payload.get("capability_id"),
                tool_id=payload.get("tool_id"),
                workflow_id=payload.get("workflow_id"),
                approval_id=payload.get("approval_id"),
                risk_level=payload.get("risk_level", "low"),
                request_summary=payload.get("request_summary"),
                response_summary=payload.get("response_summary"),
                resp_code=payload.get("resp_code"),
                error_code=payload.get("error_code"),
                error_msg=payload.get("error_msg"),
                outcome=payload.get("outcome", 0),
                payload=payload,
                tags=payload.get("tags"),
                request_time=payload.get("request_time", now),
                response_time=payload.get("response_time"),
                duration_ms=payload.get("duration_ms"),
            )
        )
        session.flush()

    def list_events(self, session: Session) -> List[AuditEventResponse]:
        items = session.query(AuditLogModel).order_by(AuditLogModel.create_time.desc()).all()
        return [
            AuditEventResponse(
                action=item.op_type,
                actor_id=item.user_id,
                payload=item.payload or {},
                created_at=item.create_time.isoformat(),
            )
            for item in items
        ]
