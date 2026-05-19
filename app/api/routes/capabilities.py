from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_capability_registry
from app.registry.base import CapabilityResolver
from app.schemas import BizDomain, CapabilityInfo

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


@router.get("", response_model=list[CapabilityInfo])
def list_capabilities(
    biz_domain: BizDomain | None = Query(default=None),
    source: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    requires_approval: bool | None = Query(default=None),
    transport: str | None = Query(default=None),
    registry: CapabilityResolver = Depends(get_capability_registry),
) -> list[CapabilityInfo]:
    items = registry.describe_capabilities(biz_domain)
    if source:
        if source == "external":
            items = [item for item in items if item.source != "local"]
        else:
            items = [item for item in items if item.source == source]
    if risk_level:
        items = [item for item in items if item.risk_level == risk_level]
    if requires_approval is not None:
        items = [item for item in items if item.requires_approval == requires_approval]
    if transport:
        items = [item for item in items if item.transport == transport]
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
            version=item.version,
            risk_level=item.risk_level,
            requires_approval=item.requires_approval,
            tags=item.tags,
            transport=item.transport,
            endpoint=item.endpoint,
            service_name=item.service_name,
            service_host=item.service_host,
            service_port=item.service_port,
            service_path=item.service_path,
            extras=item.extras,
        )
        for item in items
    ]


@router.get("/{capability_id}", response_model=CapabilityInfo)
def get_capability(
    capability_id: str,
    registry: CapabilityResolver = Depends(get_capability_registry),
) -> CapabilityInfo:
    item = next(
        (entry for entry in registry.describe_capabilities() if entry.capability_id == capability_id),
        None,
    )
    if item is None:
        raise HTTPException(status_code=404, detail="capability not found")
    return CapabilityInfo(
        capability_id=item.capability_id,
        capability_name=item.capability_name,
        biz_domain=item.biz_domain,
        description=item.description,
        priority=item.priority,
        triggers=item.triggers,
        skills=item.skills,
        source=item.source,
        version=item.version,
        risk_level=item.risk_level,
        requires_approval=item.requires_approval,
        tags=item.tags,
        transport=item.transport,
        endpoint=item.endpoint,
        service_name=item.service_name,
        service_host=item.service_host,
        service_port=item.service_port,
        service_path=item.service_path,
        extras=item.extras,
    )
