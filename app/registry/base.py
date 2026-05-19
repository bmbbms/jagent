from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.agents.base import CapabilityAgent
from app.schemas import BizDomain, ChatRequest


@dataclass(frozen=True)
class CapabilityMetadata:
    capability_id: str
    capability_name: str
    biz_domain: BizDomain
    description: str
    priority: int
    triggers: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
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
    source: str = "local"


@dataclass(frozen=True)
class CapabilityRoutePlan:
    selected: CapabilityMetadata
    candidates: List[CapabilityMetadata] = field(default_factory=list)
    matched: List[CapabilityMetadata] = field(default_factory=list)
    selected_agent: Optional[CapabilityAgent] = None
    strategy: str = "priority_trigger_match"
    reason: str = ""


class CapabilityRegistrar(ABC):
    @abstractmethod
    def register_local(self, agent: CapabilityAgent) -> None:
        raise NotImplementedError


class CapabilityResolver(ABC):
    @abstractmethod
    def resolve(self, request: ChatRequest) -> CapabilityAgent:
        raise NotImplementedError

    @abstractmethod
    def list_capabilities(self, biz_domain: Optional[BizDomain] = None) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def describe_capabilities(
        self, biz_domain: Optional[BizDomain] = None
    ) -> List[CapabilityMetadata]:
        raise NotImplementedError

    def explain_route(self, request: ChatRequest) -> CapabilityRoutePlan:
        selected_agent = self.resolve(request)
        selected = self._metadata_from_agent(selected_agent)
        candidates = self.describe_capabilities(request.biz_domain)
        matched = [
            item
            for item in candidates
            if not item.triggers
            or any(trigger.lower() in request.message.lower() for trigger in item.triggers)
        ]
        return CapabilityRoutePlan(
            selected=selected,
            candidates=candidates,
            matched=matched or candidates,
            selected_agent=selected_agent,
            reason="Selected by resolver priority and trigger matching.",
        )

    def _metadata_from_agent(self, agent: CapabilityAgent) -> CapabilityMetadata:
        return CapabilityMetadata(
            capability_id=agent.definition.capability_id,
            capability_name=agent.definition.name,
            biz_domain=agent.definition.biz_domain,
            description=agent.definition.description,
            priority=agent.definition.priority,
            triggers=agent.definition.triggers,
            skills=agent.definition.skills,
            source="local",
        )
