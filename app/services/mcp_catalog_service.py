from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session, sessionmaker

from app.repositories.tool_execution_repository import ToolExecutionRepository
from app.schemas import MCPToolGovernanceIssueResponse, MCPToolInfo, MCPToolOverviewResponse
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

    def list_governance_issues(self) -> list[MCPToolGovernanceIssueResponse]:
        items = self.list_tools()
        issues: list[MCPToolGovernanceIssueResponse] = []
        for item in items:
            governance_status, reasons, recommended_action = self._build_governance_status(item)
            if governance_status == "healthy":
                continue
            issues.append(
                MCPToolGovernanceIssueResponse(
                    tool_id=item.tool_id,
                    provider=item.provider,
                    transport=item.transport,
                    enabled=item.enabled,
                    call_count=item.call_count,
                    failure_count=item.failure_count,
                    average_duration_ms=item.average_duration_ms,
                    governance_status=governance_status,
                    reasons=reasons,
                    recommended_action=recommended_action,
                )
            )
        issues.sort(
            key=lambda item: (
                0 if item.governance_status == "blocked" else 1,
                -item.failure_count,
                -(item.average_duration_ms or 0),
                item.tool_id,
            )
        )
        return issues

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

    @staticmethod
    def _build_governance_status(
        item: MCPToolInfo,
    ) -> tuple[str, list[str], str]:
        reasons: list[str] = []
        if not item.enabled:
            reasons.append("tool_disabled")
        if item.failure_count >= 3:
            reasons.append("failure_count_high")
        elif item.failure_count > 0:
            reasons.append("tool_has_failures")
        if (item.average_duration_ms or 0) >= 3000:
            reasons.append("latency_too_high")

        if "failure_count_high" in reasons:
            governance_status = "blocked"
        elif reasons:
            governance_status = "degraded"
        else:
            governance_status = "healthy"

        if "failure_count_high" in reasons:
            recommended_action = "建议优先排查连续失败原因，并在恢复前限制生产使用。"
        elif "latency_too_high" in reasons:
            recommended_action = "建议检查 MCP 服务端时延、网络链路和超时策略。"
        elif "tool_disabled" in reasons:
            recommended_action = "建议确认该工具是否仍需启用，避免配置与实际依赖不一致。"
        elif "tool_has_failures" in reasons:
            recommended_action = "建议回看最近调用任务和失败日志，定位参数或服务端问题。"
        else:
            recommended_action = "当前治理状态稳定，可继续观察。"

        return governance_status, reasons, recommended_action
