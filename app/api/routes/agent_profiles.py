from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_agent_profile_sync_service
from app.schemas import (
    AgentDeclaredMCPResponse,
    AgentDeclaredSkillResponse,
    AgentDeclaredWorkflowResponse,
    AgentProfileDetailResponse,
    AgentProfileResponse,
    AgentProfileSyncLogResponse,
    AgentProfileSyncResponse,
)
from app.services.agent_profile_service import AgentProfileSyncService

router = APIRouter(prefix="/agent-profiles", tags=["agent-profiles"])


@router.post("/sync", response_model=AgentProfileSyncResponse)
def sync_agent_profiles(
    service: AgentProfileSyncService = Depends(get_agent_profile_sync_service),
) -> AgentProfileSyncResponse:
    return AgentProfileSyncResponse(**service.sync_from_nacos())


@router.get("", response_model=list[AgentProfileResponse])
def list_agent_profiles(
    biz_domain: str | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    service: AgentProfileSyncService = Depends(get_agent_profile_sync_service),
) -> list[AgentProfileResponse]:
    return [_profile_to_response(item) for item in service.list_profiles(
        biz_domain=biz_domain,
        enabled=enabled,
    )]


@router.get("/sync-logs", response_model=list[AgentProfileSyncLogResponse])
def list_agent_profile_sync_logs(
    limit: int = Query(default=20, ge=1, le=100),
    service: AgentProfileSyncService = Depends(get_agent_profile_sync_service),
) -> list[AgentProfileSyncLogResponse]:
    return [_sync_log_to_response(item) for item in service.list_sync_logs(limit=limit)]


@router.get("/{agent_id}", response_model=AgentProfileDetailResponse)
def get_agent_profile(
    agent_id: str,
    service: AgentProfileSyncService = Depends(get_agent_profile_sync_service),
) -> AgentProfileDetailResponse:
    bundle = service.get_profile_bundle(agent_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="agent profile not found")
    return _bundle_to_response(bundle)


@router.get("/{agent_id}/declared-skills", response_model=list[AgentDeclaredSkillResponse])
def list_agent_declared_skills(
    agent_id: str,
    service: AgentProfileSyncService = Depends(get_agent_profile_sync_service),
) -> list[AgentDeclaredSkillResponse]:
    bundle = service.get_profile_bundle(agent_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="agent profile not found")
    return [_skill_to_response(item) for item in bundle["skills"]]


@router.get("/{agent_id}/declared-mcps", response_model=list[AgentDeclaredMCPResponse])
def list_agent_declared_mcps(
    agent_id: str,
    service: AgentProfileSyncService = Depends(get_agent_profile_sync_service),
) -> list[AgentDeclaredMCPResponse]:
    bundle = service.get_profile_bundle(agent_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="agent profile not found")
    return [_mcp_to_response(item) for item in bundle["mcps"]]


@router.get(
    "/{agent_id}/declared-workflows",
    response_model=list[AgentDeclaredWorkflowResponse],
)
def list_agent_declared_workflows(
    agent_id: str,
    service: AgentProfileSyncService = Depends(get_agent_profile_sync_service),
) -> list[AgentDeclaredWorkflowResponse]:
    bundle = service.get_profile_bundle(agent_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="agent profile not found")
    return [_workflow_to_response(item) for item in bundle["workflows"]]


def _bundle_to_response(bundle: dict) -> AgentProfileDetailResponse:
    profile = bundle["profile"]
    base = _profile_to_response(profile).model_dump()
    return AgentProfileDetailResponse(
        **base,
        raw_card=dict(profile.raw_card or {}),
        normalized_card=dict(profile.normalized_card or {}),
        declared_skills=[_skill_to_response(item) for item in bundle["skills"]],
        declared_mcps=[_mcp_to_response(item) for item in bundle["mcps"]],
        declared_workflows=[
            _workflow_to_response(item) for item in bundle["workflows"]
        ],
    )


def _profile_to_response(item) -> AgentProfileResponse:  # noqa: ANN001
    normalized_card = dict(item.normalized_card or {})
    return AgentProfileResponse(
        agent_id=item.agent_id,
        source_agent_name=item.source_agent_name,
        agent_name=item.agent_name,
        description=item.description or "",
        endpoint=item.endpoint,
        protocol=item.protocol,
        transport=item.transport,
        version=item.version,
        namespace=item.namespace,
        source=item.source,
        biz_domain=item.biz_domain,
        tags=list(item.tags or []),
        health_status=item.health_status,
        governance_status=item.governance_status,
        risk_level=item.risk_level,
        enabled=bool(item.enabled),
        declared_skill_count=int(normalized_card.get("declared_skill_count") or 0),
        declared_mcp_count=int(normalized_card.get("declared_mcp_count") or 0),
        declared_workflow_count=int(normalized_card.get("declared_workflow_count") or 0),
        last_sync_time=item.last_sync_time.isoformat() if item.last_sync_time else None,
        create_time=item.create_time.isoformat() if item.create_time else None,
        update_time=item.update_time.isoformat() if item.update_time else None,
    )


def _skill_to_response(item) -> AgentDeclaredSkillResponse:  # noqa: ANN001
    return AgentDeclaredSkillResponse(
        skill_id=item.skill_id,
        skill_name=item.skill_name,
        description=item.description or "",
        tags=list(item.tags or []),
        examples=list(item.examples or []),
        input_modes=list(item.input_modes or []),
        output_modes=list(item.output_modes or []),
        raw_payload=dict(item.raw_payload or {}),
    )


def _mcp_to_response(item) -> AgentDeclaredMCPResponse:  # noqa: ANN001
    return AgentDeclaredMCPResponse(
        mcp_id=item.mcp_id,
        mcp_name=item.mcp_name,
        description=item.description or "",
        transport=item.transport,
        endpoint=item.endpoint,
        tags=list(item.tags or []),
        raw_payload=dict(item.raw_payload or {}),
    )


def _workflow_to_response(item) -> AgentDeclaredWorkflowResponse:  # noqa: ANN001
    return AgentDeclaredWorkflowResponse(
        workflow_id=item.workflow_id,
        workflow_name=item.workflow_name,
        description=item.description or "",
        steps=list(item.steps or []),
        tags=list(item.tags or []),
        raw_payload=dict(item.raw_payload or {}),
    )


def _sync_log_to_response(item) -> AgentProfileSyncLogResponse:  # noqa: ANN001
    return AgentProfileSyncLogResponse(
        sync_id=item.sync_id,
        namespace=item.namespace,
        source=item.source,
        status=item.status,
        pulled_count=item.pulled_count,
        upserted_count=item.upserted_count,
        failed_count=item.failed_count,
        error_message=item.error_message,
        start_time=item.start_time.isoformat(),
        end_time=item.end_time.isoformat() if item.end_time else None,
    )
