from __future__ import annotations

import json
from unittest.mock import patch

from app.config import Settings
from app.registry.base import CapabilityMetadata
from app.registry.nacos_ai_client import NacosAiHttpClient
from app.registry.nacos_registry import NacosCapabilityRegistry
from app.schemas import BizDomain, ChatRequest
from app.services.nacos_registry_service import NacosRegistryService
from app.services.skill_catalog_service import SkillCatalogService
from app.services.skill_registry import SkillRegistry


def test_nacos_registry_can_register_and_resolve_local_cache() -> None:
    registry = NacosCapabilityRegistry(
        Settings(
            nacos_ai_enabled=False,
            nacos_ai_server_address="http://127.0.0.1:8848",
        )
    )
    metadata = CapabilityMetadata(
        capability_id="merchant.review.agent",
        capability_name="Merchant Review Agent",
        biz_domain=BizDomain.merchant,
        description="review",
        priority=1,
        triggers=["review"],
        skills=["merchant_review"],
        transport="a2a",
        endpoint="http://127.0.0.1:8001/a2a",
        service_path="/a2a",
    )
    registry.register_remote(metadata)

    items = registry.describe_capabilities()
    assert items[0].capability_id == "merchant.review.agent"

    resolved = registry.resolve(
        ChatRequest(
            user_id="u1",
            biz_domain=BizDomain.merchant,
            message="please review",
        )
    )
    assert resolved.definition.capability_id == "merchant.review.agent"


def test_nacos_registry_supports_unregister() -> None:
    registry = NacosCapabilityRegistry(
        Settings(
            nacos_ai_enabled=False,
            nacos_ai_server_address="http://127.0.0.1:8848",
        )
    )
    metadata = CapabilityMetadata(
        capability_id="operations.quota.agent",
        capability_name="Operations Quota Agent",
        biz_domain=BizDomain.operations,
        description="quota",
        priority=1,
        transport="http",
        endpoint="http://127.0.0.1:8002/api/chat",
    )
    registry.register_remote(metadata)
    assert registry.unregister_remote("operations.quota.agent") is True
    assert registry.list_capabilities() == []


class _FakeResponse:
    def __init__(self, payload: str) -> None:
        self._payload = payload.encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_nacos_ai_client_refreshes_access_token() -> None:
    requests: list[str] = []

    def fake_urlopen(request, timeout=0):  # noqa: ANN001
        requests.append(request.full_url)
        if request.full_url.endswith("/nacos/v1/auth/users/login"):
            return _FakeResponse(json.dumps({"accessToken": "token-123"}))
        auth = request.headers.get("Authorization")
        assert auth == "Bearer token-123"
        return _FakeResponse(json.dumps({"code": 0, "message": "success", "data": []}))

    client = NacosAiHttpClient(
        "http://127.0.0.1:8848",
        username="nacos",
        password="secret",
    )
    with patch("app.registry.nacos_ai_client.urlopen", side_effect=fake_urlopen):
        result = client.list_agent_cards(page_size=5)
    assert result == []
    assert requests[0].endswith("/nacos/v1/auth/users/login")


def test_nacos_registry_treats_conflict_as_idempotent() -> None:
    registry = NacosCapabilityRegistry(
        Settings(
            nacos_ai_enabled=True,
            nacos_ai_server_address="http://127.0.0.1:8848",
        )
    )
    metadata = CapabilityMetadata(
        capability_id="merchant.review.agent",
        capability_name="Merchant Review Agent",
        biz_domain=BizDomain.merchant,
        description="review",
        priority=1,
        transport="http",
        endpoint="http://127.0.0.1:8001",
        service_path="/api/chat",
    )

    with patch.object(
        registry._client,
        "publish_agent_card",
        return_value=type("R", (), {"code": 20005, "message": "resource conflict"})(),
    ):
        registry.register_remote(metadata)

    assert "merchant.review.agent" in registry._local_cache


def test_nacos_registry_does_not_publish_local_agents_by_default() -> None:
    registry = NacosCapabilityRegistry(
        Settings(
            nacos_ai_enabled=True,
            nacos_ai_publish_local_agents=False,
            nacos_ai_server_address="http://127.0.0.1:8848",
        )
    )

    class _FakeAgent:
        definition = type(
            "Definition",
            (),
            {
                "capability_id": "merchant.test.agent",
                "name": "Merchant Test Agent",
                "biz_domain": BizDomain.merchant,
                "description": "test",
                "priority": 1,
                "triggers": [],
                "skills": [],
                "version": "v1",
                "risk_level": "low",
                "requires_approval": False,
                "tags": [],
                "transport": "inproc",
                "endpoint": None,
                "service_name": None,
                "service_host": None,
                "service_port": None,
                "service_path": "/api/chat",
                "extras": {},
            },
        )()

    with patch.object(registry, "_publish_agent_card") as mocked_publish:
        registry.register_local(_FakeAgent())
    mocked_publish.assert_not_called()


