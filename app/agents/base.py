from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable, List

from app.schemas import BizDomain, ChatRequest, ChatResponse


@dataclass(frozen=True)
class CapabilityDefinition:
    capability_id: str
    name: str
    biz_domain: BizDomain
    description: str
    triggers: List[str] = field(default_factory=list)
    priority: int = 100

    def matches(self, request: ChatRequest) -> bool:
        if request.biz_domain != self.biz_domain:
            return False
        if not self.triggers:
            return True
        message = request.message.lower()
        return any(trigger.lower() in message for trigger in self.triggers)


class CapabilityAgent(ABC):
    definition: CapabilityDefinition

    @abstractmethod
    def run(self, request: ChatRequest) -> ChatResponse:
        raise NotImplementedError


def match_capabilities(
    request: ChatRequest, capability_agents: Iterable[CapabilityAgent]
) -> List[CapabilityAgent]:
    matched = [agent for agent in capability_agents if agent.definition.matches(request)]
    return sorted(matched, key=lambda agent: agent.definition.priority)
