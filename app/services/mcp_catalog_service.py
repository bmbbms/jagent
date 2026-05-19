from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session, sessionmaker

from app.repositories.tool_execution_repository import ToolExecutionRepository
from app.schemas import MCPToolInfo, MCPToolOverviewResponse
from app.tools import list_mcp_tool_specs


class MCPCatalogService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        repository: ToolExecutionRepository,
    ) -> None:
        self._session_factory = session_factory
        self._repository = repository

    def list_tools(
        self,
        *,
        provider: str | None = None,
        transport: str | None = None,
        enabled: bool | None = None,
        only_called: bool = False,
    ) -> list[MCPToolInfo]:
        usage_map = self._build_usage_map()
        items: list[MCPToolInfo] = []
        for spec in list_mcp_tool_specs():
            usage = usage_map.get(spec.tool_id, {})
            item = MCPToolInfo(
                tool_id=spec.tool_id,
                provider=spec.provider,
                description=spec.description,
                transport=str(spec.metadata.get("transport", "stdio")),
                command=spec.metadata.get("command"),
                args=list(spec.metadata.get("args", [])),
                enabled=bool(spec.metadata.get("enabled", False)),
                config_path=spec.metadata.get("config_path"),
                call_count=int(usage.get("call_count", 0)),
                success_count=int(usage.get("success_count", 0)),
                failure_count=int(usage.get("failure_count", 0)),
                last_status=usage.get("last_status"),
                last_called_at=usage.get("last_called_at"),
                average_duration_ms=usage.get("average_duration_ms"),
            )
            items.append(item)

        if provider:
            items = [item for item in items if item.provider == provider]
        if transport:
            items = [item for item in items if item.transport == transport]
        if enabled is not None:
            items = [item for item in items if item.enabled == enabled]
        if only_called:
            items = [item for item in items if item.call_count > 0]
        return items

    def get_overview(self) -> MCPToolOverviewResponse:
        items = self.list_tools()
        providers = sorted({item.provider for item in items})
        transports = sorted({item.transport for item in items})
        called_items = [item for item in items if item.call_count > 0]
        failure_items = [item for item in items if item.failure_count > 0]
        provider_failure_counts: dict[str, int] = {}
        transport_failure_counts: dict[str, int] = {}

        for item in items:
            if item.failure_count > 0:
                provider_failure_counts[item.provider] = (
                    provider_failure_counts.get(item.provider, 0) + item.failure_count
                )
                transport_failure_counts[item.transport] = (
                    transport_failure_counts.get(item.transport, 0) + item.failure_count
                )

        return MCPToolOverviewResponse(
            total=len(items),
            enabled_count=sum(1 for item in items if item.enabled),
            provider_count=len(providers),
            transport_count=len(transports),
            called_tool_count=len(called_items),
            failure_tool_count=len(failure_items),
            total_call_count=sum(item.call_count for item in items),
            disabled_tool_count=sum(1 for item in items if not item.enabled),
            slow_tool_count=sum(
                1 for item in items if (item.average_duration_ms or 0) >= 1500
            ),
            total_failure_count=sum(item.failure_count for item in items),
            high_risk_tool_count=sum(
                1
                for item in items
                if item.failure_count > 0 or (item.average_duration_ms or 0) >= 1500
            ),
            providers=providers,
            transports=transports,
            provider_failure_counts=provider_failure_counts,
            transport_failure_counts=transport_failure_counts,
        )

    def _build_usage_map(self) -> dict[str, dict[str, object]]:
        with self._session_factory() as session:
            rows = self._repository.list_tool_call_logs_by_type(session, tool_type="mcp")

        durations_by_tool: dict[str, list[int]] = defaultdict(list)
        usage_map: dict[str, dict[str, object]] = {}
        for row in rows:
            current = usage_map.setdefault(
                row.tool_id,
                {
                    "call_count": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "last_status": None,
                    "last_called_at": None,
                    "average_duration_ms": None,
                },
            )
            current["call_count"] = int(current["call_count"]) + 1
            if row.status == "success":
                current["success_count"] = int(current["success_count"]) + 1
            else:
                current["failure_count"] = int(current["failure_count"]) + 1
            if current["last_called_at"] is None:
                current["last_called_at"] = row.start_time.isoformat()
                current["last_status"] = row.status
            if row.duration_ms is not None:
                durations_by_tool[row.tool_id].append(int(row.duration_ms))

        for tool_id, durations in durations_by_tool.items():
            if durations:
                usage_map.setdefault(tool_id, {})["average_duration_ms"] = int(
                    sum(durations) / len(durations)
                )
        return usage_map
