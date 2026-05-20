from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.db.session import session_scope
from app.repositories.task_repository import TaskRepository
from app.schemas import (
    AgentCollaborationStepResponse,
    AgentHandoffResponse,
    AgentRecoveryStepResponse,
    AgentTaskArtifactResponse,
    AgentTaskDeliverableResponse,
    AgentTaskDetailResponse,
    AgentTaskEventResponse,
    AgentTaskListResponse,
    AgentObservationLogResponse,
    AgentTaskOutputOverviewResponse,
    AgentTaskSummaryResponse,
    ChatRequest,
    ChatResponse,
    DataAccessLogResponse,
    RuntimeSessionViewResponse,
    TaskAgentCollaborationViewResponse,
    TaskRuntimeGovernanceFocusTaskResponse,
    TaskRuntimeGovernanceOverviewResponse,
    TaskRuntimeGovernanceSummaryResponse,
    TaskRuntimeGovernanceTrendPointResponse,
    StructuredToolResultResponse,
    TaskRuntimeRecoveryViewResponse,
    ToolCallLogResponse,
)
from app.services.mcp_service import MCPService
from app.services.observation_service import ObservationService
from app.services.tool_execution_log_service import ToolExecutionLogService
from app.services.tool_execution_service import ToolExecutionService


class TaskService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        repository: TaskRepository,
        mcp_service: MCPService | None = None,
        tool_execution_service: ToolExecutionService | None = None,
        tool_execution_log_service: ToolExecutionLogService | None = None,
        observation_service: ObservationService | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._repository = repository
        self._mcp_service = mcp_service or MCPService()
        self._tool_execution_service = tool_execution_service or ToolExecutionService(
            mcp_service=self._mcp_service
        )
        self._tool_execution_log_service = tool_execution_log_service
        self._observation_service = observation_service

    def create_runtime_task(
        self,
        *,
        request: ChatRequest,
        selected_agent_id: str | None,
        capability_name: str,
    ) -> dict[str, str]:
        with session_scope(self._session_factory) as session:
            task = self._repository.create_task(
                session,
                user_id=request.user_id,
                biz_domain=request.biz_domain.value,
                requested_agent_id=request.metadata.get("requested_agent_id"),
                selected_agent_id=selected_agent_id,
                task_title=f"{capability_name} 任务",
                task_goal=request.message,
                input_summary=request.message,
                risk_level="low",
            )
            self._repository.append_event(
                session,
                task_id=task.task_id,
                contact_id=task.contact_id,
                event_type="task_created",
                event_seq=1,
                title="任务已创建",
                content=request.message,
                agent_id=selected_agent_id,
                event_payload={"biz_domain": request.biz_domain.value},
            )
            return {
                "task_id": task.task_id,
                "contact_id": task.contact_id,
                "trace_id": task.trace_id,
            }

    def emit_runtime_event(
        self,
        *,
        task_id: str,
        event_type: str,
        title: str = "",
        content: str = "",
        event_status: str = "success",
        agent_id: str | None = None,
        artifact_id: str | None = None,
        tool_call_id: str | None = None,
        visible_to_user: bool = True,
        event_payload: dict | None = None,
        current_stage: str | None = None,
        task_status: str | None = None,
    ) -> dict[str, Any] | None:
        with session_scope(self._session_factory) as session:
            task = self._repository.get_task(session, task_id)
            if task is None:
                return None
            event_payload = dict(event_payload or {})
            previous_agent_id = task.current_agent_id
            if previous_agent_id and "previous_agent_id" not in event_payload:
                event_payload["previous_agent_id"] = previous_agent_id
            if current_stage or task_status or agent_id is not None:
                self._repository.update_task_stage(
                    session,
                    task=task,
                    current_stage=current_stage or task.current_stage or "running",
                    current_agent_id=agent_id if agent_id is not None else task.current_agent_id,
                    status=task_status,
                )
            current_count = len(self._repository.list_events(session, task_id))
            event = self._repository.append_event(
                session,
                task_id=task_id,
                contact_id=task.contact_id,
                event_type=event_type,
                event_seq=current_count + 1,
                title=title,
                content=content,
                event_status=event_status,
                agent_id=agent_id,
                artifact_id=artifact_id,
                tool_call_id=tool_call_id,
                visible_to_user=visible_to_user,
                event_payload=event_payload,
            )
            return {"event_id": event.event_id, "event_seq": event.event_seq}

    def finalize_chat_task(
        self,
        *,
        task_id: str,
        response: ChatResponse,
    ) -> str | None:
        with self._session_factory() as session:
            task = self._repository.get_task(session, task_id)
            if task is None:
                return None
            contact_id = task.contact_id
            trace_id = task.trace_id

        runtime_session_id = self._resolve_runtime_session_id(task_id)

        tool_names = response.selected_tools or []
        executed_tool_ids = {
            item.get("tool_id")
            for item in response.runtime_tool_results
            if item.get("tool_id")
        }

        for tool_name in tool_names:
            if tool_name in executed_tool_ids:
                continue
            self._tool_execution_service.execute_tool(
                tool_id=tool_name,
                request_context={
                    "task_id": task_id,
                    "contact_id": contact_id,
                    "trace_id": trace_id,
                    "runtime_session_id": runtime_session_id,
                    "agent_id": response.capability_id,
                    "request_message": response.summary,
                },
                emit_event=self.emit_runtime_event,
                agent_id=response.capability_id,
            )

        self.emit_runtime_event(
            task_id=task_id,
            event_type="final_response",
            title="生成最终回复",
            content=response.summary,
            agent_id=response.capability_id,
            event_payload={
                "next_action": response.next_action,
                "selected_tools": response.selected_tools,
            },
        )

        artifact = self._create_final_artifact(
            task_id=task_id,
            contact_id=contact_id,
            agent_id=response.capability_id,
            content=response.summary,
        )
        self.emit_runtime_event(
            task_id=task_id,
            event_type="artifact_generated",
            title="生成任务产物",
            content=artifact.artifact_name,
            agent_id=response.capability_id,
            artifact_id=artifact.artifact_id,
            event_payload={"artifact_type": artifact.artifact_type},
        )
        self._complete_task(
            task_id=task_id,
            final_output_summary=response.summary,
            status="success",
        )

        return contact_id

    def list_tasks(
        self,
        *,
        status: str | None = None,
        biz_domain: str | None = None,
        selected_agent_id: str | None = None,
        risk_level: str | None = None,
        current_stage: str | None = None,
        start_time_from: datetime | None = None,
        start_time_to: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "start_time",
        sort_order: str = "desc",
    ) -> AgentTaskListResponse:
        page = max(1, page)
        page_size = max(1, min(page_size, 200))
        offset = (page - 1) * page_size
        with self._session_factory() as session:
            total = self._repository.count_tasks(
                session,
                status=status,
                biz_domain=biz_domain,
                selected_agent_id=selected_agent_id,
                risk_level=risk_level,
                current_stage=current_stage,
                start_time_from=start_time_from,
                start_time_to=start_time_to,
            )
            items = [
                self._to_summary(item)
                for item in self._repository.list_tasks(
                    session,
                    status=status,
                    biz_domain=biz_domain,
                    selected_agent_id=selected_agent_id,
                    risk_level=risk_level,
                    current_stage=current_stage,
                    start_time_from=start_time_from,
                    start_time_to=start_time_to,
                    offset=offset,
                    limit=page_size,
                    sort_by=sort_by,
                    sort_order=sort_order,
                )
            ]
            return AgentTaskListResponse(
                items=items,
                total=total,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_order=sort_order,
                has_next=offset + len(items) < total,
            )

    def get_task_detail(self, task_id: str) -> AgentTaskDetailResponse | None:
        with self._session_factory() as session:
            task = self._repository.get_task(session, task_id)
            if task is None:
                return None
            raw_events = self._repository.list_events(session, task_id)
            raw_artifacts = self._repository.list_artifacts(session, task_id)
            events = [self._to_event(item) for item in raw_events]
            artifacts = [self._to_artifact(item) for item in raw_artifacts]
            data = self._to_summary(task).model_dump()
            data["events"] = [item.model_dump() for item in events]
            data["artifacts"] = [item.model_dump() for item in artifacts]
            data["output_overview"] = None
            data["tool_calls"] = []
            data["data_access_logs"] = []
            data["structured_tool_results"] = []
            data["observations"] = []
            data["runtime_sessions"] = []
            data["evaluation"] = None
            observation_items: list[AgentObservationLogResponse] = []
            tool_call_items: list[ToolCallLogResponse] = []
            data_access_items: list[DataAccessLogResponse] = []
            if self._observation_service is not None:
                observation_items = self._observation_service.list_observations(task_id=task_id)
                data["observations"] = [item.model_dump() for item in observation_items]
            if self._tool_execution_log_service is not None:
                tool_call_items = self._tool_execution_log_service.list_tool_call_logs(task_id=task_id)
                data_access_items = self._tool_execution_log_service.list_data_access_logs(
                    task_id=task_id
                )
                data["tool_calls"] = [item.model_dump() for item in tool_call_items]
                data["data_access_logs"] = [item.model_dump() for item in data_access_items]
                data["structured_tool_results"] = [
                    item.model_dump()
                    for item in self._build_structured_tool_results(
                        raw_events=raw_events,
                        tool_calls=tool_call_items,
                        data_access_logs=data_access_items,
                    )
                ]
            data["output_overview"] = self.build_output_overview(
                task_id=task_id,
                final_output_summary=task.final_output_summary or "",
                events=events,
                artifacts=artifacts,
                structured_tool_results=[
                    StructuredToolResultResponse(**item)
                    for item in data["structured_tool_results"]
                ],
            ).model_dump()
            data["runtime_sessions"] = [
                item.model_dump()
                for item in self._build_runtime_sessions(
                    observations=observation_items,
                    tool_calls=tool_call_items,
                    data_access_logs=data_access_items,
                )
            ]
            data["runtime_governance"] = self._build_runtime_governance_summary(
                events=events,
                observations=observation_items,
                runtime_sessions=[
                    RuntimeSessionViewResponse(**item)
                    for item in data["runtime_sessions"]
                ],
            ).model_dump()
            return AgentTaskDetailResponse(**data)

    def get_task_output_overview(
        self,
        task_id: str,
    ) -> AgentTaskOutputOverviewResponse | None:
        detail = self.get_task_detail(task_id)
        if detail is None:
            return None
        return detail.output_overview

    def build_runtime_governance_overview(
        self,
        *,
        status: str | None = None,
        biz_domain: str | None = None,
        selected_agent_id: str | None = None,
        risk_level: str | None = None,
        current_stage: str | None = None,
        start_time_from: datetime | None = None,
        start_time_to: datetime | None = None,
        limit: int = 50,
    ) -> TaskRuntimeGovernanceOverviewResponse:
        task_list = self.list_tasks(
            status=status,
            biz_domain=biz_domain,
            selected_agent_id=selected_agent_id,
            risk_level=risk_level,
            current_stage=current_stage,
            start_time_from=start_time_from,
            start_time_to=start_time_to,
            page=1,
            page_size=limit,
            sort_by="start_time",
            sort_order="desc",
        )

        details = [
            self.get_task_detail(item.task_id)
            for item in task_list.items
        ]
        valid_details = [item for item in details if item is not None]

        risk_flag_counts: dict[str, int] = {}
        active_agent_counts: dict[str, int] = {}
        focus_tasks: list[TaskRuntimeGovernanceFocusTaskResponse] = []
        trend_map: dict[str, dict[str, Any]] = {}
        completed_task_count = 0
        failed_task_count = 0
        fallback_task_count = 0
        mcp_error_task_count = 0
        external_agent_error_task_count = 0
        multi_agent_task_count = 0
        multi_session_task_count = 0

        for item in valid_details:
            summary = item.runtime_governance
            stat_date = item.start_time[:10] if item.start_time else ""
            bucket = trend_map.setdefault(
                stat_date,
                {
                    "stat_date": stat_date,
                    "task_count": 0,
                    "completed_task_count": 0,
                    "failed_task_count": 0,
                    "fallback_task_count": 0,
                    "mcp_error_task_count": 0,
                    "external_agent_error_task_count": 0,
                    "multi_agent_task_count": 0,
                    "duration_total_ms": 0,
                    "duration_count": 0,
                },
            )
            bucket["task_count"] += 1
            if item.status == "success":
                bucket["completed_task_count"] += 1
            elif item.status == "failed":
                bucket["failed_task_count"] += 1
            if item.duration_ms is not None:
                bucket["duration_total_ms"] += item.duration_ms
                bucket["duration_count"] += 1
            if item.status == "success":
                completed_task_count += 1
            elif item.status == "failed":
                failed_task_count += 1

            if summary is None:
                continue
            if summary.fallback_count > 0:
                fallback_task_count += 1
                bucket["fallback_task_count"] += 1
            if summary.mcp_error_count > 0:
                mcp_error_task_count += 1
                bucket["mcp_error_task_count"] += 1
            if summary.external_agent_error_count > 0:
                external_agent_error_task_count += 1
                bucket["external_agent_error_task_count"] += 1
            if summary.agent_handoff_count > 0 or summary.unique_agent_count > 1:
                multi_agent_task_count += 1
                bucket["multi_agent_task_count"] += 1
            if summary.runtime_session_count > 1:
                multi_session_task_count += 1

            for risk_flag in summary.risk_flags:
                risk_flag_counts[risk_flag] = risk_flag_counts.get(risk_flag, 0) + 1
            for agent_id in summary.active_agents:
                active_agent_counts[agent_id] = active_agent_counts.get(agent_id, 0) + 1

            risk_score = (
                summary.external_agent_error_count * 4
                + summary.mcp_error_count * 3
                + summary.fallback_count * 2
                + summary.agent_handoff_count
                + len(summary.risk_flags)
            )
            if risk_score > 0:
                focus_tasks.append(
                    TaskRuntimeGovernanceFocusTaskResponse(
                        task_id=item.task_id,
                        task_title=item.task_title,
                        selected_agent_id=item.selected_agent_id,
                        status=item.status,
                        current_stage=item.current_stage,
                        start_time=item.start_time,
                        risk_score=risk_score,
                        risk_flags=summary.risk_flags,
                        fallback_count=summary.fallback_count,
                        mcp_error_count=summary.mcp_error_count,
                        external_agent_error_count=summary.external_agent_error_count,
                        handoff_count=summary.agent_handoff_count,
                        runtime_session_count=summary.runtime_session_count,
                    )
                )

        focus_tasks.sort(
            key=lambda item: (
                -item.risk_score,
                -item.external_agent_error_count,
                -item.mcp_error_count,
                -item.fallback_count,
                -item.handoff_count,
                item.task_id,
            )
        )

        return TaskRuntimeGovernanceOverviewResponse(
            task_count=len(valid_details),
            completed_task_count=completed_task_count,
            failed_task_count=failed_task_count,
            fallback_task_count=fallback_task_count,
            mcp_error_task_count=mcp_error_task_count,
            external_agent_error_task_count=external_agent_error_task_count,
            multi_agent_task_count=multi_agent_task_count,
            multi_session_task_count=multi_session_task_count,
            risk_flag_counts=risk_flag_counts,
            active_agent_counts=active_agent_counts,
            trend_points=[
                TaskRuntimeGovernanceTrendPointResponse(
                    stat_date=item["stat_date"],
                    task_count=item["task_count"],
                    completed_task_count=item["completed_task_count"],
                    failed_task_count=item["failed_task_count"],
                    fallback_task_count=item["fallback_task_count"],
                    mcp_error_task_count=item["mcp_error_task_count"],
                    external_agent_error_task_count=item["external_agent_error_task_count"],
                    multi_agent_task_count=item["multi_agent_task_count"],
                    avg_duration_ms=round(
                        item["duration_total_ms"] / item["duration_count"], 2
                    )
                    if item["duration_count"]
                    else 0.0,
                )
                for item in sorted(trend_map.values(), key=lambda x: x["stat_date"])
            ],
            focus_tasks=focus_tasks[:10],
        )

    def list_task_events_after(
        self,
        task_id: str,
        after_seq: int,
    ) -> list[AgentTaskEventResponse]:
        with self._session_factory() as session:
            task = self._repository.get_task(session, task_id)
            if task is None:
                return []
            return [
                self._to_event(item)
                for item in self._repository.list_events_after(session, task_id, after_seq)
            ]

    def get_task_contact_id(self, task_id: str) -> str | None:
        with self._session_factory() as session:
            task = self._repository.get_task(session, task_id)
            if task is None:
                return None
            return task.contact_id

    def fail_task(
        self,
        *,
        task_id: str,
        final_output_summary: str,
    ) -> None:
        self._complete_task(
            task_id=task_id,
            final_output_summary=final_output_summary,
            status="failed",
        )

    def _create_final_artifact(
        self,
        *,
        task_id: str,
        contact_id: str,
        agent_id: str | None,
        content: str,
    ):
        with session_scope(self._session_factory) as session:
            return self._repository.create_artifact(
                session,
                task_id=task_id,
                contact_id=contact_id,
                agent_id=agent_id,
                artifact_type="text",
                artifact_name="final_response",
                artifact_summary=content[:200],
                content_snapshot=content,
                is_final=True,
            )

    def _complete_task(
        self,
        *,
        task_id: str,
        final_output_summary: str,
        status: str,
    ) -> None:
        with session_scope(self._session_factory) as session:
            task = self._repository.get_task(session, task_id)
            if task is None:
                return
            self._repository.complete_task(
                session,
                task=task,
                final_output_summary=final_output_summary,
                status=status,
            )

    def _resolve_runtime_session_id(self, task_id: str) -> str | None:
        if self._observation_service is not None:
            observations = self._observation_service.list_observations(task_id=task_id)
            for item in reversed(observations):
                if item.session_id:
                    return item.session_id

        with self._session_factory() as session:
            events = self._repository.list_events(session, task_id)
            for item in reversed(events):
                event_payload = item.event_payload if isinstance(item.event_payload, dict) else {}
                runtime_session_id = event_payload.get("runtime_session_id")
                if isinstance(runtime_session_id, str) and runtime_session_id:
                    return runtime_session_id
        return None

    @staticmethod
    def _build_structured_tool_results(
        *,
        raw_events: list[Any],
        tool_calls: list[ToolCallLogResponse],
        data_access_logs: list[DataAccessLogResponse],
    ) -> list[StructuredToolResultResponse]:
        finished_event_map: dict[str, Any] = {}
        for event in raw_events:
            if event.event_type not in {"tool_call_finished", "mcp_call_finished"}:
                continue
            if not event.tool_call_id:
                continue
            finished_event_map[event.tool_call_id] = event

        data_access_map: dict[str, list[dict[str, Any]]] = {}
        for item in data_access_logs:
            if not item.tool_call_id:
                continue
            data_access_map.setdefault(item.tool_call_id, []).append(item.model_dump())

        results: list[StructuredToolResultResponse] = []
        for tool_call in tool_calls:
            event = finished_event_map.get(tool_call.tool_call_id)
            event_payload = event.event_payload if event and isinstance(event.event_payload, dict) else {}
            payload = event_payload.get("payload") if isinstance(event_payload.get("payload"), dict) else {}
            results.append(
                StructuredToolResultResponse(
                    tool_call_id=tool_call.tool_call_id,
                    tool_id=event_payload.get("tool_id") or tool_call.tool_id,
                    tool_name=tool_call.tool_name,
                    tool_type=tool_call.tool_type,
                    provider=tool_call.provider,
                    agent_id=tool_call.agent_id,
                    runtime_session_id=tool_call.runtime_session_id,
                    status=tool_call.status,
                    output_summary=event_payload.get("output_summary")
                    or tool_call.response_summary
                    or "",
                    request_query=payload.get("request_query", ""),
                    request_kwargs=payload.get("request_kwargs", {}),
                    result=payload.get("result", {}),
                    data_access_records=payload.get("data_access_records")
                    or data_access_map.get(tool_call.tool_call_id, []),
                    event_time=event.start_time.isoformat() if event else tool_call.start_time,
                )
            )
        return results

    @staticmethod
    def _build_runtime_sessions(
        *,
        observations: list[AgentObservationLogResponse],
        tool_calls: list[ToolCallLogResponse],
        data_access_logs: list[DataAccessLogResponse],
    ) -> list[RuntimeSessionViewResponse]:
        session_groups: dict[str, list[AgentObservationLogResponse]] = {}
        for item in observations:
            if not item.session_id:
                continue
            session_groups.setdefault(item.session_id, []).append(item)

        tool_call_groups: dict[str, list[ToolCallLogResponse]] = {}
        for item in tool_calls:
            if not item.runtime_session_id:
                continue
            tool_call_groups.setdefault(item.runtime_session_id, []).append(item)

        tool_call_session_map = {
            item.tool_call_id: item.runtime_session_id
            for item in tool_calls
            if item.runtime_session_id
        }
        data_access_groups: dict[str, list[DataAccessLogResponse]] = {}
        for item in data_access_logs:
            runtime_session_id = item.runtime_session_id or tool_call_session_map.get(item.tool_call_id or "")
            if not runtime_session_id:
                continue
            data_access_groups.setdefault(runtime_session_id, []).append(item)

        runtime_sessions: list[RuntimeSessionViewResponse] = []
        for session_id, items in session_groups.items():
            first = items[0]
            phases = [item.phase for item in items if item.phase]
            statuses = [item.status for item in items if item.status]
            fallback_reasons = [
                item.fallback_reason for item in items if item.fallback_reason
            ]
            tool_call_count = len(tool_call_groups.get(session_id, []))
            data_access_count = len(data_access_groups.get(session_id, []))
            runtime_sessions.append(
                RuntimeSessionViewResponse(
                    session_id=session_id,
                    trace_id=first.trace_id,
                    agent_id=first.agent_id,
                    runtime_name=first.runtime_name,
                    phases=phases,
                    statuses=statuses,
                    fallback_reasons=fallback_reasons,
                    total_latency_ms=sum(item.latency_ms or 0 for item in items),
                    observation_count=len(items),
                    tool_call_count=tool_call_count,
                    data_access_count=data_access_count,
                    observations=items,
                )
            )
        return runtime_sessions

    @staticmethod
    def _build_runtime_governance_summary(
        *,
        events: list[AgentTaskEventResponse],
        observations: list[AgentObservationLogResponse],
        runtime_sessions: list[RuntimeSessionViewResponse],
    ) -> TaskRuntimeGovernanceSummaryResponse:
        fallback_reasons = sorted(
            {
                reason
                for item in observations
                for reason in ([item.fallback_reason] if item.fallback_reason else [])
            }
        )
        phases = sorted({item.phase for item in observations if item.phase})
        active_agents = []
        for item in events:
            if item.agent_id and item.agent_id not in active_agents:
                active_agents.append(item.agent_id)
        agent_handoff_count = max(0, len(active_agents) - 1)
        mcp_call_count = sum(1 for item in events if item.event_type == "mcp_call_finished")
        mcp_error_count = sum(
            1
            for item in events
            if item.event_type == "mcp_call_finished" and item.event_status == "failed"
        )
        mcp_providers = sorted(
            {
                str(item.event_payload.get("provider"))
                for item in events
                if item.event_type in {"mcp_call_started", "mcp_call_finished"}
                and isinstance(item.event_payload, dict)
                and item.event_payload.get("provider")
            }
        )
        external_agent_call_count = sum(
            1 for item in events if item.event_type == "external_agent_call_finished"
        )
        external_agent_error_count = sum(
            1 for item in events if item.event_type == "external_agent_call_failed"
        )
        fallback_count = sum(1 for item in observations if item.fallback_used) + sum(
            1 for item in events if item.event_type == "runtime_fallback"
        )
        risk_flags: list[str] = []
        if fallback_count:
            risk_flags.append("runtime_fallback_detected")
        if mcp_error_count:
            risk_flags.append("mcp_error_detected")
        if external_agent_error_count:
            risk_flags.append("external_agent_error_detected")
        if agent_handoff_count > 0:
            risk_flags.append("multi_agent_handoff_detected")
        if len(runtime_sessions) > 1:
            risk_flags.append("multi_session_execution")
        collaboration_view = TaskService._build_agent_collaboration_view(
            events=events,
            runtime_sessions=runtime_sessions,
        )
        recovery_view = TaskService._build_runtime_recovery_view(
            events=events,
            observations=observations,
        )
        return TaskRuntimeGovernanceSummaryResponse(
            runtime_session_count=len(runtime_sessions),
            observation_count=len(observations),
            fallback_count=fallback_count,
            mcp_call_count=mcp_call_count,
            mcp_error_count=mcp_error_count,
            mcp_provider_count=len(mcp_providers),
            mcp_providers=mcp_providers,
            external_agent_call_count=external_agent_call_count,
            external_agent_error_count=external_agent_error_count,
            agent_handoff_count=agent_handoff_count,
            unique_agent_count=len(active_agents),
            active_agents=active_agents,
            observed_phases=phases,
            fallback_reasons=fallback_reasons,
            risk_flags=risk_flags,
            collaboration_view=collaboration_view,
            recovery_view=recovery_view,
        )

    @staticmethod
    def _build_runtime_recovery_view(
        *,
        events: list[AgentTaskEventResponse],
        observations: list[AgentObservationLogResponse],
    ) -> TaskRuntimeRecoveryViewResponse:
        fallback_reasons = sorted(
            {
                reason
                for item in observations
                for reason in ([item.fallback_reason] if item.fallback_reason else [])
            }
        )
        steps: list[AgentRecoveryStepResponse] = []
        recovery_path: list[str] = []
        retry_count = 0
        degrade_count = 0
        recovery_success_count = 0
        recovery_failed_count = 0

        for event in events:
            payload = event.event_payload if isinstance(event.event_payload, dict) else {}
            session_id = payload.get("runtime_session_id")
            if not isinstance(session_id, str) or not session_id:
                session_id = None
            source_agent_id = payload.get("previous_agent_id")
            if not isinstance(source_agent_id, str) or not source_agent_id:
                source_agent_id = None
            target_agent_id = event.agent_id

            recovery_type = ""
            if event.event_type == "runtime_fallback":
                recovery_type = "fallback"
                degrade_count += 1
            elif event.event_type == "external_agent_call_failed":
                recovery_type = "failure"
                recovery_failed_count += 1
                retry_count += int(payload.get("retry_count") or 0)
            elif event.event_type == "external_agent_call_finished" and source_agent_id:
                recovery_type = "recovered"
                recovery_success_count += 1

            if not recovery_type:
                continue

            path_marker = target_agent_id or str(payload.get("fallback") or payload.get("degrade_strategy") or event.event_type)
            if source_agent_id:
                if not recovery_path:
                    recovery_path.append(source_agent_id)
                elif recovery_path[-1] != source_agent_id:
                    recovery_path.append(source_agent_id)
            if path_marker:
                recovery_path.append(path_marker)

            if event.event_type == "runtime_fallback":
                fallback_target = str(payload.get("fallback") or "local_capability_agent")
                if fallback_target not in fallback_reasons:
                    fallback_reasons.append(fallback_target)

            steps.append(
                AgentRecoveryStepResponse(
                    order_no=len(steps) + 1,
                    event_type=event.event_type,
                    recovery_type=recovery_type,
                    title=event.title,
                    event_status=event.event_status,
                    source_agent_id=source_agent_id,
                    target_agent_id=target_agent_id,
                    session_id=session_id,
                    timestamp=event.start_time,
                    summary=event.content or "",
                    metadata=payload,
                )
            )

        fallback_count = sum(1 for item in observations if item.fallback_used) + sum(
            1 for item in events if item.event_type == "runtime_fallback"
        )
        return TaskRuntimeRecoveryViewResponse(
            fallback_count=fallback_count,
            retry_count=retry_count,
            degrade_count=degrade_count,
            recovery_success_count=recovery_success_count,
            recovery_failed_count=recovery_failed_count,
            fallback_reasons=fallback_reasons,
            recovery_path=recovery_path,
            steps=steps,
        )

    @staticmethod
    def _build_agent_collaboration_view(
        *,
        events: list[AgentTaskEventResponse],
        runtime_sessions: list[RuntimeSessionViewResponse],
    ) -> TaskAgentCollaborationViewResponse:
        session_agent_map = {
            item.session_id: item.agent_id
            for item in runtime_sessions
            if item.session_id
        }
        collaboration_event_types = {
            "agent_selected": "agent_selected",
            "agent_started": "agent_started",
            "runtime_session_started": "runtime_session_started",
            "workflow_started": "workflow_started",
            "workflow_step_registered": "workflow_step_registered",
            "mcp_call_started": "mcp_call",
            "mcp_call_finished": "mcp_call",
            "external_agent_call_started": "external_agent_call",
            "external_agent_call_finished": "external_agent_call",
            "external_agent_call_failed": "external_agent_call",
            "final_response": "final_response",
        }

        steps: list[AgentCollaborationStepResponse] = []
        collaboration_path: list[str] = []
        handoff_path: list[str] = []
        handoffs: list[AgentHandoffResponse] = []
        external_agent_step_count = 0
        mcp_step_count = 0
        route_handoff_count = 0

        def append_handoff(
            *,
            handoff_type: str,
            from_agent_id: str | None,
            from_agent_label: str,
            to_agent_id: str | None,
            to_agent_label: str,
            trigger_event_type: str,
            handoff_status: str,
            session_id: str | None,
            timestamp: str,
            summary: str,
            metadata: dict[str, Any],
        ) -> None:
            nonlocal route_handoff_count
            from_marker = from_agent_id or from_agent_label or "unknown"
            to_marker = to_agent_id or to_agent_label or "unknown"
            if not handoff_path:
                handoff_path.append(from_marker)
            if handoff_path[-1] != from_marker:
                handoff_path.append(from_marker)
            handoff_path.append(to_marker)
            if handoff_type == "routing":
                route_handoff_count += 1
            handoffs.append(
                AgentHandoffResponse(
                    order_no=len(handoffs) + 1,
                    handoff_type=handoff_type,
                    from_agent_id=from_agent_id,
                    from_agent_label=from_agent_label,
                    to_agent_id=to_agent_id,
                    to_agent_label=to_agent_label,
                    trigger_event_type=trigger_event_type,
                    handoff_status=handoff_status,
                    session_id=session_id,
                    timestamp=timestamp,
                    summary=summary,
                    metadata=metadata,
                )
            )

        for index, item in enumerate(events, start=1):
            if item.event_type not in collaboration_event_types:
                continue
            payload = item.event_payload if isinstance(item.event_payload, dict) else {}
            session_id = None
            runtime_session_id = payload.get("runtime_session_id")
            if isinstance(runtime_session_id, str) and runtime_session_id:
                session_id = runtime_session_id
            agent_id = item.agent_id or session_agent_map.get(session_id or "")
            if agent_id and (not collaboration_path or collaboration_path[-1] != agent_id):
                collaboration_path.append(agent_id)
            previous_agent_id = payload.get("previous_agent_id")
            if not isinstance(previous_agent_id, str) or not previous_agent_id:
                previous_agent_id = None
            if item.event_type.startswith("external_agent_call"):
                external_agent_step_count += 1
            if item.event_type.startswith("mcp_call"):
                mcp_step_count += 1

            if item.event_type == "agent_selected":
                selected_agent_id = (
                    payload.get("capability_id")
                    if isinstance(payload.get("capability_id"), str)
                    else agent_id
                )
                selected_agent_label = (
                    str(payload.get("capability_name") or item.content or selected_agent_id or "")
                )
                requested_agent_id = (
                    payload.get("requested_agent_id")
                    if isinstance(payload.get("requested_agent_id"), str)
                    else None
                )
                requested_agent_label = str(
                    payload.get("requested_agent_name")
                    or requested_agent_id
                    or "router"
                )
                if selected_agent_id and selected_agent_id != requested_agent_id:
                    append_handoff(
                        handoff_type="routing",
                        from_agent_id=requested_agent_id,
                        from_agent_label=requested_agent_label,
                        to_agent_id=selected_agent_id,
                        to_agent_label=selected_agent_label,
                        trigger_event_type=item.event_type,
                        handoff_status=item.event_status,
                        session_id=session_id,
                        timestamp=item.start_time,
                        summary=item.content or f"router selected {selected_agent_label}",
                        metadata=payload,
                    )

            if item.event_type == "external_agent_call_started":
                external_capability_id = (
                    payload.get("capability_id")
                    if isinstance(payload.get("capability_id"), str)
                    else agent_id
                )
                external_capability_name = str(
                    payload.get("capability_name") or external_capability_id or item.content or ""
                )
                source_agent_id = previous_agent_id
                source_agent_label = str(
                    payload.get("source_agent_name")
                    or source_agent_id
                    or "runtime"
                )
                if external_capability_id and external_capability_id != source_agent_id:
                    append_handoff(
                        handoff_type="execution",
                        from_agent_id=source_agent_id,
                        from_agent_label=source_agent_label,
                        to_agent_id=external_capability_id,
                        to_agent_label=external_capability_name,
                        trigger_event_type=item.event_type,
                        handoff_status=item.event_status,
                        session_id=session_id,
                        timestamp=item.start_time,
                        summary=item.content
                        or f"{source_agent_label} handed off to {external_capability_name}",
                        metadata=payload,
                    )

            stage_label = collaboration_event_types[item.event_type]
            summary = item.content or ""
            if not summary:
                summary = str(payload.get("summary") or payload.get("next_action") or "")
            steps.append(
                AgentCollaborationStepResponse(
                    order_no=index,
                    event_type=item.event_type,
                    title=item.title,
                    agent_id=agent_id,
                    session_id=session_id,
                    event_status=item.event_status,
                    timestamp=item.start_time,
                    stage_label=stage_label,
                    summary=summary[:240],
                )
            )

        execution_handoff_count = max(0, len(collaboration_path) - 1)
        return TaskAgentCollaborationViewResponse(
            agent_count=len(collaboration_path),
            handoff_count=execution_handoff_count,
            route_handoff_count=route_handoff_count,
            total_handoff_count=len(handoffs),
            external_agent_step_count=external_agent_step_count,
            mcp_step_count=mcp_step_count,
            collaboration_path=collaboration_path,
            handoff_path=handoff_path,
            handoffs=handoffs,
            steps=steps,
        )

    @staticmethod
    def build_output_overview(
        *,
        task_id: str,
        final_output_summary: str,
        events: list[AgentTaskEventResponse],
        artifacts: list[AgentTaskArtifactResponse],
        structured_tool_results: list[StructuredToolResultResponse],
    ) -> AgentTaskOutputOverviewResponse:
        deliverables: list[AgentTaskDeliverableResponse] = []
        next_action = ""

        final_response_event = next(
            (item for item in reversed(events) if item.event_type == "final_response"),
            None,
        )
        if final_response_event is not None:
            next_action = str(final_response_event.event_payload.get("next_action") or "")
            deliverables.append(
                AgentTaskDeliverableResponse(
                    deliverable_id=final_response_event.event_id,
                    deliverable_type="final_response",
                    title=final_response_event.title or "最终回复",
                    summary=(final_response_event.content or "")[:200],
                    content=final_response_event.content or "",
                    source_type="event",
                    source_ref=final_response_event.event_id,
                    agent_id=final_response_event.agent_id,
                    status=final_response_event.event_status,
                    metadata=final_response_event.event_payload,
                    create_time=final_response_event.start_time,
                )
            )

        for artifact in artifacts:
            deliverables.append(
                AgentTaskDeliverableResponse(
                    deliverable_id=artifact.artifact_id,
                    deliverable_type=f"artifact:{artifact.artifact_type}",
                    title=artifact.artifact_name,
                    summary=artifact.artifact_summary,
                    content=artifact.content_snapshot,
                    source_type="artifact",
                    source_ref=artifact.artifact_id,
                    status="success",
                    metadata={"is_final": artifact.is_final},
                    create_time=artifact.create_time,
                )
            )

        for result in structured_tool_results:
            deliverables.append(
                AgentTaskDeliverableResponse(
                    deliverable_id=result.tool_call_id,
                    deliverable_type=f"tool_result:{result.tool_type}",
                    title=result.tool_name,
                    summary=result.output_summary,
                    content=result.output_summary,
                    source_type="tool_call",
                    source_ref=result.tool_call_id,
                    agent_id=result.agent_id,
                    status=result.status,
                    metadata={
                        "tool_id": result.tool_id,
                        "provider": result.provider,
                        "result": result.result,
                        "request_query": result.request_query,
                    },
                    create_time=result.event_time,
                )
            )

        for event in events:
            if event.event_type not in {
                "external_agent_call_finished",
                "workflow_step_registered",
            }:
                continue
            deliverables.append(
                AgentTaskDeliverableResponse(
                    deliverable_id=event.event_id,
                    deliverable_type=event.event_type,
                    title=event.title or event.event_type,
                    summary=(event.content or "")[:200],
                    content=event.content or "",
                    source_type="event",
                    source_ref=event.event_id,
                    agent_id=event.agent_id,
                    status=event.event_status,
                    references=list(event.event_payload.get("references") or []),
                    metadata=event.event_payload,
                    create_time=event.start_time,
                )
            )

        return AgentTaskOutputOverviewResponse(
            task_id=task_id,
            total_deliverables=len(deliverables),
            final_output=final_output_summary,
            next_action=next_action,
            deliverables=deliverables,
        )

    @staticmethod
    def _to_summary(task) -> AgentTaskSummaryResponse:
        return AgentTaskSummaryResponse(
            task_id=task.task_id,
            contact_id=task.contact_id,
            user_id=task.user_id,
            biz_domain=task.biz_domain,
            selected_agent_id=task.selected_agent_id,
            status=task.status,
            current_stage=task.current_stage,
            task_title=task.task_title or "",
            task_goal=task.task_goal or "",
            risk_level=task.risk_level,
            trace_id=task.trace_id,
            start_time=task.start_time.isoformat(),
            end_time=task.end_time.isoformat() if task.end_time else None,
            duration_ms=task.duration_ms,
            final_output_summary=task.final_output_summary or "",
        )

    @staticmethod
    def _to_event(event) -> AgentTaskEventResponse:
        return AgentTaskEventResponse(
            event_id=event.event_id,
            event_type=event.event_type,
            event_seq=event.event_seq,
            title=event.title or "",
            content=event.content or "",
            event_status=event.event_status,
            visible_to_user=event.visible_to_user,
            agent_id=event.agent_id,
            start_time=event.start_time.isoformat(),
            end_time=event.end_time.isoformat() if event.end_time else None,
            duration_ms=event.duration_ms,
            event_payload=event.event_payload or {},
        )

    @staticmethod
    def _to_artifact(artifact) -> AgentTaskArtifactResponse:
        return AgentTaskArtifactResponse(
            artifact_id=artifact.artifact_id,
            artifact_type=artifact.artifact_type,
            artifact_name=artifact.artifact_name,
            artifact_summary=artifact.artifact_summary or "",
            is_final=artifact.is_final,
            visible_to_user=artifact.visible_to_user,
            content_snapshot=artifact.content_snapshot or "",
            create_time=artifact.create_time.isoformat(),
        )
