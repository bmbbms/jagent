from __future__ import annotations

from app.registry.base import CapabilityResolver
from app.schemas import ChatRequest, ChatResponse


class RouterAgent:
    def __init__(self, capability_resolver: CapabilityResolver) -> None:
        self._capability_resolver = capability_resolver

    def run(self, request: ChatRequest) -> ChatResponse:
        capability_agent = self._capability_resolver.resolve(request)
        return capability_agent.run(request)
