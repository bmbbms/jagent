from fastapi import APIRouter, Depends, Query

from app.dependencies import get_mcp_catalog_service, get_tool_execution_log_service
from app.schemas import MCPToolInfo, MCPToolOverviewResponse, ToolCallLogResponse
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


@router.get("/tools/{tool_id}/recent-calls", response_model=list[ToolCallLogResponse])
def list_mcp_recent_calls(
    tool_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    service: ToolExecutionLogService = Depends(get_tool_execution_log_service),
) -> list[ToolCallLogResponse]:
    return service.list_tool_call_logs_by_tool_id(tool_id=tool_id, limit=limit)
