from fastapi import APIRouter, Depends, Query

from app.dependencies import get_capability_registry
from app.registry.base import CapabilityResolver
from app.schemas import BizDomain, CapabilityInfo

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


@router.get("", response_model=list[CapabilityInfo])
def list_capabilities(
    biz_domain: BizDomain | None = Query(default=None),
    registry: CapabilityResolver = Depends(get_capability_registry),
) -> list[CapabilityInfo]:
    return [
        CapabilityInfo(
            capability_id=item.capability_id,
            capability_name=item.capability_name,
            biz_domain=item.biz_domain,
            description=item.description,
            priority=item.priority,
            triggers=item.triggers,
            skills=item.skills,
            source=item.source,
        )
        for item in registry.describe_capabilities(biz_domain)
    ]
