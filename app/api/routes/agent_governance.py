from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import (
    get_agent_profile_sync_service,
    get_audit_service,
    get_evaluation_service,
    get_task_service,
)
from app.schemas import (
    AgentGovernanceIssueActionRequest,
    AgentGovernanceIssueActionResponse,
    AgentGovernanceIssueResponse,
    AgentGovernanceOverviewResponse,
)
from app.services.agent_profile_service import AgentProfileSyncService
from app.services.audit_service import AuditService
from app.services.evaluation_service import EvaluationService
from app.services.task_service import TaskService

router = APIRouter(prefix="/agent-governance", tags=["agent-governance"])

_ISSUE_ACTION_STATE: dict[str, list[AgentGovernanceIssueActionResponse]] = {}


@router.get("/overview", response_model=AgentGovernanceOverviewResponse)
def get_agent_governance_overview(
    biz_domain: str | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
    agent_profile_service: AgentProfileSyncService = Depends(get_agent_profile_sync_service),
    task_service: TaskService = Depends(get_task_service),
) -> AgentGovernanceOverviewResponse:
    return evaluation_service.build_agent_governance_overview(
        agent_profile_service=agent_profile_service,
        task_service=task_service,
        biz_domain=biz_domain,
        enabled=enabled,
        limit=limit,
    )


@router.get("/issues", response_model=list[AgentGovernanceIssueResponse])
def list_agent_governance_issues(
    agent_id: str | None = Query(default=None),
    biz_domain: str | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    issue_type: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    attention_level: str | None = Query(default=None),
    governance_status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
    agent_profile_service: AgentProfileSyncService = Depends(get_agent_profile_sync_service),
    task_service: TaskService = Depends(get_task_service),
) -> list[AgentGovernanceIssueResponse]:
    items = evaluation_service.build_agent_governance_issues(
        agent_profile_service=agent_profile_service,
        task_service=task_service,
        biz_domain=biz_domain,
        enabled=enabled,
        limit=limit,
    )
    if agent_id:
        items = [item for item in items if item.agent_id == agent_id]
    if issue_type:
        items = [item for item in items if item.issue_type == issue_type]
    if severity:
        items = [item for item in items if item.severity == severity]
    if attention_level:
        items = [item for item in items if item.attention_level == attention_level]
    if governance_status:
        items = [item for item in items if item.governance_status == governance_status]
    return items


@router.post(
    "/issues/{issue_id}/actions",
    response_model=AgentGovernanceIssueActionResponse,
)
def act_on_agent_governance_issue(
    issue_id: str,
    request: AgentGovernanceIssueActionRequest,
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
    agent_profile_service: AgentProfileSyncService = Depends(get_agent_profile_sync_service),
    task_service: TaskService = Depends(get_task_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> AgentGovernanceIssueActionResponse:
    issue = _find_issue(
        issue_id=issue_id,
        evaluation_service=evaluation_service,
        agent_profile_service=agent_profile_service,
        task_service=task_service,
    )
    if issue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="governance issue not found")

    action = request.action.strip().lower()
    if action not in {"ack", "ignore", "close"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid action")

    response = AgentGovernanceIssueActionResponse(
        issue_id=issue_id,
        action=action,
        operator_id=request.operator_id,
        status="closed" if action == "close" else "acknowledged" if action == "ack" else "ignored",
        message={
            "ack": "治理问题已确认",
            "ignore": "治理问题已忽略",
            "close": "治理问题已关闭",
        }[action],
        performed_at=datetime.utcnow().isoformat(),
    )
    _ISSUE_ACTION_STATE.setdefault(issue_id, []).append(response)

    audit_service.record(
        "agent_governance.issue.action",
        request.operator_id,
        {
            "source": "agent_governance",
            "event_type": "issue_action",
            "outcome": 1,
            "agent_id": issue.agent_id,
            "capability_id": issue.agent_id,
            "request_summary": f"{action} governance issue {issue_id}",
            "response_summary": response.message,
            "payload": {
                "issue_id": issue.issue_id,
                "issue_type": issue.issue_type,
                "severity": issue.severity,
                "governance_status": issue.governance_status,
                "operator_id": request.operator_id,
                "comment": request.comment,
                "target_ui": issue.target_ui,
                "target_api": issue.target_api,
            },
        },
    )
    return response


@router.get(
    "/issues/{issue_id}/actions",
    response_model=list[AgentGovernanceIssueActionResponse],
)
def list_agent_governance_issue_actions(issue_id: str) -> list[AgentGovernanceIssueActionResponse]:
    return _ISSUE_ACTION_STATE.get(issue_id, [])


def _find_issue(
    *,
    issue_id: str,
    evaluation_service: EvaluationService,
    agent_profile_service: AgentProfileSyncService,
    task_service: TaskService,
) -> AgentGovernanceIssueResponse | None:
    items = evaluation_service.build_agent_governance_issues(
        agent_profile_service=agent_profile_service,
        task_service=task_service,
        limit=300,
    )
    for item in items:
        if item.issue_id == issue_id:
            return item
    return None
