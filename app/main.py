from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes.audit import router as audit_router
from app.api.routes.approvals import router as approvals_router
from app.api.routes.capabilities import router as capabilities_router
from app.api.routes.chat import router as chat_router
from app.api.routes.evaluations import router as evaluations_router
from app.api.routes.external_agents import router as external_agents_router
from app.api.routes.health import router as health_router
from app.api.routes.home import router as home_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.skills import router as skills_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.ui import router as ui_router
from app.api.routes.workflows import router as workflows_router
from app.config import get_settings
from app.dependencies import get_approval_service, get_capability_registry, get_engine

settings = get_settings()

@asynccontextmanager
async def lifespan(_: FastAPI):
    get_engine()
    get_capability_registry()
    get_approval_service()
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
app.include_router(evaluations_router, prefix=settings.api_prefix)
app.include_router(capabilities_router, prefix=settings.api_prefix)
app.include_router(external_agents_router, prefix=settings.api_prefix)
app.include_router(skills_router, prefix=settings.api_prefix)
app.include_router(workflows_router, prefix=settings.api_prefix)
app.include_router(approvals_router, prefix=settings.api_prefix)
app.include_router(knowledge_router, prefix=settings.api_prefix)
app.include_router(tasks_router, prefix=settings.api_prefix)
app.include_router(audit_router, prefix=settings.api_prefix)
app.include_router(ui_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
