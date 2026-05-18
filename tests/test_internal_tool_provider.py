from __future__ import annotations

from typing import Any

import pytest

from app.config import get_settings
from app.dependencies import get_internal_tool_provider
from app.services.internal_tool_http_provider import HttpInternalToolProvider


class StubHttpProvider(HttpInternalToolProvider):
    def __init__(self, responses: dict[tuple[str, str], dict[str, Any]]) -> None:
        super().__init__(base_url="http://provider.test", timeout_seconds=3.0, bearer_token="t")
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def _request_json(
        self,
        *,
        method: str,
        path: str,
        query_params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "method": method,
                "path": path,
                "query_params": query_params or {},
                "body": body or {},
            }
        )
        return self.responses[(method, path)]


def test_http_internal_tool_provider_supports_get_and_post_contracts() -> None:
    provider = StubHttpProvider(
        responses={
            ("GET", "/merchant/profile"): {
                "merchant_id": "M100001",
                "merchant_name": "示例商户",
                "status": "active",
                "risk_level": "low",
                "industry_code": "retail",
                "contact_name": "张三",
                "contact_phone": "13800000000",
                "register_time": "2026-05-18T10:00:00",
            },
            ("POST", "/operations/service-tickets"): {
                "ticket_id": "TCK-0001",
                "merchant_id": "M100001",
                "status": "submitted",
                "category": "settlement",
                "priority": "high",
            },
        }
    )

    profile = provider.query_merchant_profile(merchant_id="M100001")
    ticket = provider.submit_service_ticket(
        ticket_id="TCK-0001",
        merchant_id="M100001",
        requested_by="u001",
        category="settlement",
        priority="high",
        title="结算异常排查",
        description="需要人工核查",
        payload={"source": "agent"},
    )

    assert profile is not None
    assert profile.merchant_id == "M100001"
    assert profile.merchant_name == "示例商户"
    assert ticket.ticket_id == "TCK-0001"
    assert ticket.category == "settlement"
    assert ticket.priority == "high"

    assert provider.calls[0] == {
        "method": "GET",
        "path": "/merchant/profile",
        "query_params": {"merchant_id": "M100001"},
        "body": {},
    }
    assert provider.calls[1]["method"] == "POST"
    assert provider.calls[1]["path"] == "/operations/service-tickets"
    assert provider.calls[1]["body"]["requested_by"] == "u001"
    assert provider.calls[1]["body"]["payload"] == {"source": "agent"}


def test_dependency_factory_supports_http_internal_tool_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACQUIRING_AI_INTERNAL_TOOL_PROVIDER_BACKEND", "http_adapter")
    monkeypatch.setenv("ACQUIRING_AI_INTERNAL_TOOL_HTTP_BASE_URL", "http://remote-provider.test")
    monkeypatch.setenv("ACQUIRING_AI_INTERNAL_TOOL_HTTP_TIMEOUT_SECONDS", "5")
    monkeypatch.setenv("ACQUIRING_AI_INTERNAL_TOOL_HTTP_BEARER_TOKEN", "secret-token")

    get_settings.cache_clear()
    get_internal_tool_provider.cache_clear()
    provider = get_internal_tool_provider()

    assert isinstance(provider, HttpInternalToolProvider)
    assert provider._base_url == "http://remote-provider.test"
    assert provider._timeout_seconds == 5.0
    assert provider._bearer_token == "secret-token"

    get_internal_tool_provider.cache_clear()
    get_settings.cache_clear()


def test_dependency_factory_rejects_http_provider_without_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ACQUIRING_AI_INTERNAL_TOOL_PROVIDER_BACKEND", "http_adapter")
    monkeypatch.delenv("ACQUIRING_AI_INTERNAL_TOOL_HTTP_BASE_URL", raising=False)

    get_settings.cache_clear()
    get_internal_tool_provider.cache_clear()

    with pytest.raises(ValueError, match="INTERNAL_TOOL_HTTP_BASE_URL"):
        get_internal_tool_provider()

    get_internal_tool_provider.cache_clear()
    get_settings.cache_clear()
