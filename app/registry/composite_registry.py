from __future__ import annotations

from typing import Iterable, List, Optional

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

    def resolve(self, request: ChatRequest) -> CapabilityAgent:
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
        try:
            return self._local_registry.explain_route(request)
        except Exception:
            for registry in self._secondary_registries:
                try:
                    return registry.explain_route(request)
                except Exception:
                    continue
            raise

    def list_capabilities(self, biz_domain: Optional[BizDomain] = None) -> List[str]:
        return self._local_registry.list_capabilities(biz_domain)

    def describe_capabilities(
        self, biz_domain: Optional[BizDomain] = None
    ) -> List[CapabilityMetadata]:
        return self._local_registry.describe_capabilities(biz_domain)
