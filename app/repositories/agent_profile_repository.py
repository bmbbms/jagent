from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import (
    AgentDeclaredMCPModel,
    AgentDeclaredSkillModel,
    AgentDeclaredWorkflowModel,
    AgentProfileModel,
    AgentProfileSyncLogModel,
)


class AgentProfileRepository:
    def list_profiles(
        self,
        session: Session,
        *,
        biz_domain: str | None = None,
        enabled: bool | None = None,
    ) -> list[AgentProfileModel]:
        query = session.query(AgentProfileModel)
        if biz_domain:
            query = query.filter(AgentProfileModel.biz_domain == biz_domain)
        if enabled is not None:
            query = query.filter(AgentProfileModel.enabled.is_(enabled))
        return query.order_by(
            AgentProfileModel.biz_domain.asc(),
            AgentProfileModel.agent_name.asc(),
        ).all()

    def get_profile(self, session: Session, agent_id: str) -> AgentProfileModel | None:
        return session.get(AgentProfileModel, agent_id)

    def list_declared_skills(
        self,
        session: Session,
        agent_id: str,
    ) -> list[AgentDeclaredSkillModel]:
        return (
            session.query(AgentDeclaredSkillModel)
            .filter(AgentDeclaredSkillModel.agent_id == agent_id)
            .order_by(AgentDeclaredSkillModel.skill_id.asc())
            .all()
        )

    def list_declared_mcps(
        self,
        session: Session,
        agent_id: str,
    ) -> list[AgentDeclaredMCPModel]:
        return (
            session.query(AgentDeclaredMCPModel)
            .filter(AgentDeclaredMCPModel.agent_id == agent_id)
            .order_by(AgentDeclaredMCPModel.mcp_id.asc())
            .all()
        )

    def list_declared_workflows(
        self,
        session: Session,
        agent_id: str,
    ) -> list[AgentDeclaredWorkflowModel]:
        return (
            session.query(AgentDeclaredWorkflowModel)
            .filter(AgentDeclaredWorkflowModel.agent_id == agent_id)
            .order_by(AgentDeclaredWorkflowModel.workflow_id.asc())
            .all()
        )

    def upsert_profile(
        self,
        session: Session,
        *,
        profile: dict[str, Any],
        skills: list[dict[str, Any]],
        mcps: list[dict[str, Any]],
        workflows: list[dict[str, Any]],
        sync_time: datetime,
    ) -> AgentProfileModel:
        agent_id = str(profile["agent_id"])
        item = session.get(AgentProfileModel, agent_id)
        if item is None:
            item = AgentProfileModel(agent_id=agent_id)
            session.add(item)

        for key, value in profile.items():
            setattr(item, key, value)
        item.last_sync_time = sync_time
        item.enabled = True

        self._replace_declared_skills(session, agent_id=agent_id, skills=skills)
        self._replace_declared_mcps(session, agent_id=agent_id, mcps=mcps)
        self._replace_declared_workflows(
            session,
            agent_id=agent_id,
            workflows=workflows,
        )
        session.flush()
        return item

    def create_sync_log(
        self,
        session: Session,
        *,
        sync_id: str,
        namespace: str,
        source: str,
        start_time: datetime,
    ) -> AgentProfileSyncLogModel:
        item = AgentProfileSyncLogModel(
            sync_id=sync_id,
            namespace=namespace,
            source=source,
            status="running",
            pulled_count=0,
            upserted_count=0,
            failed_count=0,
            start_time=start_time,
        )
        session.add(item)
        session.flush()
        return item

    def finish_sync_log(
        self,
        session: Session,
        *,
        sync_id: str,
        status: str,
        pulled_count: int,
        upserted_count: int,
        failed_count: int,
        end_time: datetime,
        error_message: str | None = None,
    ) -> AgentProfileSyncLogModel:
        item = session.get(AgentProfileSyncLogModel, sync_id)
        if item is None:
            item = AgentProfileSyncLogModel(sync_id=sync_id)
            session.add(item)
        item.status = status
        item.pulled_count = pulled_count
        item.upserted_count = upserted_count
        item.failed_count = failed_count
        item.error_message = error_message
        item.end_time = end_time
        session.flush()
        return item

    def list_sync_logs(
        self,
        session: Session,
        *,
        limit: int = 20,
    ) -> list[AgentProfileSyncLogModel]:
        return (
            session.query(AgentProfileSyncLogModel)
            .order_by(AgentProfileSyncLogModel.start_time.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def _replace_declared_skills(
        session: Session,
        *,
        agent_id: str,
        skills: list[dict[str, Any]],
    ) -> None:
        session.query(AgentDeclaredSkillModel).filter(
            AgentDeclaredSkillModel.agent_id == agent_id
        ).delete(synchronize_session=False)
        for payload in skills:
            session.add(AgentDeclaredSkillModel(agent_id=agent_id, **payload))

    @staticmethod
    def _replace_declared_mcps(
        session: Session,
        *,
        agent_id: str,
        mcps: list[dict[str, Any]],
    ) -> None:
        session.query(AgentDeclaredMCPModel).filter(
            AgentDeclaredMCPModel.agent_id == agent_id
        ).delete(synchronize_session=False)
        for payload in mcps:
            session.add(AgentDeclaredMCPModel(agent_id=agent_id, **payload))

    @staticmethod
    def _replace_declared_workflows(
        session: Session,
        *,
        agent_id: str,
        workflows: list[dict[str, Any]],
    ) -> None:
        session.query(AgentDeclaredWorkflowModel).filter(
            AgentDeclaredWorkflowModel.agent_id == agent_id
        ).delete(synchronize_session=False)
        for payload in workflows:
            session.add(AgentDeclaredWorkflowModel(agent_id=agent_id, **payload))
