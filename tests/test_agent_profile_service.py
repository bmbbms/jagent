from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db import models  # noqa: F401
from app.db.base import Base
from app.repositories.agent_profile_repository import AgentProfileRepository
from app.services.agent_profile_service import AgentProfileSyncService


class _FakeNacosClient:
    def __init__(self, cards: list[dict]) -> None:
        self._cards = cards

    def list_agent_cards(self, *, page_size: int = 100):  # noqa: ANN001
        return self._cards


def _build_service(cards: list[dict]) -> AgentProfileSyncService:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )
    return AgentProfileSyncService(
        settings=Settings(
            nacos_ai_enabled=True,
            nacos_ai_namespace="public",
            nacos_ai_server_address="http://127.0.0.1:8848",
        ),
        session_factory=session_factory,
        repository=AgentProfileRepository(),
        client=_FakeNacosClient(cards),
    )


def test_agent_profile_sync_preserves_declared_capabilities() -> None:
    service = _build_service(
        [
            {
                "name": "payment-regulation-agent",
                "description": "regulation assistant",
                "protocolVersion": "0.3.0",
                "version": "1.0.0",
                "supportedInterfaces": [
                    {"transport": "JSONRPC", "url": "http://127.0.0.1:9000/a2a"}
                ],
                "skills": [
                    {
                        "id": "dialog",
                        "name": "Natural Language Dialog",
                        "description": "dialog skill",
                        "tags": ["conversation"],
                    }
                ],
                "metadata": {
                    "biz_domain": "merchant",
                    "tags": ["regulation", "knowledge"],
                    "mcps": [
                        {
                            "id": "policy_search_mcp",
                            "name": "Policy Search MCP",
                            "transport": "sse",
                            "endpoint": "http://127.0.0.1:9100/mcp",
                        }
                    ],
                    "workflows": [
                        {
                            "id": "regulation_review_flow",
                            "name": "Regulation Review Flow",
                            "steps": ["search", "answer"],
                        }
                    ],
                },
            }
        ]
    )

    result = service.sync_from_nacos()
    assert result["status"] == "success"
    assert result["pulled_count"] == 1
    assert result["upserted_count"] == 1

    profiles = service.list_profiles()
    assert len(profiles) == 1
    assert profiles[0].agent_id == "nacos.merchant.payment.regulation.agent"
    assert profiles[0].endpoint == "http://127.0.0.1:9000/a2a"
    assert profiles[0].tags == ["regulation", "knowledge"]

    bundle = service.get_profile_bundle(profiles[0].agent_id)
    assert bundle is not None
    assert [item.skill_id for item in bundle["skills"]] == ["dialog"]
    assert [item.mcp_id for item in bundle["mcps"]] == ["policy_search_mcp"]
    assert [item.workflow_id for item in bundle["workflows"]] == [
        "regulation_review_flow"
    ]


def test_agent_profile_sync_handles_missing_metadata() -> None:
    service = _build_service(
        [
            {
                "name": "weath-agent",
                "description": "weather agent",
                "version": "1.0.0",
                "skills": [],
            }
        ]
    )

    result = service.sync_from_nacos()
    assert result["status"] == "success"
    profiles = service.list_profiles()
    assert len(profiles) == 1
    assert profiles[0].agent_id == "nacos.merchant.weath.agent"
    assert profiles[0].biz_domain == "merchant"
    assert profiles[0].raw_card["name"] == "weath-agent"
