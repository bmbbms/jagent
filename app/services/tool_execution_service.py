from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Callable
from uuid import uuid4

from app.services.internal_tool_registry import InternalToolRegistry
from app.services.mcp_service import MCPService
from app.services.tool_execution_log_service import ToolExecutionLogService
from app.tools import ToolSpec, get_tool_spec


@dataclass(frozen=True)
class ToolExecutionResult:
    tool_call_id: str
    tool_id: str
    tool_type: str
    provider: str
    status: str
    output_summary: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_event_payload(self) -> dict[str, Any]:
        return asdict(self)


class ToolExecutionService:
    def __init__(
        self,
        mcp_service: MCPService | None = None,
        internal_tool_registry: InternalToolRegistry | None = None,
        log_service: ToolExecutionLogService | None = None,
    ) -> None:
        self._mcp_service = mcp_service or MCPService()
        self._internal_tool_registry = internal_tool_registry or InternalToolRegistry()
        self._log_service = log_service

    def execute_tool(
        self,
        *,
        tool_id: str,
        request_context: dict[str, Any] | None = None,
        emit_event: Callable[..., dict[str, Any] | None] | None = None,
        agent_id: str | None = None,
        current_stage: str = "executing",
    ) -> ToolExecutionResult:
        request_context = dict(request_context or {})
        spec = get_tool_spec(tool_id)
        if spec is None:
            raise ValueError(f"Unsupported tool: {tool_id}")

        tool_call_id = request_context.get("tool_call_id") or self._new_id("tcall")
        task_id = request_context.get("task_id", "")
        event_type_prefix = "mcp_call" if spec.tool_type == "mcp" else "tool_call"
        start_time = datetime.utcnow()

        self._emit_event(
            emit_event=emit_event,
            task_id=task_id,
            event_type=f"{event_type_prefix}_started",
            title="开始调用 MCP 工具" if spec.tool_type == "mcp" else "开始调用工具",
            content=tool_id,
            agent_id=agent_id,
            tool_call_id=tool_call_id,
            current_stage=current_stage,
            event_payload={
                "tool_id": spec.tool_id,
                "tool_type": spec.tool_type,
                "provider": spec.provider,
                "request_context": request_context,
            },
        )

        try:
            result = self._execute_with_spec(
                tool_call_id=tool_call_id,
                request_context=request_context,
                spec=spec,
            )
        except Exception as exc:  # noqa: BLE001
            end_time = datetime.utcnow()
            failure_result = ToolExecutionResult(
                tool_call_id=tool_call_id,
                tool_id=spec.tool_id,
                tool_type=spec.tool_type,
                provider=spec.provider,
                status="failed",
                output_summary=f"Tool execution failed: {type(exc).__name__}",
                payload={
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "request_context": request_context,
                    "data_access_records": [],
                },
            )
            self._emit_event(
                emit_event=emit_event,
                task_id=task_id,
                event_type=f"{event_type_prefix}_finished",
                title="MCP 工具调用失败" if spec.tool_type == "mcp" else "工具调用失败",
                content=failure_result.output_summary,
                event_status="failed",
                agent_id=agent_id,
                tool_call_id=tool_call_id,
                current_stage=current_stage,
                event_payload=failure_result.to_event_payload(),
            )
            self._record_execution_log(
                spec=spec,
                tool_call_id=tool_call_id,
                task_id=task_id,
                agent_id=agent_id,
                request_context=request_context,
                result=failure_result,
                start_time=start_time,
                end_time=end_time,
            )
            raise

        end_time = datetime.utcnow()
        self._emit_event(
            emit_event=emit_event,
            task_id=task_id,
            event_type=f"{event_type_prefix}_finished",
            title="MCP 工具调用完成" if spec.tool_type == "mcp" else "工具调用完成",
            content=result.output_summary,
            event_status="success" if result.status == "success" else result.status,
            agent_id=agent_id,
            tool_call_id=tool_call_id,
            current_stage=current_stage,
            event_payload=result.to_event_payload(),
        )
        self._record_execution_log(
            spec=spec,
            tool_call_id=tool_call_id,
            task_id=task_id,
            agent_id=agent_id,
            request_context=request_context,
            result=result,
            start_time=start_time,
            end_time=end_time,
        )
        return result

    def _execute_with_spec(
        self,
        *,
        tool_call_id: str,
        request_context: dict[str, Any],
        spec: ToolSpec,
    ) -> ToolExecutionResult:
        if spec.tool_type == "mcp":
            result = self._mcp_service.invoke_tool(spec.tool_id, request_context)
            payload = {
                **result.payload,
                "data_access_records": result.payload.get("data_access_records", []),
            }
            return ToolExecutionResult(
                tool_call_id=tool_call_id,
                tool_id=result.tool_id,
                tool_type="mcp",
                provider=result.provider,
                status=result.status,
                output_summary=result.output_summary,
                payload=payload,
            )

        adapter = self._internal_tool_registry.get_adapter(spec.tool_id)
        adapter_result = adapter.execute(
            tool_spec=spec,
            request_context=request_context,
        )
        payload = {
            **adapter_result.payload,
            "output_summary": adapter_result.output_summary,
        }
        return ToolExecutionResult(
            tool_call_id=tool_call_id,
            tool_id=spec.tool_id,
            tool_type=spec.tool_type,
            provider=spec.provider,
            status=adapter_result.status,
            output_summary=adapter_result.output_summary,
            payload=payload,
        )

    def _record_execution_log(
        self,
        *,
        spec: ToolSpec,
        tool_call_id: str,
        task_id: str,
        agent_id: str | None,
        request_context: dict[str, Any],
        result: ToolExecutionResult,
        start_time: datetime,
        end_time: datetime,
    ) -> None:
        if self._log_service is None or not task_id:
            return
        duration_ms = max(0, int((end_time - start_time).total_seconds() * 1000))
        self._log_service.record_tool_execution(
            tool_call_id=tool_call_id,
            task_id=task_id,
            event_id=request_context.get("event_id"),
            agent_id=agent_id,
            tool_id=spec.tool_id,
            tool_name=spec.tool_id,
            tool_type=spec.tool_type,
            provider=spec.provider,
            request_args={
                "request_context": request_context,
                "request_query": request_context.get("query"),
                "request_kwargs": request_context.get("kwargs", {}),
            },
            response_summary=result.output_summary,
            status=result.status,
            error_code=result.payload.get("error_type"),
            error_msg=result.payload.get("error_message"),
            sensitive_hit=False,
            duration_ms=duration_ms,
            start_time=start_time,
            end_time=end_time,
            data_access_records=result.payload.get("data_access_records", []),
        )

    @staticmethod
    def _emit_event(
        *,
        emit_event: Callable[..., dict[str, Any] | None] | None,
        task_id: str,
        event_type: str,
        title: str,
        content: str,
        event_status: str = "success",
        agent_id: str | None = None,
        tool_call_id: str | None = None,
        current_stage: str | None = None,
        event_payload: dict[str, Any] | None = None,
    ) -> None:
        if emit_event is None or not task_id:
            return
        emit_event(
            task_id=task_id,
            event_type=event_type,
            title=title,
            content=content,
            event_status=event_status,
            agent_id=agent_id,
            tool_call_id=tool_call_id,
            current_stage=current_stage,
            event_payload=event_payload or {},
        )

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:24]}"
