from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import (
    get_external_capability_persistence_service,
    get_external_agent_discovery_service,
    get_external_agent_health_service,
    get_manual_remote_registry,
    get_task_service,
)
from app.registry.base import CapabilityMetadata
from app.registry.manual_remote_registry import ManualRemoteCapabilityRegistry
from app.schemas import (
    ExternalAgentAddRequest,
    ExternalAgentGovernanceOverviewResponse,
    ExternalAgentGovernanceIssueResponse,
    ExternalAgentHealthResponse,
    ExternalAgentHealthOverviewResponse,
    ExternalAgentInfo,
    ExternalAgentRegisterRequest,
    ExternalAgentUpdateRequest,
    AgentTaskSummaryResponse,
)
from app.services.external_agent_health_service import ExternalAgentHealthService
from app.services.external_agent_discovery import ExternalAgentDiscoveryService
from app.services.external_capability_persistence_service import (
    ExternalCapabilityPersistenceService,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/external-agents", tags=["external-agents"])


@router.post("/register", response_model=ExternalAgentInfo)
def register_external_agent(
    request: ExternalAgentRegisterRequest,
    registry: ManualRemoteCapabilityRegistry = Depends(get_manual_remote_registry),
    persistence_service: ExternalCapabilityPersistenceService = Depends(
        get_external_capability_persistence_service
    ),
) -> ExternalAgentInfo:
    try:
        metadata = registry.register_remote(
            CapabilityMetadata(
                capability_id=request.capability_id,
                capability_name=request.capability_name,
                biz_domain=request.biz_domain,
                description=request.description,
                priority=request.priority,
                triggers=request.triggers,
                skills=request.skills,
                version=request.version,
                risk_level=request.risk_level,
                requires_approval=request.requires_approval,
                tags=request.tags,
                transport=request.transport,
                endpoint=request.endpoint,
                service_name=request.service_name,
                service_host=request.service_host,
                service_port=request.service_port,
                service_path=request.service_path,
                extras=request.extras,
                source="manual_remote",
            )
        )
        persistence_service.save(metadata)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return _to_response(metadata)


@router.post("/discover", response_model=ExternalAgentInfo)
def discover_external_agent(
    request: ExternalAgentAddRequest,
    discovery_service: ExternalAgentDiscoveryService = Depends(
        get_external_agent_discovery_service
    ),
) -> ExternalAgentInfo:
    try:
        metadata = discovery_service.discover(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return _to_response(metadata)


@router.post("/add", response_model=ExternalAgentInfo)
def add_external_agent(
    request: ExternalAgentAddRequest,
    registry: ManualRemoteCapabilityRegistry = Depends(get_manual_remote_registry),
    persistence_service: ExternalCapabilityPersistenceService = Depends(
        get_external_capability_persistence_service
    ),
    discovery_service: ExternalAgentDiscoveryService = Depends(
        get_external_agent_discovery_service
    ),
) -> ExternalAgentInfo:
    try:
        metadata = discovery_service.discover(request)
        metadata = registry.register_remote(metadata)
        persistence_service.save(metadata)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return _to_response(metadata)


@router.get("", response_model=list[ExternalAgentInfo])
def list_external_agents(
    biz_domain: str | None = Query(default=None),
    source: str | None = Query(default=None),
    capability_id: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    requires_approval: bool | None = Query(default=None),
    transport: str | None = Query(default=None),
    health_status: str | None = Query(default=None),
    registry: ManualRemoteCapabilityRegistry = Depends(get_manual_remote_registry),
    persistence_service: ExternalCapabilityPersistenceService = Depends(
        get_external_capability_persistence_service
    ),
) -> list[ExternalAgentInfo]:
    health_map = {
        item.capability_id: item
        for item in persistence_service.list_items()
    }
    items = [
        _to_response(item, health_item=health_map.get(item.capability_id))
        for item in registry.describe_capabilities()
    ]
    if biz_domain:
        items = [item for item in items if item.biz_domain.value == biz_domain]
    if source:
        items = [item for item in items if item.source == source]
    if capability_id:
        items = [item for item in items if item.capability_id == capability_id]
    if risk_level:
        items = [item for item in items if item.risk_level == risk_level]
    if requires_approval is not None:
        items = [item for item in items if item.requires_approval == requires_approval]
    if transport:
        items = [item for item in items if item.transport == transport]
    if health_status:
        items = [item for item in items if item.health_status == health_status]
    return items


@router.get("/health-overview", response_model=ExternalAgentHealthOverviewResponse)
def get_external_agent_health_overview(
    persistence_service: ExternalCapabilityPersistenceService = Depends(
        get_external_capability_persistence_service
    ),
) -> ExternalAgentHealthOverviewResponse:
    items = persistence_service.list_items()
    total = len(items)
    healthy_count = sum(1 for item in items if (item.health_status or "unknown") == "healthy")
    unhealthy_count = sum(
        1 for item in items if (item.health_status or "unknown") == "unhealthy"
    )
    unknown_count = total - healthy_count - unhealthy_count
    return ExternalAgentHealthOverviewResponse(
        total=total,
        healthy_count=healthy_count,
        unhealthy_count=unhealthy_count,
        unknown_count=unknown_count,
    )


@router.get("/governance-overview", response_model=ExternalAgentGovernanceOverviewResponse)
def get_external_agent_governance_overview(
    registry: ManualRemoteCapabilityRegistry = Depends(get_manual_remote_registry),
    persistence_service: ExternalCapabilityPersistenceService = Depends(
        get_external_capability_persistence_service
    ),
) -> ExternalAgentGovernanceOverviewResponse:
    health_map = {item.capability_id: item for item in persistence_service.list_items()}
    items = [
        _to_response(item, health_item=health_map.get(item.capability_id))
        for item in registry.describe_capabilities()
    ]
    source_counts: dict[str, int] = {}
    transport_counts: dict[str, int] = {}
    domain_counts: dict[str, int] = {}
    healthy_count = 0
    unhealthy_count = 0
    unknown_count = 0
    approval_required_count = 0
    high_risk_count = 0
    degraded_count = 0
    blocked_count = 0
    slow_count = 0

    for item in items:
        source_counts[item.source] = source_counts.get(item.source, 0) + 1
        transport_counts[item.transport] = transport_counts.get(item.transport, 0) + 1
        domain_key = item.biz_domain.value
        domain_counts[domain_key] = domain_counts.get(domain_key, 0) + 1

        if item.health_status == "healthy":
            healthy_count += 1
        elif item.health_status == "unhealthy":
            unhealthy_count += 1
        else:
            unknown_count += 1
        if item.requires_approval:
            approval_required_count += 1
        if item.risk_level == "high":
            high_risk_count += 1
        if item.governance_status == "degraded":
            degraded_count += 1
        if item.governance_status == "blocked":
            blocked_count += 1
        if item.last_latency_ms is not None and item.last_latency_ms >= 3000:
            slow_count += 1

    return ExternalAgentGovernanceOverviewResponse(
        total=len(items),
        healthy_count=healthy_count,
        unhealthy_count=unhealthy_count,
        unknown_count=unknown_count,
        approval_required_count=approval_required_count,
        high_risk_count=high_risk_count,
        degraded_count=degraded_count,
        blocked_count=blocked_count,
        slow_count=slow_count,
        source_counts=source_counts,
        transport_counts=transport_counts,
        domain_counts=domain_counts,
    )


@router.get("/governance-issues", response_model=list[ExternalAgentGovernanceIssueResponse])
def list_external_agent_governance_issues(
    governance_status: str | None = Query(default=None),
    biz_domain: str | None = Query(default=None),
    health_status: str | None = Query(default=None),
    source: str | None = Query(default=None),
    transport: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    min_consecutive_failures: int = Query(default=0, ge=0),
    latency_ms_from: int | None = Query(default=None, ge=0),
    registry: ManualRemoteCapabilityRegistry = Depends(get_manual_remote_registry),
    persistence_service: ExternalCapabilityPersistenceService = Depends(
        get_external_capability_persistence_service
    ),
    health_service: ExternalAgentHealthService = Depends(get_external_agent_health_service),
) -> list[ExternalAgentGovernanceIssueResponse]:
    health_map = {item.capability_id: item for item in persistence_service.list_items()}
    issues: list[ExternalAgentGovernanceIssueResponse] = []
    for metadata in registry.describe_capabilities():
        health_item = health_map.get(metadata.capability_id)
        response = _to_response(metadata, health_item=health_item)
        health = health_service.get_health(metadata.capability_id)
        if health is None:
            continue
        if health.governance_status == "healthy":
            continue
        issue_severity = _resolve_governance_issue_severity(health)
        if governance_status and health.governance_status != governance_status:
            continue
        if biz_domain and response.biz_domain.value != biz_domain:
            continue
        if health_status and response.health_status != health_status:
            continue
        if source and response.source != source:
            continue
        if transport and response.transport != transport:
            continue
        if severity and issue_severity != severity:
            continue
        if int(health.consecutive_failures or 0) < min_consecutive_failures:
            continue
        if latency_ms_from is not None and int(health.last_latency_ms or 0) < latency_ms_from:
            continue
        issues.append(
            ExternalAgentGovernanceIssueResponse(
                capability_id=response.capability_id,
                capability_name=response.capability_name,
                biz_domain=response.biz_domain,
                source=response.source,
                transport=response.transport,
                risk_level=response.risk_level,
                requires_approval=response.requires_approval,
                health_status=response.health_status,
                governance_status=health.governance_status,
                severity=issue_severity,
                consecutive_failures=health.consecutive_failures,
                last_latency_ms=health.last_latency_ms,
                last_check_time=health.last_check_time,
                last_error=health.last_error,
                reasons=health.governance_reasons,
                recommended_action=health.recommended_action,
                target_ui=f"/ui/external-agents?capability_id={response.capability_id}",
                target_api=f"/api/external-agents/{response.capability_id}/health",
            )
        )
    issues.sort(
        key=lambda item: (
            0 if item.severity == "critical" else 1 if item.severity == "high" else 2,
            -item.consecutive_failures,
            -(item.last_latency_ms or 0),
            item.capability_id,
        )
    )
    return issues


def _resolve_governance_issue_severity(health: ExternalAgentHealthResponse) -> str:
    if health.governance_status == "blocked":
        return "critical"
    if int(health.consecutive_failures or 0) >= 2 or int(health.last_latency_ms or 0) >= 3000:
        return "high"
    return "medium"


@router.put("/{capability_id}", response_model=ExternalAgentInfo)
def update_external_agent(
    capability_id: str,
    request: ExternalAgentUpdateRequest,
    registry: ManualRemoteCapabilityRegistry = Depends(get_manual_remote_registry),
    persistence_service: ExternalCapabilityPersistenceService = Depends(
        get_external_capability_persistence_service
    ),
) -> ExternalAgentInfo:
    try:
        metadata = registry.update_remote(
            capability_id,
            CapabilityMetadata(
                capability_id=capability_id,
                capability_name=request.capability_name,
                biz_domain=request.biz_domain,
                description=request.description,
                priority=request.priority,
                triggers=request.triggers,
                skills=request.skills,
                version=request.version,
                risk_level=request.risk_level,
                requires_approval=request.requires_approval,
                tags=request.tags,
                transport=request.transport,
                endpoint=request.endpoint,
                service_name=request.service_name,
                service_host=request.service_host,
                service_port=request.service_port,
                service_path=request.service_path,
                extras=request.extras,
                source="manual_remote",
            ),
        )
        persistence_service.save(metadata)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return _to_response(metadata)


@router.delete("/{capability_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_external_agent(
    capability_id: str,
    registry: ManualRemoteCapabilityRegistry = Depends(get_manual_remote_registry),
    persistence_service: ExternalCapabilityPersistenceService = Depends(
        get_external_capability_persistence_service
    ),
) -> None:
    deleted = registry.unregister(capability_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"External agent not found: {capability_id}",
        )
    persistence_service.delete(capability_id)


@router.get("/{capability_id}/health", response_model=ExternalAgentHealthResponse)
def get_external_agent_health(
    capability_id: str,
    health_service: ExternalAgentHealthService = Depends(get_external_agent_health_service),
) -> ExternalAgentHealthResponse:
    health = health_service.get_health(capability_id)
    if health is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"External agent not found: {capability_id}",
        )
    return health


@router.post("/{capability_id}/health-check", response_model=ExternalAgentHealthResponse)
def check_external_agent_health(
    capability_id: str,
    health_service: ExternalAgentHealthService = Depends(get_external_agent_health_service),
) -> ExternalAgentHealthResponse:
    health = health_service.check_health(capability_id)
    if health is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"External agent not found: {capability_id}",
        )
    return health


