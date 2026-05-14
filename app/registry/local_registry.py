from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict, Dict, List, Optional

from app.agents.base import CapabilityAgent, match_capabilities
from app.registry.base import CapabilityMetadata, CapabilityRegistrar, CapabilityResolver
from app.schemas import BizDomain, ChatRequest


class LocalCapabilityRegistry(CapabilityRegistrar, CapabilityResolver):
    """In-process capability registry for local development and unit tests."""

    def __init__(self) -> None:
        self._capabilities: DefaultDict[BizDomain, List[CapabilityAgent]] = defaultdict(list)
        self._all_by_id: Dict[str, CapabilityAgent] = {}

    def register_local(self, agent: CapabilityAgent) -> None:
        capability_id = agent.definition.capability_id
        if capability_id in self._all_by_id:
            raise ValueError(f"Duplicate capability id: {capability_id}")
        self._all_by_id[capability_id] = agent
        self._capabilities[agent.definition.biz_domain].append(agent)
        self._capabilities[agent.definition.biz_domain].sort(
            key=lambda item: item.definition.priority
        )

    def resolve(self, request: ChatRequest) -> CapabilityAgent:
        candidates = self._capabilities.get(request.biz_domain, [])
        matched = match_capabilities(request, candidates)
        if matched:
            return matched[0]
        raise ValueError(f"No registered capability for domain: {request.biz_domain}")

    def list_capabilities(self, biz_domain: Optional[BizDomain] = None) -> List[str]:
        if biz_domain is not None:
            return [item.definition.capability_id for item in self._capabilities[biz_domain]]
        return list(self._all_by_id.keys())

    def describe_capabilities(
        self, biz_domain: Optional[BizDomain] = None
    ) -> List[CapabilityMetadata]:
        agents = (
            self._capabilities.get(biz_domain, [])
            if biz_domain is not None
            else list(self._all_by_id.values())
        )
        return [
            CapabilityMetadata(
                capability_id=agent.definition.capability_id,
                capability_name=agent.definition.name,
                biz_domain=agent.definition.biz_domain,
                description=agent.definition.description,
                priority=agent.definition.priority,
                triggers=agent.definition.triggers,
            )
            for agent in agents
        ]
