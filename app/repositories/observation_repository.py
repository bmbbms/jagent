from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import AgentObservationLogModel


class ObservationRepository:
    def create_observation_log(
        self,
        session: Session,
        *,
        task_id: str,
        trace_id: str,
        session_id: str | None,
        agent_id: str | None,
        runtime_name: str,
        call_type: str,
        phase: str | None,
        model_provider: str | None,
        model_name: str | None,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        latency_ms: int | None,
        first_token_ms: int | None,
        status: str,
        fallback_used: bool,
        fallback_reason: str | None,
        input_snapshot: str | None,
        output_snapshot: str | None,
        extra_info: dict[str, Any] | None,
        start_time: datetime,
        end_time: datetime | None,
    ) -> None:
        payload = dict(
            task_id=task_id,
            trace_id=trace_id,
            session_id=session_id,
            agent_id=agent_id,
            runtime_name=runtime_name,
            call_type=call_type,
            phase=phase,
            model_provider=model_provider,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            first_token_ms=first_token_ms,
            status=status,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            input_snapshot=input_snapshot,
            output_snapshot=output_snapshot,
            extra_info=extra_info or {},
            start_time=start_time,
            end_time=end_time,
        )
        if session.bind is not None and session.bind.dialect.name == "sqlite":
            payload["id"] = self._next_id(session)
        session.add(
            AgentObservationLogModel(
                **payload,
            )
        )
        session.flush()

    def list_observation_logs(
        self,
        session: Session,
        *,
        task_id: str,
    ) -> list[AgentObservationLogModel]:
        return (
            session.query(AgentObservationLogModel)
            .filter(AgentObservationLogModel.task_id == task_id)
            .order_by(AgentObservationLogModel.start_time.asc(), AgentObservationLogModel.id.asc())
            .all()
        )

    @staticmethod
    def _next_id(session: Session) -> int:
        current_max = session.query(func.max(AgentObservationLogModel.id)).scalar()
        return int(current_max or 0) + 1
