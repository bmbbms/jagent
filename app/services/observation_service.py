from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.db.session import session_scope
from app.repositories.observation_repository import ObservationRepository
from app.schemas import AgentObservationLogResponse


class ObservationService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        repository: ObservationRepository,
    ) -> None:
        self._session_factory = session_factory
        self._repository = repository

    def record_observation(
        self,
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
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        latency_ms: int | None = None,
        first_token_ms: int | None = None,
        status: str = "success",
        fallback_used: bool = False,
        fallback_reason: str | None = None,
        input_snapshot: str | None = None,
        output_snapshot: str | None = None,
        extra_info: dict[str, Any] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> None:
        if not task_id:
            return
        actual_start = start_time or datetime.utcnow()
        with session_scope(self._session_factory) as session:
            self._repository.create_observation_log(
                session,
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
                start_time=actual_start,
                end_time=end_time,
            )

    def list_observations(self, *, task_id: str) -> list[AgentObservationLogResponse]:
        with self._session_factory() as session:
            return [
                AgentObservationLogResponse(
                    id=item.id,
                    task_id=item.task_id,
                    trace_id=item.trace_id,
                    session_id=item.session_id,
                    agent_id=item.agent_id,
                    runtime_name=item.runtime_name,
                    call_type=item.call_type,
                    phase=item.phase,
                    model_provider=item.model_provider,
                    model_name=item.model_name,
                    input_tokens=item.input_tokens,
                    output_tokens=item.output_tokens,
                    total_tokens=item.total_tokens,
                    latency_ms=item.latency_ms,
                    first_token_ms=item.first_token_ms,
                    status=item.status,
                    fallback_used=item.fallback_used,
                    fallback_reason=item.fallback_reason,
                    input_snapshot=item.input_snapshot or "",
                    output_snapshot=item.output_snapshot or "",
                    extra_info=item.extra_info or {},
                    start_time=item.start_time.isoformat(),
                    end_time=item.end_time.isoformat() if item.end_time else None,
                )
                for item in self._repository.list_observation_logs(session, task_id=task_id)
            ]
