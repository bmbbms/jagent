from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import AgentPolicyModel


class AgentPolicyRepository:
    def list_policies(self, session: Session) -> list[AgentPolicyModel]:
        return (
            session.query(AgentPolicyModel)
            .order_by(AgentPolicyModel.agent_id.asc(), AgentPolicyModel.tenant_id.asc())
            .all()
        )

    def get_policy(
        self,
        session: Session,
        *,
        agent_id: str,
        tenant_id: str | None = None,
    ) -> AgentPolicyModel | None:
        query = session.query(AgentPolicyModel).filter(
            AgentPolicyModel.agent_id == agent_id
        )
        if tenant_id:
            scoped = query.filter(AgentPolicyModel.tenant_id == tenant_id).first()
            if scoped is not None:
                return scoped
        return query.filter(AgentPolicyModel.tenant_id.is_(None)).first()

    def upsert_policy(
        self,
        session: Session,
        *,
        policy_id: str,
        agent_id: str,
        tenant_id: str | None,
        allowed_users: list[str],
        allowed_roles: list[str],
        allowed_sources: list[str],
        default_decision: str,
        rate_limit: int | None,
        audit_required: bool,
        enabled: bool,
    ) -> AgentPolicyModel:
        item = session.get(AgentPolicyModel, policy_id)
        if item is None:
            item = AgentPolicyModel(policy_id=policy_id)
            session.add(item)
            item.create_time = datetime.utcnow()
        item.agent_id = agent_id
        item.tenant_id = tenant_id
        item.allowed_users = allowed_users
        item.allowed_roles = allowed_roles
        item.allowed_sources = allowed_sources
        item.default_decision = default_decision
        item.rate_limit = rate_limit
        item.audit_required = audit_required
        item.enabled = enabled
        item.update_time = datetime.utcnow()
        session.flush()
        return item
