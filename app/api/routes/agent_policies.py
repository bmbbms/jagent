from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_agent_policy_service
from app.schemas import (
    AgentPolicyCheckRequest,
    AgentPolicyCheckResponse,
    AgentPolicyResponse,
    AgentPolicyUpdateRequest,
)
from app.services.agent_policy_service import AgentPolicyService

router = APIRouter(prefix="/agent-policies", tags=["agent-policies"])


@router.get("", response_model=list[AgentPolicyResponse])
def list_agent_policies(
    service: AgentPolicyService = Depends(get_agent_policy_service),
) -> list[AgentPolicyResponse]:
    return [_policy_to_response(item) for item in service.list_policies()]


@router.put("/{agent_id}", response_model=AgentPolicyResponse)
def update_agent_policy(
    agent_id: str,
    request: AgentPolicyUpdateRequest,
    service: AgentPolicyService = Depends(get_agent_policy_service),
) -> AgentPolicyResponse:
    item = service.save_policy(
        agent_id=agent_id,
        tenant_id=request.tenant_id,
        allowed_users=request.allowed_users,
        allowed_roles=request.allowed_roles,
        allowed_sources=request.allowed_sources,
        default_decision=request.default_decision,
        rate_limit=request.rate_limit,
        audit_required=request.audit_required,
        enabled=request.enabled,
    )
    return _policy_to_response(item)


@router.post("/check", response_model=AgentPolicyCheckResponse)
def check_agent_policy(
    request: AgentPolicyCheckRequest,
    service: AgentPolicyService = Depends(get_agent_policy_service),
) -> AgentPolicyCheckResponse:
    result = service.check_access(
        agent_id=request.agent_id,
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        roles=request.roles,
        source=request.source,
    )
    return AgentPolicyCheckResponse(
        agent_id=request.agent_id,
        allowed=result.allowed,
        decision=result.decision,
        reason=result.reason,
        audit_required=result.audit_required,
        matched_policy_id=result.matched_policy_id,
    )


def _policy_to_response(item) -> AgentPolicyResponse:  # noqa: ANN001
    return AgentPolicyResponse(
        policy_id=item.policy_id,
        agent_id=item.agent_id,
        tenant_id=item.tenant_id,
        allowed_users=list(item.allowed_users or []),
        allowed_roles=list(item.allowed_roles or []),
        allowed_sources=list(item.allowed_sources or []),
        default_decision=item.default_decision,
        rate_limit=item.rate_limit,
        audit_required=bool(item.audit_required),
        enabled=bool(item.enabled),
        create_time=item.create_time.isoformat() if item.create_time else None,
        update_time=item.update_time.isoformat() if item.update_time else None,
    )
