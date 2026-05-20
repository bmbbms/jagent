from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db import models  # noqa: F401
from app.db.base import Base
from app.repositories.agent_policy_repository import AgentPolicyRepository
from app.repositories.agent_profile_repository import AgentProfileRepository
from app.services.agent_gateway_routing_service import AgentGatewayRoutingService
from app.services.agent_policy_service import AgentPolicyService
from app.services.agent_profile_service import AgentProfileSyncService


class _FakeNacosClient:
    def __init__(self, cards: list[dict]) -> None:
        self._cards = cards

    def list_agent_cards(self, *, page_size: int = 100):  # noqa: ANN001
        return self._cards


def _build_services(cards: list[dict]):
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )
    profile_service = AgentProfileSyncService(
        settings=Settings(
            nacos_ai_enabled=True,
            nacos_ai_namespace="public",
            nacos_ai_server_address="http://127.0.0.1:8848",
        ),
        session_factory=session_factory,
        repository=AgentProfileRepository(),
        client=_FakeNacosClient(cards),
    )
    policy_service = AgentPolicyService(
        session_factory=session_factory,
        repository=AgentPolicyRepository(),
    )
    routing_service = AgentGatewayRoutingService(
        agent_profile_service=profile_service,
        agent_policy_service=policy_service,
    )
    return profile_service, policy_service, routing_service


def test_agent_policy_denies_by_default_when_configured() -> None:
    _, policy_service, _ = _build_services([])
    policy = policy_service.save_policy(
        agent_id="nacos.merchant.payment.regulation.agent",
        tenant_id=None,
        allowed_users=[],
        allowed_roles=["risk_admin"],
        allowed_sources=[],
        default_decision="deny",
        rate_limit=None,
        audit_required=True,
        enabled=True,
    )
    decision = policy_service.check_access(
        agent_id=policy.agent_id,
        tenant_id=None,
        user_id="u1",
        roles=["guest"],
        source="api",
    )
    assert decision.allowed is False
    assert decision.decision == "deny"
    assert decision.reason == "default_deny"


def test_agent_gateway_route_respects_policy_and_skill_match() -> None:
    profile_service, policy_service, routing_service = _build_services(
        [
            {
                "name": "payment-regulation-agent",
                "description": "handles regulation and compliance",
                "version": "1.0.0",
                "skills": [
                    {
                        "id": "regulation_query",
                        "name": "Regulation Query",
                        "description": "query regulation rules",
                    }
                ],
                "metadata": {"biz_domain": "merchant", "tags": ["regulation"]},
            },
            {
                "name": "merchant-ops-agent",
                "description": "handles merchant operations",
                "version": "1.0.0",
                "skills": [
                    {
                        "id": "ops_review",
                        "name": "Ops Review",
                        "description": "merchant operations review",
                    }
                ],
                "metadata": {"biz_domain": "merchant", "tags": ["operations"]},
            },
        ]
    )
    profile_service.sync_from_nacos()
    policy_service.save_policy(
        agent_id="nacos.merchant.payment.regulation.agent",
        tenant_id=None,
        allowed_users=[],
        allowed_roles=["risk_admin"],
        allowed_sources=[],
        default_decision="deny",
        rate_limit=None,
        audit_required=True,
        enabled=True,
    )
    policy_service.save_policy(
        agent_id="nacos.merchant.merchant.ops.agent",
        tenant_id=None,
        allowed_users=[],
        allowed_roles=[],
        allowed_sources=[],
        default_decision="allow",
        rate_limit=None,
        audit_required=True,
        enabled=True,
    )

    denied_payload = routing_service.explain_route(
        user_id="u1",
        biz_domain="merchant",
        message="请帮我查询 regulation rule",
        tenant_id=None,
        roles=["guest"],
        source="api",
    )
    assert denied_payload["selected_agent_id"] == "nacos.merchant.merchant.ops.agent"
    assert denied_payload["filtered_candidates"][0]["agent_id"] == "nacos.merchant.payment.regulation.agent"

    allowed_payload = routing_service.explain_route(
        user_id="u2",
        biz_domain="merchant",
        message="请帮我查询 regulation rule",
        tenant_id=None,
        roles=["risk_admin"],
        source="api",
    )
    assert allowed_payload["selected_agent_id"] == "nacos.merchant.payment.regulation.agent"
    assert "regulation_query" in allowed_payload["matched_skill_ids"]
    assert "requested_agent_matched" not in allowed_payload["route_reason"]
