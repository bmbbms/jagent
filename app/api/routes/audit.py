from fastapi import APIRouter, Depends

from app.dependencies import get_audit_service
from app.schemas import AuditEventResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditEventResponse])
def list_audit_events(
    audit_service: AuditService = Depends(get_audit_service),
) -> list[AuditEventResponse]:
    return audit_service.list_events()
