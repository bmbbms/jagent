from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_agent_gateway_routing_service
from app.schemas import (
    AgentGatewayFilteredCandidateResponse,
    AgentGatewayRankedCandidateResponse,
    AgentGatewayRouteRequest,
    AgentGatewayRouteResponse,
)
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
