from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_skill_registry
from app.schemas import BizDomain, SkillDetailInfo, SkillInfo
from app.services.skill_registry import SkillRegistry

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillInfo])
def list_skills(
    biz_domain: BizDomain | None = Query(default=None),
    registry: SkillRegistry = Depends(get_skill_registry),
) -> list[SkillInfo]:
    return registry.describe_skills(biz_domain)


@router.get("/{skill_id}", response_model=SkillDetailInfo)
def get_skill(
    skill_id: str,
    registry: SkillRegistry = Depends(get_skill_registry),
) -> SkillDetailInfo:
    item = registry.describe_skill(skill_id)
    if item is None:
        raise HTTPException(status_code=404, detail="skill not found")
    return item
