from fastapi import APIRouter, Depends, Query

from app.dependencies import get_mcp_catalog_service, get_tool_execution_log_service
from app.schemas import (
    MCPToolGovernanceIssueResponse,
    MCPToolInfo,
    MCPToolOverviewResponse,
    ToolCallLogResponse,
    GovernanceAlertResponse,
)
from app.services.mcp_catalog_service import MCPCatalogService
from app.services.tool_execution_log_service import ToolExecutionLogService

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("/tools", response_model=list[MCPToolInfo])
def list_mcp_tools(
    provider: str | None = Query(default=None),
    transport: str | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    only_called: bool = Query(default=False),
    service: MCPCatalogService = Depends(get_mcp_catalog_service),
) -> list[MCPToolInfo]:
    return service.list_tools(
        provider=provider,
        transport=transport,
        enabled=enabled,
        only_called=only_called,
    )


@router.get("/overview", response_model=MCPToolOverviewResponse)
def get_mcp_overview(
    service: MCPCatalogService = Depends(get_mcp_catalog_service),
) -> MCPToolOverviewResponse:
    return service.get_overview()


@router.get("/governance-issues", response_model=list[MCPToolGovernanceIssueResponse])
def list_mcp_governance_issues(
    service: MCPCatalogService = Depends(get_mcp_catalog_service),
) -> list[MCPToolGovernanceIssueResponse]:
    return service.list_governance_issues()


@router.get("/alerts", response_model=list[GovernanceAlertResponse])
def list_mcp_governance_alerts(
    service: MCPCatalogService = Depends(get_mcp_catalog_service),
) -> list[GovernanceAlertResponse]:
    alerts: list[GovernanceAlertResponse] = []
    for item in service.list_governance_issues():
        alerts.append(
            GovernanceAlertResponse(
                alert_id=f"mcp-{item.tool_id}",
                alert_type="mcp_tool",
                source=item.provider,
                target_id=item.tool_id,
                target_name=item.tool_id,
                severity="critical" if item.governance_status == "blocked" else "high",
                status=item.governance_status,
                title=f"MCP Tool {item.tool_id} 出现治理告警",
                summary="; ".join(item.reasons) or item.recommended_action,
                reasons=item.reasons,
                recommended_action=item.recommended_action,
                last_latency_ms=item.average_duration_ms,
                consecutive_failures=item.failure_count,
                target_ui=f"/ui/mcp?tool_id={item.tool_id}",
                target_api=f"/api/mcp/tools/{item.tool_id}/recent-calls",
            )
        )
    return alerts


@router.get("/tools/{tool_id}/recent-calls", response_model=list[ToolCallLogResponse])
def list_mcp_recent_calls(
    tool_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    service: ToolExecutionLogService = Depends(get_tool_execution_log_service),
) -> list[ToolCallLogResponse]:
    return service.list_tool_call_logs_by_tool_id(tool_id=tool_id, limit=limit)
