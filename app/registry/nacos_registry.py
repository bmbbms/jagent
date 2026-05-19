from __future__ import annotations

from typing import List, Optional

from app.agents.base import CapabilityAgent
from app.registry.base import CapabilityMetadata, CapabilityRegistrar, CapabilityResolver
from app.registry.nacos_client import NacosHttpClient, NacosInstance
from app.registry.remote_proxy import RemoteCapabilityProxy
from app.schemas import BizDomain, ChatRequest


class NacosCapabilityRegistry(CapabilityRegistrar, CapabilityResolver):
    """
    Nacos-backed capability registry.

    Phase 1 behavior:
    - publish local capability metadata to Nacos when enabled
    - discover remote capability instances from Nacos when asked to resolve
    - if no remote endpoint exists, remain metadata-only
    """

    def __init__(
        self,
        server_address: str,
        namespace: str,
        group: str,
        service_prefix: str = "agent",
        enabled: bool = False,
        service_host: str = "127.0.0.1",
        service_port: int = 8000,
        service_path: str = "/api/chat",
        service_cluster: str = "DEFAULT",
        service_weight: float = 1.0,
    ) -> None:
        self.server_address = server_address
        self.namespace = namespace
        self.group = group
        self.service_prefix = service_prefix
        self.enabled = enabled
        self.service_host = service_host
        self.service_port = service_port
        self.service_path = service_path
        self.service_cluster = service_cluster
        self.service_weight = service_weight
        self._published_metadata: List[CapabilityMetadata] = []
        self._client = NacosHttpClient(f"http://{self.server_address}")

    def register_local(self, agent: CapabilityAgent) -> None:
        metadata = self._build_metadata(agent)
        self._published_metadata.append(metadata)
        if not self.enabled:
            return
        instance = NacosInstance(
            service_name=metadata.service_name or self._service_name(metadata.capability_id),
            ip=metadata.service_host or self.service_host,
            port=metadata.service_port or self.service_port,
            healthy=True,
            weight=self.service_weight,
            cluster_name=self.service_cluster,
            metadata=self._metadata_payload(metadata),
            ephemeral=True,
        )
        self._client.register_instance(
            namespace_id=self.namespace,
            group_name=self.group,
            instance=instance,
        )

    def resolve(self, request: ChatRequest) -> CapabilityAgent:
        metadata = self._select_metadata(request)
        if metadata is None:
            raise NotImplementedError(
                "No Nacos capability metadata matched the request."
            )
        if not self.enabled:
            raise NotImplementedError(
                "Nacos discovery is disabled. Use local registry for resolution."
            )
        service_name = metadata.service_name or self._service_name(metadata.capability_id)
        instances = self._client.list_instances(
            namespace_id=self.namespace,
            group_name=self.group,
            service_name=service_name,
            healthy_only=True,
        )
        for instance in instances:
            proxy = self._to_proxy(metadata, instance)
            if proxy is not None:
                return proxy
        raise RuntimeError(f"No healthy Nacos instance found for {service_name}")

    def list_capabilities(self, biz_domain: Optional[BizDomain] = None) -> List[str]:
        items = self._published_metadata
        if biz_domain is not None:
            items = [item for item in items if item.biz_domain == biz_domain]
        return [item.capability_id for item in items]

    def describe_published(self) -> List[CapabilityMetadata]:
        return list(self._published_metadata)

    def describe_capabilities(
        self, biz_domain: Optional[BizDomain] = None
    ) -> List[CapabilityMetadata]:
        items = self._published_metadata
        if biz_domain is not None:
            items = [item for item in items if item.biz_domain == biz_domain]
        return list(items)

    def _build_metadata(self, agent: CapabilityAgent) -> CapabilityMetadata:
        return CapabilityMetadata(
            capability_id=agent.definition.capability_id,
            capability_name=agent.definition.name,
            biz_domain=agent.definition.biz_domain,
            description=agent.definition.description,
            priority=agent.definition.priority,
            triggers=agent.definition.triggers,
            skills=agent.definition.skills,
            version="v1",
            risk_level="high" if agent.definition.biz_domain == BizDomain.operations else "low",
            requires_approval=agent.definition.biz_domain == BizDomain.operations,
            tags=["phase1", "registered"],
            transport="http",
            endpoint=f"http://{self.service_host}:{self.service_port}",
            service_name=self._service_name(agent.definition.capability_id),
            service_host=self.service_host,
            service_port=self.service_port,
            service_path=self.service_path,
            extras={
                "registry": "nacos",
                "namespace": self.namespace,
                "group": self.group,
            },
            source="nacos",
        )

    def _metadata_payload(self, metadata: CapabilityMetadata) -> dict[str, str]:
        return {
            "capability_id": metadata.capability_id,
            "capability_name": metadata.capability_name,
            "biz_domain": metadata.biz_domain.value,
            "priority": str(metadata.priority),
            "triggers": ",".join(metadata.triggers),
            "skills": ",".join(metadata.skills),
            "version": metadata.version,
            "risk_level": metadata.risk_level,
            "requires_approval": str(metadata.requires_approval).lower(),
            "transport": metadata.transport,
            "endpoint": metadata.endpoint or "",
            "service_path": metadata.service_path,
        }

    def _select_metadata(self, request: ChatRequest) -> Optional[CapabilityMetadata]:
        candidates = [item for item in self._published_metadata if item.biz_domain == request.biz_domain]
        if not candidates:
            return None
        message = request.message.lower()
        matched = [
            item for item in candidates if not item.triggers or any(trigger.lower() in message for trigger in item.triggers)
        ]
        if not matched:
            matched = candidates
        matched.sort(key=lambda item: item.priority)
        return matched[0]

    def _to_proxy(self, metadata: CapabilityMetadata, instance: dict) -> Optional[RemoteCapabilityProxy]:
        ip = instance.get("ip") or instance.get("instanceId")
        port = instance.get("port")
        endpoint = None
        if ip and port:
            endpoint = f"http://{ip}:{port}"
        instance_metadata = instance.get("metadata") or {}
        resolved = CapabilityMetadata(
            capability_id=metadata.capability_id,
            capability_name=metadata.capability_name,
            biz_domain=metadata.biz_domain,
            description=metadata.description,
            priority=metadata.priority,
            triggers=metadata.triggers,
            skills=metadata.skills,
            version=metadata.version,
            risk_level=metadata.risk_level,
            requires_approval=metadata.requires_approval,
            tags=metadata.tags,
            transport=instance_metadata.get("transport", metadata.transport),
            endpoint=instance_metadata.get("endpoint", endpoint or metadata.endpoint),
            service_name=metadata.service_name,
            service_host=ip or metadata.service_host,
            service_port=int(port) if port is not None else metadata.service_port,
            service_path=instance_metadata.get("service_path", metadata.service_path),
            extras={**metadata.extras, **{k: str(v) for k, v in instance_metadata.items()}},
            source=metadata.source,
        )
        if not resolved.endpoint and not (resolved.service_host and resolved.service_port):
            return None
        return RemoteCapabilityProxy(resolved)

    def _service_name(self, capability_id: str) -> str:
        sanitized = capability_id.replace(".", "-")
        return f"{self.service_prefix}-{sanitized}"
