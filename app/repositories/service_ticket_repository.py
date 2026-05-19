from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import ServiceTicketModel


class ServiceTicketRepository:
    def list_tickets(
        self,
        session: Session,
        *,
        category: str | None = None,
        status: str | None = None,
        owner: str | None = None,
        requested_by: str | None = None,
        source: str | None = None,
        priority: str | None = None,
        task_id: str | None = None,
    ) -> list[ServiceTicketModel]:
        query = session.query(ServiceTicketModel).order_by(
            ServiceTicketModel.create_time.desc(),
            ServiceTicketModel.ticket_id.desc(),
        )
        if category:
            query = query.filter(ServiceTicketModel.category == category)
        if status:
            query = query.filter(ServiceTicketModel.status == status)
        if owner:
            query = query.filter(ServiceTicketModel.owner == owner)
        if requested_by:
            query = query.filter(ServiceTicketModel.requested_by == requested_by)
        if source:
            query = query.filter(ServiceTicketModel.source == source)
        if priority:
            query = query.filter(ServiceTicketModel.priority == priority)
        if task_id:
            query = query.filter(ServiceTicketModel.payload["task_id"].as_string() == task_id)
        return query.all()

    def get_ticket(self, session: Session, ticket_id: str) -> ServiceTicketModel | None:
        return session.get(ServiceTicketModel, ticket_id)

    def update_ticket(
        self,
        session: Session,
        *,
        ticket_id: str,
        status: str | None = None,
        owner: str | None = None,
        priority: str | None = None,
    ) -> ServiceTicketModel | None:
        item = session.get(ServiceTicketModel, ticket_id)
        if item is None:
            return None
        if status is not None:
            item.status = status
            if status in {"resolved", "closed"}:
                item.closed_at = datetime.utcnow()
        if owner is not None:
            item.owner = owner
        if priority is not None:
            item.priority = priority
        session.flush()
        return item
