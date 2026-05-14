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
