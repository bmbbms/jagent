from __future__ import annotations

from typing import Any, List, Optional

from app.agents.base import CapabilityAgent
from app.config import Settings
from app.registry.base import CapabilityMetadata, CapabilityRegistrar, CapabilityResolver
from app.registry.nacos_ai_client import NacosAiHttpClient
from app.registry.remote_proxy import RemoteCapabilityProxy
from app.schemas import BizDomain, ChatRequest


class NacosCapabilityRegistry(CapabilityRegistrar, CapabilityResolver):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = NacosAiHttpClient(
            settings.nacos_ai_server_address or settings.nacos_server_address,
            namespace_id=settings.nacos_ai_namespace or settings.nacos_namespace,
            username=settings.nacos_ai_username or settings.nacos_username,
            password=settings.nacos_ai_password or settings.nacos_password,
        )
        self._local_cache: dict[str, CapabilityMetadata] = {}

    def register_local(self, agent: CapabilityAgent) -> None:
        metadata = self._to_metadata(agent)
        self._local_cache[metadata.capability_id] = metadata
        if self._settings.nacos_ai_enabled:
            print(
                f"[nacos] publish local capability capability_id={metadata.capability_id} "
                f"name={metadata.capability_name}",
                flush=True,
            )
            self._publish_agent_card(metadata)

    def register_remote(self, metadata: CapabilityMetadata) -> CapabilityMetadata:
        self._local_cache[metadata.capability_id] = metadata
        if self._settings.nacos_ai_enabled:
            print(
                f"[nacos] publish remote capability capability_id={metadata.capability_id} "
                f"name={metadata.capability_name}",
                flush=True,
            )
            self._publish_agent_card(metadata)
        return metadata

    def unregister_remote(self, capability_id: str) -> bool:
        removed = self._local_cache.pop(capability_id, None) is not None
        if self._settings.nacos_ai_enabled:
            try:
                self._client.delete_agent_card(capability_id)
            except Exception:
                pass
        return removed

    def resolve(self, request: ChatRequest) -> CapabilityAgent:
        metadata = self._select_metadata(request)
        if metadata is None:
            raise ValueError(f"No Nacos capability matched domain={request.biz_domain.value}")
        return RemoteCapabilityProxy(metadata)

    def list_capabilities(self, biz_domain: Optional[BizDomain] = None) -> List[str]:
        return [item.capability_id for item in self.describe_capabilities(biz_domain)]

    def describe_capabilities(
        self, biz_domain: Optional[BizDomain] = None
    ) -> List[CapabilityMetadata]:
        items = list(self._local_cache.values())
        if self._settings.nacos_ai_enabled and self._settings.nacos_ai_server_address:
            items.extend(self._load_remote_agent_cards())
        if biz_domain is not None:
            items = [item for item in items if item.biz_domain == biz_domain]
        merged: dict[str, CapabilityMetadata] = {}
        for item in items:
            existing = merged.get(item.capability_id)
            if existing is None or item.priority < existing.priority:
                merged[item.capability_id] = item
        return sorted(merged.values(), key=lambda item: (item.priority, item.capability_id))

    def _publish_agent_card(self, metadata: CapabilityMetadata) -> None:
        agent_card = self._build_agent_card(metadata)
        result = self._client.publish_agent_card(agent_card)
        if int(result.code) in {0, 20005}:
            status = "created" if int(result.code) == 0 else "conflict_ignored"
            print(
                f"[nacos] publish agent card status={status} "
                f"capability_id={metadata.capability_id} "
                f"name={metadata.capability_name} code={result.code}",
                flush=True,
            )
            return
        print(
            f"[nacos] publish agent card failed capability_id={metadata.capability_id} "
            f"name={metadata.capability_name} code={result.code} message={result.message}",
            flush=True,
        )
        raise RuntimeError(
            f"Unexpected Nacos publish result: code={result.code}, message={result.message}"
        )

    def _load_remote_agent_cards(self) -> list[CapabilityMetadata]:
        cards = self._client.list_agent_cards(page_size=self._settings.nacos_ai_page_size)
        items: list[CapabilityMetadata] = []
        for card in cards:
            item = self._from_agent_card(card)
            if item is not None:
                items.append(item)
        return items

    def _select_metadata(self, request: ChatRequest) -> CapabilityMetadata | None:
        requested_agent_id = str(request.metadata.get("requested_agent_id") or "").strip()
        candidates = [
            item
            for item in self.describe_capabilities(request.biz_domain)
            if item.biz_domain == request.biz_domain
        ]
        if requested_agent_id:
            for item in candidates:
                if item.capability_id == requested_agent_id:
                    return item
            return None
        lowered_message = request.message.lower()
        matched = [
            item
            for item in candidates
            if not item.triggers
            or any(trigger.lower() in lowered_message for trigger in item.triggers)
        ]
        matched.sort(key=lambda item: (item.priority, item.capability_id))
        return matched[0] if matched else (candidates[0] if candidates else None)

    def _build_agent_card(self, metadata: CapabilityMetadata) -> dict[str, Any]:
        target_url = metadata.endpoint or self._default_agent_url(metadata)
        service_url = self._join_url(target_url, metadata.service_path)
        return {
            "name": metadata.capability_name,
            "description": metadata.description,
            "url": service_url,
            "protocolVersion": metadata.extras.get("protocol_version", "1.0.0"),
            "preferredTransport": "JSONRPC",
            "version": metadata.version,
            "supportedInterfaces": [
                {
                    "transport": "JSONRPC",
                    "url": service_url,
                }
            ],
            "skills": [{"id": skill_id, "name": skill_id} for skill_id in metadata.skills],
            "metadata": {
                "capability_id": metadata.capability_id,
                "biz_domain": metadata.biz_domain.value,
                "priority": metadata.priority,
                "risk_level": metadata.risk_level,
                "requires_approval": metadata.requires_approval,
                "tags": metadata.tags,
                "transport": metadata.transport,
                "service_path": metadata.service_path,
                "endpoint": metadata.endpoint,
                "service_name": metadata.service_name,
                "service_host": metadata.service_host,
                "service_port": metadata.service_port,
                "extras": metadata.extras,
                "source": metadata.source,
            },
        }

    def _from_agent_card(self, card: dict[str, Any]) -> CapabilityMetadata | None:
        metadata = card.get("metadata") or {}
        capability_id = str(metadata.get("capability_id") or "").strip()
        if not capability_id:
            return None
        skills = []
        for item in card.get("skills") or []:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                skills.append(item["id"])
        transport = str(metadata.get("transport") or "a2a")
        endpoint = metadata.get("endpoint") or card.get("url")
        service_path = str(metadata.get("service_path") or "/a2a")
        biz_domain = metadata.get("biz_domain") or "merchant"
        return CapabilityMetadata(
            capability_id=capability_id,
            capability_name=str(card.get("name") or capability_id),
            biz_domain=BizDomain(str(biz_domain)),
            description=str(card.get("description") or ""),
            priority=int(metadata.get("priority") or 100),
            triggers=list(metadata.get("triggers") or []),
            skills=skills,
            version=str(card.get("version") or metadata.get("version") or "v1"),
            risk_level=str(metadata.get("risk_level") or "low"),
            requires_approval=bool(metadata.get("requires_approval") or False),
            tags=list(metadata.get("tags") or []),
            transport=transport,
            endpoint=str(endpoint) if endpoint else None,
            service_name=metadata.get("service_name"),
            service_host=metadata.get("service_host"),
            service_port=metadata.get("service_port"),
            service_path=service_path,
            extras={k: str(v) for k, v in (metadata.get("extras") or {}).items()},
            source=str(metadata.get("source") or "nacos_ai"),
        )

    @staticmethod
    def _to_metadata(agent: CapabilityAgent) -> CapabilityMetadata:
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

    def _default_agent_url(self, metadata: CapabilityMetadata) -> str:
        if metadata.endpoint:
            return metadata.endpoint.rstrip("/")
        if metadata.service_host and metadata.service_port:
            return f"http://{metadata.service_host}:{metadata.service_port}"
        return f"http://{self._settings.nacos_service_host}:{self._settings.nacos_service_port}"

    @staticmethod
    def _join_url(base_url: str, service_path: str) -> str:
        base = base_url.rstrip("/")
        path = (service_path or "").strip()
        if not path:
            return base
        if path.startswith("http://") or path.startswith("https://"):
            return path.rstrip("/")
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{base}{path}"
