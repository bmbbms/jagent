from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Protocol

from app.agents.base import CapabilityAgent
from app.registry.base import CapabilityRoutePlan
from app.schemas import ChatRequest, ChatResponse


@dataclass(frozen=True)
class RuntimeContext:
    route_plan: CapabilityRoutePlan
    skill_ids: List[str] = field(default_factory=list)
    tool_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)


class AgentRuntime(Protocol):
    runtime_name: str

    def run(
        self,
        agent: CapabilityAgent,
        request: ChatRequest,
        context: RuntimeContext,
    ) -> ChatResponse:
        raise NotImplementedError