@router.get("/{capability_id}/recent-tasks", response_model=list[AgentTaskSummaryResponse])
def list_external_agent_recent_tasks(
    capability_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    task_service: TaskService = Depends(get_task_service),
) -> list[AgentTaskSummaryResponse]:
    task_list = task_service.list_tasks(
        selected_agent_id=capability_id,
        page=1,
        page_size=limit,
        sort_by="start_time",
        sort_order="desc",
    )
    return task_list.items


def _to_response(
    metadata: CapabilityMetadata,
    *,
    health_item=None,
) -> ExternalAgentInfo:
    return ExternalAgentInfo(
        capability_id=metadata.capability_id,
        capability_name=metadata.capability_name,
        biz_domain=metadata.biz_domain,
        description=metadata.description,
        priority=metadata.priority,
        triggers=metadata.triggers,
        skills=metadata.skills,
        version=metadata.version,
        risk_level=metadata.risk_level,
        requires_approval=metadata.requires_approval,
        tags=metadata.tags,
        transport=metadata.transport,
        endpoint=metadata.endpoint,
        service_name=metadata.service_name,
        service_host=metadata.service_host,
        service_port=metadata.service_port,
        service_path=metadata.service_path,
        extras=metadata.extras,
        source=metadata.source,
        health_status=getattr(health_item, "health_status", "unknown") or "unknown",
        last_check_time=getattr(health_item, "last_check_time", None).isoformat()
        if getattr(health_item, "last_check_time", None)
        else None,
        last_success_time=getattr(health_item, "last_success_time", None).isoformat()
        if getattr(health_item, "last_success_time", None)
        else None,
        last_failure_time=getattr(health_item, "last_failure_time", None).isoformat()
        if getattr(health_item, "last_failure_time", None)
        else None,
        last_error=getattr(health_item, "last_error", None),
        consecutive_failures=int(getattr(health_item, "consecutive_failures", 0) or 0),
        last_latency_ms=getattr(health_item, "last_latency_ms", None),
        governance_status=ExternalAgentHealthService._build_governance_status(health_item)[0]
        if health_item is not None
        else "healthy",
        governance_reasons=ExternalAgentHealthService._build_governance_status(health_item)[1]
        if health_item is not None
        else [],
        recommended_action=ExternalAgentHealthService._build_governance_status(health_item)[2]
        if health_item is not None
        else "当前治理状态稳定，可继续观察。",
    )
