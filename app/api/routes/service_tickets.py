from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_service_ticket_service
from app.schemas import ServiceTicketResponse, ServiceTicketUpdateRequest
from app.services.service_ticket_service import ServiceTicketService

router = APIRouter(prefix="/service-tickets", tags=["service-tickets"])


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
) -> ServiceTicketResponse:
    item = service_ticket_service.update_ticket(ticket_id, request)
    if item is None:
        raise HTTPException(status_code=404, detail="service ticket not found")
    return item
