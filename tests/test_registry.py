from app.dependencies import get_capability_registry


def test_registry_lists_phase1_capabilities() -> None:
    registry = get_capability_registry()
    capability_ids = registry.list_capabilities()
    assert "merchant.qa" in capability_ids
    assert "operations.quota_review" in capability_ids
    assert "data_support.compliance_report" in capability_ids
