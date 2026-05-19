from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.db.session import session_scope
from app.repositories.tool_execution_repository import ToolExecutionRepository
from app.schemas import DataAccessLogResponse, ToolCallLogResponse


class ToolExecutionLogService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        repository: ToolExecutionRepository,
    ) -> None:
        self._session_factory = session_factory
        self._repository = repository

    def record_tool_execution(
        self,
        *,
        tool_call_id: str,
        task_id: str,
        event_id: str | None,
        agent_id: str | None,
        tool_id: str,
        tool_name: str,
        tool_type: str,
        provider: str | None,
        request_args: dict[str, Any] | None,
        response_summary: str | None,
        status: str,
        error_code: str | None,
        error_msg: str | None,
        sensitive_hit: bool,
        duration_ms: int | None,
        start_time: datetime,
        end_time: datetime | None,
        data_access_records: list[dict[str, Any]] | None = None,
    ) -> None:
        if not task_id:
            return
        with session_scope(self._session_factory) as session:
            self._repository.create_tool_call_log(
                session,
                tool_call_id=tool_call_id,
                task_id=task_id,
                event_id=event_id,
                agent_id=agent_id,
                tool_id=tool_id,
                tool_name=tool_name,
                tool_type=tool_type,
                provider=provider,
                request_args=request_args,
                response_summary=response_summary,
                status=status,
                error_code=error_code,
                error_msg=error_msg,
                sensitive_hit=sensitive_hit,
                duration_ms=duration_ms,
                start_time=start_time,
                end_time=end_time,
            )
            for item in data_access_records or []:
                self._repository.create_data_access_log(
                    session,
                    task_id=task_id,
                    agent_id=agent_id,
                    tool_call_id=tool_call_id,
                    data_source=item["data_source"],
                    data_object=item["data_object"],
                    access_type=item.get("access_type", "read"),
                    sensitive_level=item.get("sensitive_level", "low"),
                    row_count=item.get("row_count"),
                    field_scope=item.get("field_scope"),
                    approved=item.get("approved", False),
                    approval_id=item.get("approval_id"),
                    operator_id=item.get("operator_id"),
                    create_time=end_time or start_time,
                )

    def list_tool_call_logs(self, *, task_id: str) -> list[ToolCallLogResponse]:
        with self._session_factory() as session:
            return [
                ToolCallLogResponse(
                    tool_call_id=item.tool_call_id,
                    task_id=item.task_id,
                    event_id=item.event_id,
                    agent_id=item.agent_id,
                    runtime_session_id=self._extract_runtime_session_id(item.request_args),
                    tool_id=item.tool_id,
                    tool_name=item.tool_name,
                    tool_type=item.tool_type,
                    provider=item.provider,
                    request_args=item.request_args or {},
                    response_summary=item.response_summary or "",
                    status=item.status,
                    error_code=item.error_code,
                    error_msg=item.error_msg,
                    sensitive_hit=item.sensitive_hit,
                    duration_ms=item.duration_ms,
                    start_time=item.start_time.isoformat(),
                    end_time=item.end_time.isoformat() if item.end_time else None,
                )
                for item in self._repository.list_tool_call_logs(session, task_id=task_id)
            ]

    def list_data_access_logs(self, *, task_id: str) -> list[DataAccessLogResponse]:
        with self._session_factory() as session:
            tool_call_items = self._repository.list_tool_call_logs(session, task_id=task_id)
            runtime_session_by_tool_call_id = {
                item.tool_call_id: self._extract_runtime_session_id(item.request_args)
                for item in tool_call_items
            }
            return [
                DataAccessLogResponse(
                    id=item.id,
                    task_id=item.task_id,
                    agent_id=item.agent_id,
                    tool_call_id=item.tool_call_id,
                    runtime_session_id=runtime_session_by_tool_call_id.get(item.tool_call_id),
                    data_source=item.data_source,
                    data_object=item.data_object,
                    access_type=item.access_type,
                    sensitive_level=item.sensitive_level,
                    row_count=item.row_count,
                    field_scope=item.field_scope or {},
                    approved=item.approved,
                    approval_id=item.approval_id,
                    operator_id=item.operator_id,
                    create_time=item.create_time.isoformat(),
                )
                for item in self._repository.list_data_access_logs(session, task_id=task_id)
            ]

    @staticmethod
    def _extract_runtime_session_id(request_args: dict[str, Any] | None) -> str | None:
        if not isinstance(request_args, dict):
            return None
        request_context = request_args.get("request_context")
        if not isinstance(request_context, dict):
            return None
        runtime_session_id = request_context.get("runtime_session_id")
        return runtime_session_id if isinstance(runtime_session_id, str) and runtime_session_id else None
