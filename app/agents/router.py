from __future__ import annotations

from app.registry.base import CapabilityResolver
from app.schemas import ChatRequest, ChatResponse, RoutingTrace


class RouterAgent:
    def __init__(self, capability_resolver: CapabilityResolver) -> None:
        self._capability_resolver = capability_resolver

    def run(self, request: ChatRequest) -> ChatResponse:
        route_plan = self._capability_resolver.explain_route(request)
        capability_agent = route_plan.selected_agent
        if capability_agent is None:
            capability_agent = self._capability_resolver.resolve(request)
        response = capability_agent.run(request)
        response.routing_trace = RoutingTrace(
            requested_domain=request.biz_domain,
            selected_capability_id=route_plan.selected.capability_id,
            candidate_capability_ids=[
                item.capability_id for item in route_plan.candidates
            ],
            matched_capability_ids=[item.capability_id for item in route_plan.matched],
            declared_skills=route_plan.selected.skills,
            strategy=route_plan.strategy,
            reason=route_plan.reason,
        )
        return response
