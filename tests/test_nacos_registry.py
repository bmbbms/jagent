from __future__ import annotations

import json
from unittest.mock import patch

from app.config import Settings
from app.registry.base import CapabilityMetadata
from app.registry.nacos_ai_client import NacosAiHttpClient
from app.registry.nacos_registry import NacosCapabilityRegistry
from app.schemas import BizDomain, ChatRequest


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
