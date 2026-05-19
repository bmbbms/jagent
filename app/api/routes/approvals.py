from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_approval_service, get_audit_service, get_task_service
from app.schemas import (
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    ApprovalTask,
    CreateApprovalRequest,
)
from app.services.approval_service import ApprovalService
from app.services.audit_service import AuditService
from app.services.task_service import TaskService

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalTask])
def list_approvals(
    status: str | None = None,
    biz_domain: str | None = None,
    requested_by: str | None = None,
    risk_level: str | None = None,
    capability_id: str | None = None,
    workflow: str | None = None,
    approval_service: ApprovalService = Depends(get_approval_service),
) -> list[ApprovalTask]:
    return approval_service.list_tasks(
        status=status,
        biz_domain=biz_domain,
        requested_by=requested_by,
        risk_level=risk_level,
        capability_id=capability_id,
        workflow=workflow,
    )


@router.get("/{approval_id}", response_model=ApprovalTask)
def get_approval(
    approval_id: str,
    approval_service: ApprovalService = Depends(get_approval_service),
) -> ApprovalTask:
    try:
        return approval_service.get_task(approval_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="approval task not found") from exc


@router.post("", response_model=ApprovalTask)
def create_approval(
    request: CreateApprovalRequest,
    approval_service: ApprovalService = Depends(get_approval_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> ApprovalTask:
    task = approval_service.create(request)
    audit_service.record(
        action="approval.create",
        actor_id=request.requested_by,
        payload={
            "approval_id": task.approval_id,
            "biz_domain": task.biz_domain.value,
            "capability_id": task.capability_id,
            "workflow": task.workflow,
        },
    )
    return task


@router.post("/{approval_id}/decision", response_model=ApprovalDecisionResponse)
def decide_approval(
    approval_id: str,
    request: ApprovalDecisionRequest,
    approval_service: ApprovalService = Depends(get_approval_service),
    audit_service: AuditService = Depends(get_audit_service),
    task_service: TaskService = Depends(get_task_service),
) -> ApprovalDecisionResponse:
    try:
        response = approval_service.decide(approval_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="approval task not found") from exc

    audit_service.record(
        action="approval.decision",
        actor_id=request.reviewer_id,
        payload={
            "approval_id": approval_id,
            "decision": request.decision.value,
            "comment": request.comment,
        },
    )
    task_service.resolve_approval_task(
        approval_id=approval_id,
        approval_status=response.status,
        reviewer_id=request.reviewer_id,
        comment=request.comment,
    )
    return response
