from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_capability_registry, get_skill_registry
from app.registry.composite_registry import CompositeCapabilityRegistry

from app.schemas import BizDomain, SkillDetailInfo, SkillInfo
from app.services.skill_registry import SkillRegistry

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillInfo])
def list_skills(
    biz_domain: BizDomain | None = Query(default=None),
    allowed_tool: str | None = Query(default=None),
    has_human_escalation: bool | None = Query(default=None),
    capability_id: str | None = Query(default=None),
    registry: SkillRegistry = Depends(get_skill_registry),
    capability_registry: CompositeCapabilityRegistry = Depends(get_capability_registry),
) -> list[SkillInfo]:
    bound_skill_ids: list[str] | None = None
    if capability_id:
        metadata = next(
            (
                item
                for item in capability_registry.describe_capabilities()
                if item.capability_id == capability_id
            ),
            None,
        )
        if metadata is None:
            return []
        bound_skill_ids = metadata.skills
    return registry.describe_skills(
        biz_domain,
        allowed_tool=allowed_tool,
        has_human_escalation=has_human_escalation,
        skill_ids=bound_skill_ids,
    )


@router.get("/{skill_id}", response_model=SkillDetailInfo)
def get_skill(
    skill_id: str,
    registry: SkillRegistry = Depends(get_skill_registry),
) -> SkillDetailInfo:
    item = registry.describe_skill(skill_id)
    if item is None:
        raise HTTPException(status_code=404, detail="skill not found")
    return item
