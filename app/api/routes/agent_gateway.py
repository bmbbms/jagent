from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import (
    get_agent_gateway_execution_service,
    get_agent_gateway_routing_service,
)
from app.schemas import (
    AgentDeclaredMCPResponse,
    AgentDeclaredSkillResponse,
    AgentDeclaredWorkflowResponse,
    AgentGatewayFilteredCandidateResponse,
    AgentGatewayInvokeRequest,
    AgentGatewayInvokeResponse,
    AgentGatewayRankedCandidateResponse,
    AgentGatewayRouteRequest,
    AgentGatewayRouteResponse,
)
from app.services.agent_gateway_execution_service import AgentGatewayExecutionService
from app.services.agent_gateway_routing_service import AgentGatewayRoutingService

router = APIRouter(prefix="/agent-gateway", tags=["agent-gateway"])


@router.post("/route", response_model=AgentGatewayRouteResponse)
def explain_agent_route(
    request: AgentGatewayRouteRequest,
    service: AgentGatewayRoutingService = Depends(get_agent_gateway_routing_service),
) -> AgentGatewayRouteResponse:
    payload = service.explain_route(
        user_id=request.user_id,
        biz_domain=request.biz_domain,
        message=request.message,
        requested_agent_id=request.requested_agent_id,
        tenant_id=request.tenant_id,
        roles=request.roles,
        source=request.source,
    )
    return AgentGatewayRouteResponse(
        selected_agent_id=payload["selected_agent_id"],
        selected_agent_name=payload["selected_agent_name"],
        matched_skill_ids=payload["matched_skill_ids"],
        route_reason=payload["route_reason"],
        candidate_agent_ids=payload["candidate_agent_ids"],
        allowed_agent_ids=payload["allowed_agent_ids"],
        filtered_candidates=[
            AgentGatewayFilteredCandidateResponse(**item)
            for item in payload["filtered_candidates"]
        ],
        ranked_candidates=[
            AgentGatewayRankedCandidateResponse(**item)
            for item in payload["ranked_candidates"]
        ],
        policy_decision=payload["policy_decision"],
        risk_flags=payload["risk_flags"],
    )


@router.post("/invoke", response_model=AgentGatewayInvokeResponse)
def invoke_agent_route(
    request: AgentGatewayInvokeRequest,
    service: AgentGatewayExecutionService = Depends(get_agent_gateway_execution_service),
) -> AgentGatewayInvokeResponse:
    try:
        payload = service.invoke(
            user_id=request.user_id,
            biz_domain=request.biz_domain,
            message=request.message,
            requested_agent_id=request.requested_agent_id,
            tenant_id=request.tenant_id,
            roles=request.roles,
            source=request.source,
            metadata=request.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return AgentGatewayInvokeResponse(
        task_id=payload.task_id,
        contact_id=payload.contact_id,
        selected_agent_id=payload.selected_agent_id,
        selected_agent_name=payload.selected_agent_name,
        matched_skill_ids=payload.matched_skill_ids,
        route_reason=payload.route_reason,
        policy_decision=payload.policy_decision,
        declared_skills=[_skill_to_response(item) for item in payload.declared_skills],
        declared_mcps=[_mcp_to_response(item) for item in payload.declared_mcps],
        declared_workflows=[_workflow_to_response(item) for item in payload.declared_workflows],
        summary=payload.summary,
        next_action=payload.next_action,
        references=payload.references,
        audit_tags=payload.audit_tags,
        routing_trace=payload.routing_trace,
        risk_flags=payload.risk_flags,
    )


def _skill_to_response(item) -> AgentDeclaredSkillResponse:  # noqa: ANN001
    return AgentDeclaredSkillResponse(
        skill_id=item.skill_id,
        skill_name=item.skill_name,
        description=item.description or "",
        tags=list(item.tags or []),
        examples=list(item.examples or []),
        input_modes=list(item.input_modes or []),
        output_modes=list(item.output_modes or []),
        raw_payload=dict(item.raw_payload or {}),
    )


def _mcp_to_response(item) -> AgentDeclaredMCPResponse:  # noqa: ANN001
    return AgentDeclaredMCPResponse(
        mcp_id=item.mcp_id,
        mcp_name=item.mcp_name,
        description=item.description or "",
        transport=item.transport,
        endpoint=item.endpoint,
        tags=list(item.tags or []),
        raw_payload=dict(item.raw_payload or {}),
    )


def _workflow_to_response(item) -> AgentDeclaredWorkflowResponse:  # noqa: ANN001
    return AgentDeclaredWorkflowResponse(
        workflow_id=item.workflow_id,
        workflow_name=item.workflow_name,
        description=item.description or "",
        steps=list(item.steps or []),
        tags=list(item.tags or []),
        raw_payload=dict(item.raw_payload or {}),
    )
