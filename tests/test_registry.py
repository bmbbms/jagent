from app.dependencies import get_capability_registry
from app.schemas import BizDomain, ChatRequest
from app.services.skill_registry import SkillRegistry


def test_registry_lists_phase1_capabilities() -> None:
    registry = get_capability_registry()
    capability_ids = registry.list_capabilities()
    assert "merchant.qa" in capability_ids
    assert "operations.quota_review" in capability_ids
    assert "data_support.compliance_report" in capability_ids


def test_registry_describes_capability_skills() -> None:
    registry = get_capability_registry()
    merchant_qa = next(
        item for item in registry.describe_capabilities() if item.capability_id == "merchant.qa"
    )
    assert merchant_qa.skills == ["merchant_qa"]


def test_registry_explains_route() -> None:
    registry = get_capability_registry()
    plan = registry.explain_route(
        ChatRequest(
            user_id="u-route",
            biz_domain=BizDomain.operations,
            message="quota review",
        )
    )
    assert plan.selected.capability_id == "operations.quota_review"
    assert "quota_review" in plan.selected.skills


def test_skill_registry_loads_skill_files() -> None:
    registry = SkillRegistry.from_directory("app/skills")
    all_skills = registry.describe_skills()
    skill_ids = {item.skill_id for item in all_skills}
    assert "merchant_qa" in skill_ids
    assert "direct_sales_data_assistant" in skill_ids
