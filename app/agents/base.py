from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from app.schemas import BizDomain, ChatRequest, ChatResponse


@dataclass(frozen=True)
class CapabilityDefinition:
    capability_id: str
    name: str
    biz_domain: BizDomain
    description: str
    triggers: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    priority: int = 100
    version: str = "v1"
    risk_level: str = "low"
    requires_approval: bool = False
    tags: List[str] = field(default_factory=list)
    transport: str = "inproc"
    endpoint: Optional[str] = None
    service_name: Optional[str] = None
    service_host: Optional[str] = None
    service_port: Optional[int] = None
    service_path: str = "/api/chat"
    extras: Dict[str, str] = field(default_factory=dict)

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
