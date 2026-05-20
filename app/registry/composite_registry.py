from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from app.agents.base import CapabilityAgent
from app.registry.base import (
    CapabilityMetadata,
    CapabilityRegistrar,
    CapabilityResolver,
    CapabilityRoutePlan,
)
from app.schemas import BizDomain, ChatRequest


class CompositeCapabilityRegistry(CapabilityRegistrar, CapabilityResolver):
    """
    Compose one local resolver with optional secondary registries such as Nacos.

    Current strategy:
    - all local capability agents register into local registry
    - optional external registries receive metadata publication
    - resolution always prefers local registry in phase 1
    """

    def __init__(
        self,
        local_registry: CapabilityResolver & CapabilityRegistrar,
        secondary_registries: Optional[Iterable[CapabilityResolver & CapabilityRegistrar]] = None,
    ) -> None:
        self._local_registry = local_registry
        self._secondary_registries = list(secondary_registries or [])

    def register_local(self, agent: CapabilityAgent) -> None:
        self._local_registry.register_local(agent)
        for registry in self._secondary_registries:
            registry.register_local(agent)

    def register_remote(self, metadata: CapabilityMetadata) -> CapabilityMetadata:
        result = metadata
        for registry in self._secondary_registries:
            try:
                result = registry.register_remote(metadata)
            except Exception:
                continue
        return result

    def unregister_remote(self, capability_id: str) -> bool:
        removed = False
        for registry in self._secondary_registries:
            try:
                removed = bool(registry.unregister_remote(capability_id)) or removed
            except Exception:
                continue
        return removed

    def resolve(self, request: ChatRequest) -> CapabilityAgent:
        requested_agent_id = self._requested_agent_id(request)
        if requested_agent_id:
            for registry in self._registries():
                if requested_agent_id not in registry.list_capabilities():
                    continue
                return registry.resolve(request)
            raise ValueError(f"Requested capability not found: {requested_agent_id}")

        try:
            return self._local_registry.resolve(request)
        except Exception:
            for registry in self._secondary_registries:
                try:
                    return registry.resolve(request)
                except Exception:
                    continue
            raise

    def explain_route(self, request: ChatRequest) -> CapabilityRoutePlan:
        selected_agent = self.resolve(request)
        candidates = self.describe_capabilities(request.biz_domain)
        selected_by_id: Dict[str, CapabilityMetadata] = {
            item.capability_id: item for item in candidates
        }
        selected_metadata = selected_by_id.get(
            selected_agent.definition.capability_id,
            self._metadata_from_agent(selected_agent),
        )
        requested_agent_id = self._requested_agent_id(request)
        if requested_agent_id:
            matched = [
                item for item in candidates if item.capability_id == requested_agent_id
            ]
            reason = "Selected by requested_agent_id across composite registry."
        else:
            lowered_message = request.message.lower()
            matched = [
                item
                for item in candidates
                if not item.triggers
                or any(trigger.lower() in lowered_message for trigger in item.triggers)
            ]
            reason = "Selected by resolver priority and trigger matching across registries."
        return CapabilityRoutePlan(
            selected=selected_metadata,
            candidates=candidates,
            matched=matched or candidates,
            selected_agent=selected_agent,
            reason=reason,
        )

    def list_capabilities(self, biz_domain: Optional[BizDomain] = None) -> List[str]:
        return [item.capability_id for item in self.describe_capabilities(biz_domain)]

    def describe_capabilities(
        self, biz_domain: Optional[BizDomain] = None
    ) -> List[CapabilityMetadata]:
        merged: Dict[str, CapabilityMetadata] = {}
        for registry in self._registries():
            for item in registry.describe_capabilities(biz_domain):
                existing = merged.get(item.capability_id)
                if existing is None or item.priority < existing.priority:
                    merged[item.capability_id] = item
        return sorted(
            merged.values(),
            key=lambda item: (item.priority, item.capability_id),
        )

    def _registries(self) -> List[CapabilityResolver & CapabilityRegistrar]:
        return [self._local_registry, *self._secondary_registries]

    @staticmethod
    def _requested_agent_id(request: ChatRequest) -> str:
        return str(request.metadata.get("requested_agent_id") or "").strip()
