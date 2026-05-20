from __future__ import annotations

from app.config import Settings
from app.registry.base import CapabilityMetadata
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

