from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from app.db.session import session_scope
from app.repositories.agent_policy_repository import AgentPolicyRepository


@dataclass(frozen=True)
class AgentPolicyDecision:
    allowed: bool
    decision: str
    reason: str
    audit_required: bool = True
    matched_policy_id: str | None = None


class AgentPolicyService:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        repository: AgentPolicyRepository,
    ) -> None:
        self._session_factory = session_factory
        self._repository = repository

    def list_policies(self):
        with self._session_factory() as session:
            return self._repository.list_policies(session)

    def get_policy(self, *, agent_id: str, tenant_id: str | None = None):
        with self._session_factory() as session:
            return self._repository.get_policy(
                session,
                agent_id=agent_id,
                tenant_id=tenant_id,
            )

    def save_policy(
        self,
        *,
        agent_id: str,
        tenant_id: str | None,
        allowed_users: list[str],
        allowed_roles: list[str],
        allowed_sources: list[str],
        default_decision: str,
        rate_limit: int | None,
        audit_required: bool,
        enabled: bool,
    ):
        policy_id = f"ap_{uuid4().hex[:24]}"
        existing = self.get_policy(agent_id=agent_id, tenant_id=tenant_id)
        if existing is not None:
            policy_id = existing.policy_id
        with session_scope(self._session_factory) as session:
            return self._repository.upsert_policy(
                session,
                policy_id=policy_id,
                agent_id=agent_id,
                tenant_id=tenant_id,
                allowed_users=allowed_users,
                allowed_roles=allowed_roles,
                allowed_sources=allowed_sources,
                default_decision=default_decision,
                rate_limit=rate_limit,
                audit_required=audit_required,
                enabled=enabled,
            )

    def check_access(
        self,
        *,
        agent_id: str,
        tenant_id: str | None,
        user_id: str,
        roles: list[str],
        source: str | None,
    ) -> AgentPolicyDecision:
        policy = self.get_policy(agent_id=agent_id, tenant_id=tenant_id)
        if policy is None:
            return AgentPolicyDecision(
                allowed=True,
                decision="allow",
                reason="no_policy_configured",
                audit_required=True,
            )
        if not policy.enabled:
            return AgentPolicyDecision(
                allowed=False,
                decision="deny",
                reason="policy_disabled",
                audit_required=bool(policy.audit_required),
                matched_policy_id=policy.policy_id,
            )

        allowed_users = list(policy.allowed_users or [])
        allowed_roles = list(policy.allowed_roles or [])
        allowed_sources = list(policy.allowed_sources or [])

        if allowed_users and user_id in allowed_users:
            return AgentPolicyDecision(
                allowed=True,
                decision="allow",
                reason="user_matched",
                audit_required=bool(policy.audit_required),
                matched_policy_id=policy.policy_id,
            )
        if allowed_roles and set(roles).intersection(allowed_roles):
            return AgentPolicyDecision(
                allowed=True,
                decision="allow",
                reason="role_matched",
                audit_required=bool(policy.audit_required),
                matched_policy_id=policy.policy_id,
            )
        if allowed_sources and source and source in allowed_sources:
            return AgentPolicyDecision(
                allowed=True,
                decision="allow",
                reason="source_matched",
                audit_required=bool(policy.audit_required),
                matched_policy_id=policy.policy_id,
            )

        if policy.default_decision == "deny":
            return AgentPolicyDecision(
                allowed=False,
                decision="deny",
                reason="default_deny",
                audit_required=bool(policy.audit_required),
                matched_policy_id=policy.policy_id,
            )

        return AgentPolicyDecision(
            allowed=True,
            decision="allow",
            reason="default_allow",
            audit_required=bool(policy.audit_required),
            matched_policy_id=policy.policy_id,
        )
