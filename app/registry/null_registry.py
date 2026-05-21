from __future__ import annotations

from typing import List, Optional

from app.agents.base import CapabilityAgent
from app.registry.base import CapabilityMetadata, CapabilityRegistrar, CapabilityResolver
from app.schemas import BizDomain, ChatRequest


class NullCapabilityRegistry(CapabilityRegistrar, CapabilityResolver):
    def register_local(self, agent: CapabilityAgent) -> None:
        return None

    def register_remote(self, metadata: CapabilityMetadata) -> CapabilityMetadata:
        return metadata

    def unregister_remote(self, capability_id: str) -> bool:
        return False

    def resolve(self, request: ChatRequest) -> CapabilityAgent:
        raise ValueError(f"No registered capability for domain: {request.biz_domain}")

    def list_capabilities(self, biz_domain: Optional[BizDomain] = None) -> List[str]:
        return []

    def describe_capabilities(
        self, biz_domain: Optional[BizDomain] = None
    ) -> List[CapabilityMetadata]:
        return []
