from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import AgentTaskArtifactModel, AgentTaskEventModel, AgentTaskModel


class TaskRepository:
    _SORTABLE_COLUMNS = {
        "start_time": AgentTaskModel.start_time,
        "end_time": AgentTaskModel.end_time,
        "duration_ms": AgentTaskModel.duration_ms,
        "status": AgentTaskModel.status,
        "biz_domain": AgentTaskModel.biz_domain,
        "selected_agent_id": AgentTaskModel.selected_agent_id,
    }

    def create_task(
        self,
        session: Session,
        *,
        user_id: str,
        biz_domain: str,
        requested_agent_id: str | None,
        selected_agent_id: str | None,
        task_title: str,
        task_goal: str,
        input_summary: str,
        risk_level: str = "low",
    ) -> AgentTaskModel:
        task = AgentTaskModel(
            task_id=self._new_id("task"),
            contact_id=self._new_id("ct"),
            user_id=user_id,
            app_id="default",
            biz_domain=biz_domain,
            requested_agent_id=requested_agent_id,
            selected_agent_id=selected_agent_id,
            runtime_type="agentscope",
            status="running",
            current_stage="routing",
            current_agent_id=selected_agent_id,
            task_title=task_title,
            task_goal=task_goal,
            input_summary=input_summary,
            risk_level=risk_level,
            trace_id=self._new_id("trace"),
        )
        session.add(task)
        session.flush()
        return task

    def update_task_stage(
        self,
        session: Session,
        *,
        task: AgentTaskModel,
        current_stage: str,
        current_agent_id: str | None = None,
        status: str | None = None,
    ) -> AgentTaskModel:
        task.current_stage = current_stage
        if current_agent_id is not None:
            task.current_agent_id = current_agent_id
        if status is not None:
            task.status = status
        session.add(task)
        session.flush()
        return task

    def append_event(
        self,
        session: Session,
        *,
        task_id: str,
        contact_id: str,
        event_type: str,
        event_seq: int,
        title: str = "",
        content: str = "",
        event_status: str = "success",
        agent_id: str | None = None,
        artifact_id: str | None = None,
        approval_id: str | None = None,
        tool_call_id: str | None = None,
        visible_to_user: bool = True,
        event_payload: dict | None = None,
    ) -> AgentTaskEventModel:
        event = AgentTaskEventModel(
            event_id=self._new_id("evt"),
            task_id=task_id,
            contact_id=contact_id,
            event_type=event_type,
            event_seq=event_seq,
            title=title,
            content=content,
            event_status=event_status,
            agent_id=agent_id,
            artifact_id=artifact_id,
            approval_id=approval_id,
            tool_call_id=tool_call_id,
            visible_to_user=visible_to_user,
            event_payload=event_payload or {},
        )
        session.add(event)
        session.flush()
        return event

    def create_artifact(
        self,
        session: Session,
        *,
        task_id: str,
        contact_id: str,
        agent_id: str | None,
        artifact_type: str,
        artifact_name: str,
        artifact_summary: str,
        content_snapshot: str,
        is_final: bool = False,
        visible_to_user: bool = True,
    ) -> AgentTaskArtifactModel:
        artifact = AgentTaskArtifactModel(
            artifact_id=self._new_id("art"),
            task_id=task_id,
            contact_id=contact_id,
            agent_id=agent_id,
            artifact_type=artifact_type,
            artifact_name=artifact_name,
            artifact_summary=artifact_summary,
            content_snapshot=content_snapshot,
            is_final=is_final,
            visible_to_user=visible_to_user,
        )
        session.add(artifact)
        session.flush()
        return artifact

    def mark_waiting_approval(
        self,
        session: Session,
        *,
        task: AgentTaskModel,
        approval_id: str,
        final_output_summary: str | None = None,
    ) -> AgentTaskModel:
        task.status = "waiting_approval"
        task.current_stage = "approval"
        task.approval_required = True
        task.approval_id = approval_id
        if final_output_summary is not None:
            task.final_output_summary = final_output_summary
        session.add(task)
        session.flush()
        return task

    def complete_task(
        self,
        session: Session,
        *,
        task: AgentTaskModel,
        final_output_summary: str,
        status: str = "success",
    ) -> AgentTaskModel:
        now = datetime.utcnow()
        task.status = status
        task.current_stage = "completed" if status == "success" else "failed"
        task.final_output_summary = final_output_summary
        task.end_time = now
        task.duration_ms = max(0, int((now - task.start_time).total_seconds() * 1000))
        session.add(task)
        session.flush()
        return task

    def list_tasks(
        self,
        session: Session,
        *,
        status: str | None = None,
        biz_domain: str | None = None,
        selected_agent_id: str | None = None,
        start_time_from: datetime | None = None,
        start_time_to: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
        sort_by: str = "start_time",
        sort_order: str = "desc",
    ) -> List[AgentTaskModel]:
        query = self._apply_task_filters(
            session.query(AgentTaskModel),
            status=status,
            biz_domain=biz_domain,
            selected_agent_id=selected_agent_id,
            start_time_from=start_time_from,
            start_time_to=start_time_to,
        )
        sort_column = self._SORTABLE_COLUMNS.get(sort_by, AgentTaskModel.start_time)
        is_asc = sort_order.lower() == "asc"
        ordered_query = query.order_by(
            sort_column.asc() if is_asc else sort_column.desc(),
            AgentTaskModel.task_id.asc() if is_asc else AgentTaskModel.task_id.desc(),
        )
        return ordered_query.offset(max(0, offset)).limit(limit).all()

    def count_tasks(
        self,
        session: Session,
        *,
        status: str | None = None,
        biz_domain: str | None = None,
        selected_agent_id: str | None = None,
        start_time_from: datetime | None = None,
        start_time_to: datetime | None = None,
    ) -> int:
        query = self._apply_task_filters(
            session.query(func.count(AgentTaskModel.task_id)),
            status=status,
            biz_domain=biz_domain,
            selected_agent_id=selected_agent_id,
            start_time_from=start_time_from,
            start_time_to=start_time_to,
        )
        return int(query.scalar() or 0)

    def get_task(self, session: Session, task_id: str) -> AgentTaskModel | None:
        return session.get(AgentTaskModel, task_id)

    def list_events(self, session: Session, task_id: str) -> List[AgentTaskEventModel]:
        return (
            session.query(AgentTaskEventModel)
            .filter(AgentTaskEventModel.task_id == task_id)
            .order_by(AgentTaskEventModel.event_seq.asc())
            .all()
        )

    def list_events_after(
        self,
        session: Session,
        task_id: str,
        after_seq: int,
    ) -> List[AgentTaskEventModel]:
        return (
            session.query(AgentTaskEventModel)
            .filter(AgentTaskEventModel.task_id == task_id)
            .filter(AgentTaskEventModel.event_seq > after_seq)
            .order_by(AgentTaskEventModel.event_seq.asc())
            .all()
        )

    def list_artifacts(
        self,
        session: Session,
        task_id: str,
    ) -> List[AgentTaskArtifactModel]:
        return (
            session.query(AgentTaskArtifactModel)
            .filter(AgentTaskArtifactModel.task_id == task_id)
            .order_by(AgentTaskArtifactModel.create_time.asc())
            .all()
        )

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:24]}"

    @staticmethod
    def _apply_task_filters(
        query,
        *,
        status: str | None,
        biz_domain: str | None,
        selected_agent_id: str | None,
        start_time_from: datetime | None,
        start_time_to: datetime | None,
    ):
        if status:
            query = query.filter(AgentTaskModel.status == status)
        if biz_domain:
            query = query.filter(AgentTaskModel.biz_domain == biz_domain)
        if selected_agent_id:
            query = query.filter(AgentTaskModel.selected_agent_id == selected_agent_id)
        if start_time_from is not None:
            query = query.filter(AgentTaskModel.start_time >= start_time_from)
        if start_time_to is not None:
            query = query.filter(AgentTaskModel.start_time <= start_time_to)
        return query
