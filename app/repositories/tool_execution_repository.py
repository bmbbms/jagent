from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import DataAccessLogModel, ToolCallLogModel


class ToolExecutionRepository:
    def create_tool_call_log(
        self,
        session: Session,
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
    ) -> None:
        session.add(
            ToolCallLogModel(
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
        )
        session.flush()

    def create_data_access_log(
        self,
        session: Session,
        *,
        task_id: str,
        agent_id: str | None,
        tool_call_id: str | None,
        data_source: str,
        data_object: str,
        access_type: str,
        sensitive_level: str,
        row_count: int | None,
        field_scope: dict[str, Any] | None,
        approved: bool,
        approval_id: str | None,
        operator_id: str | None,
        create_time: datetime,
    ) -> None:
        session.add(
            DataAccessLogModel(
                id=self._new_data_access_log_id(),
                task_id=task_id,
                agent_id=agent_id,
                tool_call_id=tool_call_id,
                data_source=data_source,
                data_object=data_object,
                access_type=access_type,
                sensitive_level=sensitive_level,
                row_count=row_count,
                field_scope=field_scope,
                approved=approved,
                approval_id=approval_id,
                operator_id=operator_id,
                create_time=create_time,
            )
        )
        session.flush()

    @staticmethod
    def _new_data_access_log_id() -> int:
        return uuid4().int & ((1 << 63) - 1)

    def list_tool_call_logs(
        self,
        session: Session,
        *,
        task_id: str,
    ) -> list[ToolCallLogModel]:
        return (
            session.query(ToolCallLogModel)
            .filter(ToolCallLogModel.task_id == task_id)
            .order_by(ToolCallLogModel.start_time.asc())
            .all()
        )

    def list_data_access_logs(
        self,
        session: Session,
        *,
        task_id: str,
    ) -> list[DataAccessLogModel]:
        return (
            session.query(DataAccessLogModel)
            .filter(DataAccessLogModel.task_id == task_id)
            .order_by(DataAccessLogModel.create_time.asc())
            .all()
        )