def test_nacos_registry_maps_remote_agent_without_capability_metadata() -> None:
    registry = NacosCapabilityRegistry(
        Settings(
            nacos_ai_enabled=True,
            nacos_ai_server_address="http://127.0.0.1:8848",
        )
    )
    remote_cards = [
        {
            "name": "payment-regulation-agent",
            "description": "desc",
            "supportedInterfaces": [
                {"transport": "JSONRPC", "url": "http://127.0.0.1:9000/a2a"}
            ],
            "skills": [{"id": "dialog", "name": "dialog"}],
            "metadata": {},
        }
    ]
    with patch.object(registry, "_load_remote_agent_cards") as mocked_loader:
        mocked_loader.return_value = [
            registry._from_agent_card(remote_cards[0])  # noqa: SLF001
        ]
        items = registry.describe_capabilities()
    assert items
    assert items[0].capability_id == "nacos.merchant.payment.regulation.agent"
    assert items[0].service_path == "/a2a"
    assert items[0].priority == 1000


def test_nacos_registry_service_maps_remote_skills() -> None:
    service = NacosRegistryService(
        Settings(
            nacos_ai_enabled=True,
            nacos_ai_server_address="http://127.0.0.1:8848",
        ),
        SkillRegistry([]),
    )
    remote_skills = [
        {
            "name": "dialog",
            "description": "Supports natural language chat",
            "version": "1.0.0",
            "metadata": {
                "biz_domain": "operations",
                "allowed_tools": ["merchant_profile_query"],
                "human_escalation": ["missing_customer_context"],
                "required_inputs": ["merchant_id"],
                "steps": ["analyze", "answer"],
            },
        }
    ]

    with patch.object(service, "_safe_list_skills", return_value=remote_skills):
        items = service.list_remote_skill_infos(
            biz_domain=BizDomain.operations,
            allowed_tool="merchant_profile_query",
            has_human_escalation=True,
        )

    assert len(items) == 1
    assert items[0].skill_id == "dialog"
    assert items[0].biz_domain == BizDomain.operations
    assert items[0].path == "nacos://skills/dialog:1.0.0"


def test_nacos_registry_service_maps_remote_mcp_servers() -> None:
    service = NacosRegistryService(
        Settings(
            nacos_ai_enabled=True,
            nacos_ai_server_address="http://127.0.0.1:8848",
        ),
        SkillRegistry([]),
    )
    remote_servers = [
        {
            "name": "risk-engine",
            "description": "Risk scoring MCP",
            "transportType": "sse",
            "version": "1.0.1",
            "url": "http://127.0.0.1:9001/mcp",
        }
    ]

    with patch.object(service, "_safe_list_mcp_servers", return_value=remote_servers):
        items = service.list_remote_mcp_tools(
            {"nacos_mcp_risk_engine": {"call_count": 2, "success_count": 2}}
        )

    assert len(items) == 1
    assert items[0].tool_id == "nacos_mcp_risk_engine"
    assert items[0].transport == "sse"
    assert items[0].command == "http://127.0.0.1:9001/mcp"
    assert items[0].config_path == "nacos://mcp/risk-engine:1.0.1"
    assert items[0].call_count == 2


def test_skill_catalog_service_merges_local_and_remote_skills() -> None:
    local_registry = SkillRegistry([])
    nacos_service = NacosRegistryService(
        Settings(
            nacos_ai_enabled=True,
            nacos_ai_server_address="http://127.0.0.1:8848",
        ),
        local_registry,
    )
    catalog = SkillCatalogService(
        registry=local_registry,
        nacos_registry_service=nacos_service,
    )

    remote_items = [
        type(
            "RemoteSkill",
            (),
            {
                "skill_id": "remote_dialog",
                "biz_domain": BizDomain.merchant,
                "name": "Remote Dialog",
                "path": "nacos://skills/remote_dialog",
                "purpose": "remote",
                "when_to_use": [],
            },
        )()
    ]
    remote_detail = type(
        "RemoteDetail",
        (),
        {
            "skill_id": "remote_dialog",
            "biz_domain": BizDomain.merchant,
            "name": "Remote Dialog",
            "path": "nacos://skills/remote_dialog",
            "purpose": "remote",
            "when_to_use": [],
            "required_inputs": [],
            "steps": [],
            "output_fields": [],
            "allowed_tools": [],
            "human_escalation": [],
        },
    )()

    with (
        patch.object(nacos_service, "list_remote_skill_infos", return_value=remote_items),
        patch.object(nacos_service, "get_remote_skill_detail", return_value=remote_detail),
    ):
        items = catalog.list_skills(BizDomain.merchant)
        detail = catalog.get_skill("remote_dialog")

    assert [item.skill_id for item in items] == ["remote_dialog"]
    assert detail is remote_detail
