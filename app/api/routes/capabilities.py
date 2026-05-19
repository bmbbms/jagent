from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_capability_registry, get_task_service
from app.registry.base import CapabilityResolver
from app.schemas import (
    AgentTaskSummaryResponse,
    BizDomain,
    CapabilityInfo,
    CapabilityOverviewResponse,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


@router.get("", response_model=list[CapabilityInfo])
def list_capabilities(
    biz_domain: BizDomain | None = Query(default=None),
    source: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    requires_approval: bool | None = Query(default=None),
    transport: str | None = Query(default=None),
    health_status: str | None = Query(default=None),
    skill_id: str | None = Query(default=None),
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
    if health_status:
        items = [
            item for item in items if (getattr(item, "health_status", None) or "unknown") == health_status
        ]
    if skill_id:
        items = [item for item in items if skill_id in item.skills]
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
            health_status=getattr(item, "health_status", None),
            last_check_time=item.last_check_time.isoformat()
            if getattr(item, "last_check_time", None)
            else None,
            last_latency_ms=getattr(item, "last_latency_ms", None),
        )
        for item in items
    ]


@router.get("/overview/summary", response_model=CapabilityOverviewResponse)
def get_capability_overview(
    registry: CapabilityResolver = Depends(get_capability_registry),
) -> CapabilityOverviewResponse:
    items = registry.describe_capabilities()
    domain_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    transport_counts: dict[str, int] = {}
    healthy_count = 0
    unhealthy_count = 0
    unknown_health_count = 0
    local_count = 0
    external_count = 0
    approval_required_count = 0
    high_risk_count = 0

    for item in items:
        domain_key = item.biz_domain.value
        source_key = "external" if item.source != "local" else "local"
        transport_key = item.transport or "unknown"
        health_key = getattr(item, "health_status", None) or "unknown"

        domain_counts[domain_key] = domain_counts.get(domain_key, 0) + 1
        source_counts[source_key] = source_counts.get(source_key, 0) + 1
        transport_counts[transport_key] = transport_counts.get(transport_key, 0) + 1

        if source_key == "local":
            local_count += 1
        else:
            external_count += 1
        if item.requires_approval:
            approval_required_count += 1
        if item.risk_level == "high":
            high_risk_count += 1
        if health_key == "healthy":
            healthy_count += 1
        elif health_key == "unhealthy":
            unhealthy_count += 1
        else:
            unknown_health_count += 1

    return CapabilityOverviewResponse(
        total=len(items),
        local_count=local_count,
        external_count=external_count,
        approval_required_count=approval_required_count,
        high_risk_count=high_risk_count,
        healthy_count=healthy_count,
        unhealthy_count=unhealthy_count,
        unknown_health_count=unknown_health_count,
        domain_counts=domain_counts,
        source_counts=source_counts,
        transport_counts=transport_counts,
    )


@router.get("/{capability_id}/recent-tasks", response_model=list[AgentTaskSummaryResponse])
def list_capability_recent_tasks(
    capability_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    registry: CapabilityResolver = Depends(get_capability_registry),
    task_service: TaskService = Depends(get_task_service),
) -> list[AgentTaskSummaryResponse]:
    item = next(
        (entry for entry in registry.describe_capabilities() if entry.capability_id == capability_id),
        None,
    )
    if item is None:
        raise HTTPException(status_code=404, detail="capability not found")
    task_list = task_service.list_tasks(
        selected_agent_id=capability_id,
        page=1,
        page_size=limit,
        sort_by="start_time",
        sort_order="desc",
    )
    return task_list.items


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
        health_status=getattr(item, "health_status", None),
        last_check_time=item.last_check_time.isoformat()
        if getattr(item, "last_check_time", None)
        else None,
        last_latency_ms=getattr(item, "last_latency_ms", None),
    )
