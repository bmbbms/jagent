from fastapi import APIRouter, Depends, Query

from app.dependencies import get_skill_registry
from app.schemas import BizDomain, SkillInfo
from app.services.skill_registry import SkillRegistry

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillInfo])
def list_skills(
    biz_domain: BizDomain | None = Query(default=None),
    registry: SkillRegistry = Depends(get_skill_registry),
) -> list[SkillInfo]:
    return registry.describe_skills(biz_domain)
