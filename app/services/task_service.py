from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.db.session import session_scope
from app.repositories.task_repository import TaskRepository
from app.schemas import (
    AgentTaskArtifactResponse,
    AgentTaskDetailResponse,
    AgentTaskEventResponse,
    AgentTaskListResponse,
    AgentObservationLogResponse,
    AgentTaskSummaryResponse,
    ApprovalStatus,
    ChatRequest,
    ChatResponse,
    DataAccessLogResponse,
    RuntimeSessionViewResponse,
    StructuredToolResultResponse,
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
        approval_id: str | None = None,
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
                approval_id=approval_id,
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
        approval_id: str | None = None,
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

        if approval_id:
            self._mark_task_waiting_approval(
                task_id=task_id,
                approval_id=approval_id,
                final_output_summary=response.summary,
            )
            self.emit_runtime_event(
                task_id=task_id,
                event_type="approval_requested",
                title="任务等待审批",
                content=f"审批单号：{approval_id}",
                event_status="waiting",
                agent_id=response.capability_id,
                approval_id=approval_id,
                event_payload={"approval_id": approval_id},
                current_stage="approval",
                task_status="waiting_approval",
            )
        else:
            self._complete_task(
                task_id=task_id,
                final_output_summary=response.summary,
                status="success",
            )

        return contact_id

    def resolve_approval_task(
        self,
        *,
        approval_id: str,
        approval_status: ApprovalStatus,
        reviewer_id: str,
        comment: str,
    ) -> str | None:
        with session_scope(self._session_factory) as session:
            tasks = self._repository.list_tasks(session, limit=200)
            target = next((item for item in tasks if item.approval_id == approval_id), None)
            if target is None:
                return None

            event_count = len(self._repository.list_events(session, target.task_id))
            self._repository.append_event(
                session,
                task_id=target.task_id,
                contact_id=target.contact_id,
                event_type="approval_finished",
                event_seq=event_count + 1,
                title="审批已完成",
                content=approval_status.value,
                agent_id=target.selected_agent_id,
                approval_id=approval_id,
                event_payload={
                    "reviewer_id": reviewer_id,
                    "comment": comment,
                    "status": approval_status.value,
                },
            )

            self._repository.complete_task(
                session,
                task=target,
                final_output_summary=target.final_output_summary or "",
                status="success" if approval_status == ApprovalStatus.approved else "failed",
            )
            return target.task_id

    def list_tasks(
        self,
        *,
        status: str | None = None,
        biz_domain: str | None = None,
        selected_agent_id: str | None = None,
        risk_level: str | None = None,
        current_stage: str | None = None,
        approval_id: str | None = None,
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
                approval_id=approval_id,
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
                    approval_id=approval_id,
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
            data["runtime_sessions"] = [
                item.model_dump()
                for item in self._build_runtime_sessions(
                    observations=observation_items,
                    tool_calls=tool_call_items,
                    data_access_logs=data_access_items,
                )
            ]
            return AgentTaskDetailResponse(**data)

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

    def _mark_task_waiting_approval(
        self,
        *,
        task_id: str,
        approval_id: str,
        final_output_summary: str,
    ) -> None:
        with session_scope(self._session_factory) as session:
            task = self._repository.get_task(session, task_id)
            if task is None:
                return
            self._repository.mark_waiting_approval(
                session,
                task=task,
                approval_id=approval_id,
                final_output_summary=final_output_summary,
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
            approval_required=task.approval_required,
            approval_id=task.approval_id,
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
