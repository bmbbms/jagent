from fastapi import APIRouter, Depends

from app.config import get_settings
from app.dependencies import get_capability_registry
from app.registry.base import CapabilityResolver
from app.schemas import HomeResponse

router = APIRouter(tags=["home"])


@router.get("/", response_model=HomeResponse)
def home(
    registry: CapabilityResolver = Depends(get_capability_registry),
) -> HomeResponse:
    settings = get_settings()
    return HomeResponse(
        app_name=settings.app_name,
        version="0.1.0",
        message="Acquiring AI minimum usable MVP is running.",
        api_prefix=settings.api_prefix,
        capabilities=registry.list_capabilities(),
        endpoints=[
            "/health",
            f"{settings.api_prefix}/chat",
            f"{settings.api_prefix}/capabilities",
            f"{settings.api_prefix}/skills",
            f"{settings.api_prefix}/external-agents",
            f"{settings.api_prefix}/mcp/tools",
            f"{settings.api_prefix}/workflows",
            f"{settings.api_prefix}/knowledge/search",
            f"{settings.api_prefix}/approvals",
            f"{settings.api_prefix}/service-tickets",
            f"{settings.api_prefix}/audit",
        ],
    )
