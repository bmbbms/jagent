from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict, Dict, List, Optional

from app.agents.base import CapabilityAgent, match_capabilities
from app.registry.base import (
    CapabilityMetadata,
    CapabilityRegistrar,
    CapabilityResolver,
    CapabilityRoutePlan,
)
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

    def register_remote(self, metadata: CapabilityMetadata) -> CapabilityMetadata:
        raise NotImplementedError("Local registry does not support remote registration")

    def unregister_remote(self, capability_id: str) -> bool:
        raise NotImplementedError("Local registry does not support remote unregister")

    def resolve(self, request: ChatRequest) -> CapabilityAgent:
        requested_agent_id = str(request.metadata.get("requested_agent_id") or "").strip()
        if requested_agent_id:
            agent = self._all_by_id.get(requested_agent_id)
            if agent is None:
                raise ValueError(
                    f"Requested local capability not found: {requested_agent_id}"
                )
            if agent.definition.biz_domain != request.biz_domain:
                raise ValueError(
                    "Requested local capability domain mismatch: "
                    f"{requested_agent_id} != {request.biz_domain.value}"
                )
            return agent
        candidates = self._capabilities.get(request.biz_domain, [])
        matched = match_capabilities(request, candidates)
        if matched:
            return matched[0]
        raise ValueError(f"No registered capability for domain: {request.biz_domain}")

    def explain_route(self, request: ChatRequest) -> CapabilityRoutePlan:
        candidates = self._capabilities.get(request.biz_domain, [])
        requested_agent_id = str(request.metadata.get("requested_agent_id") or "").strip()
        if requested_agent_id:
            selected = self.resolve(request)
            return CapabilityRoutePlan(
                selected=self._to_metadata(selected),
                candidates=[self._to_metadata(item) for item in candidates],
                matched=[self._to_metadata(selected)],
                selected_agent=selected,
                reason="Selected by requested_agent_id in local registry.",
            )
        matched = match_capabilities(request, candidates)
        if not matched:
            raise ValueError(f"No registered capability for domain: {request.biz_domain}")
        return CapabilityRoutePlan(
            selected=self._to_metadata(matched[0]),
            candidates=[self._to_metadata(item) for item in candidates],
            matched=[self._to_metadata(item) for item in matched],
            selected_agent=matched[0],
            reason="Selected first matched capability after priority sorting.",
        )

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
        return [self._to_metadata(agent) for agent in agents]

    def _to_metadata(self, agent: CapabilityAgent) -> CapabilityMetadata:
        return CapabilityMetadata(
            capability_id=agent.definition.capability_id,
            capability_name=agent.definition.name,
            biz_domain=agent.definition.biz_domain,
            description=agent.definition.description,
            priority=agent.definition.priority,
            triggers=agent.definition.triggers,
            skills=agent.definition.skills,
            version=agent.definition.version,
            risk_level=agent.definition.risk_level,
            requires_approval=agent.definition.requires_approval,
            tags=agent.definition.tags,
            transport=agent.definition.transport,
            endpoint=agent.definition.endpoint,
            service_name=agent.definition.service_name,
            service_host=agent.definition.service_host,
            service_port=agent.definition.service_port,
            service_path=agent.definition.service_path,
            extras=agent.definition.extras,
            source="local",
        )
