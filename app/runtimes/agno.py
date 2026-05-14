from __future__ import annotations

from app.agents.base import CapabilityAgent
from app.runtimes.base import RuntimeContext
from app.schemas import ChatRequest, ChatResponse


class AgnoAgentRuntime:
    """Agno runtime adapter placeholder.

    The platform selects Agno as the target agent framework. Phase 1 keeps
    existing capability agents executable while isolating the framework boundary
    here, so the next step can replace direct local execution with real Agno
    Agent/Tool orchestration without changing FastAPI routes or registries.
    """

    runtime_name = "agno"

    def run(
        self,
        agent: CapabilityAgent,
        request: ChatRequest,
        context: RuntimeContext,
    ) -> ChatResponse:
        try:
            import agno  # noqa: F401
        except ImportError:
            response = agent.run(request)
            response.audit_tags.append("runtime_fallback:local")
            return response
        return agent.run(request)
