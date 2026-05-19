from fastapi import APIRouter, Depends

from app.dependencies import get_audit_service
from app.schemas import (
    AuditContextDrilldownResponse,
    AuditEventResponse,
    AuditExecutionPlanRunsResponse,
    AuditLinkedContextResponse,
    AuditOverviewResponse,
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/overview", response_model=AuditOverviewResponse)
def get_audit_overview(
    audit_service: AuditService = Depends(get_audit_service),
) -> AuditOverviewResponse:
    return audit_service.build_overview()


@router.get("", response_model=list[AuditEventResponse])
def list_audit_events(
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
    audit_service: AuditService = Depends(get_audit_service),
) -> list[AuditEventResponse]:
    return audit_service.list_events(
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


@router.get("/linked-context", response_model=AuditLinkedContextResponse)
def get_linked_context(
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
    audit_service: AuditService = Depends(get_audit_service),
) -> AuditLinkedContextResponse:
    return audit_service.build_linked_context(
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


@router.get("/context/{context_type}/{context_id}", response_model=AuditContextDrilldownResponse)
def get_context_drilldown(
    context_type: str,
    context_id: str,
    audit_service: AuditService = Depends(get_audit_service),
) -> AuditContextDrilldownResponse:
    return audit_service.build_context_drilldown(
        context_type=context_type,
        context_id=context_id,
    )


@router.get("/execution-plan-runs", response_model=AuditExecutionPlanRunsResponse)
def list_execution_plan_runs(
    actor_id: str | None = None,
    agent_id: str | None = None,
    limit: int = 10,
    audit_service: AuditService = Depends(get_audit_service),
) -> AuditExecutionPlanRunsResponse:
    return audit_service.list_execution_plan_runs(
        actor_id=actor_id,
        agent_id=agent_id,
        limit=limit,
    )
