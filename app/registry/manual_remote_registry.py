from __future__ import annotations

from typing import Dict, List, Optional

from app.agents.base import CapabilityAgent
from app.registry.base import (
    CapabilityMetadata,
    CapabilityRegistrar,
    CapabilityResolver,
    CapabilityRoutePlan,
)
from app.registry.remote_proxy import RemoteCapabilityProxy
from app.schemas import BizDomain, ChatRequest


class ManualRemoteCapabilityRegistry(CapabilityRegistrar, CapabilityResolver):
    """In-memory registry for manually configured external capability agents."""

    def __init__(self) -> None:
        self._capabilities: Dict[str, CapabilityMetadata] = {}

    def register_local(self, agent: CapabilityAgent) -> None:
        # Manual remote registry only stores external endpoints.
        return

    def register_remote(self, metadata: CapabilityMetadata) -> CapabilityMetadata:
        if not metadata.endpoint and not (
            metadata.service_host and metadata.service_port
        ):
            raise ValueError(
                "External capability must provide endpoint or service_host/service_port."
            )
        self._capabilities[metadata.capability_id] = metadata
        return metadata

    def update_remote(
        self,
        capability_id: str,
        metadata: CapabilityMetadata,
    ) -> CapabilityMetadata:
        if capability_id not in self._capabilities:
            raise KeyError(f"External capability not found: {capability_id}")
        if metadata.capability_id != capability_id:
            raise ValueError("capability_id in path and payload must match.")
        return self.register_remote(metadata)

    def unregister(self, capability_id: str) -> bool:
        return self._capabilities.pop(capability_id, None) is not None

    def clear(self) -> None:
        self._capabilities.clear()

    def get(self, capability_id: str) -> Optional[CapabilityMetadata]:
        return self._capabilities.get(capability_id)

    def resolve(self, request: ChatRequest) -> CapabilityAgent:
        metadata = self._select_metadata(request)
        if metadata is None:
            raise ValueError(
                f"No manual remote capability for domain: {request.biz_domain.value}"
            )
        return RemoteCapabilityProxy(metadata)

    def explain_route(self, request: ChatRequest) -> CapabilityRoutePlan:
        selected = self._select_metadata(request)
        if selected is None:
            raise ValueError(
                f"No manual remote capability for domain: {request.biz_domain.value}"
            )
        candidates = self.describe_capabilities(request.biz_domain)
        requested_agent_id = str(request.metadata.get("requested_agent_id") or "").strip()
        if requested_agent_id:
            matched = [
                item for item in candidates if item.capability_id == requested_agent_id
            ]
            reason = "Selected by requested_agent_id in manual remote registry."
        else:
            matched = self._match_candidates(candidates, request.message)
            reason = "Selected by priority and trigger matching in manual remote registry."
        return CapabilityRoutePlan(
            selected=selected,
            candidates=candidates,
            matched=matched or candidates,
            selected_agent=RemoteCapabilityProxy(selected),
            reason=reason,
        )

    def list_capabilities(self, biz_domain: Optional[BizDomain] = None) -> List[str]:
        return [item.capability_id for item in self.describe_capabilities(biz_domain)]

    def describe_capabilities(
        self, biz_domain: Optional[BizDomain] = None
    ) -> List[CapabilityMetadata]:
        items = list(self._capabilities.values())
        if biz_domain is not None:
            items = [item for item in items if item.biz_domain == biz_domain]
        return sorted(items, key=lambda item: (item.priority, item.capability_id))

    def _select_metadata(self, request: ChatRequest) -> Optional[CapabilityMetadata]:
        requested_agent_id = str(request.metadata.get("requested_agent_id") or "").strip()
        if requested_agent_id:
            item = self._capabilities.get(requested_agent_id)
            if item is None:
                raise ValueError(
                    f"Requested external capability not found: {requested_agent_id}"
                )
            if item.biz_domain != request.biz_domain:
                raise ValueError(
                    "Requested external capability domain mismatch: "
                    f"{requested_agent_id} != {request.biz_domain.value}"
                )
            return item

        candidates = self.describe_capabilities(request.biz_domain)
        matched = self._match_candidates(candidates, request.message)
        if matched:
            return matched[0]
        if candidates:
            return candidates[0]
        return None

    @staticmethod
    def _match_candidates(
        candidates: List[CapabilityMetadata],
        message: str,
    ) -> List[CapabilityMetadata]:
        lowered_message = message.lower()
        matched = [
            item
            for item in candidates
            if not item.triggers
            or any(trigger.lower() in lowered_message for trigger in item.triggers)
        ]
        return sorted(matched, key=lambda item: (item.priority, item.capability_id))
