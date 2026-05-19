from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import (
    get_external_agent_discovery_service,
    get_manual_remote_registry,
)
from app.registry.base import CapabilityMetadata
from app.registry.manual_remote_registry import ManualRemoteCapabilityRegistry
from app.schemas import (
    ExternalAgentAddRequest,
    ExternalAgentInfo,
    ExternalAgentRegisterRequest,
    ExternalAgentUpdateRequest,
)
from app.services.external_agent_discovery import ExternalAgentDiscoveryService

router = APIRouter(prefix="/external-agents", tags=["external-agents"])


@router.post("/register", response_model=ExternalAgentInfo)
def register_external_agent(
    request: ExternalAgentRegisterRequest,
    registry: ManualRemoteCapabilityRegistry = Depends(get_manual_remote_registry),
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
            )
        )
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
    discovery_service: ExternalAgentDiscoveryService = Depends(
        get_external_agent_discovery_service
    ),
) -> ExternalAgentInfo:
    try:
        metadata = discovery_service.discover(request)
        metadata = registry.register_remote(metadata)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return _to_response(metadata)


@router.get("", response_model=list[ExternalAgentInfo])
def list_external_agents(
    registry: ManualRemoteCapabilityRegistry = Depends(get_manual_remote_registry),
) -> list[ExternalAgentInfo]:
    return [_to_response(item) for item in registry.describe_capabilities()]


@router.put("/{capability_id}", response_model=ExternalAgentInfo)
def update_external_agent(
    capability_id: str,
    request: ExternalAgentUpdateRequest,
    registry: ManualRemoteCapabilityRegistry = Depends(get_manual_remote_registry),
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
            ),
        )
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
) -> None:
    deleted = registry.unregister(capability_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"External agent not found: {capability_id}",
        )


def _to_response(metadata: CapabilityMetadata) -> ExternalAgentInfo:
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
        source=metadata.extras.get("source", "manual_remote"),
    )
