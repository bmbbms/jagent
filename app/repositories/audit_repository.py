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
                workflow_id=payload.get("workflow_id") or payload.get("workflow"),
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

    def list_events(
        self,
        session: Session,
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
        query = session.query(AuditLogModel)
        if action:
            query = query.filter(AuditLogModel.op_type == action)
        if actor_id:
            query = query.filter(AuditLogModel.user_id == actor_id)
        if source:
            query = query.filter(AuditLogModel.source == source)
        if event_type:
            query = query.filter(AuditLogModel.event_type == event_type)
        if outcome is not None:
            query = query.filter(AuditLogModel.outcome == outcome)
        if task_id:
            query = query.filter(AuditLogModel.task_id == task_id)
        if approval_id:
            query = query.filter(AuditLogModel.approval_id == approval_id)
        if capability_id:
            query = query.filter(AuditLogModel.capability_id == capability_id)
        if workflow:
            query = query.filter(AuditLogModel.workflow_id == workflow)
        if ticket_id:
            query = query.filter(AuditLogModel.payload["ticket_id"].as_string() == ticket_id)
        if suggestion_id is not None:
            query = query.filter(
                AuditLogModel.payload["suggestion_id"].as_integer() == suggestion_id
            )
        if evaluation_id:
            query = query.filter(
                AuditLogModel.payload["evaluation_id"].as_string() == evaluation_id
            )
        items = query.order_by(AuditLogModel.create_time.desc()).all()
        return [
            AuditEventResponse(
                action=item.op_type,
                actor_id=item.user_id,
                payload=item.payload or {},
                created_at=item.create_time.isoformat(),
                source=item.source,
                event_type=item.event_type,
                outcome=item.outcome,
                task_id=item.task_id,
                approval_id=item.approval_id,
                capability_id=item.capability_id,
                workflow=item.workflow_id,
                ticket_id=(item.payload or {}).get("ticket_id"),
                suggestion_id=(item.payload or {}).get("suggestion_id"),
                evaluation_id=(item.payload or {}).get("evaluation_id"),
            )
            for item in items
        ]
