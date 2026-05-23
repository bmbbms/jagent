from contextlib import asynccontextmanager
import traceback

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes.agent_gateway import router as agent_gateway_router
from app.api.routes.agent_governance import router as agent_governance_router
from app.api.routes.agent_policies import router as agent_policies_router
from app.api.routes.agent_profiles import router as agent_profiles_router
from app.api.routes.audit import router as audit_router
from app.api.routes.capabilities import router as capabilities_router
from app.api.routes.chat import router as chat_router
from app.api.routes.evaluations import router as evaluations_router
from app.api.routes.external_agents import router as external_agents_router
from app.api.routes.health import router as health_router
from app.api.routes.home import router as home_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.mcp import router as mcp_router
from app.api.routes.nacos import router as nacos_router
from app.api.routes.skills import router as skills_router
from app.api.routes.service_tickets import router as service_tickets_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.ui import router as ui_router
from app.api.routes.workflows import router as workflows_router
from app.config import get_settings
from app.dependencies import (
    get_capability_registry,
    get_engine,
    get_external_capability_persistence_service,
)

settings = get_settings()

@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        print("[startup] begin initialization", flush=True)
        print("[startup] step=engine", flush=True)
        get_engine()
        print("[startup] step=engine ok", flush=True)

        print("[startup] step=capability_registry", flush=True)
        get_capability_registry()
        print("[startup] step=capability_registry ok", flush=True)

        if not settings.nacos_ai_enabled:
            print("[startup] step=restore_external_capabilities", flush=True)
            restored = get_external_capability_persistence_service().restore_into_registry()
            print(
                f"[startup] step=restore_external_capabilities ok restored={restored}",
                flush=True,
            )
        else:
            print(
                "[startup] step=restore_external_capabilities skipped in nacos mode",
                flush=True,
            )
        print("[startup] initialization complete", flush=True)
    except Exception as exc:
        print(f"[startup] initialization failed: {exc!r}", flush=True)
        traceback.print_exc()
        raise
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="0.1.0",
    description="Phase 1 MVP for the acquiring AI intelligent service system.",
    lifespan=lifespan,
)


app.include_router(home_router)
app.include_router(health_router)
app.include_router(chat_router, prefix=settings.api_prefix)
app.include_router(agent_gateway_router, prefix=settings.api_prefix)
app.include_router(agent_governance_router, prefix=settings.api_prefix)
app.include_router(agent_policies_router, prefix=settings.api_prefix)
app.include_router(agent_profiles_router, prefix=settings.api_prefix)
app.include_router(evaluations_router, prefix=settings.api_prefix)
app.include_router(capabilities_router, prefix=settings.api_prefix)
app.include_router(external_agents_router, prefix=settings.api_prefix)
app.include_router(mcp_router, prefix=settings.api_prefix)
app.include_router(nacos_router, prefix=settings.api_prefix)
app.include_router(skills_router, prefix=settings.api_prefix)
app.include_router(workflows_router, prefix=settings.api_prefix)
app.include_router(knowledge_router, prefix=settings.api_prefix)
app.include_router(service_tickets_router, prefix=settings.api_prefix)
app.include_router(tasks_router, prefix=settings.api_prefix)
app.include_router(audit_router, prefix=settings.api_prefix)
app.include_router(ui_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
