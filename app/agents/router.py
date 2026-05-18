from __future__ import annotations

from app.registry.base import CapabilityResolver
from app.runtimes.base import AgentRuntime, RuntimeContext
from app.schemas import ChatRequest, ChatResponse, RoutingTrace


class RouterAgent:
    def __init__(
        self,
        capability_resolver: CapabilityResolver,
        runtime: AgentRuntime,
    ) -> None:
        self._capability_resolver = capability_resolver
        self._runtime = runtime

    def plan(self, request: ChatRequest):
        return self._capability_resolver.explain_route(request)

    def run(self, request: ChatRequest) -> ChatResponse:
        route_plan = self.plan(request)
        capability_agent = route_plan.selected_agent
        if capability_agent is None:
            capability_agent = self._capability_resolver.resolve(request)
        runtime_context = request.metadata.get("_runtime_context", {})
        context = RuntimeContext(
            route_plan=route_plan,
            task_id=runtime_context.get("task_id", ""),
            contact_id=runtime_context.get("contact_id", ""),
            trace_id=runtime_context.get("trace_id", ""),
            skill_ids=route_plan.selected.skills,
            metadata={"runtime": self._runtime.runtime_name},
            emit_event=runtime_context.get("emit_event"),
        )
        response = self._runtime.run(capability_agent, request, context)
        response.routing_trace = RoutingTrace(
            requested_domain=request.biz_domain,
            selected_capability_id=route_plan.selected.capability_id,
            candidate_capability_ids=[
                item.capability_id for item in route_plan.candidates
            ],
            matched_capability_ids=[item.capability_id for item in route_plan.matched],
            declared_skills=route_plan.selected.skills,
            strategy=route_plan.strategy,
            reason=f"{route_plan.reason} Runtime={self._runtime.runtime_name}.",
        )
        return response
