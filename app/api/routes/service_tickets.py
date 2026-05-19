from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_audit_service, get_service_ticket_service
from app.schemas import (
    ServiceTicketOverviewResponse,
    ServiceTicketResponse,
    ServiceTicketUpdateRequest,
)
from app.services.audit_service import AuditService
from app.services.service_ticket_service import ServiceTicketService

router = APIRouter(prefix="/service-tickets", tags=["service-tickets"])


@router.get("/overview", response_model=ServiceTicketOverviewResponse)
def get_service_ticket_overview(
    service_ticket_service: ServiceTicketService = Depends(get_service_ticket_service),
) -> ServiceTicketOverviewResponse:
    return service_ticket_service.build_overview()


@router.get("", response_model=list[ServiceTicketResponse])
def list_service_tickets(
    category: str | None = Query(default=None),
    status: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    requested_by: str | None = Query(default=None),
    source: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    task_id: str | None = Query(default=None),
    service_ticket_service: ServiceTicketService = Depends(get_service_ticket_service),
) -> list[ServiceTicketResponse]:
    return service_ticket_service.list_tickets(
        category=category,
        status=status,
        owner=owner,
        requested_by=requested_by,
        source=source,
        priority=priority,
        task_id=task_id,
    )


@router.get("/{ticket_id}", response_model=ServiceTicketResponse)
def get_service_ticket(
    ticket_id: str,
    service_ticket_service: ServiceTicketService = Depends(get_service_ticket_service),
) -> ServiceTicketResponse:
    item = service_ticket_service.get_ticket(ticket_id)
    if item is None:
        raise HTTPException(status_code=404, detail="service ticket not found")
    return item


@router.put("/{ticket_id}", response_model=ServiceTicketResponse)
def update_service_ticket(
    ticket_id: str,
    request: ServiceTicketUpdateRequest,
    service_ticket_service: ServiceTicketService = Depends(get_service_ticket_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> ServiceTicketResponse:
    ticket_ctx = service_ticket_service.get_ticket_audit_context(ticket_id)
    item = service_ticket_service.update_ticket(ticket_id, request)
    if item is None:
        raise HTTPException(status_code=404, detail="service ticket not found")
    audit_service.record(
        "service_ticket.update",
        request.owner or item.requested_by,
        {
            "source": item.source,
            "event_type": "service_ticket",
            "outcome": 1,
            "task_id": ticket_ctx.get("task_id") if ticket_ctx else item.linked_task_id,
            "evaluation_id": (
                ticket_ctx.get("evaluation_id") if ticket_ctx else item.linked_evaluation_id
            ),
            "suggestion_id": (
                ticket_ctx.get("suggestion_id") if ticket_ctx else item.linked_suggestion_id
            ),
            "ticket_id": item.ticket_id,
            "ticket_status": item.status,
            "capability_id": ticket_ctx.get("agent_id") if ticket_ctx else item.linked_agent_id,
            "agent_id": ticket_ctx.get("agent_id") if ticket_ctx else item.linked_agent_id,
            "request_summary": f"update service ticket {item.ticket_id}",
            "response_summary": (
                f"status={item.status}, owner={item.owner or '-'}, priority={item.priority}"
            ),
            "payload": {
                "ticket_id": item.ticket_id,
                "suggestion_id": item.linked_suggestion_id,
                "evaluation_id": item.linked_evaluation_id,
                "task_id": item.linked_task_id,
                "agent_id": item.linked_agent_id,
                "status": item.status,
                "priority": item.priority,
                "owner": item.owner,
            },
        },
    )
    return item
