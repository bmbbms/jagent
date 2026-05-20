from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_nacos_registry_service
from app.schemas import NacosRegistryOverviewResponse
from app.services.nacos_registry_service import NacosRegistryService

router = APIRouter(prefix="/nacos", tags=["nacos"])


@router.get("/overview", response_model=NacosRegistryOverviewResponse)
def get_nacos_overview(
    service: NacosRegistryService = Depends(get_nacos_registry_service),
) -> NacosRegistryOverviewResponse:
    payload = service.get_overview()
    return NacosRegistryOverviewResponse(**payload)


@router.get("/agents")
def list_nacos_agents(
    service: NacosRegistryService = Depends(get_nacos_registry_service),
):
    return service.list_agent_cards()


@router.get("/skills")
def list_nacos_skills(
    service: NacosRegistryService = Depends(get_nacos_registry_service),
):
    return service.list_skills()


@router.get("/mcp")
def list_nacos_mcp_servers(
    service: NacosRegistryService = Depends(get_nacos_registry_service),
):
    return service.list_mcp_servers()

