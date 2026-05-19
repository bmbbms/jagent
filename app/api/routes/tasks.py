import asyncio
import json
from datetime import date, datetime, time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.dependencies import (
    get_evaluation_service,
    get_observation_service,
    get_task_service,
    get_tool_execution_log_service,
)
from app.schemas import (
    AgentEvaluationResponse,
    AgentObservationLogResponse,
    AgentTaskDetailResponse,
    AgentTaskListResponse,
    AgentTaskOutputOverviewResponse,
    DataAccessLogResponse,
    RuntimeSessionViewResponse,
    ToolCallLogResponse,
)
from app.services.evaluation_service import EvaluationService
from app.services.observation_service import ObservationService
from app.services.task_service import TaskService
from app.services.tool_execution_log_service import ToolExecutionLogService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=AgentTaskListResponse)
def list_tasks(
    status: str | None = None,
    biz_domain: str | None = None,
    selected_agent_id: str | None = None,
    risk_level: str | None = None,
    current_stage: str | None = None,
    approval_id: str | None = None,
    start_date_from: date | None = None,
    start_date_to: date | None = None,
    limit: int | None = Query(default=None, ge=1, le=200),
    page: int = Query(default=1, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=200),
    sort_by: Literal[
        "start_time",
        "end_time",
        "duration_ms",
        "status",
        "biz_domain",
        "selected_agent_id",
    ] = "start_time",
    sort_order: Literal["asc", "desc"] = "desc",
    task_service: TaskService = Depends(get_task_service),
) -> AgentTaskListResponse:
    start_time_from = (
        datetime.combine(start_date_from, time.min) if start_date_from is not None else None
    )
    start_time_to = (
        datetime.combine(start_date_to, time.max) if start_date_to is not None else None
    )
    effective_page_size = page_size or limit or 50
    return task_service.list_tasks(
        status=status,
        biz_domain=biz_domain,
        selected_agent_id=selected_agent_id,
        risk_level=risk_level,
        current_stage=current_stage,
        approval_id=approval_id,
        start_time_from=start_time_from,
        start_time_to=start_time_to,
        page=page,
        page_size=effective_page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/{task_id}", response_model=AgentTaskDetailResponse)
def get_task_detail(
    task_id: str,
    task_service: TaskService = Depends(get_task_service),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> AgentTaskDetailResponse:
    detail = task_service.get_task_detail(task_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="task not found")
    payload = detail.model_dump()
    payload["evaluation"] = evaluation_service.get_latest_by_task(task_id)
    return AgentTaskDetailResponse(**payload)


@router.get("/{task_id}/evaluation", response_model=AgentEvaluationResponse)
def get_task_evaluation(
    task_id: str,
    task_service: TaskService = Depends(get_task_service),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> AgentEvaluationResponse:
    detail = task_service.get_task_detail(task_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="task not found")
    evaluation = evaluation_service.get_latest_by_task(task_id)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="evaluation not found")
    return evaluation


@router.get("/{task_id}/output-overview", response_model=AgentTaskOutputOverviewResponse)
def get_task_output_overview(
    task_id: str,
    task_service: TaskService = Depends(get_task_service),
) -> AgentTaskOutputOverviewResponse:
    overview = task_service.get_task_output_overview(task_id)
    if overview is None:
        raise HTTPException(status_code=404, detail="task not found")
    return overview


@router.get("/{task_id}/tool-calls", response_model=list[ToolCallLogResponse])
def list_task_tool_calls(
    task_id: str,
    task_service: TaskService = Depends(get_task_service),
    tool_execution_log_service: ToolExecutionLogService = Depends(
        get_tool_execution_log_service
    ),
) -> list[ToolCallLogResponse]:
    detail = task_service.get_task_detail(task_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="task not found")
    return tool_execution_log_service.list_tool_call_logs(task_id=task_id)


@router.get("/{task_id}/data-access", response_model=list[DataAccessLogResponse])
def list_task_data_access(
    task_id: str,
    task_service: TaskService = Depends(get_task_service),
    tool_execution_log_service: ToolExecutionLogService = Depends(
        get_tool_execution_log_service
    ),
) -> list[DataAccessLogResponse]:
    detail = task_service.get_task_detail(task_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="task not found")
    return tool_execution_log_service.list_data_access_logs(task_id=task_id)


@router.get("/{task_id}/observations", response_model=list[AgentObservationLogResponse])
def list_task_observations(
    task_id: str,
    task_service: TaskService = Depends(get_task_service),
    observation_service: ObservationService = Depends(get_observation_service),
) -> list[AgentObservationLogResponse]:
    detail = task_service.get_task_detail(task_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="task not found")
    return observation_service.list_observations(task_id=task_id)


@router.get("/{task_id}/runtime-sessions", response_model=list[RuntimeSessionViewResponse])
def list_task_runtime_sessions(
    task_id: str,
    task_service: TaskService = Depends(get_task_service),
) -> list[RuntimeSessionViewResponse]:
    detail = task_service.get_task_detail(task_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="task not found")
    return detail.runtime_sessions


@router.get("/{task_id}/events/stream")
async def stream_task_events(
    task_id: str,
    last_event_seq: int = 0,
    poll_interval: float = 1.0,
    max_idle_rounds: int = 30,
    task_service: TaskService = Depends(get_task_service),
) -> StreamingResponse:
    detail = task_service.get_task_detail(task_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="task not found")

    async def event_generator():
        current_seq = last_event_seq
        idle_rounds = 0
        while True:
            events = task_service.list_task_events_after(task_id, current_seq)
            if events:
                idle_rounds = 0
                for event in events:
                    current_seq = event.event_seq
                    payload = json.dumps(event.model_dump(), ensure_ascii=False)
                    yield f"id: {event.event_seq}\n"
                    yield f"event: {event.event_type}\n"
                    yield f"data: {payload}\n\n"

                refreshed = task_service.get_task_detail(task_id)
                if refreshed and refreshed.status in {"success", "failed"}:
                    done_payload = json.dumps(
                        {
                            "task_id": refreshed.task_id,
                            "status": refreshed.status,
                            "current_stage": refreshed.current_stage,
                        },
                        ensure_ascii=False,
                    )
                    yield "event: task_completed\n"
                    yield f"data: {done_payload}\n\n"
                    break
            else:
                idle_rounds += 1
                heartbeat_payload = json.dumps(
                    {"task_id": task_id, "last_event_seq": current_seq},
                    ensure_ascii=False,
                )
                yield "event: heartbeat\n"
                yield f"data: {heartbeat_payload}\n\n"
                refreshed = task_service.get_task_detail(task_id)
                if refreshed and refreshed.status in {"success", "failed"} and idle_rounds >= 2:
                    done_payload = json.dumps(
                        {
                            "task_id": refreshed.task_id,
                            "status": refreshed.status,
                            "current_stage": refreshed.current_stage,
                        },
                        ensure_ascii=False,
                    )
                    yield "event: task_completed\n"
                    yield f"data: {done_payload}\n\n"
                    break
                if idle_rounds >= max_idle_rounds:
                    break
                await asyncio.sleep(max(0.2, poll_interval))

    return StreamingResponse(event_generator(), media_type="text/event-stream")
