from __future__ import annotations

from app.agents.base import CapabilityAgent
from app.runtimes.base import RuntimeContext
from app.schemas import ChatRequest, ChatResponse


class LocalAgentRuntime:
    runtime_name = "local"

    def run(
        self,
        agent: CapabilityAgent,
        request: ChatRequest,
        context: RuntimeContext,
    ) -> ChatResponse:
        return agent.run(request)
